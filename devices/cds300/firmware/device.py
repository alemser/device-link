"""GET /device: who this bridge is and what it can do, in the DeviceLink contract api 2 (device-link docs/contract-v2.md).

The app builds the CD-S300's screen from this: the state fields to show and the remote in groups (the
contract carries nothing else). Nothing changes while the bridge runs, so the JSON is built once, on the first request, and served as stored
bytes afterwards (a Pico should not rebuild 1 KB of JSON per request).

describe() runs the same in MicroPython (Pico) and CPython (tools/test_device.py).
"""

import json

import ir_codes

API = 2
NAME = "cds300"                 # the discovery and network name (cds300.local, AmpLink-CDS300-XXXX); send.py reads it
KIND = "cd_player"
MODEL = "Yamaha CD-S300"
FIRMWARE = "alemser/device-link/cds300"   # its releases: alemser/device-link, tagged cds300-<version> (send.py --publish)
FEATURES = ("control", "update", "wifi_setup")

STATE = (
    {"id": "transport", "type": "enum", "values": ["playing", "paused", "stopped", "loading", "open"]},
    {"id": "media.track", "type": "int", "label": "Track"},
    {"id": "media.elapsed_s", "type": "duration", "label": "Time"},
    {"id": "disc.tracks", "type": "int", "label": "Tracks"},
    {"id": "disc.total_s", "type": "duration", "label": "Total"},
    {"id": "lcd", "type": "lines", "label": "Display", "columns": 12},
)

CONTROLS = (
    ("transport", ("previous", "rewind", "play", "pause", "stop", "fast_forward", "next", "eject")),
    ("modes", ("repeat", "shuffle", "repeat_a_b", "program", "display", "dimmer")),
    ("numbers", ("digit_1", "digit_2", "digit_3", "digit_4", "digit_5", "digit_6", "digit_7", "digit_8", "digit_9",
                 "digit_0", "enter", "clear")),
    ("source", ("cd_usb", "pure_direct", "folder_down", "folder_up")),
)

_cached = None


def describe(version, name):
    controls = [{"group": g, "keys": list(keys)} for g, keys in CONTROLS]
    return {"api": API, "kind": KIND, "model": MODEL, "name": name, "bridge_version": version,
            "firmware": FIRMWARE, "features": list(FEATURES), "state": list(STATE), "controls": controls}


def check():
    """Every key in the remote is one the IR sender knows (tools/test_device.py)."""
    listed = [k for _, keys in CONTROLS for k in keys]
    return sorted(set(listed) - set(ir_codes.KEYS)), sorted(set(ir_codes.KEYS) - set(listed))


async def handle(req, writer):
    """Route /device (see web.Publisher)."""
    global _cached
    import ota
    from web import reply, not_found
    if req.path != "/device":
        return await not_found(writer)
    if _cached is None:
        from ponte import net
        _cached = json.dumps(describe(await ota.current_version(), net.name)).encode()
    await reply(writer, "200 OK", "application/json", _cached)
