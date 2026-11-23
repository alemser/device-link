#!/usr/bin/env python3
"""Checks the bridge's description (firmware/device.py) against the DeviceLink contract api 2.

    python3 tools/test_device.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import device   # noqa: E402

raw = json.dumps(device.describe("abcd1234", "MR780-D85E"))
d = json.loads(raw)
assert d["api"] == 2
assert d["kind"] == "amplifier"
assert d["model"] == "Magnat MR 780" and d["name"] == "MR780-D85E"
assert d["bridge_version"] == "abcd1234"
assert d["firmware"] == "alemser/device-link/mr780"
assert d["features"] == ["control", "update", "wifi_setup"]
assert d["state"] == [{"id": "power", "type": "enum", "values": ["on", "standby"]},
                      {"id": "warmup_s", "type": "duration", "label": "Warming up"},
                      {"id": "lcd", "type": "lines", "label": "Display", "columns": 16},
                      {"id": "muted", "type": "bool", "label": "Mute"},
                      {"id": "direct", "type": "bool", "label": "Direct"}]
assert [c["group"] for c in d["controls"]] == ["power", "volume", "mute", "input", "transport", "tuner"]
assert d["controls"][0] == {"group": "power", "keys": ["power_toggle"]}
# Volume in the contract's one form for it: a step, its value the volume the display shows (device-link#4).
assert d["controls"][1] == {"group": "volume", "steps": [{"target": "volume", "state": "volume_db", "label": "Volume"}]}
assert d["controls"][2] == {"group": "mute", "keys": ["mute"]}
assert d["controls"][4] == {"group": "transport", "keys": ["previous", "next"]}
assert d["controls"][5] == {"group": "tuner", "keys": ["tune_down", "tune_up"]}
assert not [k for c in d["controls"] for k in c.get("keys", []) if k.startswith("volume")], "no volume keys"
# The input select (inputs.py): every input, in the cycle's order, pressed as select_<id>.
sel = d["controls"][3]["select"]
assert sel["state"] == "input_id" and len(sel["options"]) == 15
assert sel["options"][2] == {"id": "phono", "name": "PHONO", "key": "select_phono"}
assert "settings" not in d, "the contract: device, state and remote only"
# The remote holds exactly the keys the IR sender can send: none missing, none unknown.
assert device.check() == ([], []), device.check()
# Small enough for a Pico: chosen bound, no larger than the SP103's ~1.7 KB, which its bridge serves as stored bytes
# (contract, "Light enough for a Pico").
assert len(raw) < 1800, len(raw)
assert device.NAME == "mr780"       # tools/send.py and discovery use this name
assert len(device.INPUTS) == 15
# groove-rig's input cycle order (profiles/magnat_mr780.yaml): don't change it without changing it there.
assert [i for i, _ in device.INPUTS] == ["usb_audio", "bluetooth", "phono", "cd", "dvd", "aux1", "aux2", "tape",
                                         "line_in", "fm", "dab", "opt1", "opt2", "coax1", "coax2"]
print("all good (%d bytes)" % len(raw))
