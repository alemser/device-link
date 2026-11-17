# Measurements

The owner measures; Claude takes notes. The "Expected" values come from the manual's schematic (`docs/research.md`).
Measurements were taken with the illustrated guide (`docs/measurement-guide.html`, published at
https://claude.ai/artifact/1Gud8oKmZ5HQ2eygCHr3Kf): one card per measurement, on photos of this unit, with a button that
copies the results into the chat.

## Before soldering

Only what changed a decision: whether the Pico may connect to the lines it uses, where to solder the remote's wire,
whether `D+5` can power the Pico, and which `CB701` joint each wire goes on (`docs/plan.md`, "The wiring"). Any line
above **3.4 V** stops everything.

| Measurement | Device | Expected | Measured | Decides |
|---|---|---|---|---|
| `CB701` joints of `DGND`, `FL_/CS`, `FL_CLK`, `FL_DATA` and `FL_/RST`: beep from the `CB304` window | Unplugged | One joint per line | The map holds (three beeps) | Where the reading wires go |
| The `U701` leg that beeps with two neighbouring `IC702` legs | Unplugged | One (`OUT`) | Leg C | Where the IR wire goes |
| `D+3.3V` | On, stopped | 3.4 V | 3.28 V | The front board is 3.3 V |
| `FL_/CS` | On, stopped | 3.3 V | 2.92 V (an average: it drops to 0 on every write) | The Pico may listen to the display |
| `FL_/RST` | On, stopped | 3.3 V | 3.27 V | Same |
| `REM` | On, stopped | 3.4 V | 3.28 V | Same, for the remote |
| `U701` output at rest | On, stopped | 3.3 V | 3.0 V | The Pico may pull the line low |
| `D+5` (on `CB301`) | On | 4.75 to 5.25 V | 5.05 V | Power the Pico from `D+5` |
| `+B2` (on `CB301`) | On | ~12 V | 12.00 V | The fallback supply |
| `IC801` heatsink after playing, with the Pico on `D+5` | Unplugged | Warm | Fine | Same |

## Left for later

- **The other 11 lines of the flat** (LEDs, keys): the Pico doesn't connect to them.
- **How the device comes back after the plug is pulled** (option B): only if a Wi-Fi plug is ever wanted.
- **Photos of the rear (`CB902`) and of `IC305`/`IC4`**: for later ideas (RS-232, read errors, S/PDIF).

## Log

Readings in the order they were taken.

- **2026-11-16, 16:00:** the 15-way flat's pitch, measured from photos with a tape measure against `CB304` (photos
  `20261116_160859.jpg` and `20261116_160947.jpg`, not in the repository): first to 15th contact, 17.4 and 18.1 mm, so
  a **1.25 mm** pitch (1.0 mm would give 14 mm). Matches the schematic's `52044`/`52045` connectors. A Raspberry Pi
  camera cable (15 ways, 1.0 mm) won't fit.
- **2026-11-16, afternoon** (guide page):
  - The `CB701` map confirmed with three beeps: `CB304` window 2 → bottom 7th, window 6 → bottom 5th, window 1 → top
    8th. The plan's positions hold.
  - `U701` output: **leg C** (the bottom one in `20261116_111503.jpg`).
  - On, stopped, no disc, black probe on top 5th (`DGND`): `D+3.3V` 3.28 V, `FL_/CS` 2.92 V, `FL_/RST` 3.27 V, `REM`
    3.28 V, `U701` output 3.0 V. Nothing above 3.4 V.
  - `D+5` **5.05 V** and `+B2` **12.00 V** (on `CB301`).
- **2026-11-16, 18:00:** six wires soldered (photos `20261116_175957.jpg` and `20261116_180004.jpg`, copies in
  `docs/guide/`). Beep check between the loose ends, device unplugged: **no short**.
- **2026-11-16, 19:00:** the Pico (formerly the MR 780's, chip `D85E`) with the bridge program, powered from `D+5` on
  VSYS (pin 39), ground through pin 3. On the home network as `CDS300-D85E`. The remote line idles high; `play` sent
  over Wi-Fi started the disc.
- **2026-11-16, evening:** grey wire (`FL_/CS`) re-soldered properly. `IC801` heatsink fine after playing with the Pico
  on `D+5`. Case closed: the Pico sees the home network (`conway_tv-5349`) at **−47 dBm**, and answers over Wi-Fi.
