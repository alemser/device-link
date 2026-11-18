"""The Pico's HTTP server: publishes the device's state on the network (Wi-Fi is in wifi.py).

This file belongs to the shared base (firmware-base/): change it there and copy it with copy_base.py --all, never here.

    GET /state    the state as JSON
    GET /events   Server-Sent Events: one "data: {json}" on change (at most 4 per second, always the latest)
    others        extra routes, by prefix: routes={"/update": ota.handle, "/device": device.handle}

Use (with asyncio):
    pub = Publisher(state, routes={...})
    (routes: async handler(req, writer); req = Request, below; answers with reply())
    asyncio.create_task(pub.serve())
    ...
    pub.changed()      # call after every state change
"""

import json
import asyncio

from listeners import make_room

CHUNK = 1024                    # the body goes in chunks: the Pico's Wi-Fi has little memory
# /events: at most one state every EVENT_GAP_S, always the latest. Sending one on every change (turning the SP103's
# volume gives dozens per second) fills lwIP's memory, and then each write stalls the Pico for 10 s (SP103 issue #2).
EVENT_GAP_S = 0.25
PING_S = 1                      # groove-rig gives up after 5 s of silence


MAX_BODY = 4096                 # a route that reads its body whole (PUT /wifi) refuses more; ota.py streams its files


def unquote(text):
    """A query value as sent: "+" is a space and %XX a byte, UTF-8 ("a%20b+c" -> "a b c"). Bad escapes stay as they are."""
    if "%" not in text and "+" not in text:
        return text
    raw = bytearray()
    data = text.replace("+", " ").encode()
    i = 0
    while i < len(data):
        byte = _hex(data[i + 1:i + 3]) if data[i] == 37 else None      # 37 = "%"
        if byte is not None:
            raw.append(byte)
            i += 3
        else:
            raw.append(data[i])
            i += 1
    return bytes(raw).decode("utf-8", "replace")


def _hex(two):
    """Two ASCII hex digits as a byte, or None."""
    if len(two) != 2 or any(c not in b"0123456789abcdefABCDEF" for c in two):
        return None
    return int(two.decode(), 16)


def hex_byte(text):
    """A byte from its hex text ("05", "0x7A"), or None if it isn't one (the /ir/send?code=XX routes)."""
    if not text:
        return None
    if text[:2] in ("0x", "0X"):
        text = text[2:]
    if len(text) == 1:
        text = "0" + text
    return _hex(text.encode())


class Request:
    """An HTTP request read up to its headers. The body is left in reader (length bytes). bad: why it can't be served
    (the server answers 400 with it), or None."""

    def __init__(self, method, path, headers, reader):
        self.method = method
        self.path, _, query = path.partition("?")
        self.query = {}                 # "?tz=120&x=a%20b" -> {"tz": "120", "x": "a b"}
        for p in query.split("&"):
            if p:
                key, _, value = p.partition("=")
                self.query[unquote(key)] = unquote(value)
        self.headers = headers          # names in lower case
        self.reader = reader
        self.bad = None
        try:
            self.length = int(headers.get("content-length", 0))
        except ValueError:
            self.length = 0
            self.bad = "bad Content-Length"
        if self.length < 0:
            self.length = 0
            self.bad = "bad Content-Length"


async def discard(req):
    """Reads and drops the request body: answering without reading it makes lwIP send a reset, and the client never
    sees the answer (an error message included)."""
    left = req.length
    while left > 0:
        chunk = await req.reader.read(min(1024, left))
        if not chunk:
            break
        left -= len(chunk)


async def reply(writer, status, ctype, body):
    # no-store: everything here changes with the state and with OTA updates.
    writer.write(("HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\nCache-Control: no-store\r\n"
                  "Access-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n"
                  % (status, ctype, len(body))).encode())
    await writer.drain()
    # In chunks: a large answer in one go squeezes the Wi-Fi's memory (SP103 issue #2).
    for i in range(0, len(body), CHUNK):
        writer.write(body[i:i + CHUNK])
        await writer.drain()


