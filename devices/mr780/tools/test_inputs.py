#!/usr/bin/env python3
"""Tests the input select (firmware/inputs.py) on the computer, with a fake IR line and a fake clock.

    python3 tools/test_inputs.py
"""

import asyncio
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import inputs   # noqa: E402

IDS = inputs.IDS
assert IDS[:4] == ("usb_audio", "bluetooth", "phono", "cd") and len(IDS) == 15

# plan(): the shorter way round, forward on a tie (15 is odd: no ties), wrapping both ways.
assert inputs.plan("cd", "cd") == (None, 0)
assert inputs.plan("phono", "cd") == ("next_input", 1)
assert inputs.plan("cd", "phono") == ("prev_input", 1)
assert inputs.plan("usb_audio", "coax2") == ("prev_input", 1)          # wraps backwards
assert inputs.plan("coax2", "usb_audio") == ("next_input", 1)          # wraps forwards
assert inputs.plan("usb_audio", "line_in") == ("prev_input", 7)         # line_in is 8 forward, 7 back

# after_raw(): an arming press doesn't move; a step within the open window does; 2-5 s is unknown.
assert inputs.after_raw("cd", "next_input", None, False) == "cd"
assert inputs.after_raw("cd", "next_input", 6000, False) == "cd"
assert inputs.after_raw("cd", "next_input", 1500, True) == "dvd"
assert inputs.after_raw("cd", "next_input", 800, True) == "cd"         # ignored right after arming
assert inputs.after_raw("cd", "prev_input", 600, False) == "phono"
assert inputs.after_raw("cd", "next_input", 3000, False) is None
assert inputs.after_raw(None, "next_input", 600, False) is None


class Clock:
    def __init__(self):
        self.t = 100_000

    def now(self):
        return self.t

    async def sleep(self, ms):
        self.t += int(ms)


class FakeRemote:
    def __init__(self, clock):
        self.clock = clock
        self.sent = []                  # (time, key)

    def sending(self):
        return False

    def send(self, key):
        self.sent.append((self.clock.t, key))


def run(coro):
    return asyncio.run(coro)


with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "input.json")
    clock = Clock()
    remote = FakeRemote(clock)
    changes = []
    sel = inputs.Selector(remote, lambda: changes.append(sel.current), path=path, now=clock.now, sleep=clock.sleep)
    assert sel.current is None and sel.name() is None

    # First choice with nothing tracked: only learns where the amp is; no IR.
    assert run(sel.select("phono")) is None
    assert sel.current == "phono" and remote.sent == [] and changes == ["phono"]

    # phono -> coax1: shorter backwards (phono is 2, coax1 is 13: back 4, forward 11). Arm, settle, 4 steps 600 ms
    # apart.
    t0 = clock.t
    assert run(sel.select("coax1")) is None
    keys = [k for _, k in remote.sent]
    times = [t - t0 for t, _ in remote.sent]
    assert keys == ["prev_input"] * 5, keys
    assert times == [0, 1500, 2100, 2700, 3300], times
    assert sel.current == "coax1" and changes[-1] == "coax1"

    # Right after (selector still open): no arming press, first step STEP_MS after the last press.
    remote.sent.clear()
    t0 = clock.t
    assert run(sel.select("coax2")) is None
    assert [(t - t0, k) for t, k in remote.sent] == [(600, "next_input")], remote.sent
    assert sel.current == "coax2"

    # 3 s later (maybe open, maybe closed): waits until surely closed, then arms.
    remote.sent.clear()
    clock.t += 3000
    t0 = clock.t
    assert run(sel.select("usb_audio")) is None          # coax2 -> usb_audio: forward 1, wraps
    assert [(t - t0, k) for t, k in remote.sent] == [(2000, "next_input"), (3500, "next_input")], remote.sent

    # Already there: nothing sent.
    remote.sent.clear()
    assert run(sel.select("usb_audio")) is None and remote.sent == []
    assert run(sel.select("nope")) == "unknown input"

    # A raw next_input long after: only arms (no move); one within the window: moves.
    clock.t += 10_000
    sel.raw("next_input")
    assert sel.current == "usb_audio"
    clock.t += 1500
    sel.raw("next_input")
    assert sel.current == "bluetooth"

    # Remembered across restarts.
    again = inputs.Selector(remote, lambda: None, path=path, now=clock.now, sleep=clock.sleep)
    assert again.current == "bluetooth"

    # 2026-11-23: stepping through the inputs, the amp stopped at OPT 1 while the presses said usb_audio. Once the
    # display names the input, it is the input: a select's guess and raw presses no longer move it.
    sel.seen("opt1")
    assert sel.current == "opt1" and sel.read
    clock.t += 10_000
    remote.sent.clear()
    assert run(sel.select("usb_audio")) is None
    assert [k for _, k in remote.sent] == ["next_input"] * 5, remote.sent     # opt1 -> usb_audio: arming + 4 steps
    assert sel.current == "opt1", "the display, not the guess, says where the amp landed"
    sel.seen("usb_audio")
    assert sel.current == "usb_audio"
    clock.t += 1500
    sel.raw("next_input")
    assert sel.current == "usb_audio", "a raw press waits for the display"
    sel.seen("nope")
    assert sel.current == "usb_audio", "an id outside the cycle is ignored"

print("all good")
