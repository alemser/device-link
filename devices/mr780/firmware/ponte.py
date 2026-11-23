"""The MR 780 bridge: the program main.py imports when the Pico starts.

Wi-Fi without a cable (wifi.py), updates over Wi-Fi (ota.py), /device, the remote-control keys by wire (control.py,
ir.py), on/standby from the LIGA wire (power.py) and the rest of /state from the display (display.py, screen.py): the
two lines, the input, the volume, mute and the warm-up. The read-only phase: nothing is ever written to the display.

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
        self.selector = None            # inputs.Selector: the input, from the display (seen()) or tracked presses
        self.display = None             # display.Display, once started

    def to_dict(self):
        sel = self.selector
        scr = self.display.screen if self.display else None
        return {"power": self.power.state if self.power else None,
                "warmup_s": scr.warmup_s if scr else None, "volume_db": scr.volume_db if scr else None,
                "muted": scr.muted if scr else None,
                "input": sel.name() if sel else None, "input_id": sel.current if sel else None,
                "lcd": list(scr.lines) if scr and scr.seen else [],
                "updated_at": time.ticks_ms(), "version": self.version}


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


def display_changed():
    """The display's text changed: the input it names (if any) goes to the selector, the rest is read in to_dict()."""
    state.selector.seen(state.display.screen.input_id)
    state_changed()


def _power():
    from power import Power
    return Power(on_change=state_changed)


def _display():
    from display import Display
    return Display(on_change=display_changed)


def start(what, make):
    """make(), or None if it fails: the bridge must stay reachable for updates regardless."""
    try:
        return make()
    except Exception as e:
        print(what + ":", repr(e))
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
    state.power = start("power", _power)
    state.display = start("display", _display)
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
    for part in (state.power, state.display):
        if part:
            asyncio.create_task(part.task())
    while True:
        await asyncio.sleep(60)


asyncio.run(main())
