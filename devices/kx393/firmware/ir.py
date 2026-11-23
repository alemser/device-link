"""Sends the remote's keys to the KX-393 down the IR line, by wire.

Wiring (planned, not yet soldered; docs/plan.md):

    GP6 = the REM line, on the CB8 joint of the 27-way flat (front board). The service manual's schematic: the
    remote sensor U1 (SPS-421-1) drives REM straight into the microcontroller's REMOCON input (IC12 pin 22), with no
    gate in between, as on the SP103. Idle at 4.8 V (schematic); the RP2350's pins tolerate it while powered.

SAFETY RULE (the SP103's): GP6 is NEVER driven to 1. Its output value stays 0 and only the direction changes. The
line rises through the sensor's own output.

Drive strength 12 mA (2026-11-18): at 2 mA the deck answered no address (7F, 7A, FE, 5E), though the Pico read its
own pin as 0; a stronger pull settles whether the line came down far enough for the deck's 5 V microcontroller.
Pulling low only, so the strength can't push anything into the deck. hold() keeps the line at 0 for the multimeter.

The PIO holds the line at 0 only for a counted time. While waiting for the next time, the line is released: if the
DMA stopped midway, the line would not stay stuck at 0 and a real remote keeps working. The DMA feeds the times by
itself, so a pause in Python does not spoil the code being sent.

The PIO and DMA come from the CD-S300's ir.py (devices/cds300, itself from the SP103's), working in the CD-S300 since 2026-11-16.
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
_DRIVE_12MA = 0x3 << 4
HOLD_MAX_MS = 10_000


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
        mem32[pad] = (mem32[pad] & ~_DRIVE_MASK & ~1) | _DRIVE_12MA     # 12 mA, slow edge
        self.sm.active(1)
        pio, sm = divmod(sm_id, 4)
        self._fifo = PIO_BASE[pio] + TXF0 + 4 * sm
        self.dma = rp2.DMA()
        self._ctrl = self.dma.pack_ctrl(size=2, inc_read=True, inc_write=False,
                                        treq_sel=DREQ_PIO_TX0[pio] + sm)
        self._words = None              # the DMA reads from here: it must outlive the send
        self._until = time.ticks_ms()
        self.sent = 0
        self.last = None                # the last command byte sent

    def sending(self):
        return time.ticks_diff(self._until, time.ticks_ms()) > 0

    def send(self, key):
        self.send_command(ir_codes.COMMANDS[key])

    def send_command(self, command, address=ir_codes.ADDRESS):
        """Any command byte, at the deck's address or another: how the address is settled (ir_codes.py)."""
        self._send_words(ir_codes.frame_command(command, address), "%02X/%02X" % (address, command))

    def _send_words(self, words, label):
        self._words = array("I", words)
        self._until = time.ticks_add(time.ticks_ms(), sum(words) // 1000 + 10)
        self.dma.config(read=self._words, write=self._fifo, count=len(words), ctrl=self._ctrl, trigger=True)
        self.sent += 1
        self.last = label

    def hold(self, ms):
        """The line at 0 for ms (at most HOLD_MAX_MS), then released: to measure how low it gets."""
        ms = max(1, min(int(ms), HOLD_MAX_MS))
        self._send_words([ms * 1000, 1000], "hold %d ms" % ms)

    def status(self):
        return {"commands": list(ir_codes.KEYS), "sending": self.sending(), "sent": self.sent,
                "last": self.last, "line": self.line.value()}
