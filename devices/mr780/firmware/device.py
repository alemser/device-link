"""GET /device: who this bridge is and what it can do, in the DeviceLink contract api 2 (device-link docs/contract-v2.md).

The app builds the MR 780's screen from this: the state fields to show and the remote in groups (the contract carries
nothing else). Nothing changes while the bridge runs, so the JSON is built once, on the first request, and served as
stored bytes afterwards (a Pico should not rebuild 1 KB of JSON per request).

Since 2026-11-18 (owner): the read-only phase, as on the CD-S300 and the KX-393: device, state and remote, nothing
written to the display. The remote holds the ten keys whose codes are known (ir_codes.py), with the input as a
select that steps the cycle (inputs.py). State: power from the LIGA wire (power.py); the display's two lines, the
volume, mute, the warm-up and the input from reading the display (screen.py, docs/protocol.md).

describe() runs the same in MicroPython (Pico) and in the computer's Python (tools/test_device.py).
"""


import ir_codes
import screen

API = 2                         # changes only when something stops being compatible
NAME = "mr780"                  # the name in discovery and on the network (mr780.local, DeviceLink-MR780-XXXX); send.py reads it
KIND = "amplifier"
MODEL = "Magnat MR 780"         # the full name: in /device and, as "label", in discovery
FIRMWARE = "alemser/device-link/mr780"   # its releases: alemser/device-link, tagged mr780-<version> (send.py --publish)
FEATURES = ("control", "update", "wifi_setup")

STATE = (
    {"id": "power", "type": "enum", "values": ["on", "standby"]},     # the LIGA wire (power.py)
    {"id": "warmup_s", "type": "duration", "label": "Warming up"},    # the display's countdown; null outside it
    {"id": "lcd", "type": "lines", "label": "Display", "columns": screen.COLUMNS},
    {"id": "muted", "type": "bool", "label": "Mute"},
)   # volume_db is the volume step's value, so it isn't repeated here (contract, State fields)

# The steps (contract: volume is a step): the IR key each direction presses (control.py), and the state field that
# holds the value, the last volume the display showed (screen.py).
STEPS = {"volume": {"up": "volume_up", "down": "volume_down", "state": "volume_db", "label": "Volume"}}

CONTROLS = (
    ("power", ("power_toggle",)),
    ("volume", "steps"),
    ("mute", ("mute",)),                        # a group holds one kind of control: the mute key has its own
    ("input", "select"),                        # the select below (inputs.py steps the cycle to the chosen input)
    ("transport", ("previous", "next")),        # the remote's ◄◄ ►►: Bluetooth and USB
    ("tuner", ("tune_down", "tune_up")),
)
SELECT_KEYS = ("prev_input", "next_input")      # IR keys the select drives, not shown as buttons
STEP_KEYS = tuple(s[d] for s in STEPS.values() for d in ("up", "down"))     # IR keys the steps press

# The inputs in the order of the SOURCE knob and the remote, with groove-rig's ids
# (internal/catalog/profiles/magnat_mr780.yaml). The names are the manual's; the display's come from the captures.
# The "input" select's options, each pressed as the key select_<id> (inputs.py steps the cycle to it).
INPUTS = (("usb_audio", "USB"), ("bluetooth", "BT"), ("phono", "PHONO"), ("cd", "CD"), ("dvd", "DVD"),
          ("aux1", "AUX 1"), ("aux2", "AUX 2"), ("tape", "TAPE"), ("line_in", "LINE IN"), ("fm", "FM"),
          ("dab", "DAB"), ("opt1", "OPT 1"), ("opt2", "OPT 2"), ("coax1", "COAX 1"), ("coax2", "COAX 2"))

net = None                      # ponte.py sets it: the discovery name comes from the chip ("MR780-D85E")


def _select():
    return {"state": "input_id",
            "options": [{"id": i, "name": n, "key": "select_" + i} for i, n in INPUTS]}


def _steps():
    return [{"target": t, "state": s["state"], "label": s["label"]} for t, s in STEPS.items()]


def _group(group, content):
    if content == "select":
        return {"group": group, "select": _select()}
    if content == "steps":
        return {"group": group, "steps": _steps()}
    return {"group": group, "keys": list(content)}


def describe(version, name):
    controls = [_group(g, c) for g, c in CONTROLS]
    return {"api": API, "kind": KIND, "model": MODEL, "name": name, "bridge_version": version,
            "firmware": FIRMWARE, "features": list(FEATURES), "state": list(STATE), "controls": controls}


def check():
    """Every key in the remote is one the IR sender knows, and every known one is in the remote or driven by the
    select or a step (tools/test_device.py)."""
    listed = [k for _, c in CONTROLS if isinstance(c, tuple) for k in c] + list(STEP_KEYS)
    known = set(ir_codes.KEYS) - set(SELECT_KEYS)
    return sorted(set(listed) - known), sorted(known - set(listed))


async def handle(req, writer):
    """Route /device (see web.Publisher): built once by the base and served as stored bytes."""
    from web import serve_description
    await serve_description(req, writer, lambda version: describe(version, net.name if net else NAME))
