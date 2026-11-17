# Plan

The fourth modified device, after the SP103, the MR 780 and the CD-S300, and the same path: look and measure first,
then capture, and only then solder. Like the CD-S300 there is a service manual with a schematic, so the multimeter
only checks what the schematic says.

Written on 2026-11-17, away from the deck: before any photo, measurement or service manual. Everything below that
depends on the hardware is marked as open.

## Safety

- The KX-393 plugs straight into the mains (230 V), and **stays powered in standby** (5 W): pressing STANDBY/ON
  does not cut the mains. Unplug it before touching anything inside.
- A fluorescent display needs a negative voltage (around −25 to −30 V) and an AC filament. Where those run is on the
  schematic; the Pico connects only to logic.
- **The logic is probably 5 V** (a 1998 design), not the CD-S300's 3.3 V. The RP2350's pins tolerate 5 V only while the
  Pico is powered, so every line the Pico reads gets checked first, and a divider or a series resistor goes in where
  needed (step 2).
- **Recording erases tape.** Every test of the remote codes uses a cassette with both record tabs broken off, or no
  cassette: an unknown code may start recording.
- Pico wires only on existing through-hole joints, never on SMD pads. Each wire held with hot glue or kapton tape.
  Nothing removed: to undo, unsolder the wires.

## Goals

Taken from the CD-S300's (2026-11-16), to confirm with the owner:

1. **Know the state**: playing, winding, stopped, recording or rec-paused, cassette in, the counter, the tape type,
   Dolby.
2. **Remote control over Wi-Fi**, with the remote's codes sent down a wire.
3. **Easy to undo**: nothing removed.

Alongside: the DeviceLink contract `api` 2 (`device-link/docs/contract-v2.md`), `kind` `tape_deck`.

## Step 1: service manual and photos

**The service manual** (to do by hand: the download page has a browser check): "YAMAHA KX-393 493 SM" on
Elektrotanya, or the same 35 pages from audioservicemanuals or ManualMachine. Into `docs/manual/` (kept out of git:
copyrighted), with a `.txt` of its text alongside (`pdftotext -layout`). The pages that matter are listed in
`docs/research.md`.

**The photos** (into `docs/images/`, reduced to 2400 px; full size in `docs/images-originais/`, out of git):

| Photo | Why |
|---|---|
| Front, rear and the label | Model, voltage, serial, date |
| Inside, from above, case off | Board layout, which board holds what |
| Each board's solder side that can be seen without unscrewing | Joints for the wires |
| The display board from behind, and its cable to the main board | How the display is driven |
| The microcontroller, close enough to read its marking | Its part number and pin 1 |
| The remote sensor from behind, its legs | Where the IR wire goes |
| The power supply and transformer, and any small second transformer | What lives in standby |
| Every connector between boards, with its silkscreen | Where to measure |
| The display lit, with a cassette playing | Which indicators exist on this unit |

## Step 2: where the state comes from (decide after step 1)

Two ways in, chosen from the service manual's "µ-COM data" and "display data" pages:

| Way | When | Cost |
|---|---|---|
| **A. The display bus** | The display has its own driver chip (an FL driver with a serial bus, as on the CD-S300): the Pico listens to 3 or 4 logic lines with the PIO | Like the CD-S300: a sniffer and a parser |
| **B. The display lines** | The microcontroller drives the glass directly (grids and segments, high voltage, multiplexed) | Many lines at up to −30 V: needs level shifting on each. Probably not worth it |
| **C. The microcontroller's lines** | B, or to add to A: the transport (motor, solenoid or mode switch), the reel pulse (counter), cassette in, record tabs, tape type, Dolby | A few logic lines, each with a divider if 5 V |

A is the hope. C alone gives the transport and the cassette, but not the counter as shown or the peak meters.

## Step 3: multimeter

With an illustrated guide page (as for the CD-S300, `cds300-mod/docs/measurement-guide.html`), built once the photos
and the schematic say where. At least:

1. The logic voltage on the lines the Pico would use, and the remote sensor's output at rest.
2. The supply the Pico would take, on and in standby.
3. Which sensor leg is the output (continuity to the microcontroller's remote input).

## Step 4: logic analyzer

If way A: one capture of the display bus while playing, as on the CD-S300 (`cds300-mod/docs/protocol.md`). With 5 V
lines, through dividers.

## Step 5: the program

1. **The bridge base**: done (2026-11-17). Cable-free Wi-Fi setup (`AmpLink-KX393-XXXX`, key `amplink-setup`),
   discovery, updates over Wi-Fi, from the shared base (`device-link`, `firmware-base/`).
2. **`/device`**: done, with no state fields and the five known keys.
3. **The remote keys and `/control`**: done in code, not tested on the deck. NEC 7A/85 (`firmware/ir_codes.py`).
4. **The missing codes**: `POST /ir/send?code=XX` sends any command byte; `tools/ir_sweep.py` walks the likely ones
   and logs what the deck did. Once the IR wire is in.
5. **The state reader**: after steps 2 to 4.

## Power on and off (open)

The deck has a standby, unlike the CD-S300. What the schematic has to answer:

- Is STANDBY/ON a key read by the microcontroller, with a relay for the main supply? Then the microcontroller (and the
  remote sensor) run in standby, and the deck can be switched on by a code, or by pressing the key's line.
- Does the standby supply have room for the Pico (up to about 100 mA at 5 V with Wi-Fi)? If yes, the Pico lives in
  standby and the bridge knows `power` (on or standby). If not, the Pico takes the main 5 V and leaves the network in
  standby, as the CD-S300 does when switched off.
- Does the RKX1 have a power code at all? It has no POWER key in the manual's drawing.

## Ideas

| Idea | What it is | Needs |
|---|---|---|
| Record the CD | The CD-S300 bridge starts the disc, the KX-393 bridge goes from rec-pause to record: CD synchronised recording over Wi-Fi | The central point; the transport known on both |
| Amp follows the deck | Play on the deck switches the amp on and selects TAPE | The central point |
| VU source | The peak meters, read from the display, as the VU source for the SP103 and MR 780 | Way A, if the meters are in the bus |
| Counter to time | The counter counts reel turns; with the tape length it becomes minutes left | The counter |
| Tape library | Name a cassette once (`groove-catalog`), with the counter readings of its songs | The counter |
| Auto stop at the end | Stop and rewind when the tape ends (the deck stops by itself; the bridge only rewinds) | The transport |

## Open questions

- Everything in step 2 and "Power on and off".
- The missing remote codes.
- Whether the RKX1 itself turns up: with it, the codes come from a capture instead of a sweep.

## Wire log

Each wire soldered in the device, where and when. To undo, unsolder in reverse order.

| Date | Wire | Where | Note |
|---|---|---|---|
