# Plan

The fourth modified device, after the SP103, the MR 780 and the CD-S300, and the same path: look and measure first,
then capture, and only then solder. The service manual has the schematic and the microcontroller's pin table
(`docs/research.md`), so the multimeter only checks what they say.

Written on 2026-11-17, away from the deck: after reading both manuals, before any photo or measurement.

## Safety

- The KX-393 plugs straight into the mains (230 V) and **the transformer is always on**: STANDBY/ON is a logic key,
  not a switch. Unplug the deck before opening it and before touching anything inside.
- **The display runs at up to −21 V**, and its filament at about −16 V with 4.8 V AC on top. Both sit on the 27-way
  flat, **next to** the lines the Pico uses (`KEY1`, `KEY2`, `REM`, `+5V`). A slipped probe or a solder bridge there
  puts −21 V on a Pico pin. Solder those joints with the plug out, and check each one for shorts with the beeper.
- **The logic is 5 V.** The RP2350's pins tolerate 5 V only while the Pico itself is powered. The Pico takes its
  power from the deck's own +5 V, so both come and go together, but every input gets a series resistor or a divider
  anyway (step 3 decides which).
- **Recording erases tape.** Every IR test uses a cassette with both record tabs broken off, or no cassette.
- Pico wires only on existing through-hole joints (the flat's joints on the front board, the microcontroller's legs),
  never on SMD pads. Each wire held with hot glue or kapton tape. Nothing removed: to undo, unsolder the wires.

## Goals

Taken from the CD-S300's (2026-11-16), to confirm with the owner:

1. **Know the state**: on or standby; stopped, playing, winding, searching, rec pause or recording; the tape type;
   Dolby; the counter.
2. **Remote control over Wi-Fi**, including power, with nothing pressed by hand.
3. **Easy to undo**: nothing removed.

Alongside: the DeviceLink contract `api` 2 (`device-link/docs/contract-v2.md`), `kind` `tape_deck`.

## Where the state comes from (from the service manual, 2026-11-17)

The display is driven straight by the microcontroller (no bus to listen to, unlike the CD-S300), so there are two
ways in:

| Way | What it gives | Cost |
|---|---|---|
| **A. The mode pins** of the microcontroller (5 V logic) | The transport (motor, solenoid, bias, line mute, rec/play select), the reel pulse, and the port expander's 2-wire bus (tape type) | About 8 wires on the chip's legs, each with a divider |
| **B. The display lines** on the flat (19 lines, +4.8 to −21 V) | Everything the display shows: the counter as shown, the peak meters, every indicator | 19 wires, each with a level shifter that must not load the display (off-level drive to be measured first) |

**Start with A.** It answers the first goal except the counter, with few wires and plain logic. The counter can be
kept by the bridge from the reel pulse (and reset with `counter_reset`), close enough for "where on the tape". **B
is the second phase**, if the true counter or the meters are wanted (the meters are the VU-source idea).

Power (on or standby) needs one more line either way: `P10` on the flat (the meter scale, at 4.4 V while the display is
on, off in standby) through a level shifter, or a 5 V signal that only lives while on (to find on the bench).

## The wiring (planned)

### On the front board, at the flat's joints (`CB8`)

Chosen on 2026-11-17: the front board's solder side faces the inside of the deck, so `CB8`'s joints can be reached
from above with the case off and the front panel on. The main board's solder side (`CB7`, whose silkscreen names
every line, `docs/research.md`) would need the bottom cover off.

`CB8` has no names printed. Its two staggered rows should follow `CB7`'s: 14 joints for the odd lines (`G`, `KEY2`,
`G`, `F`, `F`, `P10` … `P2`) and 13 for the even ones (`KEY1`, `REM`, `+5V`, `G9` … `P1`). The wires go on the first
three joints of each row at the line 1 end. The beeper finds that end before anything is soldered (step 2).

Confirmed on 2026-11-17 (`docs/measurements.md`): line 1 is the left end, looking at the front board from behind.

| Wire | `CB8` line | `CB8` joint (from the left) | Pico pin | What for |
|---|---|---|---|---|
| Ground | `G` (line 1) | top 1 | 3 (GND) | Common ground |
| `REM` | line 4 | bottom 2 | 9 (GP6) | Send the remote's keys: pull low only, against the sensor's output, as on the SP103 |
| `KEY1` | line 2 | bottom 1 | 10 (GP7) | Press STANDBY/ON: pull low only, against 10 kΩ |
| `+5V` | line 6 | bottom 3 | 39 (VSYS) | Power the Pico, also in standby (see "Power on and off") |

