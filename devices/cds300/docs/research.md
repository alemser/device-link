# CD-S300: what the service manual and the photos say (2026-11-16)

Source: Yamaha's service manual (2009, 57 pages), in the local copy `docs/manual/cd-s300-service-manual.pdf`, with its
text as `.txt` alongside. Page numbers are the ones printed in the manual. Voltages are the ones printed on the
schematic; the ones measured on this unit are in `docs/measurements.md`.

## Summary

- A 3.3 V serial VFD, with the controller inside the glass. Four logic lines.
- A 15-way flat cable carries everything of interest: display, remote, LEDs and keys. Logic only, 0 to 3.3 V.
- The VFD's high-voltage lines (filament and −27 V) go through **another**, 4-wire cable. Don't touch it.
- No standby: the front switch cuts the 230 V.
- Every remote code is in the manual.

## The display (page 22, schematic on page 43)

- `V701`, model **14-ST-68GINK**, on the front board (`OPERATION (1)`).
- 14 grids. Grids 1 to 12 are the 12 characters, each a **5×7 dot** matrix (35 anodes, `D0` to `D34`). Grids 13 and 14
  are the icons (play, pause, TRACK, TOTAL, REMAIN, PROG, RNDM, REP, FOLDER, A-B, USB, MP3, WMA, AAC and others).
- The controller is inside the glass. Logic pins: `CS` (select), `CP` (clock), `DA` (data), `RESET`, `OSC`. Input only:
  the microcontroller writes, the display never answers.
- Glass supply: `VDD` 3.3 V, `VFL` −28 V, AC filament `F1`/`F2` on −21.7 V.
- The capture answered whether the microcontroller sends character codes or dots: **character codes, in ASCII**, with
  the icons drawn as two custom characters (`docs/protocol.md`).

## The 15-way flat cable (schematic, page 43)

It joins `CB304` on the main board to `CB701` on the front board, and is where the Pico taps in. The front board's
silkscreen (`20261116_082804.jpg`) matches the schematic.

| Line | Name | Schematic voltage | What it is |
|---|---|---|---|
| 15 | `FL_/CS` | 3.3 V | Display select |
| 14 | `FL_DATA` | 0 V | Display data |
| 13 | `FL_CLK` | 3.3 V | Display clock |
| 12 | `FL_/RST` | 3.3 V | Display reset |
| 11 | `D+3.3V` | 3.4 V | Front-board logic supply |
| 10 | `REM` | 3.4 V | Remote receiver signal, idle high |
| 9 | `DGND` | 0 V | Digital ground |
| 8 | `LED_POWER` | 3.3 V | Power LED |
| 7 | `LED_PDIRECT` | 0 V | PURE DIRECT LED |
| 6 | `LED_/USB1` | 3.4 V | USB LED, orange |
| 5 | `LED_/USB2` | 3.4 V | USB LED, green |
| 4 | `KEY_0` | 3.4 V | STOP, PAUSE, open/close keys |
| 3 | `KEY_1` | 3.4 V | PLAY, next, previous keys |
| 2 | `KEY_2` | 3.4 V | PURE DIRECT, CD/USB keys |
| 1 | `DGND` | 0 V | Digital ground |

Between the connector and the glass, each display line has a series resistor (10 to 100 Ω, `R701` to `R704`).

### What the close-ups show (2026-11-16)

- **The numbering is reversed on the main board.** The table above is `CB701`'s (front board). On `CB304` the
  schematic (page 42) counts the other way: line 1 is `FL_/CS` and line 15 is `DGND`. A small triangle on the
  connector marks line 1.
- On the front board, the silkscreen names all 15 lines, in the table's order (`20261116_084556.jpg`). On the main
  board, next to `CB304`, only some are written (`KEY-2`, `KEY-0`, `LED-/USB1`, `LED-POWER`, `REM`, `FL-/RST`,
  `FL-DATA`), in the same order (`20261116_084644.jpg`).
- **The connectors:** the schematic marks them `52044` (front) and `52045` (main), Molex flat-cable connectors with a
  **1.25 mm pitch**, confirmed by a photo with a tape measure (`docs/measurements.md`): about 17.5 mm from the first
  line to the last. The flat has a blue stiffener at both ends and the marking `AWM 20624 80C 60V VW-1`.
- **It can be measured without soldering.** `CB304` stands on the main board with one window per line, the metal
  contact visible (`20261116_083847.jpg`). On the front board, the 15 joints of `CB701` face into the device, in two
  rows (`20261116_084546.jpg`).
