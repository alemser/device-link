"""The CD-S300's remote codes, as pulses on the IR line.

NEC format: a long leader, the address 79, its inverse (86), the command and its inverse, each LSB first, and a final
pulse. The commands are the service manual's table (page 56, docs/research.md). The names are groove-rig's
(internal/catalog/models/yamaha_cd_s300.yaml), and tools/test_ir.py checks the bits against that file.

The CD-S300's remote has no power key: the device has no standby (docs/plan.md, "Power on and off").

The timings are the NEC standard's, not measured on this device.

frame() runs the same in MicroPython (Pico) and in the computer's Python.
"""

ADDRESS = 0x79

# In the remote's order: mode, transport, play modes, display, numbers, folders.
KEYS = ("cd_usb", "pure_direct", "eject",
        "play", "pause", "stop", "previous", "next", "rewind", "fast_forward",
        "repeat", "shuffle", "program", "repeat_a_b",
        "display", "dimmer",
        "digit_1", "digit_2", "digit_3", "digit_4", "digit_5", "digit_6", "digit_7", "digit_8", "digit_9", "digit_0",
        "enter", "clear", "folder_down", "folder_up")

COMMANDS = {"cd_usb": 0x6F, "pure_direct": 0x6E, "eject": 0x01,
            "play": 0x02, "pause": 0x55, "stop": 0x56, "previous": 0x04, "next": 0x07,
            "rewind": 0x05, "fast_forward": 0x06,
            "repeat": 0x08, "shuffle": 0x1B, "program": 0x0C, "repeat_a_b": 0x09,
            "display": 0x0A, "dimmer": 0x54,
            "digit_0": 0x10, "digit_1": 0x11, "digit_2": 0x12, "digit_3": 0x13, "digit_4": 0x14,
            "digit_5": 0x15, "digit_6": 0x16, "digit_7": 0x17, "digit_8": 0x18, "digit_9": 0x19,
            "enter": 0x3F, "clear": 0x0D, "folder_down": 0x6A, "folder_up": 0x69}

LEADER_MARK, LEADER_SPACE = 9000, 4500      # µs
MARK, SPACE_0, SPACE_1 = 560, 560, 1690
END_SPACE = 40000       # silence after the code: the receiver needs it to tell two keys in a row apart


def frame(key):
    """A key's times in µs: line at 0, line released, line at 0, and so on. Ends with a space."""
    command = COMMANDS[key]
    words = [LEADER_MARK, LEADER_SPACE]
    for byte in (ADDRESS, ADDRESS ^ 0xFF, command, command ^ 0xFF):
        for bit in range(8):
            words += [MARK, SPACE_1 if byte >> bit & 1 else SPACE_0]
    words += [MARK, END_SPACE]
    return words
