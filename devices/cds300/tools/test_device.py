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

raw = json.dumps(device.describe("abcd1234", "CDS300-D85E"))
d = json.loads(raw)
assert d["api"] == 2 and d["kind"] == "cd_player" and d["model"] == "Yamaha CD-S300"
assert d["name"] == "CDS300-D85E" and d["bridge_version"] == "abcd1234"
assert d["firmware"] == "alemser/device-link/cds300"
assert d["features"] == ["control", "update", "wifi_setup"]
assert [s["id"] for s in d["state"]] == ["transport", "media.track", "media.elapsed_s", "disc.tracks", "disc.total_s",
                                         "lcd"]
assert [c["group"] for c in d["controls"]] == ["transport", "modes", "numbers", "source"]
assert d["controls"][0]["keys"][:3] == ["previous", "rewind", "play"]
assert "settings" not in d, "the contract: device, state and remote only"
# The remote holds exactly the keys the IR sender can send: none missing, none unknown.
assert device.check() == ([], []), device.check()
# Small enough to serve from a Pico in one go (contract: under 1.5 KB).
assert len(raw) < 1500, len(raw)
assert device.NAME == "cds300"      # tools/enviar.py and discovery use this name
print("all good (%d bytes)" % len(raw))
