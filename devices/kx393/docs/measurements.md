# Measurements

The bench measurements on this unit, and the log of what was done. Expected values come from the service manual
(`docs/research.md`) once it is here.

## `CB8` (front board, from behind; 2026-11-17)

Looking at the front board from behind (photo `docs/images/cb8-closeup.jpg`): the top row has 14 joints, the bottom row
13. Positions count from the left.

**The left end is line 1.** The three left joints of the bottom row run down to `SW2` and `R168`/`R169` (the key
ladder). The top row's 4th to 11th joints run up to the 8 square pads (the display: `F`, `F`, `P10` … `P5`).

| Joint | Line | Measured (deck unplugged) |
|---|---|---|
| top 1 | 1 `G` | 0 Ω to the chassis (flat in) |
| bottom 1 | 2 `KEY1` | Flat out, against top 1: open, 1.17 kΩ with STOP, 2.92 kΩ with PLAY |
| top 4 | 7 `F` | Held about 1.6 V for a while after unplugging (the FL POWER capacitors) |

STANDBY/ON is not on the front board (`SW1` → `CB5`, main board): with the flat out it doesn't reach `CB8`.

With the flat in, the volts (deck plugged in, against top 1):

| Joint | Line | Standby | On |
|---|---|---|---|
| bottom 1 | `KEY1` | 4.86 V | 4.86 V |
| top 2 | `KEY2` | 4.86 V | 4.86 V |
| bottom 2 | `REM` | 4.74 V | 4.74 V |
| bottom 3 | `+5V` | 4.90 V | 4.90 V |

So `+5V` lives in standby, as the schematic says, and the deck works with the flat back in.

**Don't trust ohms here with the deck unplugged.** With the flat in, lines 2 to 4 read about 30 Ω to ground (and
`+5V` 1.41 kΩ), yet they sit at 4.8 V once powered. The meter's current finds paths through the unpowered chips.
Check the lines in volts.

## Log

| Date | What |
|---|---|
| 2026-11-17 | Project started away from the deck: research from the owner's manual and the published remote codes, the bridge base and the IR sender |
| 2026-11-17 | Service manual found (audiocircuit.dk) and read: the microcontroller drives the display directly; the mode pins, the 27-way flat, STANDBY/ON on `KEY1`, the full remote table (custom 7F) |
