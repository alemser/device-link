"""GET /device: who this bridge is and what it can do, in the DeviceLink contract api 2 (device-link docs/contract-v2.md).

For now (2026-11-17) the MR 780 bridge can only update itself and set up Wi-Fi: the amp's state depends on the display
captures (docs/plan.md, step 3), and control on the IR wiring (step 4). So the description has no state fields and no
controls yet: the app shows the device, its firmware and nothing else. Each new capability goes in
here once it really exists. Nothing changes while the bridge runs, so the JSON is built once and served as bytes.

describe() runs the same in MicroPython (Pico) and in the computer's Python (tools/test_device.py).
"""

import json

API = 2                         # changes only when something stops being compatible
NAME = "mr780"                  # the name in discovery and on the network (mr780.local, AmpLink-MR780-XXXX); enviar.py reads it
KIND = "amplifier"
MODEL = "Magnat MR 780"         # the full name: in /device and, as "label", in discovery
FIRMWARE = "alemser/mr780-mod"  # the GitHub repository whose releases carry this firmware (enviar.py --publish)
FEATURES = ("update", "wifi_setup")

# The inputs in the order of the SOURCE knob and the remote, with groove-rig's ids
# (internal/catalog/profiles/magnat_mr780.yaml). The names are the manual's; the display's come from the captures.
# Not in the description yet: they become the "input" select once the bridge can switch and read the input.
INPUTS = (("usb_audio", "USB"), ("bluetooth", "BT"), ("phono", "PHONO"), ("cd", "CD"), ("dvd", "DVD"),
          ("aux1", "AUX 1"), ("aux2", "AUX 2"), ("tape", "TAPE"), ("line_in", "LINE IN"), ("fm", "FM"),
          ("dab", "DAB"), ("opt1", "OPT 1"), ("opt2", "OPT 2"), ("coax1", "COAX 1"), ("coax2", "COAX 2"))

net = None                      # ponte.py sets it: the discovery name comes from the chip ("MR780-D85E")
_cached = None


def describe(version, name):
    return {"api": API, "kind": KIND, "model": MODEL, "name": name, "bridge_version": version,
            "firmware": FIRMWARE, "features": list(FEATURES), "state": [], "controls": []}


async def handle(req, writer):
    """The /device route (see web.Publisher)."""
    global _cached
    import ota
    from web import reply
    if req.path != "/device":
        return await reply(writer, "404 Not Found", "text/plain", b"not found\n")
    if _cached is None:
        _cached = json.dumps(describe(await ota.current_version(), net.name if net else NAME)).encode()
    await reply(writer, "200 OK", "application/json", _cached)
