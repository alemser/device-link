# Measurements

The owner measures; Claude takes notes. The **summary** below is what counts; the **log** keeps the readings in the
order they were taken, and some of its hypotheses were corrected later (the summary says which).

## Summary (end of 2026-11-07)

Everything measured with the amp **unplugged**, multimeter black probe on PHONO GROUND (chassis). Values in kΩ.

| Pin | What it is | Certainty |
|---|---|---|
| 5, 17, 19, 20 | GND | Certain (continuous beep, connected to each other) |
| 7 | ON/STBY button | Certain (button leg to the pin, in Ω) |
| 8 | ►► button | Likely (drops from 8 to 6 when pressed) |
| 9 | MONO button | Likely (drops from 10 to 7 when pressed) |
| 10 | ◄◄ button | Certain (button leg to the pin) |
| 11 | DIM button | Certain (button leg to the pin); it also varied with VOLUME, probably an echo |
| 12 | DIRECT button | Certain (goes to ~0 when pressed: no series resistor) |
| 13, 14 | VOLUME | Both change when turning. Endless potentiometer or encoder without clicks: left for the analyzer |
| 15, 16 | SOURCE (encoder with clicks, contacts A and B) | Certain |
| 21 | Remote receiver: **signal**, idle at 3.46 V | Certain (2026-11-18: beeps with the top joint of cable 5) |
| 18 | **Receiver power**, 4.8 V in standby and on | Certain (2026-11-18: beeps with the receiver's power joint) |
| 4 | **Switched 5 V**: 0.02 V in standby, 4.78 V on. The Pico's "amp on" signal | Certain (2026-11-18) |
| 1, 2, 3 | **VFD data**: ~0.1 V in standby, oscillating up to ~4.6 V when on | Likely (2026-11-18); which joint is which still ambiguous |
| 6 | Unknown: beeps with no joint on the display board's back | — |

**2026-11-18 (amp powered):** the display's logic is **5 V**. On the display board's back, **cable 5** (the lilac
wires at the left edge, seen from behind) is the IR receiver's: 4 joints, top = signal (pin 21), 2nd from top = power
(pin 18), 2nd from bottom = GND. See the log for where each line reaches.

What this means for the project:

- **All the buttons and both knobs go through the flat.** The Pico, connected only to it, can read and "press"
  everything, including DIRECT (which the remote does not have).
- The buttons, except DIRECT, have a **series resistor** (hundreds of Ω to tens of kΩ); **each button has its own
  pin** (not a single ladder).
- The **VFD filament does not go through the flat** (no pair of pins beeps with each other): it comes from the
  transformer's yellow wires straight to the display board.
- The **VFD data** should be among 1, 2, 3, 4, 6 and 18. Pins 2 and 3 have the same value (8.62): they may be a pair
  (clock and data).

Open:

1. ~~Receiver leg 3~~: pin 18 (2026-11-18).
2. **Flat pin 1**: confirm which end it is (white mark on the board or via CN8).
3. Confirm that the multimeter was on kΩ.
4. ~~Voltages of pins 1, 2, 3, 4, 18 and 21~~: done 2026-11-18. Pin 6 still without a voltage.
5. **Pins 1, 2 and 3 against the 6 joints of the 3 upright resistors** left of the centre screw, in Ω rather than
   beep: which joint is each pin's direct one (log, 2026-11-18).
6. **`D5V`** on the main board's power connector, standby and on: whether pin 18 (4.8 V) is the same line, i.e.
   whether pin 18 can power the Pico.

## Flat cable numbering rule

- 21 lines, 1.0 mm pitch.
- The numbering is that of the **connector on the display board** (`MR780-DISPLAY-D.DDB`).
- Looking at the display board from behind, **pin 1 is the right-hand end**, the one with the triangle (2026-11-07).
  Still to be confirmed with a white mark on the board or from the CN8 side, on the main board.
- The flat may be reversed: pin 1 here may be 21 at CN8. Check with continuity before using CN8.

## Flat table

| Pin | GND? (beep) | kΩ to GND | Connected to | Standby (V) | On (V) | Notes |
|---|---|---|---|---|---|---|
| 1 | no | 13.53 | group 2, joints 2 and 3 (?) | ~0.1 | oscillates | VFD data (likely) |
| 2 | no | 8.62 | group 2, joints 1 and 2 (?) | ~0.1 | oscillates, 3.6–4.6 | VFD data (likely) |
| 3 | no | 8.62 | group 2, joint 1 (?) | ~0.1 | oscillates, 3.6–4.0 | VFD data (likely) |
| 4 | no | 6.98 | VFD row, 7th joint from the right | 0.02 | 4.78 | Switched 5 V: amp on |
| 5 | **yes** | 0 | | | | |
| 6 | no | 4.5 | nothing found | | | |
| 7 | no | 3.00 | | | | ON/STBY button |
| 8 | no | 6.0 | | | | ►► button (likely) |
| 9 | no | 10.45 | | | | MONO button (likely) |
| 10 | no | 5.5 | | | | ◄◄ button |
| 11 | no | 5.5 | | | | DIM button (also varied with VOLUME: echo) |
| 12 | no | 8.74 | | | | DIRECT button (goes to ~0 when pressed) |
| 13 | no | 0.1 | | | | VOLUME |
| 14 | no | 8.74 | | | | VOLUME |
| 15 | no | 10.42 | | | | SOURCE, contact A |
| 16 | no | 8.74 | | | | SOURCE, contact B |
| 17 | **yes** | 0 | | | | |
| 18 | no | 3.66 | VFD row, 13th joint from the right; cable 5, 2nd from top | 4.8 | 4.8 | IR receiver power |
| 19 | **yes** | 0 | | | | |
| 20 | **yes** | 0 | | | | |
| 21 | no | 8.74 | cable 5, top joint | 3.46 | 3.46 | IR receiver signal |

## Log

### 2026-11-07, amp unplugged, continuity

- Black probe on the rear **PHONO GROUND** terminal (which is the chassis). Beeping with it: **pins 5, 17, 19 and 20**.
- The other 17 do not beep.
- The beep of those 4 is continuous: they are real GND, not a capacitor charging.
- Pins 5, 17, 19 and 20 beep with each other (expected: they are all GND).
- Among the other 17 pins (1–4, 6–16, 18, 21), no pair beeps. So the VFD filament does not go through the flat: it
  must come straight from the transformer's yellow wires to the display board.

### 2026-11-07, amp unplugged, resistance to GND

The guesses in this part (power on 7 and 13, pair 10/11) were disproved later: see the summary.

Black probe on PHONO GROUND, multimeter on Ω (values in kΩ, to be confirmed). Values in the table above. These are
measured with everything connected on the board (they go through the chips), so they serve to group pins, not as
exact values.

- Pin 6: the first reading gave 0 (a mistake); measured again, 4.5.
- Pin 13: 0.1 kΩ (100 Ω), much lower than the others: candidate for power or for an LED.
- Pins 7 (3.00) and 18 (3.66): lower than the signal ones: candidates for power (5 V, 3.3 V).
- Groups of equal values (similar circuits):
  - 2 and 3: 8.62
  - 10 and 11: 5.5 (a pair: could be an encoder, A and B)
  - 9 and 15: 10.4
  - 12, 14, 16 and 21: 8.74 (four equal: buttons or data)
- On their own: 1 (13.53), 4 (6.98), 6 (4.5), 8 (6.0).

### 2026-11-07, amp unplugged, turning the knobs (Ω to GND)

Superseded later: VOLUME is on pins 13 and 14 (not 11 and 10) and SOURCE on 15 and 16 (not only 15).

- **VOLUME**: **pin 11** varies from ~10 down to ~5 kΩ, through the values in between, while turning. A gradual
  change, not click steps: it looks like a **potentiometer** read by the microcontroller (pin 11 is the wiper), and
  not an encoder. It could be a motorised potentiometer (turned by the remote): to be checked.
- **SOURCE**: pins 2 and 3 do not change when turning SOURCE (now they read above 12 kΩ, at rest). SOURCE is not on
  those pins; it may be on another pin or come through another cable (the knob boards have their own wires to the
  main board).
- The VOLUME knob turns endlessly, with no clicks and no end stop. With the remote's VOL ▲▼ it **does not turn**: only
  the dB on the display change. So it is not motorised: it is an **endless potentiometer** (the kind used in
  synthesisers), read by the microcontroller, and the real volume is digital (the microcontroller sets a volume chip).
  This kind of potentiometer usually has **two wipers** out of phase, to tell the direction: **pin 10** (same value as
  11, 5.5 kΩ) is the candidate for the second. Check by turning with the probe on pin 10.
- For the Pico: controlling the volume with the remote's code by wire is the simple path. Imitating the endless
  potentiometer (two analogue voltages) is possible, but unnecessary.
- **SOURCE**: **pin 15** changes value when turning SOURCE. **Pin 9** had the same value as 15 (10.4 kΩ): it is the
  candidate for the second contact. Still to find out whether SOURCE has clicks (encoder or switch) or turns smoothly
  (endless potentiometer, like VOLUME).
- SOURCE **has clicks**, and **pin 9 does not change** when turning it: SOURCE uses only pin 15. Hypothesis: an
  encoder whose two contacts go through different resistors to the same pin, and the microcontroller reads the value
  (each combination gives a resistance). In that case, the values repeat in a cycle of ~4 clicks. To be checked by
  noting the value at each click. Pin 9 is left with no known function.
- SOURCE turns **endlessly**. Click by click on pin 15, the values (kΩ) came out roughly like this: 10, 5, 4, 3, 2,
  5, 4, 3, 6, 8, 5, 4, 3, 2, 1… with no clear cycle and never back to 10. **Inconclusive**: the multimeter is too slow
  for an encoder, and the value it shows depends on how long you wait. On an encoder with clicks, resting on a click
  it usually always gives the same value; the change only happens between one click and the next. Left for the logic
  analyzer (or for pin 15's voltage with the amp on).

### 2026-11-07, amp unplugged, pressing the buttons (Ω to GND)

- **Pin 12**: only **DIRECT** (the button at the far right, above the panel) changes the value. The other buttons do
  not.
- DIRECT takes pin 12 to a value **near 0**: the button connects the pin to GND. For the Pico to "press" it, pulling
  pin 12 to GND for an instant is enough.
- **Pin 14**: changes **only when turning VOLUME**. So VOLUME uses **pins 11 and 14** (the endless potentiometer's two
  wipers); pin 10 is not the second wiper, as was thought.
- **Pin 16**: changes **only when turning SOURCE**. So SOURCE uses **pins 15 and 16**: an ordinary encoder, with its
  two contacts (A and B) on separate pins. The Pico can imitate it by pulling both pins to GND in the right order.
- **Pin 21**: no button or knob changes the value.
- Other buttons (weaker variations than DIRECT's, ambiguous):
  - pin 8: changes a little, but noticeably, with ◄◄ and with ►►;
  - pin 9: MONO;
  - pin 10: ◄◄ and MONO;
  - pin 11 (VOLUME wiper): MONO and ►►;
  - pin 13: changes when turning VOLUME.
  A button moving several pins, and only a little, means the multimeter is measuring "indirectly" through the board's
  other components. To know each button's pin for certain: direct continuity from the button's leg to the flat pin.
- Direct continuity from the button legs to the flat: **only the GND side of ON/STBY beeps (with pin 5)**. The other
  side of each button beeps with no pin. So the panel buttons (except DIRECT) **go through resistors** before the
  flat: probably a resistor ladder read by the microcontroller, as suggested by resistors R32–R35 next to buttons
  K2–K4 on the display board.
- In Ω, from the signal side of **ON/STBY** to the flat: **pin 7** gives a very low value. ON/STBY reaches pin 7
  (through a small resistor). Pin 7 is no longer a candidate for power: it is the line of at least one button (maybe
  the whole ladder).
- In Ω, from the signal side of **◄◄** to the flat: **pin 10** gives very low. ◄◄ = pin 10.
- ON/STBY on 7 and ◄◄ on 10: **each button has its own pin** (with a series resistor), not a single ladder.
- ►► and MONO: hard to reach (rubber cap on top).
- **Owner's correction:** where "MONO gives low on pin 11" was read, it was **DIM**. DIM has **3 legs in a triangle**
  (not in a row). So **DIM = pin 11**, from the button's signal side.
- **Conflict to resolve:** pin 11 also varied a lot when turning VOLUME. New hypothesis: VOLUME is an **encoder
  without clicks** (turns smoothly, but makes and breaks contacts), on **pins 13 and 14**: 14 changed only with
  VOLUME, 13 also changed with VOLUME, and 13 gave 0.1 kΩ at rest (an encoder contact that was closed in that
  position). The variation on 11 would be an echo. Test: beep on pin 13 (and then on 14), turning VOLUME slowly: if
  the beep goes on and off, it is an encoder contact.
- Beep while turning VOLUME slowly: **never beeps** (pins 11, 13 and 14). Not a tie-breaker: if the VOLUME contacts go
  through series resistors, like the buttons', the beep (which only sounds below ~50 Ω) does not come on even if it
  is an encoder. Left for the voltage with the amp on or for the logic analyzer. What is known: VOLUME moves pins 13
  and 14 (and 11, which is DIM).
- Pressing from the front, in Ω on pin 8: **►►** takes the value from **8 to 6 kΩ**. Likely ►► = pin 8 (a small
  drop; to be checked that no other pin drops more with ►► pressed).
- Pressing from the front, in Ω on pin 9: **MONO** takes the value from **10 to 7 kΩ or less**. MONO = pin 9. The
  drop, similar to ►►'s on pin 8, reinforces that these buttons have a series resistor, and ►► = pin 8.
- **Pins 1, 2, 3, 4, 6, 18 and 21 are left**: remote receiver, VFD data and power.

### 2026-11-07, amp unplugged, remote receiver

- The receiver sits on a separate small board, between VOLUME and DIRECT, connected by a short cable to the display
  board.
- **Middle leg = GND.** That is the typical pinout of 38 kHz receivers like the VS1838B (signal, GND, power): so one
  end is the signal and the other the power.
- **Leg 1** (the left-hand one, counting left to right as the owner was looking) **beeps with pin 21**. Pin 21 had
  8.74 kΩ to GND and did not change with any button: consistent with the output (signal) of an IR receiver, which
  idles high. Strong candidate: **pin 21 = remote signal**.
- **Leg 3** (the right-hand one), in Ω: pins **1 to 3** and **7 to 17**: no value (open). Pins 4, 6, 18 and 21 are
  still missing.

### 2026-11-18, joints on the display board's back, then voltages

Taken with the bench sheet (Claude's measurement page); the owner's text, as copied from it. "Group 2" is the group of
joints just above and to the right of the flat connector (seen from behind, the screw on its left); "group 3" is the
long row of VFD pins, counted from the right along its lower part, joints without solder counted too.

Amp unplugged, beep:

- **Cable 5** (lilac wires at the left edge): 4 joints. Top = pin 21 (IR signal); 2nd from bottom = GND; 2nd from top
  = pin 18 (the receiver's power).
- Pin 1: group 2, joints 2 and 3. Pin 2: group 2, joints 1 and 2. Pin 3: group 2, joint 1.
- Pin 4: group 3, 7th joint. Pin 18: group 3, 13th joint.
- Pin 6: beeps with nothing found.

The group 2 beeps overlap (joint 1 with pins 2 and 3, joint 2 with pins 1 and 2), yet joints 2 and 3 read different
voltages with the amp on, so they are not one node. Likely the beep sounding on a low resistance through a component,
or the probe bridging two joints. To redo in Ω: each of pins 1, 2, 3 against each of the 3 joints.

"Group 2" here is the owner's: **the 3 upright resistors just left of the centre screw** (seen from behind, above
and right of the flat connector; owner's crop, 2026-11-18). Each line goes through one of them, so each has a joint on
the flat's side and one beyond the resistor: a low-value resistor beeps at both ends, which explains the overlap. The bench
sheet's first photo marked a different group (2 joints, above and left of the connector) as "2"; the first Ω
attempt was made there by mistake: pins 1/2/3 against its joints 1 and 2 read 23.5/18.5/16.5 Ω (both joints the
same), and against a third point 12.5/8/6.5 Ω. None near 0: that group is not one of these lines. To redo on the
owner's group 2, noting the leads' own resistance first.

Amp plugged in, black probe on GND, V DC, standby | on (values per group 2 joint where the owner gave them):

| Line | Standby | On | Notes |
|---|---|---|---|
| Group 2, joint 1 | 0.10 | 3.64–4.0, oscillating | During the valve warm-up countdown |
| Group 2, joint 2 | 0.10 (once 0.10–4.58) | 4.0–4.58, oscillating; once 4.50 | During the warm-up |
| Group 2, joint 3 | 0.11 | 0.20 | |
| Pin 4 | 0.02 | 4.78 | |
| Pin 18 | 4.8 | 4.8 | |
| Pin 21 | 3.46 | 3.46 | |

Pins 1–3 against the bottom joint of each upright resistor (res1 left, res2 middle, res3 right), in Ω, as the owner
read them ("0" = the meter showed 0.0): pin 1: 19.7 / 119.7 / 0; pin 2: 14.7 / 0 / 0; pin 3: 0 / 0 / 14.7.
Inconsistent: 0.0 on res3 for pins 1 and 2, and on res2 for pins 2 and 3, would mean pins 1–3 shorted together,
which their different voltages rule out (likely the probe bridging two 1.0 mm legs). Not needed anyway: **the three resistors are the three VFD data lines** (voltages above), and
which one is clock or data is the logic analyzer's job. Esperas go on each resistor's bottom joint, labelled A, B, C
from left to right.

### 2026-11-18, the esperas (wires for the Pico), soldered

Seven wires, each added on an existing joint of the display board (nothing removed), amp unplugged:

| Label | Where | Wire colour |
|---|---|---|
| IR | Cable 5, top joint (pin 21) | blue |
| 5V | Cable 5, 2nd from top (pin 18) | red |
| GND | Cable 5, 2nd from bottom | white |
| A | Left upright resistor, bottom joint | orange |
| B | Middle upright resistor, bottom joint | olive |
| C | Right upright resistor, bottom joint | purple |
| LIGA | VFD row, lower part, 7th from the right (pin 4) | orange (same as A: labelled) |

**PENDING (2026-11-18, amp closed again):** with the Pico wired, A, B and C read 0 all the time, also through a
power-on and its countdown (triggered capture, `tools/bus_capture.py`), while LIGA reads right through the same PIO.
So A, B and C don't reach GP2, GP3, GP4 (the same symptom as the IR wire, whose solder had come off). To check end to
end with the beep at the next opening, resolder with strain relief, then capture power-on and volume.

Checks, amp unplugged: blue/red/white beep with pins 21/18 and PHONO GROUND; no beep between neighbours (IR, 5V,
GND among themselves; A–B, B–C; A, B, C against GND). Still to do with the amp on: display, remote and warm-up as
before, and 4.8 V between red and white.

What it means: the display's logic is 5 V, switched on with the amp (pin 4); pins 1–3 carry the VFD's data (the
oscillation while the countdown runs); pin 18 is the only flat line alive in standby; the IR line idles at 3.46 V, so
the Pico (3.3 V) can sit on it directly. `D5V`, `APD`, `SYS` and `POW/OF` were not measured.
