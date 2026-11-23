"""Commands to the MR 780 over the network (the contract's "control" group).

    POST /control?target=key&name=next_input   one remote key (ir_codes.KEYS); answers with the state
    POST /control?target=key&name=select_cd    the input select: steps the cycle to that input (inputs.py), a few s
    POST /control?target=volume&dir=up         the volume step: presses volume_up (or volume_down), answers with the
                                               state once the display shows the new volume
    POST /ir/send?cmd=next_input               the same key; answers with the IR line's status
    POST /ir/send?code=1A                      any command byte (hex), at the amp's address or &address=XX: for
                                               finding the keys nobody captured yet (tools/ir_try.py)
    GET  /ir                                   the IR line's status and the list of keys

Volume is a step, the one form the contract gives it, with volume_db (read from the display) as its value. The
volume_up and volume_down keys stay accepted as keys too: they are the IR keys the step presses, and /ir/send names
them the same way; the description lists only the step.

One request at a time: while a key is going out, the next one gets "busy". A key takes about 110 ms, with the
silence at the end.

check() runs the same in MicroPython (Pico) and in the computer's Python (tools/test_control.py).
"""

import device
import ir_codes
from waits import until
from web import hex_byte

# /control answers once the key is out: a key takes about 110 ms. A cap, in case the line never goes quiet.
DONE_MAX_MS = 2000
DIRECTIONS = ("up", "down")
# A volume step answers once the display shows the new volume. Chosen bound: in the 2026-11-23 captures the display
# showed it within about 1 s of the key; at the end of the range the volume doesn't change, and this caps the wait.
VOLUME_SHOWN_MS = 1500


def check(key, sending):
    """The error text to show the person (in English, as in the contract), or None if the key can go out."""
    if key not in ir_codes.COMMANDS:
        return "unknown key"
    if sending:
        return "busy"
    return None


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
        command = hex_byte(query.get("code"))
        address = hex_byte(query["address"]) if "address" in query else ir_codes.ADDRESS
        if command is None or address is None:
            return "bad code"
        if self.remote.sending():
            return "busy"
        self.remote.send_command(command, address)
        return None

    async def _done(self):
        """Waits for the IR line to go quiet: /control answers when the device has done it (docs/contract-v2.md,
        Controls), so the app's next tap doesn't get "busy". /ir/send too, so its status shows the key sent."""
        await until(lambda: not self.remote.sending(), DONE_MAX_MS)

    async def _step(self, writer, step, direction):
        """A step (device.STEPS): the direction's key, then the state once its value changes (VOLUME_SHOWN_MS at
        most)."""
        from web import reply_json
        if direction not in DIRECTIONS:
            return await reply_json(writer, {"error": "dir must be up or down"}, "400 Bad Request")
        value = lambda: self.state.to_dict().get(step["state"])     # noqa: E731
        before = value()
        error = self._press(step[direction])
        if error:
            return await reply_json(writer, {"error": error}, "400 Bad Request")
        await self._done()
        await until(lambda: value() != before, VOLUME_SHOWN_MS)
        await reply_json(writer, self.state.to_dict())

    async def handle(self, req, writer):
        """Routes /control and /ir (see web.Publisher)."""
        from web import reply_json, not_found
        if req.path == "/ir" and req.method == "GET":
            return await reply_json(writer, self.remote.status())
        if req.method != "POST" or req.path not in ("/control", "/ir/send"):
            return await not_found(writer)
        if req.path == "/control":
            target = req.query.get("target")
            if target in device.STEPS:
                return await self._step(writer, device.STEPS[target], req.query.get("dir"))
            if target != "key":
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
