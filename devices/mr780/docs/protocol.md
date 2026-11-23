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

The rhythm stops for more than 131 ms (no transfer at all) a few seconds after switching to FM or DAB, while the
tuner settles (`fm-no-transfers-*`). During the warm-up countdown screens come far less often: most 60 ms windows
held none. A reader keeps the last screen through such a pause.

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

| Input selector open (after a next/prev press) | `<   USB AUDIO  >` | (blank) | `selector-open-usb-*` |
| A digital input with nothing connected, after ~5 s | `  DIGITAL OPT1  ` | `    No Signal   ` | `opt1-no-signal-*` |
| USB with an unsupported stream, after ~5 s | `    USB AUDIO   ` | scrolls `Sample Rate Not Supported`, then blank | `usb-sample-rate-scroll-*` |
| Power key to standby, for ~2 s | `    STANDBY     ` | (blank) | `standby-entering-*` |
| Standby, after ~15 s | no transfers: A, B and C stay at 0 (the display's 5 V is off) | | `standby-15s-*` |
| Power-on, the valves' warm-up | ` MAGNAT  MR780  ` | `  WARM UP  19   ` (counting down from ~30) | `warm-up-19-*` |
| DAB, after ~10 s | `Onic 80s        ` (the station) | `   No Service   ` | — |
| FM, after ~7 s | `FM    100.75MHz ` | (blank) | — |

Line 1 names the input; line 2 shows what last changed, and goes blank within about 5 s (Mute On and No Signal stay).
The volume is in dB, right-aligned, one step per key press (−37 to −36 dB). While the input selector is open, line 1
shows the input between `<` and `>`; the first next/prev press only opens it (`firmware/inputs.py`).

On FM and DAB, line 1 stops naming the input once the tuner has settled: it shows the frequency or the station. A
reader tells those inputs apart by `FM` at the start of the line, and keeps DAB from the last name it saw.

### The inputs, as line 1 names them

In the amp's cycle order, with `firmware/device.py`'s ids (all seen on 2026-11-23, stepping with the remote keys):

| id | Line 1 | id | Line 1 | id | Line 1 |
|---|---|---|---|---|---|
| `usb_audio` | `USB AUDIO` | `aux1` | `AUX 1` | `dab` | `DAB Input` (selector), `DAB/DAB+` |
| `bluetooth` | `BLUETOOTH` | `aux2` | `AUX 2` | `opt1` | `DIGITAL OPT1` |
| `phono` | `PHONO` | `tape` | `TAPE` | `opt2` | `DIGITAL OPT2` |
| `cd` | `CD` | `line_in` | `LINE IN` | `coax1` | `DIGITAL COAX1` |
| `dvd` | `DVD` | `fm` | `FM Input` (selector), `FM    <freq>MHz` | `coax2` | `DIGITAL COAX2` |

## Still to capture

- DIM, DIRECT and the tone knobs (panel only), Bluetooth with a phone connected, DAB and FM with a station playing.
