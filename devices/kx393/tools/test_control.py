#!/usr/bin/env python3
"""Tests the network commands (firmware/control.py) on the computer, with a fake IR line and a fake panel.

    python3 tools/test_control.py
"""

import asyncio
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import control   # noqa: E402
import ir_codes  # noqa: E402
import web       # noqa: E402  (the base's web.py runs on the computer: it only uses json and asyncio)


class FakeRemote:
    def __init__(self):
        self.sent = []          # (address, command)
        self.busy = False
        self.out = 0            # polls of sending() until the last key is out

    def sending(self):
        if self.out:
            self.out -= 1
            return True
        return self.busy

    def send(self, key):
        self.send_command(ir_codes.COMMANDS[key])

    def send_command(self, command, address=ir_codes.ADDRESS):
        self.out = 3
        self.sent.append((address, command))

    def status(self):
        return {"sent": len(self.sent), "sending": self.busy}


class FakePanel:
    def __init__(self):
        self.pressing = False
        self.presses = 0

    async def press_power(self):
        self.presses += 1


class FakeState:
    def to_dict(self):
        return {"power": None, "version": 0}


class FakeWriter:
    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data

    async def drain(self):
        pass


def call(ctl, method, path):
    """(status, body) of a request, as web.Publisher hands it to the route."""
    writer = FakeWriter()
    asyncio.run(ctl.handle(web.Request(method, path, {}, None), writer))
    head, _, body = writer.data.partition(b"\r\n\r\n")
    status = int(head.split()[1])
    return status, (json.loads(body) if b"application/json" in head else body)


assert control.check("play", False) is None
assert control.check("power_toggle", False) is None
assert control.check("play", True) == "busy"
assert control.check("pause", False) == "unknown key"    # the KX-393 has no pause key: REC/PAUSE is "record"
assert control.check(None, False) == "unknown key"

assert control.parse_code("05") == 0x05
assert control.parse_code("0x7A") == 0x7A
assert control.parse_code("ff") == 0xFF
for bad in (None, "", "100", "0x", "zz", "-1"):
    assert control.parse_code(bad) is None, bad

remote, panel = FakeRemote(), FakePanel()
ctl = control.Control(FakeState(), remote, panel)
M = ir_codes.ADDRESS

# One key through /control: it goes out as IR, and the answer is the state.
assert call(ctl, "POST", "/control?target=key&name=play") == (200, {"power": None, "version": 0})
assert call(ctl, "POST", "/control?target=key&name=counter_reset") == (200, {"power": None, "version": 0})
assert remote.out == 0   # /control answered only once the key was out (contract: when done)
assert remote.sent == [(M, 0x00), (M, 0x0D)]

# power_toggle presses the panel key, not IR.
assert call(ctl, "POST", "/control?target=key&name=power_toggle") == (200, {"power": None, "version": 0})
assert panel.presses == 1 and len(remote.sent) == 2

# /ir/send: a key, or any byte at the default or a given address.
assert call(ctl, "POST", "/ir/send?cmd=stop") == (200, {"sent": 3, "sending": False})
assert call(ctl, "POST", "/ir/send?code=00") == (200, {"sent": 4, "sending": False})
assert call(ctl, "POST", "/ir/send?code=00&address=7A") == (200, {"sent": 5, "sending": False})
assert remote.sent[2:] == [(M, 0x03), (M, 0x00), (0x7A, 0x00)]
assert call(ctl, "GET", "/ir") == (200, {"sent": 5, "sending": False})

# Nothing goes out when the request is wrong or something is busy.
assert call(ctl, "POST", "/control?target=key&name=nope") == (400, {"error": "unknown key"})
assert call(ctl, "POST", "/control?target=key") == (400, {"error": "unknown key"})
assert call(ctl, "POST", "/control?target=volume&dir=up") == (400, {"error": "unknown target"})
assert call(ctl, "POST", "/ir/send?cmd=power_toggle") == (400, {"error": "unknown key"})   # not an IR key
assert call(ctl, "POST", "/ir/send") == (400, {"error": "unknown key"})
assert call(ctl, "POST", "/ir/send?code=xyz") == (400, {"error": "bad code"})
assert call(ctl, "POST", "/ir/send?code=00&address=7AA") == (400, {"error": "bad code"})
remote.busy = True
assert call(ctl, "POST", "/control?target=key&name=stop") == (400, {"error": "busy"})
assert call(ctl, "POST", "/control?target=key&name=power_toggle") == (400, {"error": "busy"})
assert call(ctl, "POST", "/ir/send?code=06") == (400, {"error": "busy"})
remote.busy, panel.pressing = False, True
assert call(ctl, "POST", "/control?target=key&name=play") == (400, {"error": "busy"})
assert call(ctl, "GET", "/control?target=key&name=stop")[0] == 404
assert len(remote.sent) == 5 and panel.presses == 1

# Without a panel (not wired), power_toggle is unknown rather than silently ignored.
bare = control.Control(FakeState(), FakeRemote())
assert call(bare, "POST", "/control?target=key&name=power_toggle") == (400, {"error": "unknown key"})

print("all good")
