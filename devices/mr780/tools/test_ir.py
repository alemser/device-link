#!/usr/bin/env python3
"""Checks firmware/ir_codes.py: the NEC format, the codes learned on oceano-0003 and groove-rig's built-in ones.

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

PROFILE = os.path.expanduser("~/Projects/groove-rig/internal/catalog/profiles/magnat_mr780.yaml")
TICK_US = 269 / 8.192           # Broadlink's time unit
LONG_US = 1000                  # above this, the space is a 1 bit


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


# The codes learned on oceano-0003 (/var/lib/groove-rig/codebook.yaml), decoded on 2026-11-18, copied separately to
# catch typos in ir_codes.py.
LEARNED = {"power_toggle": 0x12, "volume_up": 0x1B, "volume_down": 0x1F, "mute": 0x0D, "prev_input": 0x1E,
           "next_input": 0x1A, "previous": 0x13, "next": 0x58, "tune_down": 0x11, "tune_up": 0x5A}

assert ir_codes.ADDRESS == 0x40
assert ir_codes.COMMANDS == LEARNED
assert set(ir_codes.KEYS) == set(ir_codes.COMMANDS) and len(ir_codes.KEYS) == len(ir_codes.COMMANDS)
assert len(set(ir_codes.COMMANDS.values())) == len(ir_codes.COMMANDS)      # no code repeated

for command in range(256):
    words = ir_codes.frame_command(command)
    # Pairs of line at 0 and released: the PIO always ends waiting for the next line at 0.
    assert len(words) == 2 + 64 + 2, command
    assert words[0] == 9000 and words[1] == 4500, command
    assert all(w == 560 for w in words[2:-1:2]), command    # every line-at-0 pulse has the same length
    assert words[-1] >= 40000, command                      # the silence between two keys
    assert decode(words) == [0x40, 0xBF, command, command ^ 0xFF], command

for key, command in ir_codes.COMMANDS.items():
    assert ir_codes.frame(key) == ir_codes.frame_command(command), key

if os.path.exists(PROFILE):
    with open(PROFILE) as f:
        codes = dict(re.findall(r"^  (\w+):\n\s+format: broadlink_ir\n\s+body: (\S+)", f.read(), re.M))
    # The built-in profile has three of the keys; each must decode to the same bytes as here.
    assert codes and set(codes) <= set(ir_codes.COMMANDS), set(codes) - set(ir_codes.COMMANDS)
    for key, body in codes.items():
        got = decode(captured(body)[0:])
        assert got == [ir_codes.ADDRESS, ir_codes.ADDRESS ^ 0xFF, ir_codes.COMMANDS[key],
                       ir_codes.COMMANDS[key] ^ 0xFF], (key, ["%02X" % b for b in got])
else:
    print("warning: no %s, didn't compare with groove-rig" % PROFILE)

print("all good")
