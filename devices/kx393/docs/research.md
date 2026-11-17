# KX-393: what the manuals say (2026-11-17)

Written away from the deck: no photos or measurements yet. Sources, both in the local copy `docs/manual/` (not on
GitHub):

- Yamaha's **owner's manual** for the KX-493/KX-393 (11 pages, `VZ 77980`), from Yamaha's site.
- The **service manual** for the KX-393/493 (35 pages, January 1998), from audiocircuit.dk
  (`Yamaha-KX493-tape-sm.pdf`). A scan with no text layer: read from the images. The PDF's page numbers differ from
  the printed ones (some PDF pages are two-page spreads or fold-outs):

| Printed page | PDF page | Contents |
|---|---|---|
| 12 to 13 | 10 | µ-COM data: the LC65204A pinout and the KX-393's pin table |
| 14 | 11 | The KX-493's pin table |
| 15 | 12 | Display data: the glass, its pins and the grid/anode map |
| 16 | 13 | KX-393 block diagram |
| 26 | 14 (fold-out) | **KX-393 schematic**, with the remote code table |
| 27 | 15 (fold-out) | KX-493 schematic |

Where a value was read from a small part of the scan, it says so: to confirm on the bench.

## Summary

- **The microcontroller drives the display directly.** `IC12`, a Sanyo **LC65204A-4G83** (4-bit, 5 V, 52 pins), has
  high-voltage outputs for the glass: 9 grids and 10 anodes, swinging between about +4.8 V and −21 V. There is no
  display bus to listen to, as there was on the CD-S300.
- **The deck's mode is on a few 5 V logic pins** of the same chip: capstan motor, solenoid, bias, line mute, rec mute,
  rec/play select, head select, the reel pulse, and a 2-wire serial bus to the port expander (tape type, tape tuning).
  The manual has a table of their levels in each mode.
- **Display, keys and the remote sensor share one 27-way flat** between the main board (`CB7`) and the front board
  (`CB8`), Molex 52045/52044 at 1.25 mm, the same connectors as the CD-S300's.
- **The remote sensor drives the microcontroller directly** (`REM`, no gate in between): the Pico pulls it low, as on
  the SP103.
- **STANDBY/ON is a momentary key that grounds the `KEY1` line.** The transformer is always on and the
  microcontroller always powered; standby is the microcontroller switching things off. So the Pico can live in
  standby and switch the deck on by pulling `KEY1` low.
- **Every remote code is in the manual** (11 keys), but its custom code (7F) differs from the captured codes' (7A).

## The microcontroller (`IC12`, LC65204A-4G83; printed page 13)

Drawn as a 52-pin dual-in-line package: through-hole legs, if the photos agree. 4 MHz crystal (`XL1`), +5 V.

| Pin | Port | Function | Logic |
|---|---|---|---|
| 1 | PA0 | Operation key (1), A/D: `KEY1` | |
| 2 | PA1 | Operation key (2), A/D: `KEY2` | |
| 3, 4 | PA2, PA3 | Meter input L, R (A/D, from the meter amp `IC11`) | |
| 5 | PB0 | Mecha switch (A/D) | |
| 6 | PB1 | Mecha switch and timer (A/D) | |
| 7 | PB2 | **Reel pulse** | |
| 8 | PB3 | Power pulse (mains present) | |
| 15 | RES | Reset | |
| 19 | PF0 | **Port expander clock** (to `IC13`) | |
| 20 | PF1 | **Port expander data** | |
| 21 | PF2 | **Bias** | H: on |
| 22 | PF3 | **Remote input** (`REM`) | |
| 23 | PC0 | **Mecha drive: capstan motor** | H: on |
| 24 | PC1 | **Mecha drive: solenoid** | H: on |
| 25 | PC2 | Not used (47 kΩ to ground) | |
| 26 | PC3 | **Head select** | H: rec |
| 27 | PD0 | **Line mute** | H: on |
| 28 | PD1 | **Rec mute** | H: on |
| 29 | PD2 | Dolby 1 (Dolby on/off) | H: off |
| 30 | PD3 | Dolby 2 (Dolby C on/off) | H: off |
| 31 | PK0 | MPX filter | H: on |
| 32 | PK1 | **Rec/PB select** | H: play |
| 33 | PK2 | FL filament on/off (the schematic draws `P10` here) | H: on |
| 34 to 42 | PK3 … PM3 | FL segments 9 to 1 | H: on |
| 43 to 51 | PN0 … PP0 | FL digits (grids) 1 to 9 | H: on |
| 52 | Vp | −21 V, the high-voltage outputs' supply | |

### The levels in each mode (printed page 13)

The KX-393's table, as printed:

| Pin | Name | Stop | Play | FF/REW | Search | Rec pause | Rec |
|---|---|---|---|---|---|---|---|
| 21 | Bias | H | H | H | H | H | L |
| 27 | Line mute | L | L | H | L | H | H |
| 28 | Rec mute | H | H | H | H | H | L |
| 32 | Rec/PB select | H | H | H | H | L | L |

