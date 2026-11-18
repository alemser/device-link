#!/usr/bin/env python3
"""Tests the network commands (firmware/control.py) on the computer, with a fake IR line.

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


assert control.check("next_input", False) is None
assert control.check("next_input", True) == "busy"
assert control.check("power_toggle", False) is None              # an IR key on the MR 780, unlike the KX-393
assert control.check("direct", False) == "unknown key"           # a panel button, not on the remote
assert control.check(None, False) == "unknown key"

assert control.parse_code("1A") == 0x1A
assert control.parse_code("0x40") == 0x40
assert control.parse_code("ff") == 0xFF
for bad in (None, "", "100", "0x", "zz", "-1"):
    assert control.parse_code(bad) is None, bad

remote = FakeRemote()
ctl = control.Control(FakeState(), remote)
A = ir_codes.ADDRESS

# One key through /control: it goes out as IR, and the answer is the state.
assert call(ctl, "POST", "/control?target=key&name=next_input") == (200, {"power": None, "version": 0})
assert call(ctl, "POST", "/control?target=key&name=volume_down") == (200, {"power": None, "version": 0})
assert remote.out == 0   # /control answered only once the key was out (contract: when done)
assert remote.sent == [(A, 0x1A), (A, 0x1F)]

# /ir/send: a key, or any byte at the amp's address or a given one.
assert call(ctl, "POST", "/ir/send?cmd=prev_input") == (200, {"sent": 3, "sending": False})
assert call(ctl, "POST", "/ir/send?code=12") == (200, {"sent": 4, "sending": False})
assert call(ctl, "POST", "/ir/send?code=12&address=41") == (200, {"sent": 5, "sending": False})
assert remote.sent[2:] == [(A, 0x1E), (A, 0x12), (0x41, 0x12)]
assert call(ctl, "GET", "/ir") == (200, {"sent": 5, "sending": False})

# Nothing goes out when the request is wrong or the line is busy.
assert call(ctl, "POST", "/control?target=key&name=nope") == (400, {"error": "unknown key"})
assert call(ctl, "POST", "/control?target=key") == (400, {"error": "unknown key"})
assert call(ctl, "POST", "/control?target=volume&dir=up") == (400, {"error": "unknown target"})
assert call(ctl, "POST", "/ir/send") == (400, {"error": "unknown key"})
assert call(ctl, "POST", "/ir/send?code=xyz") == (400, {"error": "bad code"})
assert call(ctl, "POST", "/ir/send?code=12&address=400") == (400, {"error": "bad code"})
remote.busy = True
assert call(ctl, "POST", "/control?target=key&name=next_input") == (400, {"error": "busy"})
assert call(ctl, "POST", "/ir/send?code=12") == (400, {"error": "busy"})
assert call(ctl, "GET", "/control?target=key&name=next_input")[0] == 404
assert len(remote.sent) == 5

# The input select: select_<id> goes to the selector; next/prev sent alone are reported to it for the tracking.
class FakeSelector:
    def __init__(self):
        self.busy = False
        self.selected, self.raws = [], []

    async def select(self, input_id):
        self.selected.append(input_id)
        return None if input_id == "cd" else "unknown input"

    def raw(self, key):
        self.raws.append(key)


sel, remote = FakeSelector(), FakeRemote()
ctl = control.Control(FakeState(), remote, sel)
assert call(ctl, "POST", "/control?target=key&name=select_cd")[0] == 200
assert call(ctl, "POST", "/control?target=key&name=select_nope") == (400, {"error": "unknown input"})
assert sel.selected == ["cd", "nope"] and remote.sent == []
assert call(ctl, "POST", "/control?target=key&name=next_input")[0] == 200
assert call(ctl, "POST", "/control?target=key&name=volume_up")[0] == 200
assert sel.raws == ["next_input"]
sel.busy = True
assert call(ctl, "POST", "/control?target=key&name=volume_up") == (400, {"error": "busy"})
# Without a selector, select_ keys are just unknown.
assert call(control.Control(FakeState(), FakeRemote()), "POST", "/control?target=key&name=select_cd") == (
    400, {"error": "unknown key"})

print("all good")
