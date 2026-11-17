#!/usr/bin/env python3
"""Checks firmware/vfd.py against the real capture (captures/02-tocando.lac) and a few made-up frames.

    python3 tools/test_vfd.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import fl_decode    # noqa: E402
import vfd          # noqa: E402

CAPTURE = os.path.join(HERE, "..", "captures", "02-tocando.lac")
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("FAILED:", msg)


def words(frames):
    """What the Pico's sniffer would hand over for these frames (lists of bytes)."""
    out = []
    for frame in frames:
        out.append(vfd.MARKER)
        out += [b << 24 for b in frame]
    return out


def feed(screen, ws):
    changed = False
    for i, w in enumerate(ws):
        changed |= screen.feed(w, now_ms=i)
    return screen.flush(now_ms=len(ws)) or changed


def main():
    # The real capture: disc playing, track 1 at 0:07.
    freq, sig = fl_decode.load_lac(CAPTURE)
    frames = [fl_decode.to_bytes(f["bits"], msb_first=False) for f in fl_decode.frames(sig["CS"], sig["CLK"], sig["DATA"])]
    s = vfd.Screen()
    check(feed(s, words(frames)), "the capture changes the screen")
    check(s.text() == "  1    0:07 ", "text from the capture: %r" % s.text())
    check(s.icons().hex() == "00000000000804000000", "icons from the capture: %s" % s.icons().hex())
    check(s.lit() == ["13.0.3", "13.1.2"], "lit icon dots: %s" % s.lit())
    check(s.frames == len(frames), "every frame counted: %d of %d" % (s.frames, len(frames)))
    check(s.bad == 0, "no malformed words")
    # The text arrives in one group and the icons in the next; after that the cycle repeats unchanged.
    check(len(s.changes) == 2, "two changes while the first cycle arrives, then none: %s" % s.changes)

    # Made-up frames: text at an offset, a new icon, a partial byte, a malformed word.
    s = vfd.Screen()
    feed(s, words([[0x10] + list(b"  2    1:23 "), [0x1C, 0, 1], [0x20] + [0] * 5 + [1, 0, 0, 0, 0]]))
    check(s.text() == "  2    1:23 " and s.lit() == ["13.0.0"], "made-up screen: %r %s" % (s.text(), s.lit()))
    changed = feed(s, words([[0x17] + list(b"2:00")]))
    check(changed and s.text() == "  2    2:00 ", "write at position 7: %r" % s.text())
    check(not feed(s, words([[0x10] + list(b"  2    2:00 ")])), "the same text again is no change")
    s.feed(0x12345678)
    check(s.bad == 1, "malformed word counted")
    feed(s, words([[0x63], [0x50, 0xA0]]))
    check(s.config == {"63": "", "50": "a0"}, "config kept raw: %s" % s.config)
    d = s.debug()
    check(d["text"] == "  2    2:00 " and [c[1:] for c in d["icon_changes"]] == [["  2    1:23 ", "13.0.0"]],
          "debug view: %s" % d)

    # A long playing session: the time changes every second, the icons rarely; the debug view stays small.
    s = vfd.Screen()
    for sec in range(600):
        icon = 1 if sec % 100 < 50 else 2
        feed(s, words([[0x10] + list(("  3   %2d:%02d " % (sec // 60, sec % 60)).encode()), [0x1C, 0, 1],
                       [0x20] + [0] * 5 + [icon, 0, 0, 0, 0]]))
    import json
    size = len(json.dumps(s.debug()))
    check(size < 1024 and len(s.icon_changes) == 12 and len(s.changes) == vfd.CHANGES_KEPT,
          "debug view small: %d bytes, %d icon changes" % (size, len(s.icon_changes)))

    # The panel-key session on the device (2026-11-16), as the reader logged it: (text, lit dots) -> expected state.
    P, Z, D = vfd.ICON_PLAY, vfd.ICON_PAUSE, vfd.ICON_DISC
    session = [
        ((" 12   61:37 ", [D]), {"transport": "stopped", "tracks": 12, "total_s": 3697, "track": None}),
        ((" 12   61:37 ", [P, D]), {"transport": "playing", "track": None, "tracks": 12}),   # play, totals still shown
        (("  1    0:00 ", [P, D]), {"transport": "playing", "track": 1, "elapsed_s": 0}),
        (("  1    0:07 ", [P, D]), {"transport": "playing", "track": 1, "elapsed_s": 7, "total_s": 3697}),
        (("  1    0:09 ", [D, Z]), {"transport": "paused", "track": 1, "elapsed_s": 9}),
        ((" 12   61:37 ", [D]), {"transport": "stopped", "tracks": 12, "track": None}),
        ((" 12   61:37 ", []), {"transport": "open", "tracks": None}),
        ((" LOADING    ", [D]), {"transport": "loading", "tracks": None}),
        ((" 12   61:37 ", [D]), {"transport": "stopped", "tracks": 12}),
        (("  2    0:00 ", [D]), {"transport": "stopped", "track": 2, "tracks": 12}),          # next while stopped
    ]
    p = vfd.Player()
    for (text, lit), want in session:
        got = p.update(text, lit)
        check(all(got[k] == v for k, v in want.items()), "%r %s -> %s" % (text, lit, got))

    print("all good" if not failures else "%d failure(s)" % len(failures))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
