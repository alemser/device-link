#!/usr/bin/env python3
"""Checks firmware/ir_codes.py: the NEC format, the manual's table and groove-rig's codes.

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

MODEL = os.path.expanduser("~/Projects/groove-rig/internal/catalog/models/yamaha_cd_s300.yaml")
TICK_US = 269 / 8.192           # unidade de tempo do Broadlink
LONG_US = 1000                  # above this, the space is a 1 bit

# The service manual's table, page 56 (docs/research.md), copied separately to catch typos.
MANUAL = {"cd_usb": 0x6F, "pure_direct": 0x6E, "eject": 0x01, "program": 0x0C, "repeat": 0x08, "shuffle": 0x1B,
          "dimmer": 0x54, "repeat_a_b": 0x09, "display": 0x0A, "digit_1": 0x11, "digit_2": 0x12, "digit_3": 0x13,
          "digit_4": 0x14, "digit_5": 0x15, "digit_6": 0x16, "digit_7": 0x17, "digit_8": 0x18, "digit_9": 0x19,
          "digit_0": 0x10, "enter": 0x3F, "clear": 0x0D, "rewind": 0x05, "fast_forward": 0x06, "pause": 0x55,
          "previous": 0x04, "play": 0x02, "next": 0x07, "stop": 0x56, "folder_down": 0x6A, "folder_up": 0x69}


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
assert set(ir_codes.KEYS) == set(ir_codes.COMMANDS) and len(ir_codes.KEYS) == len(ir_codes.COMMANDS) == 30
assert len(set(ir_codes.COMMANDS.values())) == 30       # nenhum código repetido

for key, command in ir_codes.COMMANDS.items():
    words = ir_codes.frame(key)
    # Pares de linha em 0 e solta: o PIO termina sempre esperando a próxima linha em 0.
    assert len(words) == 2 + 64 + 2, key
    assert words[0] == 9000 and words[1] == 4500, key
    assert all(w == 560 for w in words[2:-1:2]), key    # todo pulso de linha em 0 tem o mesmo tamanho
    assert words[-1] >= 40000, key                      # the silence between two keys
    assert decode(words) == [0x79, 0x86, command, command ^ 0xFF], key

if os.path.exists(MODEL):
    with open(MODEL) as f:
        codes = dict(re.findall(r"^  (\w+):.*\n\s+format: broadlink_ir\n\s+body: (\S+)", f.read(), re.M))
    # groove-rig carries the family's power_toggle; the CD-S300's remote has no such key.
    assert set(codes) - {"power_toggle"} == set(ir_codes.COMMANDS), set(codes) ^ set(ir_codes.COMMANDS)
    for key in ir_codes.COMMANDS:
        want = captured(codes[key])
        assert decode(want) == decode(ir_codes.frame(key)), key
else:
    print("warning: no %s, didn't compare with groove-rig" % MODEL)

print("all good")
