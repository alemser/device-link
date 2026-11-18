"""Commands to the MR 780 over the network (the contract's "control" group).

    POST /control?target=key&name=next_input   one remote key (ir_codes.KEYS); answers with the state
    POST /control?target=key&name=select_cd    the input select: steps the cycle to that input (inputs.py), a few s
    POST /ir/send?cmd=next_input               the same key; answers with the IR line's status
    POST /ir/send?code=1A                      any command byte (hex), at the amp's address or &address=XX: for
                                               finding the keys nobody captured yet (tools/ir_try.py)
    GET  /ir                                   the IR line's status and the list of keys

Only the "key" target: volume is a pair of keys, not a step, until the bridge can read the volume from the display
(a step in the contract shows its state field next to − and +).

One request at a time: while a key is going out, the next one gets "busy". A key takes about 110 ms, with the
silence at the end.

check() and parse_code() run the same in MicroPython (Pico) and in the computer's Python (tools/test_control.py).
"""

import asyncio

import ir_codes

# /control answers once the key is out: a key takes about 110 ms. A cap, in case the line never goes quiet.
DONE_MAX_MS = 2000


def check(key, sending):
    """The error text to show the person (in English, as in the contract), or None if the key can go out."""
    if key not in ir_codes.COMMANDS:
        return "unknown key"
    if sending:
        return "busy"
    return None


def parse_code(text):
    """A byte from its hex text ("1A", "0x40"), or None if it isn't one."""
    if not text:
        return None
    if text[:2] in ("0x", "0X"):
        text = text[2:]
    if not 1 <= len(text) <= 2 or any(c not in "0123456789abcdefABCDEF" for c in text):
        return None
    return int(text, 16)


class Control:
    def __init__(self, state, remote, selector=None):
        self.state = state
        self.remote = remote
        self.selector = selector        # inputs.Selector: the select_<id> keys and the input tracking

    def _press(self, key):
        busy = self.remote.sending() or (self.selector is not None and self.selector.busy)
        error = check(key, busy)
        if error is None:
            self.remote.send(key)
            if self.selector is not None and key in ("next_input", "prev_input"):
                self.selector.raw(key)
        return error

    async def _press_any(self, key):
        """A remote key, or select_<id> for the input select (inputs.py)."""
        if key and key.startswith("select_") and self.selector is not None:
            return await self.selector.select(key[len("select_"):])
        return self._press(key)

    def _press_code(self, query):
        command = parse_code(query.get("code"))
        address = parse_code(query["address"]) if "address" in query else ir_codes.ADDRESS
        if command is None or address is None:
            return "bad code"
        if self.remote.sending():
            return "busy"
        self.remote.send_command(command, address)
        return None

    async def _done(self):
        """Waits for the IR line to go quiet: /control answers when the device has done it (docs/contract-v2.md,
        Controls), so the app's next tap doesn't get "busy". /ir/send too, so its status shows the key sent."""
        for _ in range(DONE_MAX_MS // 10):
            if not self.remote.sending():
                return
            await asyncio.sleep(0.01)

    async def handle(self, req, writer):
        """Routes /control and /ir (see web.Publisher)."""
        from web import reply_json, not_found
        if req.path == "/ir" and req.method == "GET":
            return await reply_json(writer, self.remote.status())
        if req.method != "POST" or req.path not in ("/control", "/ir/send"):
            return await not_found(writer)
        if req.path == "/control":
            if req.query.get("target") != "key":
                return await reply_json(writer, {"error": "unknown target"}, "400 Bad Request")
            error = await self._press_any(req.query.get("name"))
        elif "code" in req.query:
            error = self._press_code(req.query)
        else:
            error = self._press(req.query.get("cmd"))
        if error:
            return await reply_json(writer, {"error": error}, "400 Bad Request")
        await self._done()
        await reply_json(writer, self.state.to_dict() if req.path == "/control" else self.remote.status())
