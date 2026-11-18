"""The CD-S300 bridge: the program main.py imports when the Pico starts.

Wi-Fi without a cable (wifi.py), updates over Wi-Fi (ota.py), /device, the remote-control keys (control.py, ir.py) and,
since 2026-11-16, the display reader (display.py, vfd.py): /state carries the 12 characters on the display and the
raw icon bits; /display shows the reader's full view, for mapping which bit is which icon (docs/plan.md).

Run from the computer:  .venv/bin/mpremote run firmware/ponte.py   (or install and reset: see README)
"""

import time
import asyncio

import device
import ota
from control import Control
from ir import Remote
from vfd import Player
from web import Publisher
from wifi import Wifi


class State:
    """The device state in the contract (GET /state and /events). null = not known yet."""

    def __init__(self):
        self.version = 0
        self.display = None
        self.player = Player()

    def to_dict(self):
        """api 2 proposal (device-link docs/contract-v2.md): transport, media and disc groups."""
        d = {"power": None, "lcd": [], "updated_at": time.ticks_ms(), "version": self.version}
        if self.display is not None and self.display.alive():
            p = self.player.state
            d["power"] = "on"
            d["lcd"] = [self.display.screen.text()]
            d["icons"] = self.display.screen.icons().hex()
            d["transport"] = p["transport"]
            d["media"] = {"track": p["track"], "elapsed_s": p["elapsed_s"]}
            d["disc"] = {"tracks": p["tracks"], "total_s": p["total_s"]}
        return d


state = State()
net = Wifi(model=device.NAME, hostname=device.NAME, prefix=device.NAME.upper(),
           label=device.MODEL, kind=device.KIND, api=device.API)
control = Control(state, Remote())      # early: until then GP6 has the RP2350's pull-down, which loads the IR line
pub = None
wifi_ok = False


def wifi_result(ok, info):
    global wifi_ok
    wifi_ok = ok
    if not ok:
        print("Wi-Fi:", info)


def display_changed():
    s = state.display.screen
    state.player.update(s.text(), s.lit())
    state.version += 1
    if pub is not None:
        pub.changed()


def start_display():
    """The display reader, or None if it fails to start: the bridge must stay reachable for updates regardless."""
    try:
        from display import Display
        return Display(on_change=display_changed)
    except Exception as e:
        print("display:", repr(e))
        return None


async def confirm_update():
    """A new version on trial (ota.py): confirm it once it proves healthy, or main.py rolls back to the previous one.
    Healthy = Wi-Fi connected and the server answered someone (tools/send.py asks every 2 s), for 20 s in a row."""
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


async def not_found(req, writer):
    import web
    await web.not_found(writer, "display reader not running")


async def main():
    global pub
    state.display = start_display()
    pub = Publisher(state, routes={"/update": ota.handle, "/device": device.handle,
                                   "/control": control.handle, "/ir": control.handle,
                                   "/display": state.display.handle if state.display else not_found,
                                   "/wifi": net.handle, "/": net.page})
    asyncio.create_task(net.task(wifi_result))
    await asyncio.sleep(0.1)            # Wi-Fi comes up before the server opens its socket
    await pub.serve()
    asyncio.create_task(confirm_update())
    if state.display:
        asyncio.create_task(state.display.task())
    while True:
        await asyncio.sleep(60)


asyncio.run(main())
