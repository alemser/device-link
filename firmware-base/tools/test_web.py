"""The HTTP server's request parsing, the description route and waits.until, on the computer.

This file belongs to the shared base (firmware-base/): change it there and copy it with copy_base.py --all, never here.

    python3 tools/test_web.py
"""

import os
import sys
import json
import types
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "firmware"))

import web      # noqa: E402  (only json, asyncio and listeners)
import waits    # noqa: E402

# --- the query, as the app sends it ---
assert web.Request("POST", "/control?target=key&name=play", {}, None).query == {"target": "key", "name": "play"}
assert web.Request("GET", "/x?a=b%20c+d&e=%C3%A9&f=100%&g", {}, None).query == {"a": "b c d", "e": "é", "f": "100%",
                                                                              "g": ""}
assert web.Request("GET", "/x", {}, None).query == {}
assert web.unquote("%zz%4") == "%zz%4"          # bad escapes stay as they are

# --- hex bytes (/ir/send?code=XX) ---
assert web.hex_byte("05") == 5 and web.hex_byte("0x7A") == 0x7A and web.hex_byte("f") == 15
assert all(web.hex_byte(t) is None for t in (None, "", "0x", "123", "g1", "-1"))

# --- a bad Content-Length is refused, not a crash ---
assert web.Request("PUT", "/wifi", {"content-length": "12"}, None).length == 12
for bad in ("abc", "-5"):
    r = web.Request("PUT", "/wifi", {"content-length": bad}, None)
    assert r.length == 0 and r.bad == "bad Content-Length"


class Writer:
    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data

    async def drain(self):
        pass

    def close(self):
        pass

    async def wait_closed(self):
        pass

    def get_extra_info(self, _):
        return ("1.2.3.4", 1)


class Reader:
    def __init__(self, raw):
        self.raw = raw

    async def readline(self):
        line, sep, self.raw = self.raw.partition(b"\n")
        return line + sep

    async def read(self, n):
        out, self.raw = self.raw[:n], self.raw[n:]
        return out


def serve(raw):
    """(status, json body) of one raw request through the server."""
    pub = web.Publisher(types.SimpleNamespace(to_dict=lambda: {"power": None}))
    w = Writer()
    asyncio.run(pub._client(Reader(raw), w))
    head, _, body = w.data.partition(b"\r\n\r\n")
    return int(head.split()[1]), json.loads(body)


assert serve(b"GET /state HTTP/1.1\r\n\r\n") == (200, {"power": None})
assert serve(b"PUT /wifi HTTP/1.1\r\nContent-Length: x\r\n\r\n") == (400, {"error": "bad Content-Length"})
assert serve(b"garbage\r\n\r\n") == (400, {"error": "bad request line"})
assert serve(b"GET /nothing HTTP/1.1\r\n\r\n") == (404, {"error": "not found"})

# --- GET /device: built once, served as stored bytes, rebuilt after forget_description() ---
sys.modules["ota"] = types.SimpleNamespace(current_version=lambda: _version())


async def _version():
    return "abcd1234"


built = []


def build(version):
    built.append(version)
    return {"api": 2, "bridge_version": version, "n": len(built)}


def device(path="/device"):
    w = Writer()
    asyncio.run(web.serve_description(web.Request("GET", path, {}, None), w, build))
    head, _, body = w.data.partition(b"\r\n\r\n")
    return int(head.split()[1]), json.loads(body)


assert device() == (200, {"api": 2, "bridge_version": "abcd1234", "n": 1})
assert device() == (200, {"api": 2, "bridge_version": "abcd1234", "n": 1}) and built == ["abcd1234"]
web.forget_description()
assert device()[1]["n"] == 2
assert device("/device/x") == (404, {"error": "not found"})

# --- waits.until ---
left = [3]


def quiet():
    left[0] -= 1
    return left[0] <= 0


assert asyncio.run(waits.until(quiet, 1000)) is True and left[0] == 0
assert asyncio.run(waits.until(lambda: False, 30)) is False

print("all good")
