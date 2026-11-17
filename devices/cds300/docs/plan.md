# Plan

The same path as the SP103 and the MR 780: look and measure first, then capture, and only then solder. The difference
here is a service manual with schematics (`docs/research.md`), so the multimeter only checks what the schematic says.

Written on 2026-11-16, before any measurement; kept up to date with the decisions since.

## Safety

- The CD-S300 plugs straight into the mains (230 V). The 230 V part is the brown power-supply board: power inlet, fuse,
  the front power switch and the transformer. **Don't touch it**, and wires only with the plug out.
- The VFD uses **−27 V** and an AC filament. Those reach the front board through the 4-wire cable from `CB807`
  (`FLGND`, `ACFL1`, `ACFL2`, `-27`), on the `W702` connector. The Pico connects only to logic at 0 to 3.3 V.
- The device has no earth (2-pin plug). With the logic analyzer, run the Mac **on battery**, so the charger doesn't
  make an earth path.
- The rear programming port (`CB902`) has signals that erase the device's firmware. Only ever listen on `232C_TX`.
- In factory mode the CLEAR key erases the EEPROM. Don't send `clear` by mistake with the device in that mode.
- Pico wires only on existing through-hole joints (`CB701`, the legs of `U701`, the pins of `CB301`), never on SMD
  pads. Each wire held to the board with hot glue or kapton tape, so it doesn't pull the joint. Nothing is removed:
  to undo, unsolder the wires.

## Goals

The owner's requirements (2026-11-16), in order:

1. **Know the exact state**: playing, paused or stopped, track, time, disc in, tray, CD or USB mode, PURE DIRECT.
2. **Remote control over Wi-Fi**, with the remote's codes sent down a wire.
3. **Easy to undo**: nothing removed.

Alongside both: share the state with the other devices, through the same contract as the amps.

**Out of scope: writing to the display** (decided 2026-11-16). The CD-S300's display is simple (12 characters and the
icons) and there is nothing more to show on it. The Pico only reads the display; it never writes.

## The wiring: wires soldered in parallel (decided 2026-11-16)

The Pico only listens to the display and only pulls the receiver's line low, so nothing needs cutting or removing:
the wires go on top of existing joints and end in one connector, where the Pico or the logic analyzer plugs in (the
captures used the same wires, without clips).

| Wire | Where | Pico pin | What for |
|---|---|---|---|
| `DGND` | `CB701`, top 5th (line 9) | 3 (GND) | Common ground |
| `FL_/CS` | `CB701`, top 8th (line 15) | 4 (GP2) | Read the display |
| `FL_CLK` | `CB701`, top 7th (line 13) | 5 (GP3) | Read the display |
| `FL_DATA` | `CB701`, bottom 7th (line 14) | 6 (GP4) | Read the display |
| `FL_/RST` | `CB701`, bottom 6th (line 12) | 7 (GP5) | Know when the display is reset |
| `IR` | `U701`, leg C (output) | 9 (GP6) | Send the keys. The Pico only pulls low, against the receiver's internal resistor, as on the SP103: no series resistor |
| `D+5` | `CB301`, 5th leg (main board) | 39 (VSYS) | Power the Pico; ground through pin 3 |

Which `CB701` joint is which line: the silkscreen behind the front board gives the map (odd lines on the top row, even
on the bottom, left to right), and three beeps from the `CB304` windows confirmed it (`docs/measurement-guide.html`).
Positions count the joints left to right, looking at the front board from behind with the `W702` connector on the
left: 8 joints on the top row, 7 on the bottom.

The GP pins are the same for the logic analyzer (channels 1 to 5) and the bridge, so the harness fits both.

**Rule:** with the `D+5` wire on VSYS, never plug the Pico into a computer's USB: USB would power the CD player's logic
from behind. Updates go over Wi-Fi.

