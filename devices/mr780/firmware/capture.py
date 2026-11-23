"""A raw capture of the display's lines, on demand, for working out the VFD protocol (docs/plan.md, step 3).

    POST /capture?rate=2000000&ms=30     samples GP2..GP5 at `rate` per second for `ms` (capped by MAX_SAMPLES);
                                         answers {"rate", "samples", "bytes", "parts", "part_bytes", "pins"}
         &trigger=1                      starts only when A, B or C leaves 0; gives up after `wait` s (default 10).
                                         A and B rest at 1 while the amp is on (docs/measurements.md, 2026-11-23),
                                         so it starts at once then; it only waits while the amp is in standby
         &key=volume_up                  sends that remote key by IR right after arming, so the change comes on cue
    GET  /capture?part=0                 one part of the last capture, raw bytes (PART_BYTES each)
    GET  /capture                        what the last capture holds, as POST answers

Outside the DeviceLink contract: a diagnosis route of this bridge's own, used by tools/bus_capture.py. It goes away (or
stays, unused) once the display reader exists.

Each sample is 4 bits: bit 0 = GP2 (A), bit 1 = GP3 (B), bit 2 = GP4 (C), bit 3 = GP5 (LIGA). Eight samples per
32-bit word, the earliest in the lowest nibble; words little-endian. The PIO samples once per cycle (one `in` and a
wrap), a DMA channel moves its FIFO into the buffer, so Python and Wi-Fi can't make it miss a sample.

SAFETY: the pins are only read. Each is set up as an input with no pull before sampling: on the RP2350 a pad comes
out of reset isolated, with its input buffer off and a pull-down on, so the PIO reads 0 from a pin nothing configured.
Nothing here drives a pin, and the IR line (GP6) is not among them.

parse() and plan() run the same in MicroPython and in the computer's Python (tools/test_capture.py).
"""

BASE_PIN = 2                    # GP2..GP5
PINS = ("A", "B", "C", "LIGA")
MAX_SAMPLES = 1 << 16           # 65536 samples = 32 KB: Wi-Fi and the rest of the program keep their memory
PART_BYTES = 2048
MIN_RATE, MAX_RATE = 10_000, 50_000_000
SM_ID = 4                       # PIO1, state machine 0: the IR sender has PIO0

_PIO_BASE = (0x50200000, 0x50300000, 0x50400000)
_RXF0 = 0x020                   # RX FIFO of state machine 0; the others follow every 4 bytes
_DREQ_PIO_RX0 = (4, 12, 20)     # DMA request "RX FIFO has data"


