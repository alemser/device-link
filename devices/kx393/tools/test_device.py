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

raw = json.dumps(device.describe("abcd1234", "KX393-1A2B"))
d = json.loads(raw)
assert d["api"] == 2 and d["kind"] == "tape_deck" and d["model"] == "Yamaha KX-393"
assert d["name"] == "KX393-1A2B" and d["bridge_version"] == "abcd1234"
assert d["firmware"] == "alemser/device-link/kx393"
assert d["features"] == ["control", "update", "wifi_setup"]
assert d["state"] == []                 # no state reader yet (docs/plan.md)
assert [c["group"] for c in d["controls"]] == ["power", "transport", "record", "modes"]
assert d["controls"][0]["keys"] == ["power_toggle"]
assert d["controls"][1]["keys"] == ["previous", "rewind", "play", "stop", "fast_forward", "next"]
assert "settings" not in d, "the contract: device, state and remote only"
# The remote holds exactly the keys the IR sender can send: none missing, none unknown.
assert device.check() == ([], []), device.check()
# Small enough to serve from a Pico in one go (contract: under 1.5 KB).
assert len(raw) < 1500, len(raw)
assert device.NAME == "kx393"       # tools/send.py and discovery use this name
print("all good (%d bytes)" % len(raw))
