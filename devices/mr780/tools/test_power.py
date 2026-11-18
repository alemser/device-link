#!/usr/bin/env python3
"""Tests the on/standby decision from the LIGA wire (firmware/power.py) on the computer.

    python3 tools/test_power.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import power   # noqa: E402  (machine is imported only inside Power, so decide() runs here)

S = power.STABLE_MS

# Unknown until the line has held long enough, then whatever the line says.
assert power.decide(1, 0, None) is None
assert power.decide(1, S - 1, None) is None
assert power.decide(1, S, None) == "on"
assert power.decide(0, S, None) == "standby"

# A glitch shorter than STABLE_MS keeps the state it had.
assert power.decide(0, S - 1, "on") == "on"
assert power.decide(1, S - 1, "standby") == "standby"
assert power.decide(0, S + 5000, "on") == "standby"
assert power.decide(1, S + 5000, "standby") == "on"

# The warm-up: 30, 29 ... 1 seconds left, then None; None when power-on wasn't seen.
assert power.warmup_left(None) is None
assert power.warmup_left(0) == 30
assert power.warmup_left(999) == 30
assert power.warmup_left(1000) == 29
assert power.warmup_left(29999) == 1
assert power.warmup_left(30000) is None
assert power.warmup_left(120000) is None

assert power.LIGA_PIN == 5      # the analyzer's channel 4: the same harness serves both
print("all good")
