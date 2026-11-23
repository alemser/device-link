"""On or standby, from the LIGA wire: flat pin 4, the display's 5 V, which the amp switches on with itself.

Measured 2026-11-18 (docs/measurements.md): 0.02 V in standby, 4.78 V on. The wire is on the VFD row's joint of pin 4,
and goes to GP5 (the logic analyzer's channel 4, as the same harness serves both).

GP5 is an input only, with no pull: the line is driven by the amp in both states, and the RP2350's pull-down
misbehaves on a pin that was held high (erratum E9). The RP2350's pins take 5 V while the Pico is powered, and the Pico
is powered from the same amp.

The line must read the same for STABLE_MS before it counts, so a slow edge or a glitch while the amp switches doesn't
make the state flicker. decide() runs the same in MicroPython and in the computer's Python (tools/test_power.py).

"power" stays "on" through the valves' warm-up (the amp is on); the warm-up itself comes from the display
(screen.py).
"""

LIGA_PIN = 5
STABLE_MS = 300
POLL_MS = 100


def decide(level, since_ms, current):
    """The power state for a line that has read `level` for `since_ms`: "on", "standby", or `current` while not yet
    stable."""
    if since_ms < STABLE_MS:
        return current
    return "on" if level else "standby"


class Power:
    def __init__(self, on_change):
        from machine import Pin
        self.line = Pin(LIGA_PIN, Pin.IN, pull=None)
        self.on_change = on_change
        self.state = None               # null in /state until the line has been read long enough

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
            if state != self.state:
                self.state = state
                self.on_change()
