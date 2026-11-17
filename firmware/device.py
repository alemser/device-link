"""GET /device: who this bridge is and what it can do, in the DeviceLink contract api 2 (device-link docs/contract-v2.md).

The app builds the KX-393's screen from this: the state fields to show and the remote in groups (the
contract carries nothing else). Nothing changes while the bridge runs, so the JSON is built once, on the first request, and served as stored
bytes afterwards (a Pico should not rebuild 1 KB of JSON per request).

No state fields yet: the state reader (the microcontroller's mode lines, then maybe the display's lines) comes after
the bench (docs/plan.md). The planned fields are power, transport, the tape type, Dolby and the counter.

describe() runs the same in MicroPython (Pico) and CPython (tools/test_device.py).
"""

import json

import ir_codes

API = 2
NAME = "kx393"                  # the discovery and network name (kx393.local, AmpLink-KX393-XXXX); enviar.py reads it
KIND = "tape_deck"
MODEL = "Yamaha KX-393"
FIRMWARE = "alemser/kx393-mod"  # the GitHub repository whose releases carry this firmware (enviar.py --publish)
FEATURES = ("control", "update", "wifi_setup")
PANEL_KEYS = ("power_toggle",)  # pressed on the KEY1 line, not sent as IR (panel.py)

STATE = ()

CONTROLS = (
    ("power", ("power_toggle",)),
    ("transport", ("previous", "rewind", "play", "stop", "fast_forward", "next")),
    ("record", ("record", "rec_mute")),
    ("modes", ("intro_scan_back", "intro_scan_forward", "counter_reset")),
)

_cached = None


def describe(version, name):
    controls = [{"group": g, "keys": list(keys)} for g, keys in CONTROLS]
    return {"api": API, "kind": KIND, "model": MODEL, "name": name, "bridge_version": version,
            "firmware": FIRMWARE, "features": list(FEATURES), "state": list(STATE), "controls": controls}


def check():
    """Every key in the remote is one the bridge can press (tools/test_device.py)."""
    listed = [k for _, keys in CONTROLS for k in keys]
    known = set(ir_codes.KEYS) | set(PANEL_KEYS)
    return sorted(set(listed) - known), sorted(known - set(listed))


async def handle(req, writer):
    """Route /device (see web.Publisher)."""
    global _cached
    import ota
    from web import reply
    if req.path != "/device":
        return await reply(writer, "404 Not Found", "text/plain", b"not found\n")
    if _cached is None:
        from ponte import net
        _cached = json.dumps(describe(await ota.current_version(), net.name)).encode()
    await reply(writer, "200 OK", "application/json", _cached)
