"""A PIO state machine's output, copied nonstop by a DMA channel into a ring buffer, and the RP2350 addresses the PIO
and DMA code needs.

The DMA drains the state machine's RX FIFO into the ring by itself, so nothing is lost while Python is busy with
Wi-Fi; read() returns the words that arrived since the last call. Used by the bus readers (the SP103's sniffer.py,
clocked_bus.py); capture.py and the IR senders take only the addresses.

rp2 and uctypes are imported inside PioRing, so the addresses import in the computer's Python too (the tests).
"""

# RP2350 addresses (datasheet, PIO and DMA chapters).
PIO_BASE = (0x50200000, 0x50300000, 0x50400000)
TXF0 = 0x010                    # TX FIFO of state machine 0; the others follow every 4 bytes
RXF0 = 0x020                    # RX FIFO of state machine 0; the others follow every 4 bytes
DREQ_PIO_TX0 = (0, 8, 16)       # DMA request "the TX FIFO has room"
DREQ_PIO_RX0 = (4, 12, 20)      # DMA request "the RX FIFO has data"
ENDLESS = 0xF0000001            # TRANS_COUNT with MODE = 0xF: the DMA never stops (the count cannot be 0)


class PioRing:
    def __init__(self, sm_id, program, ring_bits, **sm_args):
        """Starts `program` on state machine `sm_id` (sm_args go to rp2.StateMachine) and the DMA that copies its
        words into a ring of 2^ring_bits bytes."""
        import rp2
        import uctypes
        from array import array

        size = 1 << ring_bits
        # The ring DMA needs a buffer aligned to its size: take twice the room and use the aligned part.
        self._buf = array("I", bytes(2 * size))
        start = uctypes.addressof(self._buf)
        self._first = ((-start) % size) // 4
        self._base = start + self._first * 4
        self._mask = size // 4 - 1
        self._rd = 0

        self.sm = rp2.StateMachine(sm_id, program, **sm_args)
        pio, sm = divmod(sm_id, 4)
        self.dma = rp2.DMA()
        ctrl = self.dma.pack_ctrl(size=2, inc_read=False, inc_write=True, ring_size=ring_bits, ring_sel=True,
                                  treq_sel=DREQ_PIO_RX0[pio] + sm)
        self.dma.config(read=PIO_BASE[pio] + RXF0 + 4 * sm, write=self._base, count=ENDLESS, ctrl=ctrl,
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
