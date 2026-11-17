"""Listens to the CD-S300's VFD bus with the PIO, never driving it, and keeps vfd.Screen up to date.

Wiring (soldered 2026-11-16 on the CB701 joints, docs/plan.md; the same harness the logic analyzer used):

    GP2 = FL_/CS    GP3 = FL_CLK    GP4 = FL_DATA    GP5 = FL_/RST (not used yet)

SAFETY: GP2..GP5 carry the microcontroller's 3.3 V signals. They are inputs, always, with no pull resistors.

How it works: the PIO pushes MARKER when /CS falls (a frame begins), then one word per byte, the bits taken on the
rising clock edges, LSB first, the byte in bits 24-31. If /CS rises mid-byte, the partial byte is dropped. A DMA channel
copies the PIO's FIFO into a ring buffer without pause, so nothing is lost while Python is busy with Wi-Fi; read()
returns the new words. The bus runs at ~62 kHz and carries ~1000 words a second.
"""

import time
import asyncio

import rp2
import uctypes
from array import array
from machine import Pin

import vfd

CS_PIN = 2                      # in_base: bit 0 = /CS, bit 1 = CLK, bit 2 = DATA
BUS_PINS = (2, 3, 4, 5)
RING_BITS = 12                  # 2^12 bytes = 1024 words, ~1 s of bus traffic
POLL_MS = 50

# RP2350 addresses (datasheet, DMA and PIO chapters), as in the SP103's sniffer.
_PIO_BASE = (0x50200000, 0x50300000, 0x50400000)
_RXF0 = 0x020                   # RX FIFO of state machine 0; the others follow every 4 bytes
_DREQ_PIO_RX0 = (4, 12, 20)     # DMA request "RX FIFO has data"
_ENDLESS = 0xF0000001           # TRANS_COUNT with MODE = 0xF: the DMA never stops


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, out_shiftdir=rp2.PIO.SHIFT_RIGHT)
def _bus():
    # jmp_pin = /CS. Polls CLK through the OSR so that /CS rising can end the frame between bits.
    wrap_target()
    label("start")
    wait(0, pin, 0)             # /CS falls: a frame begins
    mov(isr, invert(null))
    push(block)                 # MARKER
    label("byte")
    set(y, 7)
    label("poll")
    jmp(pin, "start")           # /CS high: the frame is over
    mov(osr, pins)
    out(null, 1)
    out(x, 1)                   # x = CLK
    jmp(x_dec, "poll")          # CLK still high: keep polling
    wait(1, pin, 1)             # CLK rises: DATA is valid
    mov(osr, pins)
    out(null, 2)
    in_(osr, 1)                 # DATA into the ISR, LSB first
    jmp(y_dec, "poll")
    push(block)                 # 8 bits: the byte is in bits 24-31
    jmp("byte")
    wrap()


class Sniffer:
    def __init__(self, sm_id=4):
        # sm_id 4 = PIO1, machine 0 (the IR sender uses machine 0 of PIO0; the Wi-Fi chip uses PIO2).
        for n in BUS_PINS:
            Pin(n, Pin.IN, pull=None)
        size = 1 << RING_BITS
        # The circular DMA needs a buffer aligned to its size: take twice the room and use the aligned part.
        self._buf = array("I", bytes(2 * size))
        start = uctypes.addressof(self._buf)
        self._first = ((-start) % size) // 4
        self._base = start + self._first * 4
        self._mask = size // 4 - 1
        self._rd = 0
        self.sm = rp2.StateMachine(sm_id, _bus, in_base=Pin(CS_PIN), jmp_pin=Pin(CS_PIN))
        pio, sm = divmod(sm_id, 4)
        self.dma = rp2.DMA()
        ctrl = self.dma.pack_ctrl(size=2, inc_read=False, inc_write=True, ring_size=RING_BITS, ring_sel=True,
                                  treq_sel=_DREQ_PIO_RX0[pio] + sm)
        self.dma.config(read=_PIO_BASE[pio] + _RXF0 + 4 * sm, write=self._base, count=_ENDLESS, ctrl=ctrl,
                        trigger=True)
        self.sm.active(1)

    def read(self):
        """The words that arrived since the last call (generator)."""
        wr = ((self.dma.write - self._base) >> 2) & self._mask
        buf, first, mask, rd = self._buf, self._first, self._mask, self._rd
        while rd != wr:
            yield buf[first + rd]
            rd = (rd + 1) & mask
        self._rd = rd


class Display:
    """The sniffer plus the parser. on_change() is called whenever the text or the icons change."""

    def __init__(self, on_change=None):
        self.screen = vfd.Screen()
        self.sniffer = Sniffer()
        self.on_change = on_change
        self.last_frame_ms = None

    async def task(self):
        while True:
            now = time.ticks_ms()
            changed = False
            for w in self.sniffer.read():
                changed |= self.screen.feed(w, now)
                self.last_frame_ms = now
            if changed and self.on_change:
                self.on_change()
            await asyncio.sleep_ms(POLL_MS)

    def alive(self):
        """True while the microcontroller keeps writing to the display (it does so every ~38 ms)."""
        return self.last_frame_ms is not None and time.ticks_diff(time.ticks_ms(), self.last_frame_ms) < 1000

    async def handle(self, req, writer):
        """GET /display: the reader's view, for mapping the icons (vfd.Screen.debug)."""
        from web import reply_json
        d = self.screen.debug()
        d["alive"] = self.alive()
        await reply_json(writer, d)
