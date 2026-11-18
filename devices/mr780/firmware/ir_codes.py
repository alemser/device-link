"""The MR 780's remote codes, as pulses on the IR line.

NEC format: a long leader, the address 40, its inverse (BF), the command and its inverse, each LSB first, and a final
pulse. Where the bytes come from:

- groove-rig's built-in profile (internal/catalog/profiles/magnat_mr780.yaml, Broadlink, 2026-09): next_input,
  prev_input and volume_down. tools/test_ir.py decodes them against this file.
- The codes learned on the oceano-0003 board (/var/lib/groove-rig/codebook.yaml, Broadlink, 2026-11-15 and 16): all
  ten keys below, decoded on 2026-11-18 (every one 40/BF, checksums right, the three above the same bytes). The
  decoded table is copied in tools/test_ir.py.

next and previous are the remote's ◄◄ and ►► (Bluetooth and USB); tune_down and tune_up are the tuner's. A key not in
this list can be tried on the amp with tools/ir_try.py; each new one goes in COMMANDS and KEYS, and in
device.CONTROLS.

The timings are the NEC standard's, not measured on this device.

frame() runs the same in MicroPython (Pico) and in the computer's Python.
"""

ADDRESS = 0x40

KEYS = ("power_toggle", "volume_down", "volume_up", "mute", "prev_input", "next_input",
        "previous", "next", "tune_down", "tune_up")

COMMANDS = {"power_toggle": 0x12, "volume_down": 0x1F, "volume_up": 0x1B, "mute": 0x0D,
            "prev_input": 0x1E, "next_input": 0x1A, "previous": 0x13, "next": 0x58,
            "tune_down": 0x11, "tune_up": 0x5A}

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
