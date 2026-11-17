# The display protocol

What the logic analyzer and the bridge itself showed about the CD-S300's display and remote. Each answer names the
capture in `captures/` (or the session) that shows it.

## Wiring

Analyzer: the Pico 2 W with the LogicAnalyzer firmware (`logicanalyzer-sp103`). Channel N = GPIO(N+1). The same wires
and pins serve the bridge Pico afterwards (`docs/plan.md`, "The wiring").

| Channel | GPIO | Pin | Signal |
|---|---|---|---|
| 1 | GP2 | 4 | `FL_/CS` |
| 2 | GP3 | 5 | `FL_CLK` |
| 3 | GP4 | 6 | `FL_DATA` |
| 4 | GP5 | 7 | `FL_/RST` |
| 5 | GP6 | 9 | `IR` (the `U701` output) |
| — | GND | 3 | `DGND` |

Name the channels `CS`, `CLK`, `DATA`, `RST` and `REM` in the analyzer program: `tools/fl_decode.py` reads the names
before the numbers. Everything is 3.3 V. The Mac **on battery** (the device has no earth). Read a capture with:

```sh
python3 tools/fl_decode.py captures/02-tocando.lac
```

One capture was enough (`02-tocando`, 1 MHz, 200 ms). The others planned (power-on, DISPLAY key, modes, tray) were
replaced by logging the changes from the bridge itself (below). Later, only if the matching idea is taken up: a CD
with CD-Text and a USB stick with MP3 (disc text), and listening on `232C_TX` of the `CB902` port (nothing else there).

## Questions

| Question | Answer | Shown by |
|---|---|---|
| Clock speed, edge where data is valid, bit order | 62 kHz (6 µs high, 10 µs low); data read on the rising edge; **LSB first** | `02-tocando` |
| Frame size, and whether `/CS` rises between bytes | One frame per command, with its data (8 to 104 bits); `/CS` rises only at the end of the frame | `02-tocando` |
| Does the microcontroller send **characters or dots**? | **Characters, in ASCII.** The icons are two custom characters it draws (below) | `02-tocando` |
| How the icons (grids 13 and 14) are lit | Positions 13 and 14 show custom characters 0 and 1; their dots are the icons | `02-tocando` |
| How often the display is rewritten | A ~38 ms cycle, in three groups 12.7 ms apart | `02-tocando` |
| What `DIMMER` sends | Not mapped yet | |
| The remote: NEC, address 79/86, real timings | NEC 79/86 confirmed in use: the bridge's `play` started the disc. Timings not measured | Device, 2026-11-16 |
| Does the RS-232 port say anything by itself? | Not checked | |

## The protocol (capture `02-tocando`, 2026-11-16)

Captured at 1 MHz for 200 ms, with the disc playing track 1 at 0:07. Bytes below are LSB first, as the glass reads
them. The cycle repeats every ~38 ms:

| Group | Frame | Meaning |
|---|---|---|
| 1 | `20` + `00 00 00 00 00` `08 04 00 00 00` | Draws custom characters 0 and 1 (5 bytes each): the icons |
| 2 | `10` + `20 20 31 20 20 20 20 30 3A 30 37 20` | Writes the text from position 0: `"  1    0:07 "` (track 1, time 0:07) |
| 3 | `63` | Configuration (probably the number of grids) |
| 3 | `50 A0` | Configuration (probably brightness; `DIMMER` should change this) |
| 3 | `70` | Configuration (probably "display on") |
| 3 | `1C 00 01` | Writes custom characters 0 and 1 from position 12: the two icon grids |

The commands look like Princeton's VFD controllers (PT6302 and similar): the command in the high nibble, the address
in the low one. Not confirmed: the glass's datasheet is not in the manual.

For the reader this means:

- The text comes ready, in ASCII: no font table needed.
- The state (play, pause, modes) is in the 10 bytes of the custom characters.

## Icon map and state (on the device, 2026-11-16)

Mapped with the panel keys while the Pico logged every icon change (`GET /display`, `icon_changes`). Dots are named
`grid.byte.bit` (`vfd.Screen.lit`):

| Dot | Meaning |
|---|---|
| `13.0.3` | Play (lit while playing) |
| `13.1.3` | Pause |
| `13.1.2` | Disc in the tray (off with the tray open; back on at `LOADING`) |

Text: `track  elapsed` while playing or paused, `tracks  total` when stopped with a disc, `track  0:00` when a track is
picked while stopped, `LOADING` after closing the tray. Next and previous change only the text.

`vfd.Player` turns this into `/state`: `transport` (playing, paused, stopped, loading, open), `media` (track, elapsed)
and `disc` (tracks, total, remembered from the stopped display until the tray opens).

Still to map, with the remote: repeat, random, A-B, program, USB mode, Pure Direct, dimmer.
