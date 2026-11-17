"""GET /device: who this bridge is and what it can do, in the DeviceLink contract api 2 (device-link docs/contract-v2.md).

The app builds the KX-393's screen from this: the state fields to show, the remote in groups, and the settings (none
here). Nothing changes while the bridge runs, so the JSON is built once, on the first request, and served as stored
bytes afterwards (a Pico should not rebuild 1 KB of JSON per request).

No state fields yet: how the bridge will know the deck's state (the display, or the microcontroller's lines) waits for
the service manual and the photos (docs/plan.md). The planned fields are transport, the counter, the tape type and
Dolby NR.

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

STATE = ()

CONTROLS = (
    ("transport", ("rewind", "play", "stop", "fast_forward")),
    ("record", ("record",)),
)

_cached = None


def describe(version, name):
    controls = [{"group": g, "keys": list(keys)} for g, keys in CONTROLS]
    return {"api": API, "kind": KIND, "model": MODEL, "name": name, "bridge_version": version,
            "firmware": FIRMWARE, "features": list(FEATURES), "state": list(STATE), "controls": controls,
            "settings": []}


def check():
    """Every key in the remote is one the IR sender knows (tools/test_device.py)."""
    listed = [k for _, keys in CONTROLS for k in keys]
    return sorted(set(listed) - set(ir_codes.KEYS)), sorted(set(ir_codes.KEYS) - set(listed))


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
