"""The KX-393 bridge: the program main.py imports when the Pico starts.

Wi-Fi without a cable (wifi.py), updates over Wi-Fi (ota.py), /device and the remote-control keys (control.py, ir.py).
The state reader comes later, once the service manual and the photos say where to read the state from (docs/plan.md).

Run from the computer:  .venv/bin/mpremote run firmware/ponte.py   (or install and reset: see README)
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
    """The device state in the contract (GET /state and /events). null = not known yet."""

    def __init__(self):
        self.version = 0

    def to_dict(self):
        # Without a state reader nothing is known, not even power: whether the Pico stays on in standby is still open.
        return {"power": None, "updated_at": time.ticks_ms(), "version": self.version}


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


async def confirm_update():
    """A new version on trial (ota.py): confirm it once it proves healthy, or main.py rolls back to the previous one.
    Healthy = Wi-Fi connected and the server answered someone (tools/enviar.py asks every 2 s), for 20 s in a row."""
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
                                   "/control": control.handle, "/ir": control.handle,
                                   "/wifi": net.handle, "/": net.page})
    asyncio.create_task(net.task(wifi_result))
    await asyncio.sleep(0.1)            # Wi-Fi comes up before the server opens its socket
    await pub.serve()
    asyncio.create_task(confirm_update())
    while True:
        await asyncio.sleep(60)


asyncio.run(main())