async def reply_json(writer, obj, status="200 OK"):
    await reply(writer, status, "application/json", json.dumps(obj).encode())


async def not_found(writer, text="not found"):
    """404 in the contract's error shape: {"error": "text"} (docs/contract-v2.md, Transport)."""
    await reply_json(writer, {"error": text}, "404 Not Found")


_description = None             # GET /device as stored bytes: built on the first request (contract goal 4)


def forget_description():
    """Something the description shows changed (the SP103's input names): the next GET /device rebuilds it."""
    global _description
    _description = None


async def serve_description(req, writer, build):
    """Route /device: build(version) -> the description dict (each device's device.py), served as stored bytes."""
    global _description
    if req.path != "/device":
        return await not_found(writer)
    if _description is None:
        import ota
        _description = json.dumps(build(await ota.current_version())).encode()
    await reply(writer, "200 OK", "application/json", _description)


class Publisher:
    def __init__(self, state, port=80, routes=None):
        self.state = state
        self.port = port
        self.routes = routes or {}
        self.listeners = []             # open /events connections: (ip, writer), see listeners.py
        self.served = 0                 # requests answered since the Pico started
        self.version = 0                # goes up on every changed(); each listener keeps the last one it sent

    def _json(self):
        return json.dumps(self.state.to_dict())

    def changed(self):
        """Marks the state as changed (call after each change). Each listener's loop in _events() does the sending, at
        most one state every EVENT_GAP_S, always the latest."""
        self.version += 1

    async def serve(self):
        await asyncio.start_server(self._client, "0.0.0.0", self.port)

    async def _client(self, reader, writer):
        try:
            request = await reader.readline()
            headers = {}
            while True:
                line = await reader.readline()
                if not line or line == b"\r\n":
                    break
                name, _, value = line.decode().partition(":")
                headers[name.strip().lower()] = value.strip()
            parts = request.split()
            target = parts[1].decode("utf-8", "replace") if len(parts) > 1 else ""
            req = Request(parts[0].decode("utf-8", "replace") if parts else "", target or "/", headers, reader)
            if not target.startswith("/"):
                req.bad = "bad request line"
            path = req.path
            route = path.split("/")[1].split(".")[0]    # "/bus.csv" -> "bus"; "/update/x" -> "update"
            self.served += 1

            if req.bad:
                await discard(req)
                await reply_json(writer, {"error": req.bad}, "400 Bad Request")
            elif path == "/state":
                await reply(writer, "200 OK", "application/json", self._json().encode())
            elif path == "/events":
                await self._events(writer)
                return
            elif "/" + route in self.routes:
                await self.routes["/" + route](req, writer)
            else:
                await not_found(writer)
        except Exception as e:
            print("http:", e)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

    async def _events(self, writer):
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n"
                     b"Cache-Control: no-cache\r\nAccess-Control-Allow-Origin: *\r\n\r\n")
        try:
            ip = writer.get_extra_info("peername")[0]
        except Exception:
            ip = None
        make_room(self.listeners, ip)
        writer.write(("data: " + self._json() + "\n\n").encode())   # the current state straight away
        entry = (ip, writer)
        self.listeners.append(entry)
        sent = self.version
        quiet = 0
        try:
            while entry in self.listeners:      # off the list = another connection took its place
                await writer.drain()            # fails if the connection dropped
                await asyncio.sleep(EVENT_GAP_S)
                if entry not in self.listeners:
                    break
                if self.version != sent:
                    sent = self.version
                    quiet = 0
                    writer.write(("data: " + self._json() + "\n\n").encode())
                else:
                    quiet += 1
                    if quiet * EVENT_GAP_S >= PING_S:
                        quiet = 0
                        writer.write(b": ping\n\n")   # SSE comment: keeps the connection alive
        except Exception:
            pass
        finally:
            if entry in self.listeners:
                self.listeners.remove(entry)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
