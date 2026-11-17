"""GET /device: who this bridge is and what it can do.

The contract is in the amp-link repository (docs/contract-v1.md). Everything here is fixed while the program runs:
the client reads it once on connecting. The version is the same as GET /update's.

For now (2026-11-09) the MR 780 bridge can only update itself and set up Wi-Fi: the amp's state depends on the
display captures (docs/plan.md, step 3). Each new capability goes into FEATURES once it really exists.

describe() runs the same in MicroPython (Pico) and in the computer's Python (tools/test_device.py).
"""

API = 1                         # changes only when something stops being compatible
NAME = "mr780"                  # the name in discovery and on the network (mr780.local, AmpLink-MR780-XXXX); enviar.py reads it
KIND = "amplifier"
MODEL = "Magnat MR 780"         # the full name: in /device and, as "label", in discovery
COLUMNS, ROWS = 16, 2           # the VFD: 2 lines of 16 characters (docs/research.md)
FEATURES = ("update", "wifi_setup")

# The inputs in the order of the SOURCE knob and the remote, with groove-rig's ids
# (internal/catalog/profiles/magnat_mr780.yaml). The names are the manual's; the display's come from the captures.
INPUTS = (("usb_audio", "USB"), ("bluetooth", "BT"), ("phono", "PHONO"), ("cd", "CD"), ("dvd", "DVD"),
          ("aux1", "AUX 1"), ("aux2", "AUX 2"), ("tape", "TAPE"), ("line_in", "LINE IN"), ("fm", "FM"),
          ("dab", "DAB"), ("opt1", "OPT 1"), ("opt2", "OPT 2"), ("coax1", "COAX 1"), ("coax2", "COAX 2"))


def describe(version):
    return {"api": API, "kind": KIND, "model": MODEL, "bridge_version": version,
            "inputs": [{"id": i, "name": name} for i, name in INPUTS],
            "display": {"columns": COLUMNS, "rows": ROWS},
            "features": list(FEATURES)}


async def handle(req, writer):
    """The /device route (see web.Publisher)."""
    import ota
    from web import reply, reply_json
    if req.path != "/device":
        return await reply(writer, "404 Not Found", "text/plain", b"not found\n")
    await reply_json(writer, describe(await ota.current_version()))
