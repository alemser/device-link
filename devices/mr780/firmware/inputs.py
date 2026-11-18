"""Plan B for choosing the MR 780's input from the app, until the display reader exists (owner, 2026-11-18).

The MR 780 has no direct code per input: the remote only steps the input cycle (next_input, prev_input), and the
cycle wraps. So the bridge keeps track of the input itself, in input.json, and reaches a chosen one by stepping the
shorter way round. It cannot see the amp, so the tracking is only as good as the presses it knows of:

- The first time (nothing tracked), choosing an input in the app only tells the bridge where the amp is: the person
  picks the input the amp's display shows. No IR goes out.
- Turning SOURCE or using the remote moves the amp without the bridge knowing. GET /input?set=<id> (this bridge's own
  route, outside the contract) tells it again. The display reader will replace all this.

The selector's timing, measured by groove-rig on this amp (internal/catalog/profiles/magnat_mr780.yaml):
- With the selector closed, a press only opens it (shows the input, doesn't move): the "arming" press.
- After the arming press, a press within ~1 s is ignored; at 1.33 s it landed: wait ARM_SETTLE_MS.
- Steps 600 ms apart all land.
- The selector is still open 2 s after a press and closed by 5 s: in between, a press may arm or step.

plan() and after_raw() and the Selector (with an injected clock) run in the computer's Python (tools/test_inputs.py).
"""

import json

import device

ARM_SETTLE_MS = 1500
STEP_MS = 600
OPEN_MS = 2000
CLOSED_MS = 5000
ARM_IGNORE_MS = 1200
FILE = "input.json"
IDS = tuple(i for i, _ in device.INPUTS)
NAMES = dict(device.INPUTS)


def plan(current, target):
    """(key, steps) the shorter way round the cycle; (None, 0) when already there."""
    n = len(IDS)
    c, t = IDS.index(current), IDS.index(target)
    fwd, back = (t - c) % n, (c - t) % n
    if fwd == 0:
        return None, 0
    return ("next_input", fwd) if fwd <= back else ("prev_input", back)


def after_raw(current, key, since_ms, last_was_arm):
    """The tracked input after one next/prev press that the bridge sent (not through plan()), given the time since
    the previous press (None: none known). None when it can't be told."""
    if current is None:
        return None
    if since_ms is None or since_ms >= CLOSED_MS:
        return current                  # the arming press: shows the input, doesn't move it
    if since_ms >= OPEN_MS:
        return None                     # the selector may or may not have closed
    if last_was_arm and since_ms < ARM_IGNORE_MS:
        return current                  # ignored, right after the arming press
    i = IDS.index(current)
    return IDS[(i + (1 if key == "next_input" else -1)) % len(IDS)]


def _now():
    import time
    return time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.monotonic() * 1000)


def _diff(a, b):
    import time
    return time.ticks_diff(a, b) if hasattr(time, "ticks_diff") else a - b


async def _sleep(ms):
    import asyncio
    await asyncio.sleep(ms / 1000)


class Selector:
    def __init__(self, remote, on_change, path=FILE, now=_now, sleep=_sleep):
        self.remote = remote
        self.on_change = on_change
        self.path = path
        self.now = now
        self.sleep = sleep
        self.current = self._load()
        self.last_ms = None             # when the last next/prev press went out
        self.last_was_arm = False
        self.busy = False

    def _load(self):
        try:
            with open(self.path) as f:
                value = json.load(f).get("input")
            return value if value in IDS else None
        except (OSError, ValueError):
            return None

    def _set(self, value):
        if value == self.current:
            return
        self.current = value
        try:
            with open(self.path, "w") as f:
                json.dump({"input": value}, f)
        except OSError:
            pass
        self.on_change()

    def name(self):
        return NAMES.get(self.current)

    def _since(self):
        return None if self.last_ms is None else _diff(self.now(), self.last_ms)

    def raw(self, key):
        """A next/prev key sent on its own (POST /control): keeps the tracking honest about it."""
        since = self._since()
        self._set(after_raw(self.current, key, since, self.last_was_arm))
        self.last_was_arm = since is None or since >= CLOSED_MS
        self.last_ms = self.now()

    async def _press(self, key):
        while self.remote.sending():
            await self.sleep(10)
        self.remote.send(key)
        self.last_ms = self.now()

    async def select(self, target):
        """Steps the amp to `target`. Returns an error text or None."""
        if target not in IDS:
            return "unknown input"
        if self.busy or self.remote.sending():
            return "busy"
        if self.current is None:
            self._set(target)           # the first time: the person tells where the amp is
            return None
        key, steps = plan(self.current, target)
        if not steps:
            return None
        self.busy = True
        try:
            since = self._since()
            arm = since is None or since >= OPEN_MS
            if since is not None and OPEN_MS <= since < CLOSED_MS:
                await self.sleep(CLOSED_MS - since)     # let the selector close, so the next press surely arms
            elif not arm:
                wait = (ARM_SETTLE_MS if self.last_was_arm else STEP_MS) - since
                if wait > 0:
                    await self.sleep(wait)
            if arm:
                await self._press(key)
                await self.sleep(ARM_SETTLE_MS)
            for i in range(steps):
                await self._press(key)
                if i < steps - 1:
                    await self.sleep(STEP_MS)
            self.last_was_arm = False
            self._set(target)
        finally:
            self.busy = False
        return None

    async def handle(self, req, writer):
        """Route /input (this bridge's own, outside the contract): GET /input, or /input?set=<id> to say where the
        amp is when the tracking got lost."""
        from web import reply_json
        if "set" in req.query:
            value = req.query["set"]
            if value not in IDS:
                return await reply_json(writer, {"error": "unknown input", "inputs": list(IDS)}, "400 Bad Request")
            self._set(value)
        await reply_json(writer, {"input_id": self.current, "input": self.name(), "tracked": True,
                                  "inputs": list(IDS)})
