"""Commands to the CD-S300 over the network (the contract's "control" group).

    POST /control?target=key&name=play     one remote key (ir_codes.KEYS); answers with the state
    POST /ir/send?cmd=play                 the same key; answers with the IR line's status
    GET  /ir                               the IR line's status and the list of keys

Only the "key" target exists: the contract's other targets (volume, tone) belong to amplifiers.

One request at a time: while a key is going out, the next one gets "busy". A key takes about 110 ms, with the
silence at the end.

check() runs the same in MicroPython (Pico) and in the computer's Python (tools/test_control.py).
"""

import ir_codes


def check(key, sending):
    """The error text to show the person (in English, as in the contract), or None if the key can go out."""
    if key not in ir_codes.COMMANDS:
        return "unknown key"
    if sending:
        return "busy"
    return None


class Control:
    def __init__(self, state, remote):
        self.state = state
        self.remote = remote

    def _press(self, key):
        error = check(key, self.remote.sending())
        if error is None:
            self.remote.send(key)
        return error

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
            key = req.query.get("name")
        else:
            key = req.query.get("cmd")
        error = self._press(key)
        if error:
            return await reply_json(writer, {"error": error}, "400 Bad Request")
        await reply_json(writer, self.state.to_dict() if req.path == "/control" else self.remote.status())
