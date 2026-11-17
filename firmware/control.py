"""Commands to the KX-393 over the network (the contract's "control" group).

    POST /control?target=key&name=play     one remote key (ir_codes.KEYS) or power_toggle; answers with the state
    POST /ir/send?cmd=play                 one remote key; answers with the IR line's status
    POST /ir/send?code=00&address=7A       any command byte (hex), at the given address or the default one: for
                                           settling the address (ir_codes.py) and trying other codes
    GET  /ir                               the IR line's status and the list of keys

The remote keys go out as IR (ir.py). power_toggle has no IR code: it presses STANDBY/ON on the KEY1 line (panel.py).
Only the "key" target exists: the contract's other targets (volume, tone) belong to amplifiers.

One request at a time: while a key is going out, the next one gets "busy". An IR key takes about 110 ms, with the
silence at the end; power_toggle about 200 ms.

check() and parse_code() run the same in MicroPython (Pico) and in the computer's Python (tools/test_control.py).
"""

import ir_codes

POWER = "power_toggle"


def check(key, sending):
    """The error text to show the person (in English, as in the contract), or None if the key can go out."""
    if key not in ir_codes.COMMANDS and key != POWER:
        return "unknown key"
    if sending:
        return "busy"
    return None


def parse_code(text):
    """A byte from its hex text ("05", "0x7A"), or None if it isn't one."""
    if not text:
        return None
    if text[:2] in ("0x", "0X"):
        text = text[2:]
    if not 1 <= len(text) <= 2 or any(c not in "0123456789abcdefABCDEF" for c in text):
        return None
    return int(text, 16)


class Control:
    def __init__(self, state, remote, panel=None):
        self.state = state
        self.remote = remote
        self.panel = panel

    def _busy(self):
        return self.remote.sending() or (self.panel is not None and self.panel.pressing)

    async def _press(self, key):
        error = check(key, self._busy())
        if error is None and key == POWER:
            if self.panel is None:
                return "unknown key"
            await self.panel.press_power()
        elif error is None:
            self.remote.send(key)
        return error

    def _press_code(self, query):
        command = parse_code(query.get("code"))
        address = parse_code(query["address"]) if "address" in query else ir_codes.ADDRESS
        if command is None or address is None:
            return "bad code"
        if self._busy():
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
            error = await self._press(req.query.get("name"))
        elif "code" in req.query:
            error = self._press_code(req.query)
        else:
            key = req.query.get("cmd")
            error = "unknown key" if key == POWER else await self._press(key)
        if error:
            return await reply_json(writer, {"error": error}, "400 Bad Request")
        await reply_json(writer, self.state.to_dict() if req.path == "/control" else self.remote.status())
