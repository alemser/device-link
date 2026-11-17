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
import web       # noqa: E402  (the base's web.py runs on the computer: it only uses json and asyncio)


class FakeRemote:
    def __init__(self):
        self.keys = []
        self.busy = False

    def sending(self):
        return self.busy

    def send(self, key):
        self.keys.append(key)

    def status(self):
        return {"sent": len(self.keys), "sending": self.busy}


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
assert control.check("power_toggle", False) == "unknown key"    # the CD-S300 has no power key
assert control.check(None, False) == "unknown key"

remote = FakeRemote()
ctl = control.Control(FakeState(), remote)

# One key through /control: it goes out, and the answer is the state.
assert call(ctl, "POST", "/control?target=key&name=play") == (200, {"power": None, "version": 0})
assert remote.keys == ["play"]

# The same key through /ir/send: the answer is the line's status.
assert call(ctl, "POST", "/ir/send?cmd=next") == (200, {"sent": 2, "sending": False})
assert remote.keys == ["play", "next"]
assert call(ctl, "GET", "/ir") == (200, {"sent": 2, "sending": False})

# Nothing goes out when the request is wrong or the line is busy.
assert call(ctl, "POST", "/control?target=key&name=nope") == (400, {"error": "unknown key"})
assert call(ctl, "POST", "/control?target=key") == (400, {"error": "unknown key"})
assert call(ctl, "POST", "/control?target=volume&dir=up") == (400, {"error": "unknown target"})
assert call(ctl, "POST", "/ir/send") == (400, {"error": "unknown key"})
remote.busy = True
assert call(ctl, "POST", "/control?target=key&name=stop") == (400, {"error": "busy"})
assert call(ctl, "GET", "/control?target=key&name=stop")[0] == 404
assert remote.keys == ["play", "next"]

print("all good")
