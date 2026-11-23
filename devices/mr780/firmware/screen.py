"""The MR 780's display, rebuilt from the frames its microcontroller sends to the VFD, and what the bridge reads from
it: the input, the volume, mute and the valves' warm-up (docs/protocol.md).

A frame is one line: a command byte (LINE_COMMANDS), 0x00, then the 16 characters, the rightmost column first. The
microcontroller resends both lines about every 26 ms, so only a change of text counts.

Runs the same in MicroPython and in the computer's Python (tools/test_screen.py).
"""

COLUMNS = 16
LINE_COMMANDS = {0x90: 0, 0x10: 1}      # the command byte -> the line it writes
FRAME_BYTES = 2 + COLUMNS
BLANK = " " * COLUMNS

# Line 1 names the input (in the cycle's order). While the selector is open the name sits between "<" and ">". FM and
# DAB name themselves only until the tuner settles: then FM shows its frequency ("FM    100.75MHz") and DAB the
# station, which keeps the input read last.
SHOWN = {"USB AUDIO": "usb_audio", "BLUETOOTH": "bluetooth", "PHONO": "phono", "CD": "cd", "DVD": "dvd",
         "AUX 1": "aux1", "AUX 2": "aux2", "TAPE": "tape", "LINE IN": "line_in", "FM Input": "fm",
         "DAB Input": "dab", "DAB/DAB+": "dab", "DIGITAL OPT1": "opt1", "DIGITAL OPT2": "opt2",
         "DIGITAL COAX1": "coax1", "DIGITAL COAX2": "coax2"}
FM_PREFIX, FM_UNIT = "FM ", "MHz"

# Line 2: what last changed, for a few seconds. Mute On stays while muted.
VOLUME_PREFIX, VOLUME_UNIT = "Volume", "dB"    # "   Volume  -36dB"
MUTE_ON, MUTE_OFF = "Mute On", "Mute Off"
WARM_UP_PREFIX = "WARM UP"                      # "  WARM UP  19   ", counting down after power-on


def line_of(frame):
    """(line index, text) for a frame that writes a line, else None."""
    if len(frame) != FRAME_BYTES or frame[1] != 0:
        return None
    line = LINE_COMMANDS.get(frame[0])
    if line is None:
        return None
    # The rightmost column comes first. (MicroPython slices bytearrays with step 1 only.)
    text = "".join(chr(frame[i]) if 32 <= frame[i] < 127 else "?" for i in range(FRAME_BYTES - 1, 1, -1))
    return line, text


def input_shown(text):
    """The input id line 1 names, or None when it names none (a DAB station, STANDBY, the warm-up's MAGNAT MR780)."""
    t = text.strip()
    if t.startswith("<") and t.endswith(">"):
        t = t[1:-1].strip()
    if t in SHOWN:
        return SHOWN[t]
    if t.startswith(FM_PREFIX) and t.endswith(FM_UNIT):
        return SHOWN["FM Input"]
    return None


def volume_shown(text):
    """The volume in dB line 2 shows, or None."""
    t = text.strip()
    if not (t.startswith(VOLUME_PREFIX) and t.endswith(VOLUME_UNIT)):
        return None
    try:
        return float(t[len(VOLUME_PREFIX):-len(VOLUME_UNIT)])
    except ValueError:
        return None


def warm_up_shown(text):
    """The warm-up's seconds left that line 2 shows, or None."""
    t = text.strip()
    if not t.startswith(WARM_UP_PREFIX):
        return None
    try:
        return int(t[len(WARM_UP_PREFIX):])
    except ValueError:
        return None


class Screen:
    """The two lines and what the bridge reads from them. None = not seen since the Pico started."""

    def __init__(self):
        self.lines = [BLANK, BLANK]
        self.seen = False               # a line has arrived since the Pico started
        self.input_id = None
        self.volume_db = None           # the last volume the display showed
        self.muted = None
        self.warmup_s = None

    def apply(self, frame):
        """One frame. Returns True when the text on the display changed."""
        got = line_of(frame)
        if got is None:
            return False
        line, text = got
        self.seen = True
        if self.lines[line] == text:
            return False
        self.lines[line] = text
        if line == 0:
            shown = input_shown(text)
            if shown is not None:
                self.input_id = shown
            return True
        volume = volume_shown(text)
        if volume is not None:
            self.volume_db = volume
        t = text.strip()
        if t == MUTE_ON:
            self.muted = True
        elif t == MUTE_OFF:
            self.muted = False
        self.warmup_s = warm_up_shown(text)
        return True
