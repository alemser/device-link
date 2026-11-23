# Plan

The path is the same as the SP103's: first look and measure, then capture, and only then solder. The decisions of
2026-10-28 to 2026-10-30 are in `docs/history/brief-2026-10.md`; this document is the current plan.

## Safety

- The MR 780 plugs straight into the mains (230 V) and has valves: **there are high voltages inside**, also for a few
  minutes after switching off (capacitors). Always: rear switch OFF, cable out of the socket, wait about 5 minutes.
- Do not touch the power supply (`MR780-SMPS-D`) or the valve board.
- The display board carries the VFD's power supply (Q1, DW1, D2–D4, 50 V electrolytics): **tens of volts**. Connect
  wires only to the flat cable's logic lines, and only after measuring each one.
- The Pico's GPIO is 3.3 V. If the VFD bus is 5 V, each wire goes through a divider or a level shifter.
- Wires only with the amp unplugged.

## Goals (owner, 2026-11-07)

1. **Know the amp's state**: on or standby, input, volume, DIRECT, DAB/FM text.
2. **Change what it writes on the display.**
3. **Control it without relying on the remote over the air** (no Broadlink).
4. ~~A Raspberry Pi Zero 2 WH inside the amp~~: **dropped** (owner, 2026-11-08). See below.
5. Bonus: **bass and treble** over Wi-Fi, and **switching DIRECT on or off**.

What the photos already say about each:

| Goal | How | Status |
|---|---|---|
| 1. State | The Pico listens to the VFD's data lines on the flat cable and rebuilds the screens, as on the SP103. On or standby from a main-board signal (`APD`, `SYS` or `POW/OF`) | Feasible. The lines still need measuring |
| 2. Change the display | The Pico in the middle of the data lines, between two flat extensions | Feasible, depends on the protocol (captures) |
| 3. Commands without IR over the air | (a) Send the remote's codes **by wire**, straight into the IR receiver's output, as on the SP103 (nothing goes through the air). (b) Imitate the panel buttons (ON/STBY, DIM, DIRECT, ◄◄, ►►, MONO). (c) Imitate turning the SOURCE and VOLUME knobs, if they are encoders | (a) is the path that already works on the SP103. (b) and (c) depend on how the buttons reach the main board: almost certainly through the same flat cable |
| 4. Pi Zero inside the amp | — | Dropped (2026-11-08) |
| 5a. DIRECT | The remote has no DIRECT, so it means imitating the panel button (3b). The state already shows on the display ("DIRECT ON") | Likely |
| 5b. Bass, mid, treble | See below | Hard |

### No Pi Zero inside the amp (owner, 2026-11-08)

Unlike the SP103, the MR 780 **does not get a Raspberry Pi Zero 2 W inside**. Two reasons:

- **Power:** no new power supply goes into the amp, and drawing 2 to 3 W from the main board's `VCC` line (through a
  DC-DC) would eat into the margin of the transformer and of the Magnat's digital section.
- **Interference:** a computer with Wi-Fi and a GHz clock inside an amp with valves, phono and analogue tone control
  could put noise into the sound or upset the electronics.

Only the **Pico 2 W** stays, which draws little (about 50 to 100 mA at 5 V, with Wi-Fi) and is powered from `D5V`,
the line that stays on in standby. Even so, measure the `D5V` margin first (step 2, item 5) and test whether the
Pico's Wi-Fi interferes with the sound (step 2b).

### Bass, mid and treble

The BASS, MID, TREBLE and BALANCE knobs are on a long board in the panel, full of audio capacitors. That points to an
analogue tone control, with the potentiometers directly in the signal (unlike the volume, which is read by the
microcontroller). If so, controlling them over Wi-Fi means replacing the potentiometers with digital audio
potentiometers that withstand ±12 V: possible, but it touches the signal path and is a project of its own. Confirm
with photos of that board.

DIRECT switches the tone control off. So "tone on and off" over Wi-Fi already comes with DIRECT.

## Phases (owner's decision, 2026-10-30)

**Phase 1: read the state.** Know what goes to the display and whether the amp is on or in standby. A Pico 2 W
inside the amp, only listening to the flat cable. Nothing cut.

**Phase 2: write to the display and control.** The Pico in the middle of the VFD's data lines: it reads what the main
board sends and writes its own version to the display. The other lines pass straight through. Since the VFD has its
own power supply and (from the photos) its own controller, any text can be written. Along with it: the commands (IR by
wire and the panel buttons).

~~**Phase 3: Pi Zero 2 WH inside the amp**~~: **dropped** on 2026-11-08 (see "No Pi Zero inside the amp"). The
project ends at phase 2, with the Pico only.

### The read-only phase (owner, 2026-11-18)

The extensions and flats arrived and passed the bench test, but soldering wires on the extension's 1.0 mm legs is not
feasible for the owner, and three rules hold from now on:

