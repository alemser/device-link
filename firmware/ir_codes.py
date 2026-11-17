"""The KX-393's remote codes, as pulses on the IR line.

NEC format: a long leader, the address 7A, its inverse (85), the command and its inverse, each LSB first, and a final
pulse. The KX-393 was sold without a remote; the optional one is the RKX1, shared with other Yamaha decks. No code
list exists for the KX-393 itself: these are the KX-W421's codes from Remote Central's Pronto database, decoded to
NEC (docs/research.md, "The remote"). The names are groove-rig's (internal/catalog/models/yamaha_kx393.yaml), and
tools/test_ir.py checks the bits against that file.

NOT YET TESTED ON THE DECK. Pause, rec mute, search, intro scan, counter reset and power have no published code:
POST /ir/send?code=05 sends any command byte, to find them (tools/ir_sweep.py). Each one found goes into COMMANDS.

The timings are the NEC standard's, not measured on this device.

frame() runs the same in MicroPython (Pico) and in the computer's Python.
"""

ADDRESS = 0x7A

# In the remote's order.
KEYS = ("play", "stop", "rewind", "fast_forward", "record")

COMMANDS = {"play": 0x00, "rewind": 0x01, "fast_forward": 0x02, "stop": 0x03, "record": 0x04}

LEADER_MARK, LEADER_SPACE = 9000, 4500      # µs
MARK, SPACE_0, SPACE_1 = 560, 560, 1690
END_SPACE = 40000       # silence after the code: the receiver needs it to tell two keys in a row apart


def frame_command(command):
    """A command byte's times in µs: line at 0, line released, line at 0, and so on. Ends with a space."""
    words = [LEADER_MARK, LEADER_SPACE]
    for byte in (ADDRESS, ADDRESS ^ 0xFF, command, command ^ 0xFF):
        for bit in range(8):
            words += [MARK, SPACE_1 if byte >> bit & 1 else SPACE_0]
    words += [MARK, END_SPACE]
    return words


def frame(key):
    """A named key's times (see frame_command)."""
    return frame_command(COMMANDS[key])