- The main board's power connector (`CB301`) is a few centimetres from `CB304`, with names on the silkscreen (`D+5`,
  `DGND`, `+B2` and the others). Each of its pins has a bare bent leg above the white housing, a good soldering point.
- Behind the front board, around the receiver and `IC702`, there is an insulating plastic sheet glued on
  (`20261116_084609.jpg`); it has to be lifted to solder there.
- The chips match the manual: `IC2` LC786922, `IC7` LC87F1HC, and the two NJM2068 on the analogue output board.

### With the front panel off (photos of 2026-11-16, 11:00)

Without the aluminium front, the front board (`YA984-1`, plus the small `YA984-3` USB board and the PURE DIRECT board)
stands upright, its solder side facing into the device and reachable from above. Everything the Pico needs is on
that side.

- **The IR receiver (`U701`)** has its 3 legs soldered behind the board, next to the `IC702` gate (5 legs, SOT-23) and
  `C717`/`C719` (`20261116_111503.jpg`). The output leg is the one with continuity to two neighbouring legs of
  `IC702` (the gate's two inputs): leg C, measured on 2026-11-16.
- **The display resistors** (`R701` to `R704`) sit between the `CB701` joints and the glass, in one row, with the
  codes `100` (10 Ω, the `FL_/RST` one) and `101` (100 Ω) visible (`20261116_111509.jpg`, `20261116_111519.jpg`).
- **The dangerous wires are about 2 cm away:** `W702` (`FLGND`, `ACFL1`, `ACFL2`, `-27`) is to the left of `CB701`,
  on the same side of the board (`20261116_111519.jpg`).
- **The display** (`20261116_111148.jpg`): besides the 12 characters and the known icons, the glass has the circles
  1 to 5 (from a disc changer, unused on the CD-S300) and the "15". Its pins are all on the top edge.
- The USB board (`YA984-3`) and the PURE DIRECT board carry the LEDs `D751` (USB, two colours) and `D702`, the keys
  `SW708` (USB) and `SW703` (PURE DIRECT), and take the wires `W751`, `W703` and `W701A` from the front board
  (`20261116_111152.jpg`, `20261116_111455.jpg`).
- The chassis is stamped **18 AUG 2017** (`20261116_111202.jpg`): this unit was built eight years after the manual
  (2009). Every silkscreen checked so far matches the manual.

### The panel keys (page 30)

Each `KEY_x` line is an analogue input of the microcontroller, pulled to 3.3 V through 10 kΩ. Each key grounds the
line through a different resistor:

| Line | 820 Ω (0.2 to 0.3 V) | 3.3 kΩ (0.9 to 1.0 V) | 12 kΩ (2.0 to 2.1 V) |
|---|---|---|---|
| `KEY_0` | STOP | PAUSE | open/close |
| `KEY_1` | PLAY | next / forward | previous / back |
| `KEY_2` | PURE DIRECT (100 Ω) | CD/USB | — |

Every panel key also exists on the remote. Imitating the keys on the `KEY_x` lines is only a fallback.

## The remote

### The receiver (schematic, page 43)

The receiver `U701` (GP1UE271RK) is on the front board. Its output drives both inputs of an AND gate (`IC702`,
TC7SH08), used as a buffer, and the gate's output is the `REM` line, to pin 15 (`IR`) of the microcontroller.

So `REM` is driven to 3.3 V and to 0 V by a strong output: **the Pico can't just pull it low**, as on a plain receiver
output. The chosen way: tap the **`U701` output** (before the gate), which is weak and accepts being pulled low; the
receiver keeps working (`docs/plan.md`, "The wiring"). The alternative, a 1 kΩ series resistor on `REM` on a bridge
board, was dropped with the bridge.

### The codes (page 56)

Customer code **`79`** on every key. The manual doesn't name the format, but it is **NEC, address 79/86**: `groove-rig`
already has the model (`internal/catalog/models/yamaha_cd_s300.yaml`), and six keys learned on oceano on 2026-09-24
with this unit (open/close, play, stop, pause, previous, next) decode to the same codes.

The manual settles the two doubts noted in `groove-rig`: **A/B is `09`** (added there on 2026-11-16) and **DIMMER is
`54`**. The `power_toggle` (`60`) that `groove-rig` carries comes from other models in the family: the CD-S300's remote
has no such key and the device has no standby.

| Key | Code | Key | Code | Key | Code |
|---|---|---|---|---|---|
| CD/USB | `6F` | 1 | `11` | back (◄◄) | `05` |
| PURE DIRECT | `6E` | 2 | `12` | forward (►►) | `06` |
| open/close | `01` | 3 | `13` | pause | `55` |
| PROGRAM | `0C` | 4 | `14` | previous | `04` |
| REPEAT | `08` | 5 | `15` | play | `02` |
| RANDOM | `1B` | 6 | `16` | next | `07` |
| DIMMER | `54` | 7 | `17` | stop | `56` |
| A/B | `09` | 8 | `18` | FOLDER ▼ | `6A` |
| DISPLAY | `0A` | 9 | `19` | FOLDER ▲ | `69` |
| ENTER | `3F` | 0 | `10` | | |
| CLEAR | `0D` | | | | |

**There is no power key**, and no power code.

## The power supply (schematic, page 45; block diagram, page 33)

- A linear supply. The 230 V input goes through fuse `F801` (500 mA) and switch **`SW801` (POWER ON/OFF)**, the front
  button, and only then reaches transformer `T801`. Switched off at the button, nothing in the device is powered.
- Lines on connector `CB806` (10 ways, to `CB301` on the main board):

| Pin | Name | Voltage | Use |
|---|---|---|---|
| 1 | `M2GND` | 0 | Motor ground |
| 2 | `+B2` | 12 V, unregulated | Input of the USB converter (`IC301`) |
| 3 | `M+7` | 7 to 8 V | Motors and laser |
| 4 | `M1GND` | 0 | Motor ground |
| 5 | `DGND` | 0 | Digital ground |
| 6 | `D+5` | 5.0 V (`IC801`, a 7805 with heatsink) | Logic; becomes `D+3.3V` on the main board (`IC303`) |
| 7 | `A+5` | 5.0 V | Audio |
| 8 | `AGND` | 0 | Audio ground |
| 9 | `A-5` | −5.0 V | Audio |
| 10 | `P_MUTE` | −4.5 V | Mutes the output at power on and off |

  On `CB301`, counting from the end away from the large capacitor with a cross on top, `D+5` is the 5th leg.
- `CB807` (4 wires, seen in `20261116_082821.jpg`) brings the front board the **−27 V**, the filament (`ACFL1`,
  `ACFL2`) and `FLGND`. **High voltage by the Pico's standards: don't touch.**
- The microcontroller has a `POFF_detect` input (pin 57), which warns when the input power goes, and an undescribed
  `STBY` output (pin 79). The supply uses no standby line.

## The main board (pages 28 to 30 and 33)

| Part | What it is |
|---|---|
| `IC305` | Renesas **R5F212CASNFP** microcontroller (R8C, 16-bit, 80 pins, 3.3 V). Drives the display, keys, remote, tray, DAC and the USB chip |
| `IC2` | LC786922: disc servo, MP3/WMA decoding and the digital audio (I2S and S/PDIF) |
| `IC7` | LC87F1HC8A: USB and iPod. Talks to `IC305` over serial (`USB_TX`, `USB_RX`) |
| `IC302` | PCM1780 DAC, driven by `IC305` over three wires (`DAC_/CS`, `DAC_SCL`, `DAC_SDA`) |
| `IC304` | EEPROM: keeps CD/USB mode, PURE DIRECT, "RS-232C ON/OFF" and whether there is a disc |
| `IC4` | TC7SH08: S/PDIF buffer before the optical and coaxial outputs. The 3.3 V S/PDIF is at its input |

`IC305` signals that may help later: `OPSW` and `CLSW` (tray open or closed), `C2_Flag` and `MON_1` (disc read
errors), `USB_IN` (USB stick or iPod connected), `DOUT_MUTE` (digital output muted in PURE DIRECT).

### The rear programming port (schematic, page 44; pages 16 to 21)

At the rear there is a 9-way flat connector (`CB902`), used by Yamaha to program the firmware through a 3.3 V RS-232
adapter. It carries `232C_TX`, `232C_RX`, 3.3 V, ground and the signals that put the microcontroller in programming
mode (`BOOT`, `TMODE`, `/RESET`, `TCK`).

The EEPROM keeps an "RS-232C ON/OFF" setting, so the normal firmware may say something on that serial line. **Not
known.** A listen-only capture of `232C_TX` would tell. The port's other signals are never touched: they erase the
firmware.

### Factory mode (page 15)

Hold PLAY and STOP while switching on. The display shows `FACTORY`. The remote's DISPLAY key shows the firmware
version (in CD mode `IC305`'s, in USB mode `IC7`'s). **The CLEAR key erases the EEPROM.**
