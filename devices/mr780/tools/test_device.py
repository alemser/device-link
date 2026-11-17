#!/usr/bin/env python3
"""Tests the bridge's description (firmware/device.py) on the computer.

    python3 tools/test_device.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import device   # noqa: E402

d = json.loads(json.dumps(device.describe("abcd1234", "MR780-D85E")))
assert d["api"] == 2
assert d["kind"] == "amplifier"
assert d["model"] == "Magnat MR 780" and d["name"] == "MR780-D85E"
assert d["bridge_version"] == "abcd1234"
assert d["firmware"] == "alemser/mr780-mod"
assert d["features"] == ["update", "wifi_setup"]
assert d["state"] == [] and d["controls"] == [], "nothing is known yet: nothing to show"
assert "settings" not in d, "the contract: device, state and remote only"
assert len(device.INPUTS) == 15
# groove-rig's input cycle order (profiles/magnat_mr780.yaml): don't change it without changing it there.
assert [i for i, _ in device.INPUTS] == ["usb_audio", "bluetooth", "phono", "cd", "dvd", "aux1", "aux2", "tape",
                                         "line_in", "fm", "dab", "opt1", "opt2", "coax1", "coax2"]
print("all good")
