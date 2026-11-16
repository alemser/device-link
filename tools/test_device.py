#!/usr/bin/env python3
"""Testa no computador a descrição da ponte (firmware/device.py).

    python3 tools/test_device.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import device   # noqa: E402

d = json.loads(json.dumps(device.describe("abcd1234")))
assert d["api"] == 1
assert d["kind"] == "amplifier"
assert d["model"] == "Magnat MR 780"
assert d["bridge_version"] == "abcd1234"
assert len(d["inputs"]) == 15
# A ordem do ciclo de entradas do groove-rig (profiles/magnat_mr780.yaml): não mudar sem mudar lá.
assert [i["id"] for i in d["inputs"]] == ["usb_audio", "bluetooth", "phono", "cd", "dvd", "aux1", "aux2", "tape",
                                          "line_in", "fm", "dab", "opt1", "opt2", "coax1", "coax2"]
assert d["display"] == {"columns": 16, "rows": 2}
assert d["features"] == ["update", "wifi_setup"]
assert "volume_db" not in d and "tone_db" not in d     # ainda não se sabe: a app esconde o que falta
print("tudo certo")