def plan(rate, ms):
    """(rate, samples) for a request, or an error text. Samples are a whole number of 32-bit words."""
    if not MIN_RATE <= rate <= MAX_RATE:
        return "rate must be between %d and %d" % (MIN_RATE, MAX_RATE)
    if ms <= 0:
        return "ms must be positive"
    samples = min(MAX_SAMPLES, rate * ms // 1000)
    samples -= samples % 8
    if samples < 8:
        return "too short"
    return rate, samples


def parse(data, samples):
    """The samples of a capture as a list of 4-bit values (the computer's side, tools/bus_capture.py)."""
    out = []
    for i in range(samples):
        byte = data[i // 2]
        out.append(byte & 0x0F if i % 2 == 0 else byte >> 4)
    return out


class Capture:
    def __init__(self, remote=None):
        self.remote = remote            # ir.Remote, for &key=
        self.buf = None
        self.info = {"rate": 0, "samples": 0, "bytes": 0, "parts": 0, "part_bytes": PART_BYTES, "pins": list(PINS),
                     "triggered": False}
        self.busy = False
        self.programs = None            # (untriggered, triggered), assembled once: see _programs()

    def _programs(self):
        """The two PIO programs, assembled on the first capture and reused. MicroPython loads a program it has not
        seen into the PIO's 32-instruction memory and never frees the old one, so assembling them on every capture
        filled PIO1 after about 30 captures (2026-11-23), and every later capture failed until a restart."""
        if self.programs is not None:
            return self.programs
        import rp2

        @rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, out_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True,
                     push_thresh=32, fifo_join=rp2.PIO.JOIN_RX)
        def _sample():
            wrap_target()
            in_(pins, 4)
            wrap()

        @rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, out_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True,
                     push_thresh=32, fifo_join=rp2.PIO.JOIN_RX)
        def _triggered():
            label("idle")               # A, B and C at 0: keep waiting (3 cycles a look)
            mov(osr, pins)
            out(x, 3)
            jmp(not_x, "idle")
            wrap_target()
            in_(pins, 4)
            wrap()

        self.programs = (_sample, _triggered)
        return self.programs

    async def run(self, rate, samples, trigger=False, wait_s=10, key=None):
        """True if the capture filled; False if the trigger never came within wait_s."""
        import time
        import asyncio
        import rp2
        from machine import Pin

        sample, triggered = self._programs()
        for n in range(BASE_PIN, BASE_PIN + len(PINS)):
            Pin(n, Pin.IN, pull=None)   # input only, no pull (the amp drives every level)
        nbytes = samples // 2
        if self.buf is None:
            self.buf = bytearray(MAX_SAMPLES // 2)
        sm = rp2.StateMachine(SM_ID, triggered if trigger else sample, freq=rate, in_base=Pin(BASE_PIN))
        pio, smi = divmod(SM_ID, 4)
        dma = rp2.DMA()
        full = False
        try:
            ctrl = dma.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=_DREQ_PIO_RX0[pio] + smi)
            dma.config(read=_PIO_BASE[pio] + _RXF0 + 4 * smi, write=self.buf, count=nbytes // 4, ctrl=ctrl,
                       trigger=True)
            sm.active(1)
            if key and self.remote is not None:
                await asyncio.sleep_ms(20)
                self.remote.send(key)
            start = time.ticks_ms()
            while dma.active():
                if time.ticks_diff(time.ticks_ms(), start) > wait_s * 1000:
                    break
                await asyncio.sleep_ms(5)
            full = not dma.active()
        finally:
            sm.active(0)
            dma.close()
        if full:
            self.info.update(rate=rate, samples=samples, bytes=nbytes, parts=(nbytes + PART_BYTES - 1) // PART_BYTES,
                             triggered=trigger)
        return full

    async def handle(self, req, writer):
        """Route /capture (see web.Publisher)."""
        from web import reply, reply_json
        if req.method == "POST":
            try:
                rate = int(req.query.get("rate", "2000000"))
                ms = int(req.query.get("ms", "30"))
            except ValueError:
                return await reply_json(writer, {"error": "rate and ms must be numbers"}, "400 Bad Request")
            p = plan(rate, ms)
            if isinstance(p, str):
                return await reply_json(writer, {"error": p}, "400 Bad Request")
            key = req.query.get("key")
            if key is not None:
                import ir_codes
                if key not in ir_codes.COMMANDS:
                    return await reply_json(writer, {"error": "unknown key"}, "400 Bad Request")
            if self.busy or (self.remote is not None and self.remote.sending()):
                return await reply_json(writer, {"error": "busy"}, "400 Bad Request")
            trigger = req.query.get("trigger", "0") == "1"
            try:
                wait_s = min(30, max(1, int(req.query.get("wait", "10"))))
            except ValueError:
                wait_s = 10
            self.busy = True
            try:
                full = await self.run(p[0], p[1], trigger, wait_s, key)
            finally:
                self.busy = False
            if not full:
                return await reply_json(writer, {"error": "no activity on A, B or C within %d s" % wait_s},
                                        "408 Request Timeout")
            return await reply_json(writer, self.info)
        if "part" not in req.query:
            return await reply_json(writer, self.info)
        try:
            part = int(req.query["part"])
        except ValueError:
            part = -1
        if not 0 <= part < self.info["parts"]:
            return await reply_json(writer, {"error": "no such part"}, "404 Not Found")
        start = part * PART_BYTES
        end = min(start + PART_BYTES, self.info["bytes"])
        await reply(writer, "200 OK", "application/octet-stream", bytes(memoryview(self.buf)[start:end]))
