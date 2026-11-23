"""Listens to the CD-S300's VFD bus (clocked_bus.py, never driving it) and keeps vfd.Screen up to date.

Wiring (soldered 2026-11-16 on the CB701 joints, docs/plan.md; the same harness the logic analyzer used):

    GP2 = FL_/CS    GP3 = FL_CLK    GP4 = FL_DATA    GP5 = FL_/RST (not used yet)

SAFETY: GP2..GP5 carry the microcontroller's 3.3 V signals. They are inputs, always, with no pull resistors.

The bus runs at ~62 kHz and carries ~1000 words a second.
"""

import time

from machine import Pin

import vfd
from clocked_bus import Sniffer

RST_PIN = 5                     # FL_/RST: an input with no pull, so the pad's reset pull-down never loads the line
SM_ID = 4                       # PIO1, machine 0 (the IR sender uses machine 0 of PIO0; the Wi-Fi chip uses PIO2)
RING_BITS = 12                  # 2^12 bytes = 1024 words, ~1 s of bus traffic
POLL_MS = 50


class Display:
    """The sniffer plus the parser. on_change() is called whenever the text or the icons change."""

    def __init__(self, on_change=None):
        self.screen = vfd.Screen()
        Pin(RST_PIN, Pin.IN, pull=None)
        self.sniffer = Sniffer(SM_ID, RING_BITS)
        self.on_change = on_change
        self.last_frame_ms = None

    def _feed(self, word, now_ms):
        self.last_frame_ms = now_ms
        return self.screen.feed(word, now_ms)

    async def task(self):
        await self.sniffer.follow(self._feed, self.on_change, POLL_MS)

    def alive(self):
        """True while the microcontroller keeps writing to the display (it does so every ~38 ms)."""
        return self.last_frame_ms is not None and time.ticks_diff(time.ticks_ms(), self.last_frame_ms) < 1000

    async def handle(self, req, writer):
        """GET /display: the reader's view, for mapping the icons (vfd.Screen.debug)."""
        from web import reply_json
        d = self.screen.debug()
        d["alive"] = self.alive()
        await reply_json(writer, d)