Line 7 (`F`, the filament, about −16 V) is the joint after line 5 on the odd row, diagonally next to `+5V`. Check 6
against 7 with the beeper after soldering.

`KEY1` and `KEY2` could also be read (through a divider into an ADC pin) to see which panel key was pressed: that
tells FF from REW and catches COUNTER RESET from the panel. Optional.

### On the main board, at the microcontroller's legs (`IC12`)

Each through a 10 kΩ / 20 kΩ divider (5 V to 3.3 V), unless step 3 shows the RP2350's 5 V tolerance is enough.

| Pin | Signal | Pico pin | Why |
|---|---|---|---|
| 23 | Capstan motor | GP8 | Tape moving |
| 24 | Solenoid | GP9 | Heads engaged |
| 21 | Bias | GP10 | Recording |
| 27 | Line mute | GP11 | Winding, rec pause |
| 32 | Rec/PB select | GP12 | Rec pause or recording |
| 7 | Reel pulse | GP13 | The counter, winding against playing |
| 19 | Expander clock | GP14 | Tape type (PIO sniffer) |
| 20 | Expander data | GP15 | Tape type |

Later, if wanted: 29 and 30 (Dolby), 31 (MPX), 28 (rec mute), 26 (head select).

**Rule:** with the `+5V` wire on VSYS, never plug the Pico into a computer's USB: USB would feed the deck's logic.
Updates go over Wi-Fi.

## Power on and off

From the schematic: the transformer is always on, the AN78N05 (`IC14`) keeps the +5 V up in standby, and STANDBY/ON
grounds `KEY1`. So:

- **The Pico lives in standby** on the deck's +5 V, and stays on the network.
- **`power_toggle` presses STANDBY/ON** by pulling `KEY1` low for 200 ms (`firmware/panel.py`). The remote has no
  power code.
- To check: the AN78N05 is a 300 mA regulator fed from 13 V; the Pico adds up to about 0.75 W to it. Feel or measure
  its temperature after an hour with the Pico on. If it runs hot, feed the Pico from `VB` (26.6 V) through a small
  buck converter.

## Step 1: photos

The service manual is here (2026-11-17, `docs/manual/`). The photos (into `docs/images/`, reduced to 2400 px; full
size in `docs/images-originais/`, out of git):

| Photo | Why |
|---|---|
| Front, rear and the label | Model, voltage, serial, date |
| Inside, from above, case off | Which board is where |
| The microcontroller (`IC12`), close enough to read its marking, and its legs from the solder side | Package (through-hole?) and pin 1 |
| The 27-way flat at both ends (`CB7`, `CB8`) and `CB8`'s joints from the solder side | Where the front-side wires go, line 1's end |
| The remote sensor (`U1`) and the front board behind the display | The `REM` path |
| The STANDBY/ON board (`SW1`) and its wires | The `KEY1` path |
| The power supply: `IC14` with its heatsink (if any), `T501` | Room for the Pico's current |
| The display lit, with a cassette playing | The indicators on this unit |

## Step 2: multimeter

With an illustrated guide page (as for the CD-S300, `devices/cds300/docs/measurement-guide.html`), built on the photos:

1. **The mode table:** pins 21, 23, 24, 26, 27, 28 and 32 in stop, play, FF, REW, search, rec pause and rec. Settles
   which of the two printed tables is right (`docs/research.md`).
