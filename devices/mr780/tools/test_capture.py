#!/usr/bin/env python3
"""Tests the capture's request limits and sample layout (firmware/capture.py) on the computer.

    python3 tools/test_capture.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import capture   # noqa: E402  (rp2 and machine are imported only inside Capture.run)
import capture as fw   # noqa: E402
import bus_capture as tool   # noqa: E402  (tools/, the script's own folder)

# plan(): limits, whole words, the memory cap.
assert capture.plan(2_000_000, 30) == (2_000_000, 60_000)
assert capture.plan(2_000_000, 1000) == (2_000_000, capture.MAX_SAMPLES)
assert capture.plan(1_000_003, 1) == (1_000_003, 1000)          # 1000.003 -> 1000, a multiple of 8
assert capture.plan(5_000, 30).startswith("rate")
assert capture.plan(100_000_000, 30).startswith("rate")
assert capture.plan(2_000_000, 0) == "ms must be positive"
assert capture.plan(10_000, 0 + 1) == (10_000, 8) or capture.plan(10_000, 1) == "too short"

# parse(): two samples per byte, the earliest in the low nibble, as the PIO packs them (SHIFT_RIGHT, 4 bits).
assert fw.parse(bytes([0x21, 0x43]), 4) == [1, 2, 3, 4]
assert fw.parse(bytes([0xF0]), 2) == [0, 15]

# The Mac tool's run-length helper and VCD writer.
assert tool.runs([0, 0, 1, 1, 1, 0]) == [[0, 2], [1, 3], [0, 1]]
info = {"rate": 1_000_000, "samples": 4, "pins": ["A", "B", "C", "LIGA"]}
v = tool.vcd(info, bytes([0x10, 0x11]))          # samples 0, 1, 1, 1: A rises at t=1
assert "#0" in v and "#1\n1!" in v, v
print(tool.summary(info, bytes([0x10, 0x11])).splitlines()[0])
print("all good")
