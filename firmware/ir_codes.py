"""The KX-393's remote codes, as pulses on the IR line.

NEC format: a long leader, the address, its inverse, the command and its inverse, each LSB first, and a final pulse.
The commands are the service manual's "Remote Control Data" table (schematic page, docs/research.md).

THE ADDRESS IS NOT SETTLED. The service manual says custom code 7F. The only captured codes (Remote Central, from
the KX-W421's remote VS90590, and groove-rig's model built from them) decode to 7A, with the same command bytes. The
first test on the deck decides: POST /ir/send?code=00&address=7A and &address=7F, and see which one plays. Until then
the manual's 7F is the default. tools/test_ir.py checks the command bytes against groove-rig.

Power has no code: STANDBY/ON is a panel key, pressed by the bridge on the KEY1 line (panel.py).

The timings are the NEC standard's, not measured on this device.

frame() runs the same in MicroPython (Pico) and in the computer's Python.
"""

ADDRESS = 0x7F                  # the service manual's custom code
ADDRESS_CAPTURED = 0x7A         # the KX-W421 remote's, captured: the other candidate

# In the manual's order, transport first.
KEYS = ("play", "stop", "rewind", "fast_forward", "previous", "next", "record", "rec_mute",
        "intro_scan_back", "intro_scan_forward", "counter_reset")

COMMANDS = {"play": 0x00, "rewind": 0x01, "fast_forward": 0x02, "stop": 0x03, "record": 0x04, "rec_mute": 0x05,
            "next": 0x0A, "previous": 0x0B, "counter_reset": 0x0D,
            "intro_scan_back": 0x1E, "intro_scan_forward": 0x1F}

LEADER_MARK, LEADER_SPACE = 9000, 4500      # µs
MARK, SPACE_0, SPACE_1 = 560, 560, 1690
END_SPACE = 40000       # silence after the code: the receiver needs it to tell two keys in a row apart


def frame_command(command, address=ADDRESS):
    """A command byte's times in µs: line at 0, line released, line at 0, and so on. Ends with a space."""
    words = [LEADER_MARK, LEADER_SPACE]
    for byte in (address, address ^ 0xFF, command, command ^ 0xFF):
        for bit in range(8):
            words += [MARK, SPACE_1 if byte >> bit & 1 else SPACE_0]
    words += [MARK, END_SPACE]
    return words


def frame(key):
    """A named key's times (see frame_command)."""
    return frame_command(COMMANDS[key])
