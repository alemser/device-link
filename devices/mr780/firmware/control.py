"""Commands to the MR 780 over the network (the contract's "control" group).

    POST /control?target=key&name=next_input   one remote key (ir_codes.KEYS); answers with the state
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

import ir_codes


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
    def __init__(self, state, remote):
        self.state = state
        self.remote = remote

    def _press(self, key):
        error = check(key, self.remote.sending())
        if error is None:
            self.remote.send(key)
        return error

    def _press_code(self, query):
        command = parse_code(query.get("code"))
        address = parse_code(query["address"]) if "address" in query else ir_codes.ADDRESS
        if command is None or address is None:
            return "bad code"
        if self.remote.sending():
            return "busy"
        self.remote.send_command(command, address)
        return None

    async def handle(self, req, writer):
        """Routes /control and /ir (see web.Publisher)."""
        from web import reply, reply_json
        if req.path == "/ir" and req.method == "GET":
            return await reply_json(writer, self.remote.status())
        if req.method != "POST" or req.path not in ("/control", "/ir/send"):
            return await reply(writer, "404 Not Found", "text/plain", b"not found\n")
        if req.path == "/control":
            if req.query.get("target") != "key":
                return await reply_json(writer, {"error": "unknown target"}, "400 Bad Request")
            error = self._press(req.query.get("name"))
        elif "code" in req.query:
            error = self._press_code(req.query)
        else:
            error = self._press(req.query.get("cmd"))
        if error:
            return await reply_json(writer, {"error": error}, "400 Bad Request")
        await reply_json(writer, self.state.to_dict() if req.path == "/control" else self.remote.status())
