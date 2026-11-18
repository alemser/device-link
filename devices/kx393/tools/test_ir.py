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

# The service manual's "Remote Control Data" table (docs/research.md), copied separately to catch typos.
MANUAL = {"intro_scan_back": 0x1E, "intro_scan_forward": 0x1F, "counter_reset": 0x0D, "previous": 0x0B,
          "next": 0x0A, "rewind": 0x01, "play": 0x00, "fast_forward": 0x02, "record": 0x04, "stop": 0x03,
          "rec_mute": 0x05}


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


assert ir_codes.COMMANDS == MANUAL
assert set(ir_codes.KEYS) == set(ir_codes.COMMANDS) and len(ir_codes.KEYS) == len(ir_codes.COMMANDS) == 11
assert len(set(ir_codes.COMMANDS.values())) == len(ir_codes.COMMANDS)      # no code repeated
assert (ir_codes.ADDRESS, ir_codes.ADDRESS_CAPTURED) == (0x7F, 0x7A)

for address in (ir_codes.ADDRESS, ir_codes.ADDRESS_CAPTURED):
    for command in range(256):
        words = ir_codes.frame_command(command, address, repeats=1)
        # Pairs of line at 0 and released: the PIO always ends waiting for the next line at 0.
        assert len(words) == 2 + 64 + 2, command
        assert words[0] == 9000 and words[1] == 4500, command
        assert all(w == 560 for w in words[2:-1:2]), command    # every line-at-0 pulse has the same length
        assert words[-1] >= 40000, command                      # the silence between two keys
        assert decode(words) == [address, address ^ 0xFF, command, command ^ 0xFF], command

for key, command in ir_codes.COMMANDS.items():
    assert ir_codes.frame(key) == ir_codes.frame_command(command, 0x7F), key
    # The deck ignores a single frame (2026-11-18): each key goes out as REPEATS whole frames.
    one = ir_codes.frame_command(command, 0x7F, repeats=1)
    assert ir_codes.REPEATS == 6 and ir_codes.frame(key) == one * 6, key

if os.path.exists(MODEL):
    with open(MODEL) as f:
        codes = dict(re.findall(r"^  (\w+):.*\n\s+format: broadlink_ir\n\s+body: (\S+)", f.read(), re.M))
    # groove-rig has the five captured codes, at the captured address: the same command bytes as the manual's.
    assert set(codes) <= set(ir_codes.COMMANDS), set(codes) - set(ir_codes.COMMANDS)
    addresses = set()
    for key in codes:
        got = decode(captured(codes[key]))
        assert got[0] in (ir_codes.ADDRESS, ir_codes.ADDRESS_CAPTURED), key
        assert got == decode(ir_codes.frame_command(ir_codes.COMMANDS[key], got[0], repeats=1)), key
        addresses.add(got[0])
    if addresses != {ir_codes.ADDRESS}:
        print("note: groove-rig's codes are at address %s, the bridge's default is %02X (the deck answers both)"
              % ("/".join("%02X" % a for a in sorted(addresses)), ir_codes.ADDRESS))
else:
    print("warning: no %s, didn't compare with groove-rig" % MODEL)

print("all good")
