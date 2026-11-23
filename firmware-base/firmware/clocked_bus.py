"""Listens to a three-wire clocked bus with the PIO, never driving it, and cuts what it hears into frames.

The bus: chip select (active at 0), clock and data, LSB first, the data valid on the rising clock edge. A frame is one
stretch with chip select at 0. The CD-S300's and the MR 780's microcontrollers talk to their VFDs this way, both wired
the same: GP2 = chip select, GP3 = clock, GP4 = data.

The PIO pushes MARKER when chip select falls, then one word per byte, the byte in bits 24-31; if chip select rises
mid-byte, the partial byte is dropped. A DMA ring keeps the words (pio_ring.py). Framer turns them back into frames.

SAFETY: the pins are inputs, always, with no pull resistors. Nothing here drives them.

MARKER, byte_of() and Framer run the same in MicroPython and in the computer's Python (the devices' tests); rp2 is
imported only inside Sniffer.
"""

MARKER = 0xFFFFFFFF
CS_PIN = 2                      # in_base: bit 0 = chip select, bit 1 = clock, bit 2 = data
BUS_PINS = (2, 3, 4)


def byte_of(word):
    """The data byte of a sniffer word, or None for a frame marker or a malformed word."""
    if word == MARKER or word & 0xFFFFFF:
        return None
    return word >> 24


class Framer:
    """Sniffer words back into frames. A frame ends at the next MARKER, so without `size` the last one waits for the
    next frame. With `size` (a bus whose frames are all that long: the MR 780's), a frame ends as soon as it holds
    `size` bytes, and bytes past it until the next MARKER are dropped."""

    def __init__(self, size=None):
        self.size = size
        self.frame = None               # the frame in progress; None until the first MARKER
        self.bad = 0                    # words that were neither a marker nor a byte

    def feed(self, word):
        """One word. Returns the frame this word closed (a bytearray, never empty), or None."""
        if word == MARKER:
            return self.close(reopen=True)
        b = byte_of(word)
        if b is None:
            self.bad += 1
        elif self.frame is not None:
            self.frame.append(b)
            if len(self.frame) == self.size:
                return self.close()
        return None

    def close(self, reopen=False):
        """Ends the frame in progress and returns it (None if empty)."""
        frame, self.frame = self.frame, (bytearray() if reopen else None)
        return frame or None


def _program():
    import rp2

    @rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, out_shiftdir=rp2.PIO.SHIFT_RIGHT)
    def _bus():
        # jmp_pin = chip select. Polls the clock through the OSR so that chip select rising can end the frame
        # between bits.
        wrap_target()
        label("start")
        wait(0, pin, 0)             # chip select falls: a frame begins
        mov(isr, invert(null))
        push(block)                 # MARKER
        label("byte")
        set(y, 7)
        label("poll")
        jmp(pin, "start")           # chip select high: the frame is over
        mov(osr, pins)
        out(null, 1)
        out(x, 1)                   # x = clock
        jmp(x_dec, "poll")          # clock still high: keep polling
        wait(1, pin, 1)             # clock rises: data is valid
        mov(osr, pins)
        out(null, 2)
        in_(osr, 1)                 # data into the ISR, LSB first
        jmp(y_dec, "poll")
        push(block)                 # 8 bits: the byte is in bits 24-31
        jmp("byte")
        wrap()

    return _bus


class Sniffer:
    def __init__(self, sm_id, ring_bits):
        """The bus on state machine `sm_id`, its words in a ring of 2^ring_bits bytes."""
        from machine import Pin
        from pio_ring import PioRing
        for n in BUS_PINS:
            Pin(n, Pin.IN, pull=None)
        self.ring = PioRing(sm_id, _program(), ring_bits, in_base=Pin(CS_PIN), jmp_pin=Pin(CS_PIN))

    def read(self):
        """The words that arrived since the last call (generator)."""
        return self.ring.read()

    async def follow(self, feed, on_change, poll_ms):
        """Every poll_ms, hands each new word to feed(word, now_ms), which answers True when what the display shows
        changed, and calls on_change() once after a poll that changed it."""
        import time
        import asyncio
        while True:
            now = time.ticks_ms()
            changed = False
            for w in self.read():
                changed |= feed(w, now)
            if changed and on_change:
                on_change()
            await asyncio.sleep_ms(poll_ms)