2. The `CB8` map: which joint is which line (beeps to the microcontroller's pins), line 1's end.
3. `+5V` on and in standby, `REM` at rest, `KEY1` at rest and with each key pressed (checks the ladder).
4. `P10` and one grid line, on and in standby, against ground: the display lines' levels.
5. The `IC14` temperature with a 100 mA load (later, with the Pico on).

## Step 3: logic analyzer

1. The port expander's bus (pins 19 and 20) while loading normal, CrO2 and metal tapes: the bit order and the frame.
2. The reel pulse (pin 7) while playing and winding: pulses per counter step, and the rates.
3. For way B later: one grid and one anode line through a divider, to see the multiplex timing.

## Step 4: the program

1. **The bridge base**: done (2026-11-17). Cable-free Wi-Fi setup (`AmpLink-KX393-XXXX`, key `amplink-setup`),
   discovery, updates over Wi-Fi, from the shared base (`device-link`, `firmware-base/`).
2. **`/device`**: done, with the 11 remote keys and `power_toggle`, and no state fields yet.
3. **The remote keys and `/control`**: done and tested on the deck (2026-11-18). The deck answers both 7F and 7A
   (not other addresses), but **ignores a single frame**: each key goes out as 6 frames in a row (3 sometimes miss
   while winding). The IR pin drives 12 mA (pulling low only). Tested: play, stop, fast forward, rewind, search both
   ways, intro scan both ways, counter reset. Not tested (needs a recordable tape): record, rec mute.
4. **`power_toggle`**: tested (2026-11-18): standby and back on. The Pico stays on the network in standby.
5. **The state reader** (way A): after steps 2 and 3.

## Ideas

| Idea | What it is | Needs |
|---|---|---|
| Record the CD | The CD-S300 bridge starts the disc, the KX-393 bridge goes from rec pause to record: CD synchronised recording over Wi-Fi | The central point; the transport known on both |
| Amp follows the deck | Play on the deck switches the amp on and selects TAPE | The central point |
| VU source | The peak meters, from the display lines, as the VU source for the SP103 and MR 780 | Way B |
| Counter to time | The counter counts reel turns; with the tape length it becomes minutes left | The reel pulse |
| Tape library | Name a cassette once (`groove-catalog`), with the counter readings of its songs | The counter |
| Rewind at the end | When the tape ends (the deck stops by itself), rewind | The transport |

## Open questions

- ~~The remote's address: 7F (the manual) or 7A (the captured codes).~~ Both (2026-11-18), with repeated frames.
- The mode table: the KX-393's or the KX-493's levels.
- ~~Whether `IC12` is through-hole on this unit.~~ Yes (photos, 2026-11-17).
- Whether the main board's solder side can be reached (the bottom cover) for `CB7`'s and `IC12`'s joints.
- Whether the AN78N05 has room for the Pico.
- How strongly the display lines are pulled to −21 V when off (decides whether way B is safe to tap).

## Wire log

Each wire soldered in the device, where and when. To undo, unsolder in reverse order.

| Date | Wire | Where | Note |
|---|---|---|---|
| 2026-11-17 | Black | `CB8` top 1 (`G`) | Colour to confirm; the volts at the wire ends confirm the joint |
| 2026-11-17 | Yellow | `CB8` bottom 1 (`KEY1`) | Colour to confirm |
| 2026-11-17 | Teal | `CB8` bottom 2 (`REM`) | Colour to confirm |
| 2026-11-17 | Olive | `CB8` bottom 3 (`+5V`) | Colour to confirm. Ends taped apart until the Pico is in |

## First life (2026-11-18)

The Pico 2 W: MicroPython 1.29.0 (`RPI_PICO2_W`) and the bridge by USB, then on the home Wi-Fi as `KX393-D7A2`
(192.168.178.118). Dupont ends: black pin 3, yellow pin 10, teal pin 9 (checked on a photo), olive on the right row
by the USB end (pin 39 to confirm against the silkscreen: on pin 40, VBUS, the Pico would also run). From then on,
updates over Wi-Fi only.

The `REM` line (pin 9 to pin 3) with the Pico in: 3.66 V in standby, 4.4 V with the deck on (4.74 V before the Pico:
the Pico's pad loads the sensor's pull-up a little); near 0 V when held low (`POST /ir/hold`). The deck reads it fine.

Left: `IC14`'s temperature after an hour; record and rec mute with a recordable tape; the colours below are as seen.

## Next, when the Pico arrives (left on 2026-11-17, done 2026-11-18 except steps 6 and 7)

1. **Before the Pico (deck plugged in, volts at the wire ends):** black–yellow 4.86 V, black–teal 4.74 V, black–olive
   4.90 V. Then the deck on and used as before. These settle that black is on top 1 and confirm the colours.
2. **The Pico over USB, one last time:** the bridge firmware in, joins the Wi-Fi. After this, never USB again (VSYS).
3. **Dupont ends**, labelled: black → pin 3 (GND), yellow → pin 10 (GP7), teal → pin 9 (GP6), olive → pin 39 (VSYS).
   Deck unplugged while plugging the Pico in. Pico insulated, away from the transformer and the heatsinks.
4. **First life:** the deck plugged in, in standby; the Pico boots and joins the Wi-Fi.
5. **Tests:** `tools/ir_try.py` (the address: PLAY at 7F, then 7A; a cassette with the tabs out), then each key once;
   `power_toggle` (`KEY1`).
6. **After an hour with the Pico on:** feel `IC14` (AN78N05) for heat.
7. Fill this wire log's colours, and close the case only after the Wi-Fi signal is checked with the lid on.