- **Nothing more is bought** (an FFC-to-2.54 mm adapter was considered and turned down).
- **Nothing on the amp is ever desoldered or cut.**
- **No soldering at 1.0 mm pitch.**

So the bridge does what the CD-S300 and the KX-393 do, strictly on the DeviceLink contract: **the device, its state
and its remote (IR by wire)**. Phase 2 (writing to the display) is **parked**: without cutting the data lines there is
nowhere to put the Pico in between them. The owner will think about a clean way, maybe a part made to order to act as
the bridge.

The Pico's wires go on **existing through-hole joints** (a wire added to a joint, nothing removed): the IR receiver's
signal leg for the remote, and the points on the display board's back that the continuity map ties to each flat line.
That map (amp unplugged, flat pin to joint) comes first, then the voltages are measured on those joints.

Firmware since 2026-11-18: the IR sender, `/control` and `/ir/send` (from the KX-393), with the ten keys learned on
the oceano-0003 board (groove-rig's codebook, NEC 40/BF): power, volume down and up, mute, inputs back and forward,
◄◄ ►► and tuning down and up (`firmware/ir_codes.py`). Any other remote key can be tried with `tools/ir_try.py`.

Installed on 2026-11-18 (Pico 2 W, `MR780-D8A4`), wired to 7 wires on the display board's joints
(`docs/measurements.md`): IR control works, and the state has power (the LIGA wire, `power.py`) and the valves'
30 s warm-up (`warmup_s`, counted by the bridge from power-on). The A, B, C data wires reach the
Pico (first capture 2026-11-23, `docs/measurements.md`). **Pending:** the display's protocol, captured with
`tools/bus_capture.py` (the bridge's own `/capture` route: can send an IR key on cue).

**Plan B for the input (owner, 2026-11-18), until the display reader:** the app shows the 15 inputs as a select; the
bridge tracks the input itself (`inputs.py`, `input.json`) and steps the cycle the shorter way, with groove-rig's
measured timing. The first choice only tells it where the amp is (pick what the display shows); turning SOURCE or
using the remote throws it off, and `GET /input?set=<id>` tells it again. The display reader will replace this.

## The flat cable (measured on 2026-10-30)

- 21 lines, 1.0 mm pitch, ~22 mm wide.
- **Bought on 2026-11-08, arrived on 2026-11-18**: two extensions (YDFPC22PIN-1.0: P1 and P2 on the same face,
  silkscreen "1" and "22", the ZIF wants the flat's contacts facing down) and the flats. Bench test flat → extension →
  flat passed: 1:1, position 22 empty. Soldering on the legs turned out not feasible: see "The read-only phase".
- Chosen parts: a **22P 1.0 mm FFC extension** (available ready-made), with the 21-way flat pushed against pin 1 and
  the gap at pin 22 packed with plastic or Kapton. **Test continuity line by line before powering up.** Flats: 21P,
  1.0 mm, ~10 cm, of both types (A and B), because you cannot see which side the contacts are on.
- ~~For phase 2: two extensions, with the Pico between them.~~ Phase 2 is parked (2026-11-18).
- ~~The Pico's wires are soldered to the extension, never to the Magnat's board.~~ Replaced on 2026-11-18: wires
  added to existing through-hole joints, nothing removed (see "The read-only phase").

## Step 1: photos

**Done** (2026-10-30 and 2026-11-07, `docs/img/`, summary in `research.md`).

**Still missing, close up and well lit:**

- The marking on the VFD glass (right corner, looks like "CN20-..." or "CN23"): it may give the model and the pinout.
- The flat's pin labels, on both sides (display board and main board).
- The text on the microcontroller U17 (64 pins) and on U15 (next to the flat).
- The BASS, MID, TREBLE and BALANCE board, both sides (to tell whether the tone control is analogue).
- The SOURCE and VOLUME knobs from behind: encoder (turns endlessly, with clicks, 3 pins and sometimes 2 more) or
  potentiometer.

## Step 2: multimeter

**Unplugged: done on 2026-11-07** (`docs/measurements.md`): items 1 and 6. For item 4 the pin is already known (the
receiver's signal goes to pin 21); the voltage is still missing. Items 2 to 5 are with the amp powered.

1. Amp unplugged: continuity of each flat line to GND.
2. Amp **in standby** and then **on**: voltage of each flat line to GND. Write it in a 21-row table. This separates
   the logic lines (0 V, 3.3 V or 5 V) from the high-voltage ones.
3. The `D+5V`, `APD`, `SYS` and `POW/OF` wires: which has 5 V in standby (to power the Pico) and which changes on
   power-up (so the Pico knows whether the amp is on).
4. The remote receiver's output (to control the amp over Wi-Fi, as on the SP103).
5. The main board's power connector: the `D5V` voltage in standby and on (to power the Pico). `VCC` is no longer
   needed (it was for the Pi Zero, dropped on 2026-11-08).
6. The panel buttons: which flat lines they show up on, and whether each button has its own wire or several share one
   wire with different resistors (a resistor ladder read by the microcontroller). It changes how to imitate them.

## Step 2b: Wi-Fi interference test (owner, 2026-11-08)

Before connecting any wire to the Magnat: see whether the Pico's Wi-Fi disturbs the sound, and find the best place
for it.

**Setup:**

- The Pico powered from a **power bank**, with no wire to the amp.
- A test program that **transmits non-stop** over Wi-Fi (for example, sending UDP packets to the Mac), for the worst
  case.
- The Pico **inside a small plastic bag or box**, held at the end of a wooden stick or ruler: with the amp open and
  on, no pin may touch anything, and the hand stays away. Do not go near the power supply (`MR780-SMPS-D`) or the
  valve board.

**What to listen to:** only **PHONO** (owner's decision, 2026-11-08), with no record and the volume up, with the Pico
near each board (phono, tone, main, display) and then away from everything. Listen for hiss, clicks or hum that change
as the Pico comes close. Phono is the most sensitive input: if nothing shows up there, nothing should show up on the
others (CD, AUX, digital inputs) either. The possible exception is FM and DAB, which suffer for another reason
(harmonics of the Pico's clock in the radio band); if a station ever gets worse with the Pico installed, that is the
suspect.

**Write down** in `docs/measurements.md`: where something showed up, what it was, and the Pico's Wi-Fi signal strength
(RSSI) with the lid closed. The metal chassis acts as a shield: if the signal is weak in there, the Pico retransmits
more, which makes interference and stability worse.

**How to read the result:**

- Nothing shows up: carry on. If later, with the Pico powered from `D5V`, noise appears, the culprit is the ground or
  the power, not the radio (connect only to `D5V`/`DGND`, never to `AGND`, with a capacitor at the Pico's input).
- It shows up only near one board: the Pico stays away from it.
- It shows up everywhere: think about an external antenna or another approach before going on.

## Step 3: logic analyzer

The same Pico with the LogicAnalyzer used on the SP103, on the logic lines:

- Screens: power-on (the warm-up countdown), volume, each input, DIM, DIRECT, INFO on DAB and FM, Bluetooth.
- The remote: **done on 2026-11-18** without capturing. The oceano-0003 board's groove-rig codebook has ten learned
  MR 780 keys, all **NEC 40/BF**: power 12, volume down 1F and up 1B, mute 0D, inputs back 1E and forward 1A, ◄◄ 13,
  ►► 58, tuning down 11 and up 5A (`firmware/ir_codes.py`). Anything else on the remote can be tried with
  `tools/ir_try.py`, or captured on the bench with a 38 kHz IR receiver.

Decode and document in `docs/protocol.md`, with the captures in `captures/`.

## Step 4: the program (phase 1)

Reuse from the SP103 (`devices/sp103`) whatever does not depend on the display:

- Wi-Fi and updates over Wi-Fi with automatic rollback (`ota.py`, `tools/send.py`).
- The state and the DeviceLink app's contract (`/state`, `/device`, `/control`: device, state and remote only), with
  new fields: DAB/BT/USB source, station, DAB/RDS text. Anything particular to the MR 780 that a person would configure
  goes on the bridge's own page, as the SP103's display settings do, not in the contract.
- The tests on the Mac, using the real captures.

New: the serial VFD sniffer (PIO) and the MR 780 screen reader.

**Done on 2026-11-09, without the amp: the base** (`firmware/ponte.py`). Cable-free Wi-Fi setup (`wifi.py`, the same
setup as the SP103: network `AmpLink-MR780-XXXX`, fixed key, discovery by UDP broadcast; details in
`devices/sp103/docs/wifi.md`), updates over Wi-Fi (`ota.py`, `main.py`, `tools/send.py`, which also finds the Pico
through discovery) and `/device` (15 inputs with the groove-rig ids). `/state` exists, all `null`. Still to do: the
sniffer, the screen reader and the commands.

Lessons from the SP103 that already apply here:

- No web page on the Pico: the Android app plays that role. The exception is the Wi-Fi setup page, which only exists
  while the setup network is open.
- Avoid long-lived connections (`/events`) and large responses: they lock up the Pico's Wi-Fi (lwIP out of memory).
- Copy each part of the SP103 only when it is used, so as not to carry dead code.

## What the DeviceLink app needs to gain

`GET /device` already describes the device. The MR 780 will be a second device in the same app, with its own input
list and without bass, mid, treble and balance adjustment (they are knobs on the MR 780).

## Open questions

- What to show on the display in phase 2: the same goals as the SP103 (names, VU, needle, Bluetooth quality) or
  others?
