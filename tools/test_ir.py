#!/usr/bin/env python3
"""Checks firmware/ir_codes.py: the NEC format, the decoded Remote Central table and groove-rig's codes.

    python3 tools/test_ir.py

The groove-rig comparison uses the file in ~/Projects/groove-rig; without it, that part is skipped with a warning.
"""

import base64
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import ir_codes   # noqa: E402

MODEL = os.path.expanduser("~/Projects/groove-rig/internal/catalog/models/yamaha_kx393.yaml")
TICK_US = 269 / 8.192           # Broadlink's time unit
LONG_US = 1000                  # above this, the space is a 1 bit

# The KX-W421's Pronto codes from Remote Central, decoded (docs/research.md), copied separately to catch typos.
DECODED = {"play": 0x00, "rewind": 0x01, "fast_forward": 0x02, "stop": 0x03, "record": 0x04}


def decode(words):
    """The 4 bytes of a NEC code, from its times (line at 0, line released, ...)."""
    out = [0, 0, 0, 0]
    for i in range(32):
        if words[2 + 2 * i + 1] > LONG_US:
            out[i // 8] |= 1 << (i % 8)
    return out


def captured(body):
    """The times in µs of a code in Broadlink's format."""
    data = base64.b64decode(body)
    payload = data[4:4 + (data[2] | data[3] << 8)]
    times, i = [], 0
    while i < len(payload):
        value = payload[i]
        i += 1
        if value == 0:
            value = payload[i] << 8 | payload[i + 1]
            i += 2
        times.append(value * TICK_US)
    return times


assert ir_codes.COMMANDS == DECODED
assert set(ir_codes.KEYS) == set(ir_codes.COMMANDS) and len(ir_codes.KEYS) == len(ir_codes.COMMANDS)
assert len(set(ir_codes.COMMANDS.values())) == len(ir_codes.COMMANDS)      # no code repeated

for command in range(256):
    words = ir_codes.frame_command(command)
    # Pairs of line at 0 and released: the PIO always ends waiting for the next line at 0.
    assert len(words) == 2 + 64 + 2, command
    assert words[0] == 9000 and words[1] == 4500, command
    assert all(w == 560 for w in words[2:-1:2]), command    # every line-at-0 pulse has the same length
    assert words[-1] >= 40000, command                      # the silence between two keys
    assert decode(words) == [0x7A, 0x85, command, command ^ 0xFF], command

for key, command in ir_codes.COMMANDS.items():
    assert ir_codes.frame(key) == ir_codes.frame_command(command), key

if os.path.exists(MODEL):
    with open(MODEL) as f:
        codes = dict(re.findall(r"^  (\w+):.*\n\s+format: broadlink_ir\n\s+body: (\S+)", f.read(), re.M))
    assert set(codes) == set(ir_codes.COMMANDS), set(codes) ^ set(ir_codes.COMMANDS)
    for key in ir_codes.COMMANDS:
        assert decode(captured(codes[key])) == decode(ir_codes.frame(key)), key
else:
    print("warning: no %s, didn't compare with groove-rig" % MODEL)

print("all good")
