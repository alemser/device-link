"""On or standby, from the LIGA wire: flat pin 4, the display's 5 V, which the amp switches on with itself.

Measured 2026-11-18 (docs/measurements.md): 0.02 V in standby, 4.78 V on. The wire is on the VFD row's joint of pin 4,
and goes to GP5 (the logic analyzer's channel 4, as the same harness serves both).

GP5 is an input only, with no pull: the line is driven by the amp in both states, and the RP2350's pull-down
misbehaves on a pin that was held high (erratum E9). The RP2350's pins take 5 V while the Pico is powered, and the Pico
is powered from the same amp.

The line must read the same for STABLE_MS before it counts, so a slow edge or a glitch while the amp switches doesn't
make the state flicker. decide() runs the same in MicroPython and in the computer's Python (tools/test_power.py).

The warm-up: the MR 780's valve preamp counts down 30 s on the display after power-on (groove-rig's profile has
warm_up_secs: 30). Until the display reader exists, the bridge counts it itself from the moment the line goes on:
warmup_left() gives the seconds left, or None outside the warm-up. "power" stays "on" meanwhile (the amp is on).
"""

LIGA_PIN = 5
STABLE_MS = 300
POLL_MS = 100
WARMUP_S = 30


def decide(level, since_ms, current):
    """The power state for a line that has read `level` for `since_ms`: "on", "standby", or `current` while not yet
    stable."""
    if since_ms < STABLE_MS:
        return current
    return "on" if level else "standby"


def warmup_left(on_for_ms):
    """Seconds of warm-up left, `on_for_ms` after power-on was seen (None: not warming up, or power-on not seen)."""
    if on_for_ms is None:
        return None
    left = WARMUP_S - on_for_ms // 1000
    return left if left > 0 else None


class Power:
    def __init__(self, on_change):
        from machine import Pin
        self.line = Pin(LIGA_PIN, Pin.IN, pull=None)
        self.on_change = on_change
        self.state = None               # null in /state until the line has been read long enough
        self.on_at = None               # ticks_ms when standby -> on was seen (not when the Pico starts with it on)
        self.warmup = None              # seconds left, for /state

    async def task(self):
        import time
        import asyncio
        level = self.line.value()
        since = time.ticks_ms()
        while True:
            await asyncio.sleep_ms(POLL_MS)
            now = self.line.value()
            if now != level:
                level, since = now, time.ticks_ms()
            state = decide(level, time.ticks_diff(time.ticks_ms(), since), self.state)
            changed = state != self.state
            if changed:
                # A warm-up only from a seen power-on: a Pico started with the amp already on doesn't know when.
                self.on_at = since if (state == "on" and self.state == "standby") else None
                self.state = state
            on_for = time.ticks_diff(time.ticks_ms(), self.on_at) if self.on_at is not None else None
            warmup = warmup_left(on_for)
            if warmup is None:
                self.on_at = None
            if changed or warmup != self.warmup:
                self.warmup = warmup
                self.on_change()
