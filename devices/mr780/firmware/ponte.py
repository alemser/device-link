"""The MR 780 bridge: the program main.py imports when the Pico starts.

Wi-Fi without a cable (wifi.py), updates over Wi-Fi (ota.py), /device and, since 2026-11-18, the remote-control keys
by wire (control.py, ir.py) and on/standby from the LIGA wire (power.py). The rest of /state stays null until the
display reader exists (docs/plan.md). The read-only phase: nothing is ever written to the display.

Pins (the same harness serves the logic analyzer, channel = GP - 1): A, B, C (the VFD's data) on GP2, GP3, GP4;
LIGA on GP5; IR on GP6; the Pico powered on VSYS from the 5V wire (flat pin 18).

Run from the computer:  .venv/bin/mpremote run firmware/ponte.py   (or install and reset: see the README)
"""

import time
import asyncio

import device
import ota
from control import Control
from ir import Remote
from web import Publisher
from wifi import Wifi


class State:
    """The amp's state in the contract (GET /state and /events). null = not known yet."""

    def __init__(self):
        self.version = 0
        self.power = None               # power.Power, once started
        self.selector = None            # inputs.Selector: the tracked input (plan B, not read from the amp)

    def to_dict(self):
        sel = self.selector
        return {"power": self.power.state if self.power else None,
                "warmup_s": self.power.warmup if self.power else None, "volume_db": None,
                "input": sel.name() if sel else None, "input_id": sel.current if sel else None,
                "input_tracked": True, "lcd": [], "updated_at": time.ticks_ms(), "version": self.version}


def state_changed():
    state.version += 1
    if pub is not None:
        pub.changed()


state = State()
net = Wifi(model=device.NAME, hostname=device.NAME, prefix=device.NAME.upper(),
           label=device.MODEL, kind=device.KIND, api=device.API)
device.net = net
remote = Remote()                       # early: until then GP6 has the RP2350's pull-down, which loads the IR line
from inputs import Selector             # noqa: E402
state.selector = Selector(remote, on_change=state_changed)
control = Control(state, remote, state.selector)
pub = None
wifi_ok = False


def wifi_result(ok, info):
    global wifi_ok
    wifi_ok = ok
    if not ok:
        print("Wi-Fi:", info)


def power_changed():
    state.version += 1
    if pub is not None:
        pub.changed()


def start_power():
    """The LIGA reader, or None if it fails to start: the bridge must stay reachable for updates regardless."""
    try:
        from power import Power
        return Power(on_change=power_changed)
    except Exception as e:
        print("power:", repr(e))
        return None


async def confirm_update():
    """A new version on trial (ota.py): confirm it once it proves healthy. Without that, main.py goes back to the
    previous version. Healthy = Wi-Fi connected and the server answered someone (tools/send.py asks every 2 s), for
    20 s in a row."""
    if not ota.in_trial():
        return
    start = time.ticks_ms()
    while True:
        await asyncio.sleep(2)
        if not (net.sta is not None and net.sta.isconnected() and pub.served):
            start = time.ticks_ms()
        elif time.ticks_diff(time.ticks_ms(), start) > 20000:
            ota.confirm()
            return


async def main():
    global pub
    state.power = start_power()
    from capture import Capture     # the display lines, raw, for working out the protocol (tools/bus_capture.py)
    capture = Capture(control.remote)
    pub = Publisher(state, routes={"/update": ota.handle, "/device": device.handle,
                                   "/control": control.handle, "/ir": control.handle,
                                   "/capture": capture.handle, "/input": state.selector.handle,
                                   "/wifi": net.handle, "/": net.page})
    asyncio.create_task(net.task(wifi_result))
    await asyncio.sleep(0.1)            # Wi-Fi comes up before the server opens its socket
    await pub.serve()
    asyncio.create_task(confirm_update())
    if state.power:
        asyncio.create_task(state.power.task())
    while True:
        await asyncio.sleep(60)


asyncio.run(main())