The KX-493's table (printed page 14) has the opposite levels for bias and line mute (bias H only in Rec; line mute L
in Play, Rec pause and Rec), which fits the "H: on" column better. **One of the two is wrong, or the KX-393 differs:
the multimeter decides**, pin by pin in each mode. Either way, together with the capstan motor (pin 23) these pins
tell stop, play, winding, rec pause and rec apart. FF and REW look the same on them (the KX-393 has one motor; the
KX-493's reel FF/REW pins are "not used" here); the reel pulse's rate tells winding from playing.

### The port expander (`IC13`, BU2040; printed page 13)

A serial-in, parallel-out chip on pins 19 (clock) and 20 (data): two logic lines to listen to with the PIO, as on the
CD-S300. Its outputs:

| Pin | Name | Logic | Pin | Name |
|---|---|---|---|---|
| 4 | LH (normal tape) | H: on | 10 | Level 3 |
| 5 | High (CrO2) | H: on | 11 | Level 4 |
| 6 | Metal | H: on | 12 | Bias 1 |
| 7 | 70 µs (EQ) | H: on | 13 | Bias 2 |
| 8 | Tape tuning | | 14 | Bias 3 |
| 9 | Level 1 | | 15 | Bias 4 |

So the bus carries the **tape type**, and the auto tape tuning's result.

## The display (printed page 15)

`V1`, **BJ214GK** (Yamaha part VQ667400), 47 pins: filament `F1`/`F2`, anodes `P1` to `P10`, grids `1G` to `9G`.
Multiplexed: the microcontroller lights one grid at a time and puts that grid's anodes high.

| Anode | 9G | 8G | 7G | 6G | 5G | 4G | 3G | 2G | 1G |
|---|---|---|---|---|---|---|---|---|---|
| P1 | a | a | a | a | L1 | L5 | L9 | L13 | 0-M |
| P2 | b | b | b | b | L2 | L6 | L10 | L14 | FULL |
| P3 | c | c | c | c | L3 | L7 | L11 | L15 | INTRO |
| P4 | d | d | d | d | L4 | L8 | L12 | I/NORM | ◁ |
| P5 | e | e | e | e | R1 | R5 | R9 | R13 | ▷ |
| P6 | f | f | f | f | R2 | R6 | R10 | R14 | Dolby B |
| P7 | g | g | g | g | R3 | R7 | R11 | R15 | Dolby C |
| P8 | REPEAT | — | ▫ | SYNCHRO | R4 | R8 | R12 | II/HIGH | Dolby S |
| P9 | MEMORY | — | — | REC | TAPE TUNING | — | — | IV/METAL | MPX FILTER |
| P10 | — | — | — | S1 | S1 | S1 | S1 | S1 | — |

- Grids 9 to 6 are the **4-digit counter** (7 segments each; 9G is the leftmost digit and also carries REPEAT and
  MEMORY).
- Grids 5 to 2 are the **peak meters**: `L1`–`L15` and `R1`–`R15`, from −30 to +8 dB (−30, −20, −17, −14, −12, −10, −8,
  −6, −4, −2 (the Dolby mark), 0, +2, +4, +6, +8). `S1` is the meter's printed scale.
- Grid 1 carries the indicators. REPEAT, 0-M and FULL are the KX-493's (the KX-393 has no repeat), as is Dolby S.
- There is no play or wind arrow: the transport isn't on the display, except INTRO ◁ ▷.

On the front board the schematic gives the voltages while playing: grids and most anodes "~" (multiplexed), `P8`
−20.3 V, `P9` −14.3 V, `P10` 4.4 V, the filament at −16.3 V.

## The 27-way flat (schematic, right side)

From `CB7` (main board, Molex 52045) to `CB8` (front board, Molex 52044), through a jumper flat (`#3`). The lines in
the order drawn, from the top (pin 1 side to be confirmed on the boards):

| # | Line | # | Line | # | Line |
|---|---|---|---|---|---|
| 1 | `G` (ground) | 10 | `G8` | 19 | `P6` |
| 2 | `KEY1` | 11 | `P10` | 20 | `G3` |
| 3 | `KEY2` | 12 | `G7` | 21 | `P5` |
| 4 | `REM` | 13 | `P9` | 22 | `G2` |
| 5 | `G` | 14 | `G6` | 23 | `P4` |
| 6 | `+5V` | 15 | `P8` | 24 | `G1` |
| 7 | `F` (filament) | 16 | `G5` | 25 | `P3` |
| 8 | `G9` | 17 | `P7` | 26 | `P1` |
| 9 | `F` (filament) | 18 | `G4` | 27 | `P2` |

Everything the bridge needs on the front side is here: ground, `KEY1`, `KEY2`, `REM`, `+5V`, and all 19 display lines.
**The filament (`F`, about −16 V with AC on top) and the display lines (down to −21 V) sit next to the logic lines.**

### The keys

`KEY1` and `KEY2` are A/D inputs (pins 1 and 2), each pulled to +5 V through 10 kΩ (`R142`, `R143`). Each key grounds
its line through a ladder of resistors. Read from the scan (to confirm):

| Line | 0 Ω | 1.2 kΩ | 2.5 kΩ | 4.7 kΩ | 7.7 kΩ | 11.6 kΩ | 17.8 kΩ |
|---|---|---|---|---|---|---|---|
| `KEY1` | **STANDBY/ON** (`SW1`, own board) | STOP | PLAY | FF | REW | INTRO ▷ | INTRO ◁ |
| `KEY2` | REC/PAUSE | MUTE/SEARCH | DOLBY NR | AUTO TAPE TUNING | COUNTER RESET | MEMORY | |

STANDBY/ON (`SW1`, "POWER") sits on its own small board (`MAIN(4)`), wired by `W1` to `CB5`, and shorts `KEY1` to
ground. It is a momentary key, not a mains switch.

### The remote sensor

`U1`, **SPS-421-1**, on the front board: ground, `VC` 4.8 V and `VO` 4.8 V (idle). `VO` is the `REM` line, which goes
down the flat straight to pin 22. No gate in between: the Pico can pull it low.

## Power (schematic, "power supply"; block diagram)

- The mains goes straight to transformer `T501` (`CB501`): **no switch in the primary**. The transformer is always on,
  which is the 5 W in standby.
- Windings: 4.8 V AC for the filament, 22.4 V AC through bridge `D8` (S1VB20) to `VB` (26.6 V), and the others.
- `IC14`, an **AN78N05** regulator, from 13.0 V: 5.6 V at its output (lifted by `D6`), then 4.8 V through `D4`/`D5`:
  the `+5V` of the microcontroller and the front board, always on.
- `+15V` from `Q35`, `−21V` from `Q36` (for the display), and the muting circuit (`Q38`, line mute at power on and off).
- `POWER PULSE` (pin 8) lets the microcontroller see the mains go.

So the Pico can take power from the deck's +5 V and stay on in standby. The AN78N05 is a 300 mA part; with 13 V in,
the Pico's 50 to 100 mA adds up to 0.75 W to it. To check on the bench (its temperature), or feed the Pico from `VB`
through a small buck converter instead.

## The front panel (owner's manual)

**Keys:** STANDBY/ON, EJECT (mechanical), INTRO SCAN ◁ and ▷, COUNTER RESET, MEMORY, AUTO TAPE TUNING, DOLBY NR,
◄◄, ►►, ►, ■, REC/PAUSE, MUTE/SEARCH. **Knobs:** phones level, bias adjust, play trim, balance, rec level.

Functions worth knowing:

- **Selection search:** ◄◄ or ►► with MUTE/SEARCH skips to the previous or next song (blanks of at least 4 s).
- **Intro scan:** plays the first seconds of each song, either direction.
- **Memory stop**, **0-stop**, **rec return**: winding stops at a memorised reading, at `0000`, or where recording
  began.
- **Rec mute:** records 4 s of silence and pauses.
- **Auto tape tuning:** about 20 s in rec pause, to set bias and sensitivity.
- **CD synchronised recording:** with a Yamaha CD player whose remote has a SYNCHRO key. The bridges could do it
  over Wi-Fi instead.
- Power: 230 V, 50 Hz; 12 W on, 5 W in standby.

## The remote

The KX-393 was sold without a remote. The optional one is the **RKX1** (VU643800), shared with other decks.

### The codes (schematic page, "Remote Control Data")

| Key | Custom | Data | Contract name |
|---|---|---|---|
| Intro scan ◁ | 7F | `1E` | `intro_scan_back` |
| Intro scan ▷ | 7F | `1F` | `intro_scan_forward` |
| Counter reset | 7F | `0D` | `counter_reset` |
| Search ◄◄ | 7F | `0B` | `previous` |
| Search ►► | 7F | `0A` | `next` |
| ◄◄ | 7F | `01` | `rewind` |
| Play | 7F | `00` | `play` |
| ►► | 7F | `02` | `fast_forward` |
| Rec/pause | 7F | `04` | `record` |
| Stop | 7F | `03` | `stop` |
| Rec mute | 7F | `05` | `rec_mute` |

The KX-493's table is the same. **No power code**: power is the `KEY1` line.

### The address

The only captured codes are Remote Central's Pronto codes for the KX-W421, from its remote VS90590 (not the RKX1).
Decoded they are **NEC, address 7A/85**, with the same data bytes as the table above for play, rewind, fast forward,
stop and record; IRDB's Yamaha "Tape Deck" device 122 (`0x7A`) agrees. On the CD-S300 the manual's custom code (79)
was the NEC address as is. So either the KX-393 answers to 7F and the KX-W421 to 7A, or the manual's 7F is
written another way. The first test on the deck settles it (`tools/ir_try.py`). The bridge defaults to 7F.

Remote Central also lists, for the double deck: Deck A/B `06`, Dir A `07`, Dir B `40`. Not used on the KX-393.

`groove-rig` carries the five captured codes at 7A (`yamaha_kx393.yaml`, "not yet field-tested");
`tools/test_ir.py` checks their data bytes against the manual's. Once the address is settled, groove-rig gets it, and
the six other keys.