**Dropped: a bridge board on the flat cable.** A board between the two ends of the flat (two latchless 1.25 mm
connectors, a new flat, and a 1 kΩ resistor on the `REM` line, which comes from a logic gate and can't be pulled low
directly) was only worth it for writing to the display without touching the Yamaha board. Without writing, it costs
more and gains nothing. The flat's pitch was measured anyway: 1.25 mm (`docs/measurements.md`).

## Power on and off

The front button is a switch on the 230 V (`SW801`), and the remote has no power key. With the device off the Pico is
off, and nothing over Wi-Fi turns it on. Three ways out:

| Option | What changes | Cost |
|---|---|---|
| **A. Accept it** | The Pico lives while the device is on. It leaves the network when the device is switched off, which the hub reads as "off" | None |
| **B. Smart plug** | The button stays pressed, and a Wi-Fi plug switches the device. The hub drives the plug | One plug; nothing inside the device |
| **C. Relay inside** | A small always-on 5 V supply for the Pico, and a relay instead of the switch | Works on the 230 V, inside a device with no earth |

**Decided 2026-11-16: start with A, and move to B** if switching on over Wi-Fi is missed. C repeats what was turned
down for the MR 780 (a new supply inside the device) and is the only one with a shock risk.

For B, check first: switched on at the plug, does the device come back in the mode it was in (the EEPROM keeps CD/USB
and PURE DIRECT) and read the disc by itself?

## Step 1: photos and manual

**Done 2026-11-16**: the photos and the service manual. The close-ups showed the flat at both ends, the line names on
both boards and the power connector (`docs/research.md`). With the front panel off, they also showed the legs of the
receiver `U701` and the display resistors.

## Step 2: multimeter

**Done 2026-11-16** (`docs/measurements.md`), with the illustrated guide (`docs/measurement-guide.html`,
https://claude.ai/artifact/1Gud8oKmZ5HQ2eygCHr3Kf):

1. The `CB701` joint map (three beeps) and the `OUT` leg of `U701` (the one that beeps with `IC702`): leg C.
2. The lines the Pico uses (`D+3.3V` 3.28 V, `FL_/CS` 2.92 V, `FL_/RST` 3.27 V, `REM` 3.28 V) and the `U701` output at
   rest (3.0 V). Nothing above 3.4 V.
3. `D+5` on `CB301`: 5.05 V. `+B2`: 12.00 V (the alternative supply, not needed).
4. The `IC801` heatsink after playing with the Pico on `D+5`: fine.

## Step 2b: Wi-Fi interference

Planned as on the MR 780 (`devices/mr780/docs/plan.md`, step 2b). With the Pico installed and the case closed, the home
network reads **−47 dBm** and no noise or skipping was noticed while playing.

## Step 3: logic analyzer

**Done 2026-11-16**: one capture (`captures/02-playing.lac`) answered the questions: 62 kHz clock, LSB first, the
text in ASCII, the icons as two custom characters, a ~38 ms cycle (`docs/protocol.md`). The icon map was then made
with the Pico inside the device, logging each change while the keys were pressed, which beats 200 ms captures.

## Step 4: the program

1. **The bridge base**: cable-free Wi-Fi setup (`AmpLink-CDS300-XXXX`), discovery, updates over Wi-Fi.
2. **`/device`** on the DeviceLink contract `api` 2 (`device-link/docs/contract-v2.md`): state fields, the remote in
   groups, the firmware repository.
3. **The remote keys and `/control`**: the 30 keys of the manual's table, NEC 79/86, checked bit for bit against the
   `groove-rig` model. **Working on the device 2026-11-16**: `play` over Wi-Fi started the disc.
4. **The display reader**: the PIO sniffer (`display.py`) and the parser and player state (`vfd.py`), checked against
   the real capture and on the device. `/state` carries `transport`, `media`, `disc` and the display's text.

The Wi-Fi, server and update files live in one place, the **shared base** (`device-link`, `firmware-base/`), copied into
each project by `copy_base.py`. The SP103's lessons still hold: no web page on the Pico, no large answers (a `/display`
view over 1 KB stopped answering, 2026-11-16), one `/events` connection per client.

