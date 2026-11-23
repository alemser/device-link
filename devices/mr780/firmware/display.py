"""Listens to the MR 780's VFD bus (clocked_bus.py, never driving it) and keeps screen.Screen up to date.

Wiring (docs/measurements.md, "the esperas"): A = GP2 chip select, B = GP3 clock, C = GP4 data. The display's logic is
5 V and the RP2350's pins take it while the Pico is powered, which it is from the same amp.

SAFETY: GP2..GP4 are inputs, always, with no pull resistors. Nothing on the display is ever written (the read-only
phase, docs/plan.md).
"""

from clocked_bus import Framer, Sniffer
from screen import FRAME_BYTES, Screen

SM_ID = 5                       # PIO1, state machine 1: the IR sender has PIO0, capture.py PIO1's 0
RING_BITS = 12                  # 2^12 bytes = 1024 words; a screen is 38 words every ~26 ms, so ~0.7 s of bus
POLL_MS = 50                    # chosen: ~73 words a poll, a tenth of the ring


class Display:
    """The sniffer, the framer and the screen. on_change() is called after a poll that changed the display's text."""

    def __init__(self, on_change):
        self.screen = Screen()
        self.framer = Framer(FRAME_BYTES)   # a line closes on its last byte, not 20 ms to 1 s later at the next one
        self.sniffer = Sniffer(SM_ID, RING_BITS)
        self.on_change = on_change

    def _feed(self, word, now_ms):
        frame = self.framer.feed(word)
        return frame is not None and self.screen.apply(frame)

    async def task(self):
        await self.sniffer.follow(self._feed, self.on_change, POLL_MS)

    async def handle(self, req, writer):
        """GET /display: the reader's view (screen.Screen.debug), outside the contract."""
        from web import reply_json, not_found
        if req.method != "GET" or req.path != "/display":
            return await not_found(writer)
        await reply_json(writer, self.screen.debug())
