"""Presses the Function button on the amp's front panel, from the inside.

Wiring (docs/installation.md):

    GP0 = controller leg 6     GP1 = controller leg 13

The controller pulses leg 6 and reads leg 13: with the button pressed, leg 13 falls together with leg 6
(capture from 2026-11-06). The PIO imitates that: while GP0 is at 0, it pulls GP1 to 0.

SAFETY RULE: GP0 is never an output. GP1 is never driven to 1: its output value stays 0 and only the
direction changes, at 2 mA. Leg 13 rises through a 4.7 kΩ resistor, so pulling it costs about 1 mA.

On about 1 click in 32 (measured 2026-11-23), the amp also selects the PHONO input. control.py corrects that.
"""

import time

import rp2
from machine import Pin, mem32

PIN_SCAN, PIN_READ = 0, 1
PRESS_MS = 60
WIDTH_SM = 7                    # PIO1, state machine 3: the only one free on PIO1
WIDTH_US_PER_LOOP = 0.2         # derived: 2 cycles per loop of _low_width at 10 MHz
WIDTH_BUCKETS_US = (5, 10, 13, 20, 25, 30, 40, 60, 100)     # chosen: spans the 11.6 µs pulse and the 25-30 µs of 2026-11-06
MEASURE_MS = 200                # chosen: about 2,800 leg 6 pulses (2026-11-23), short enough not to stall the server
_PADS_BANK0 = 0x40038000
_DRIVE_MASK = 0x3 << 4


@rp2.asm_pio(set_init=rp2.PIO.IN_LOW)
def _mirror():
    # At 10 MHz, so leg 13 follows leg 6 within 0.2 µs. Measured with /panel on 2026-11-23: every leg 6
    # pulse lasts 11.6 µs, one every ~72 µs, so there is no width to tell pulses apart by.
    wait(0, gpio, 0)            # leg 6 at 0
    set(pindirs, 1)             # leg 13 at 0
    wait(1, gpio, 0)            # leg 6 back at 1
    set(pindirs, 0)


@rp2.asm_pio()
def _low_width():
    # Reads only (no set or out): pushes how many loops each low pulse on the pin lasted.
    wait(1, pin, 0)
    wait(0, pin, 0)
    mov(x, invert(null))
    label("low")
    jmp(pin, "done")
    jmp(x_dec, "low")
    label("done")
    mov(isr, invert(x))
    push(noblock)


def _summary(widths):
    if not widths:
        return {"pulses": 0}
    widths.sort()
    hist, i = {}, 0
    for top in WIDTH_BUCKETS_US + (None,):
        n = 0
        while i < len(widths) and (top is None or widths[i] < top):
            n += 1
            i += 1
        hist["<%d" % top if top else ">=%d" % WIDTH_BUCKETS_US[-1]] = n
    return {"pulses": len(widths), "min_us": widths[0], "median_us": widths[len(widths) // 2],
            "max_us": widths[-1], "us": hist}


class Panel:
    def __init__(self, sm_id=6):
        # sm_id 6 = PIO1, state machine 2 (0 is busy.py's and 1 is ir.py's).
        Pin(PIN_SCAN, Pin.IN, pull=None)
        Pin(PIN_READ, Pin.IN, pull=None)
        self.sm = rp2.StateMachine(sm_id, _mirror, freq=10_000_000, set_base=Pin(PIN_READ),
                                   jmp_pin=Pin(PIN_SCAN))
        self.sm.exec("set(pins, 0)")
        self.sm.exec("set(pindirs, 0)")
        pad = _PADS_BANK0 + 4 + 4 * PIN_READ
        mem32[pad] = mem32[pad] & ~_DRIVE_MASK & ~1     # 2 mA, slow edge

    def widths(self, pin, ms):
        """The low pulses on pin for ms, in µs (a pulse that outlasts the window is not counted)."""
        sm = rp2.StateMachine(WIDTH_SM, _low_width, freq=10_000_000, in_base=Pin(pin), jmp_pin=Pin(pin))
        sm.restart()
        sm.active(1)
        out = []
        end = time.ticks_add(time.ticks_ms(), ms)
        while time.ticks_diff(end, time.ticks_ms()) > 0:
            while sm.rx_fifo():
                out.append(round(sm.get() * WIDTH_US_PER_LOOP, 1))
        sm.active(0)
        return out

    async def handle(self, req, writer):
        """/panel route, for diagnosis. GET: the widths of the leg 6 pulses (GP0), which _mirror follows.
        POST: one press, with the pulses seen on leg 13 (GP1) meanwhile; none means GP1 never pulled the line."""
        from web import reply_json, not_found
        if req.path != "/panel" or req.method not in ("GET", "POST"):
            return await not_found(writer)
        out = {"scan": _summary(self.widths(PIN_SCAN, MEASURE_MS))}
        if req.method == "POST":
            out["read_during_press"] = _summary(self.press(watch=True))
        await reply_json(writer, out)

    def press(self, watch=False):
        """One Function press. With watch, returns the low pulses seen on leg 13 meanwhile."""
        self.sm.active(1)
        seen = self.widths(PIN_READ, PRESS_MS) if watch else time.sleep_ms(PRESS_MS)
        self.sm.active(0)
        self.sm.exec("set(pindirs, 0)")
        return seen
