# The display's protocol

What the main board sends to the VFD (2 lines × 16 characters) on the three data lines of the flat, read by the Pico
on GP2–GP4 (`docs/measurements.md`, "the esperas"). Decoded on 2026-11-23 from the captures in `captures/`, with the
amp on, after the warm-up.

## The lines

| Wire | Pico | Role | Rest |
|---|---|---|---|
| A | GP2 | Chip select, active at 0 | 1 |
| B | GP3 | Clock: the data bit is read on the **rising** edge | 1 |
| C | GP4 | Data, **LSB first** | 0 |

Measured timing (2 MHz capture): clock high 6–6.5 µs, low 13–14 µs (about 51 kHz); one byte every ~173 µs.

## A screen

The main board sends the whole screen about every **26 ms**, whether or not it changed, as two transfers:

1. A low for ~3.12 ms: **18 bytes**, line 1.
2. A high for 12–14 µs.
3. A low for ~3.12 ms: 18 bytes, line 2.
4. A high for ~19.8 ms, until the next screen.

Each transfer is:

| Byte | Value | Meaning |
|---|---|---|
| 0 | `0x90` on line 1, `0x10` on line 2 | Command: which line |
| 1 | `0x00` | Always 0 so far |
| 2–17 | ASCII | The 16 characters, **the rightmost column first** |

So a reader waits for A to fall, takes 18 bytes, reverses bytes 2–17, and picks the line from byte 0. A capture
that starts while A is low begins mid-transfer: skip to the next falling edge of A.

No command other than `0x90` and `0x10` has been seen. Brightness (DIM), custom characters and standby have not been
captured.

## Screens seen

| When | Line 1 | Line 2 | Capture |
|---|---|---|---|
| On, USB input, at rest | `    USB AUDIO   ` | (blank) | `on-idle-*`, `on-idle-131ms-*` |
| Volume key, for a few seconds | `    USB AUDIO   ` | `   Volume  -36dB` | `volume-up-36db-*`, `volume-down-37db-*` |
| Mute on, stays while muted | `    USB AUDIO   ` | `    Mute On     ` | `mute-on-*` |
| Mute off, for a few seconds | `    USB AUDIO   ` | `    Mute Off    ` | `mute-off-*` |

Line 1 names the input; line 2 shows what last changed, and goes blank within about 5 s (Mute On stays). The volume
is in dB, right-aligned, one step per key press (−37 to −36 dB).

## Still to capture

- The other 14 inputs' names on line 1 (only `USB AUDIO` seen).
- The warm-up countdown, standby (the lines rest at ~0.1 V, so likely no transfers), DIM, DIRECT, the tone knobs,
  DAB and FM text, Bluetooth.
