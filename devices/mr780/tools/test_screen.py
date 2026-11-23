#!/usr/bin/env python3
"""Replays the amp's real captures (captures/*-2026-11-23.*) through the framer and firmware/screen.py.

    python3 tools/test_screen.py

The captures are raw samples of A, B and C. sniffer_words() turns them into what clocked_bus.py's PIO hands over: MARKER
when A (chip select) falls, then one word per byte taken on B's rising edges, LSB first, a byte cut short by A rising
dropped.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import capture   # noqa: E402
import device    # noqa: E402
import screen    # noqa: E402
from clocked_bus import MARKER, Framer   # noqa: E402

CAPTURES = os.path.join(HERE, "..", "captures")


def sniffer_words(name):
    with open(os.path.join(CAPTURES, name + "-2026-11-23.json")) as f:
        info = json.load(f)
    with open(os.path.join(CAPTURES, name + "-2026-11-23.bin"), "rb") as f:
        samples = capture.parse(f.read(), info["samples"])
    out, bits, prev = [], None, samples[0]
    for s in samples[1:]:
        a, b, c = s & 1, s >> 1 & 1, s >> 2 & 1
        if prev & 1 and not a:                  # A falls: a frame begins
            out.append(MARKER)
            bits = []
        elif a:
            bits = None                         # A high: no frame (a partial byte is dropped)
        elif bits is not None and b and not prev >> 1 & 1:
            bits.append(c)                      # B rises: C holds the bit
            if len(bits) == 8:
                out.append(sum(v << i for i, v in enumerate(bits)) << 24)
                bits = []
        prev = s
    return out


def replay(name, scr=None):
    """The screen after a capture, and whether the capture changed it."""
    scr = scr or screen.Screen()
    framer = Framer(screen.FRAME_BYTES)       # as display.py builds it
    changed = False
    for w in sniffer_words(name):
        frame = framer.feed(w)
        if frame is not None:
            changed |= scr.apply(frame)
    return scr, changed


def check(name, lines, **want):
    scr, _ = replay(name)
    assert scr.lines == lines, (name, scr.lines)
    for k, v in want.items():
        assert getattr(scr, k) == v, (name, k, getattr(scr, k), v)
    return scr


BLANK = screen.BLANK
check("on-idle", ["    USB AUDIO   ", BLANK], input_id="usb_audio", volume_db=None, muted=None, warmup_s=None)
check("on-idle-131ms", ["    USB AUDIO   ", BLANK], input_id="usb_audio")
check("volume-up-36db", ["    USB AUDIO   ", "   Volume  -36dB"], volume_db=-36.0)
check("volume-down-37db", ["    USB AUDIO   ", "   Volume  -37dB"], volume_db=-37.0)
check("mute-on", ["    USB AUDIO   ", "    Mute On     "], muted=True)
check("mute-off", ["    USB AUDIO   ", "    Mute Off    "], muted=False)
check("selector-open-usb", ["<   USB AUDIO  >", BLANK], input_id="usb_audio")
check("opt1-no-signal", ["  DIGITAL OPT1  ", "    No Signal   "], input_id="opt1")
check("standby-entering", ["    STANDBY     ", BLANK], input_id=None)
check("warm-up-19", [" MAGNAT  MR780  ", "  WARM UP  19   "], warmup_s=19, input_id=None)

# The scroll starts mid-frame: the first, partial frame is not a line; the scrolled text is kept as shown.
scr, _ = replay("usb-sample-rate-scroll")
assert scr.lines[0] == "    USB AUDIO   " and "Rate Not" in scr.lines[1] and scr.input_id == "usb_audio", scr.lines

# Standby after 15 s and the tuner's pause: no frames at all, so nothing changes and nothing is seen.
for quiet in ("standby-15s", "fm-no-transfers"):
    scr, changed = replay(quiet)
    assert not changed and not scr.seen and scr.lines == [BLANK, BLANK], quiet

# A DAB station keeps the input; FM's frequency names FM; the warm-up ends when line 2 moves on.
scr, _ = replay("opt1-no-signal")
for line, text in ((0, "DAB/DAB+"), (0, "Onic 80s"), (1, "   No Service   ")):
    frame = bytearray([{0: 0x90, 1: 0x10}[line], 0]) + bytes(reversed(text.ljust(16).encode()))
    scr.apply(frame)
assert scr.input_id == "dab" and scr.lines[0] == "Onic 80s        ", scr.lines
assert screen.input_shown("FM    100.75MHz ") == "fm"
assert screen.warm_up_shown("    Mute Off    ") is None and screen.volume_shown("Volume  MIN dB") is None

# The same frame again is no change (the amp resends every ~26 ms); a frame that isn't a line write is ignored.
scr, _ = replay("on-idle")
assert not replay("on-idle", scr)[1]
assert screen.line_of(bytearray([0x90, 1] + [32] * 16)) is None
assert screen.line_of(bytearray([0x44, 0] + [32] * 16)) is None
assert screen.line_of(bytearray([0x90, 0] + [32] * 15)) is None

# Every input in the cycle has a name on the display.
assert set(screen.SHOWN.values()) == {i for i, _ in device.INPUTS}
print("all good")
