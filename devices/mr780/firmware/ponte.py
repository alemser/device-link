"""The MR 780 bridge: the program main.py imports when the Pico starts.

Today (2026-11-09), without the amp: cable-free Wi-Fi setup (wifi.py), updates over Wi-Fi (ota.py) and /device.
/state exists, but with everything unknown (null): reading the display and controlling the amp come after the
measurements and the captures (docs/plan.md). Even so, the Pico can already go inside the amp and get the rest over
Wi-Fi.

Run from the computer:  .venv/bin/mpremote run firmware/ponte.py   (or install and reset: see the README)
"""

import time
import asyncio

import device
import ota
from web import Publisher
from wifi import Wifi


class State:
    """The amp's state in the contract (GET /state and /events). null = not known yet."""

    def __init__(self):
        self.version = 0

    def to_dict(self):
        return {"power": None, "volume_db": None, "input": None, "input_id": None, "lcd": [],
                "updated_at": time.ticks_ms(), "version": self.version}


state = State()
net = Wifi(model=device.NAME, hostname=device.NAME, prefix=device.NAME.upper(),
           label=device.MODEL, kind=device.KIND, api=device.API)
device.net = net
pub = None
wifi_ok = False


def wifi_result(ok, info):
    global wifi_ok
    wifi_ok = ok
    if not ok:
        print("Wi-Fi:", info)


async def confirm_update():
    """A new version on trial (ota.py): confirm it once it proves healthy. Without that, main.py goes back to the
    previous version. Healthy = Wi-Fi connected and the server answered someone (tools/enviar.py asks every 2 s), for
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
    pub = Publisher(state, routes={"/update": ota.handle, "/device": device.handle,
                                   "/wifi": net.handle, "/": net.page})
    asyncio.create_task(net.task(wifi_result))
    await asyncio.sleep(0.1)            # Wi-Fi comes up before the server opens its socket
    await pub.serve()
    asyncio.create_task(confirm_update())
    while True:
        await asyncio.sleep(60)


asyncio.run(main())
