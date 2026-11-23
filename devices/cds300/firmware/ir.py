"""Sends the remote's keys to the CD-S300 down the IR line, by wire.

Wiring (tested 2026-11-16: "play" sent over Wi-Fi started the disc; docs/plan.md):

    GP6 = the IR receiver's output (U701, leg C), before the IC702 gate. GP6, not the SP103's GP15, so the same
    harness serves the logic analyzer (channel 5) and the bridge.

The flat cable's REM line won't do: it comes from a logic gate that drives it to 3.3 V, and the Pico would fight it
(docs/research.md, "The receiver").

SAFETY RULE (the SP103's): GP6 is NEVER driven to 1. Its output value stays 0 and only the direction changes, at the
lowest drive strength (2 mA). The line rises through the receiver's own resistor.

The PIO holds the line at 0 only for a counted time. While waiting for the next time, the line is released: if the
DMA stopped midway, the line would not stay stuck at 0 and the real remote keeps working. The DMA feeds the times by
itself, so a pause in Python does not spoil the code being sent.

The PIO and DMA come from the SP103's ir.py (devices/sp103), working in the amp since 2026-11-06.
"""

import time
from array import array

import rp2
from machine import Pin, mem32

import ir_codes
from pio_ring import PIO_BASE, TXF0, DREQ_PIO_TX0

IR_PIN = 6
_PADS_BANK0 = 0x40038000
_DRIVE_MASK = 0x3 << 4


@rp2.asm_pio(set_init=rp2.PIO.IN_LOW)
def _pulses():
    # At 1 MHz each jmp loop lasts 1 µs. Each pair of words: line at 0, line released.
    pull()
    mov(x, osr)
    set(pindirs, 1)             # line at 0
    label("mark")
    jmp(x_dec, "mark")
    set(pindirs, 0)             # release the line before waiting for the next word
    pull()
    mov(x, osr)
    label("space")
    jmp(x_dec, "space")


class Remote:
    def __init__(self, sm_id=0):
        self.line = Pin(IR_PIN, Pin.IN, pull=None)
        self.sm = rp2.StateMachine(sm_id, _pulses, freq=1_000_000, set_base=Pin(IR_PIN))
        self.sm.exec("set(pins, 0)")
        self.sm.exec("set(pindirs, 0)")
        pad = _PADS_BANK0 + 4 + 4 * IR_PIN
        mem32[pad] = mem32[pad] & ~_DRIVE_MASK & ~1     # 2 mA, slow edge
        self.sm.active(1)
        pio, sm = divmod(sm_id, 4)
        self._fifo = PIO_BASE[pio] + TXF0 + 4 * sm
        self.dma = rp2.DMA()
        self._ctrl = self.dma.pack_ctrl(size=2, inc_read=True, inc_write=False,
                                        treq_sel=DREQ_PIO_TX0[pio] + sm)
        self._words = None              # the DMA reads from here: it must outlive the send
        self._until = time.ticks_ms()
        self.sent = 0

    def sending(self):
        return time.ticks_diff(self._until, time.ticks_ms()) > 0

    def send(self, key):
        words = ir_codes.frame(key)
        self._words = array("I", words)
        self._until = time.ticks_add(time.ticks_ms(), sum(words) // 1000 + 10)
        self.dma.config(read=self._words, write=self._fifo, count=len(words), ctrl=self._ctrl, trigger=True)
        self.sent += 1

    def status(self):
        return {"commands": list(ir_codes.KEYS), "sending": self.sending(), "sent": self.sent,
                "line": self.line.value()}
