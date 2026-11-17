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
        self.commands = []
        self.busy = False

    def sending(self):
        return self.busy

    def send(self, key):
        self.send_command(ir_codes.COMMANDS[key])

    def send_command(self, command):
        self.commands.append(command)

    def status(self):
        return {"sent": len(self.commands), "sending": self.busy}


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
assert control.check("play", True) == "busy"
assert control.check("pause", False) == "unknown key"    # no published code yet (docs/research.md)
assert control.check(None, False) == "unknown key"

assert control.parse_code("05") == 0x05
assert control.parse_code("0x40") == 0x40
assert control.parse_code("ff") == 0xFF
for bad in (None, "", "100", "0x", "zz", "-1"):
    assert control.parse_code(bad) is None, bad

remote = FakeRemote()
ctl = control.Control(FakeState(), remote)

# One key through /control: it goes out, and the answer is the state.
assert call(ctl, "POST", "/control?target=key&name=play") == (200, {"power": None, "version": 0})
assert remote.commands == [0x00]

# The same key through /ir/send: the answer is the line's status.
assert call(ctl, "POST", "/ir/send?cmd=stop") == (200, {"sent": 2, "sending": False})
# Any command byte, to find the unknown ones.
assert call(ctl, "POST", "/ir/send?code=05") == (200, {"sent": 3, "sending": False})
assert remote.commands == [0x00, 0x03, 0x05]
assert call(ctl, "GET", "/ir") == (200, {"sent": 3, "sending": False})

# Nothing goes out when the request is wrong or the line is busy.
assert call(ctl, "POST", "/control?target=key&name=nope") == (400, {"error": "unknown key"})
assert call(ctl, "POST", "/control?target=key") == (400, {"error": "unknown key"})
assert call(ctl, "POST", "/control?target=volume&dir=up") == (400, {"error": "unknown target"})
assert call(ctl, "POST", "/control?target=key&code=05") == (400, {"error": "unknown key"})   # code= only on /ir/send
assert call(ctl, "POST", "/ir/send") == (400, {"error": "unknown key"})
assert call(ctl, "POST", "/ir/send?code=xyz") == (400, {"error": "bad code"})
remote.busy = True
assert call(ctl, "POST", "/control?target=key&name=stop") == (400, {"error": "busy"})
assert call(ctl, "POST", "/ir/send?code=06") == (400, {"error": "busy"})
assert call(ctl, "GET", "/control?target=key&name=stop")[0] == 404
assert remote.commands == [0x00, 0x03, 0x05]

print("all good")