## The common protocol

Written up as the **DeviceLink contract, `api` 2** (`device-link/docs/contract-v2.md`): discovery says the `kind` and
`api`, `/device` describes the device, its state fields and its remote, and the DeviceLink app (the renamed Amp Link)
builds each device's screen from it, with firmware updates from each device's GitHub release. Decided 2026-11-16:
updates take no password, and the SP103 moves to `api` 2 (`api` 1 was removed everywhere on 2026-11-17).

Decided 2026-11-17: **this CD player's interface is the standard one** (device information, state and IR remote) and
every device follows it, the SP103 included. A device's own extras (the SP103's display texts, VU and info screens)
stay out of the contract, on a web page the bridge serves itself.

**Shared state.** Bridges don't talk to each other: a Pico handles few connections. A central point (`groove-rig` on
oceano) can subscribe to each device's `/events` and apply rules between them; that is a later step, outside this
project.

**The name.** The contract and the app are DeviceLink. The setup networks are still `AmpLink-…` (key
`amplink-setup`); discovery is `DEVICELINK?` only since 2026-11-17.

## Ideas

Beyond the basics (state and commands). "Needs" says what must exist besides.

| Idea | What it is | Needs |
|---|---|---|
| Amp follows the CD | Play on the CD switches the amp on and selects CD; another input or standby on the amp pauses the CD | The central point |
| Recognise the disc | On loading, the display shows the track count and total time. The pair keys the collection (`groove-catalog`): name a disc once, recognise it always | — |
| "Now playing" and history | `groove-display` shows the disc and track; groove keeps what was played | — |
| Disc and USB text | CD-Text and file and folder names, rebuilt from the display's scrolling | — |
| Direct track, program, A-B | From the app, with the remote's number keys | — |
| Sleep timer and alarm | Stop after N minutes; play at a set time | — (the alarm needs option B) |
| Hours of use | Total playing time, kept on the Pico: the laser's age | — |
| Disc health | Count read errors (`C2_Flag`, pin 31 of `IC305`): scratched disc or weak laser | One more wire on the main board |
| Tray | Know it's open (`OPSW`, `CLSW`) without the display | Two more wires, only if the display isn't enough |
| VU source for the amps | The Pico reads the S/PDIF (3.3 V, at `IC4`'s input) and publishes the audio level, as the VU source for the SP103 and MR 780 | To study: whether the Pico can read S/PDIF alongside the rest |
| Output volume | The PCM1780 DAC has a digital attenuator on three wires | To study: shares the wires with the microcontroller and touches the audio path |

## Open questions

- The icons still to map (repeat, random, A-B, program, USB mode, Pure Direct, dimmer): one short session with the
  remote, reading `GET /display`'s `icon_changes`.
- The MR 780 and the SP103 on `api` 2.

## Wire log

Each wire soldered in the device, where and when. To undo, unsolder in reverse order.

| Date | Wire | Where | Note |
|---|---|---|---|
| 2026-11-16 | Black | `CB701`, top 5th (`DGND`) | Beep check: no short |
| 2026-11-16 | Grey | `CB701`, top 8th (`FL_/CS`) | First joint had loose strands (cut, wire taped); redone properly before closing the case |
| 2026-11-16 | Orange | `CB701`, top 7th (`FL_CLK`) | Beep check: no short |
| 2026-11-16 | Teal | `CB701`, bottom 7th (`FL_DATA`) | Beep check: no short |
| 2026-11-16 | Yellow | `CB701`, bottom 6th (`FL_/RST`) | Beep check: no short |
| 2026-11-16 | Purple | `U701`, leg C (output) | Beep check: no short |
| 2026-11-16 | `D+5` | `CB301`, 5th leg → Pico VSYS | Ground through the black wire |
