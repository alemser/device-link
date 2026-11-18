"""GET /device: who this bridge is and what it can do, in the DeviceLink contract api 2 (device-link docs/contract-v2.md).

The app builds the KX-393's screen from this: the state fields to show and the remote in groups (the
contract carries nothing else). Nothing changes while the bridge runs, so the JSON is built once, on the first request, and served as stored
bytes afterwards (a Pico should not rebuild 1 KB of JSON per request).

No state fields yet: the state reader (the microcontroller's mode lines, then maybe the display's lines) comes after
the bench (docs/plan.md). The planned fields are power, transport, the tape type, Dolby and the counter.

describe() runs the same in MicroPython (Pico) and CPython (tools/test_device.py).
"""


import ir_codes

API = 2
NAME = "kx393"                  # the discovery and network name (kx393.local, AmpLink-KX393-XXXX); send.py reads it
KIND = "tape_deck"
MODEL = "Yamaha KX-393"
FIRMWARE = "alemser/device-link/kx393"   # its releases: alemser/device-link, tagged kx393-<version> (send.py --publish)
FEATURES = ("control", "update", "wifi_setup")
PANEL_KEYS = ("power_toggle",)  # pressed on the KEY1 line, not sent as IR (panel.py)

STATE = ()

CONTROLS = (
    ("power", ("power_toggle",)),
    ("transport", ("previous", "rewind", "play", "stop", "fast_forward", "next")),
    ("record", ("record", "rec_mute")),
    ("modes", ("intro_scan_back", "intro_scan_forward", "counter_reset")),
)

net = None                      # ponte.py sets it: the discovery name comes from the chip ("KX393-D85E")


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
    """Route /device (see web.Publisher): built once by the base and served as stored bytes."""
    from web import serve_description
    await serve_description(req, writer, lambda version: describe(version, net.name if net else NAME))
