"""Parser for the CD-S300 front-panel VFD bus, as seen by the Pico's sniffer (display.py).

The protocol comes from the logic-analyzer capture captures/02-playing.lac (docs/protocol.md):

- One frame per command: /CS low, a command byte, then its data bytes, LSB first, data valid on the rising clock.
- The command's high nibble is the command, the low nibble an address (Princeton PT6302-style controller):
    0x1n  write characters to the display RAM, starting at position n (positions 0-11 are the 12 characters,
          12 and 13 the two icon grids)
    0x2n  write custom characters, starting at custom character n, 5 bytes each (the icon grids show custom
          characters 0 and 1, so their bits are the icons)
    0x3n  (not seen yet) write the additional-data RAM
    other configuration (0x50 brightness?, 0x63, 0x70); kept raw
- The microcontroller rewrites everything every ~38 ms.

The sniffer hands over 32-bit words: MARKER when /CS falls (a frame begins), otherwise a data byte in bits 24-31.

Runs the same in MicroPython (Pico) and CPython (tools/test_vfd.py).
"""

MARKER = 0xFFFFFFFF

# Icon dots ("grid.byte.bit", see Screen.lit), mapped on the device on 2026-11-16 with the panel keys:
ICON_PLAY = "13.0.3"
ICON_PAUSE = "13.1.3"
ICON_DISC = "13.1.2"            # lit while a disc is in; off with the tray open
TEXT_LEN = 12
ICON_POS = (12, 13)
RAM_LEN = 16
CHANGES_KEPT = 4                # text changes every second while playing: keep only the latest
ICON_CHANGES_KEPT = 16          # icon changes are rare: enough for a mapping session (docs/protocol.md)


def _clock(s):
    """"61:37" -> seconds, or None."""
    m, sep, sec = s.partition(":")
    if sep and m.isdigit() and sec.isdigit() and len(sec) == 2:
        return int(m) * 60 + int(sec)
    return None


class Player:
    """What the display means, in CD mode (mapped on the device on 2026-11-16). Call update() on every change.

    transport: "playing", "paused", "stopped", "loading", "open" (tray), or None when unknown.
    The display shows "track  elapsed" while playing or paused ("  1    0:07 "), "tracks  total" when stopped with a
    disc (" 12   61:37 "), and "track  0:00" when a track is picked while stopped. The disc's track count and total time
    are remembered from the stopped display, until the tray opens. Anything else (messages, USB mode) stays in text.
    """

    def __init__(self):
        self.disc = None                    # (tracks, total seconds) of the disc in the tray
        self.state = self._blank()

    @staticmethod
    def _blank():
        return {"transport": None, "track": None, "elapsed_s": None, "tracks": None, "total_s": None}

    def update(self, text, lit):
        words = text.split()
        clock = _clock(words[-1]) if words else None
        number = int(words[0]) if len(words) == 2 and words[0].isdigit() and clock is not None else None
        out = self._blank()
        if text.strip() == "LOADING":
            out["transport"] = "loading"
            self.disc = None
        elif ICON_PLAY in lit or ICON_PAUSE in lit:
            out["transport"] = "playing" if ICON_PLAY in lit else "paused"
            # Right after play the display still shows the disc's totals for a moment: not a track.
            if number is not None and (number, clock) != self.disc:
                out["track"], out["elapsed_s"] = number, clock
        elif ICON_DISC in lit:
            out["transport"] = "stopped"
            if number is not None and clock:
                self.disc = (number, clock)
            elif number is not None:
                out["track"] = number            # picked with next/previous while stopped
        elif not lit:
            out["transport"] = "open"
            self.disc = None
        if self.disc:
            out["tracks"], out["total_s"] = self.disc
        self.state = out
        return out


def byte_of(word):
    """The data byte of a sniffer word, or None for a frame marker or a malformed word."""
    if word == MARKER or word & 0xFFFFFF:
        return None
    return word >> 24


class Screen:
    """The display's contents, rebuilt from the frames the microcontroller sends to the glass."""

    def __init__(self):
        self.ram = bytearray(b" " * RAM_LEN)        # display RAM: character codes per position
        self.custom = {}                            # custom character number -> 5 bytes
        self.config = {}                            # command byte -> data bytes (hex), for unknown commands
        self.frames = 0
        self.bad = 0                                # words that were neither a marker nor a byte
        self.changes = []                           # [(ms, text, icons hex)], newest last
        self.icon_changes = []                      # [(ms, text, lit dots)] when the icons change, newest last
        self._frame = None
        self._last = (self.text(), self.icons().hex())     # a blank screen is not a change

    # ---------------------------------------------------------------- input

    def feed(self, word, now_ms=0):
        """One word from the sniffer. Returns True when what the display shows changed."""
        if word == MARKER:
            return self._close(now_ms)
        b = byte_of(word)
        if b is None:
            self.bad += 1
            return False
        if self._frame is not None:
            self._frame.append(b)
        return False

    def flush(self, now_ms=0):
        """Closes the frame in progress (the last one stays open until the next marker)."""
        return self._close(now_ms, reopen=False)

    def _close(self, now_ms, reopen=True):
        frame, self._frame = self._frame, (bytearray() if reopen else None)
        if not frame:
            return False
        self.frames += 1
        self._apply(frame)
        return self._note(now_ms)

    def _apply(self, frame):
        cmd, data = frame[0], frame[1:]
        kind, addr = cmd & 0xF0, cmd & 0x0F
        if kind == 0x10:
            for i, c in enumerate(data):
                self.ram[(addr + i) % RAM_LEN] = c
        elif kind == 0x20:
            for i in range(len(data) // 5):
                self.custom[(addr + i) & 0x0F] = bytes(data[5 * i:5 * i + 5])
        else:
            self.config["%02X" % cmd] = bytes(data).hex()

    # ---------------------------------------------------------------- output

    def text(self):
        return "".join(chr(c) if 32 <= c < 127 else "?" for c in self.ram[:TEXT_LEN])

    def icons(self):
        """The 10 bytes behind the two icon grids (5 per grid)."""
        out = b""
        for pos in ICON_POS:
            out += self.custom.get(self.ram[pos], b"\x00" * 5) if self.ram[pos] < 16 else b"\x00" * 5
        return out

    def lit(self):
        """The lit icon dots as "grid.byte.bit" strings, e.g. "13.0.3": the names for the icon map."""
        out = []
        for i, b in enumerate(self.icons()):
            for bit in range(8):
                if b >> bit & 1:
                    out.append("%d.%d.%d" % (ICON_POS[i // 5], i % 5, bit))
        return out

    def _note(self, now_ms):
        now = (self.text(), self.icons().hex())
        if now == self._last:
            return False
        if now[1] != self._last[1]:
            self.icon_changes.append((now_ms, now[0], self.lit()))
            if len(self.icon_changes) > ICON_CHANGES_KEPT:
                self.icon_changes.pop(0)
        self._last = now
        self.changes.append((now_ms, now[0], now[1]))
        if len(self.changes) > CHANGES_KEPT:
            self.changes.pop(0)
        return True

    def debug(self):
        """GET /display: the reader's view, kept under ~1 KB (large replies choke the Pico's Wi-Fi)."""
        return {"text": self.text(), "lit": self.lit(), "config": self.config,
                "frames": self.frames, "bad": self.bad,
                "icon_changes": [[ms, t, " ".join(l)] for ms, t, l in self.icon_changes]}
