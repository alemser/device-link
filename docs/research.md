# KX-393: what is known before opening it (2026-11-17)

Written away from the deck: no photos, no measurements and no service manual yet. Sources:

- Yamaha's **owner's manual** for the KX-493/KX-393 (11 pages, English and French, printed in Malaysia, `VZ 77980`),
  from Yamaha's own site. Page numbers below are the manual's.
- The first two pages of the **service manual** (KX-393/493, printed in Japan, January 1998), seen as a preview: the
  cover with the contents, and the front panels. The full manual is still to be downloaded (`docs/plan.md`, step 1).
- **Remote Central**'s Pronto codes for the KX-W421, and `groove-rig`'s model built from them
  (`internal/catalog/models/yamaha_kx393.yaml`).

## Summary

- A single-well, 2-head stereo cassette deck from 1998, with Dolby B/C, HX Pro, auto tape tuning and a fluorescent
  display (tape counter, peak meters, indicators).
- **It has a standby.** STANDBY/ON is a key, not a mains switch, and the deck draws 5 W in standby (page 5 and
  specifications). So something stays powered while the deck is "off": maybe a place for the Pico, and maybe a way
  to switch the deck on over Wi-Fi. The schematic will tell.
- **It has a remote sensor**, for the optional RKX1 remote: the same way in as on the CD-S300, a wire on the sensor's
  output.
- Only five remote codes are published (play, rewind, fast forward, stop, record). The others are to be found by
  sending candidate codes (`tools/ir_sweep.py`).
- How the display is driven (by the microcontroller directly, or through a driver chip with a serial bus as on the
  CD-S300) decides how the state is read. Not known until the service manual.

## The service manual (contents, from the preview)

| Section | Pages |
|---|---|
| To service personnel, front panels | 1 |
| Rear panel | 2 |
| Specifications | 3 |
| Internal view | 4 |
| Disassembly procedures | 5 to 7 |
| Adjustments | 8 to 11 |
| **µ-COM data** (the microcontroller's pins) | 12 to 14 |
| **Display data** (the display's grids and segments) | 15 |
| KX-393 block diagram | 16 |
| KX-393 printed circuit boards | 18 to 21 |
| **KX-393 schematic** | 26 |
| Parts list | 28 to 45 |

The pages in bold answer the open questions. 35 pages in all. Third-party sites have it (Elektrotanya,
audioservicemanuals, ManualMachine); Elektrotanya's download sits behind a browser check, so it is downloaded by hand.

## The front panel (owner's manual, pages 1 and 5 to 12)

**Keys:** STANDBY/ON, EJECT, INTRO SCAN (◄◄ and ►►), COUNTER RESET, MEMORY, AUTO TAPE TUNING, DOLBY NR
(OFF / B / C / MPX), and the transport: ◄◄, ►►, ► (play), ■ (stop), REC/PAUSE, MUTE/SEARCH.

**Knobs:** PHONES LEVEL, BIAS ADJUST, PLAY TRIM, BALANCE, REC LEVEL. Analogue, out of reach of the Pico.

**What the KX-393 lacks** (KX-493 only): repeat (0-M and full), the timer switch, the sub panel, the reel motor.

### What the display shows

From the manual's figures and text; the exact glass, with its grids and segments, is on the service manual's page 15.

| Indicator | Shows | Owner's manual |
|---|---|---|
| Tape counter | 4 digits, `0000` after COUNTER RESET; counts reel turns, not time | page 9 |
| PEAK level meters | Left and right, from −30 to +8 dB (−30, −20, −17, −14, −12, −10, −8, −6, −4, −2, 0, +2, +4, +6, +8); the Dolby mark at −2 dB | page 11 |
| Tape type | Lights when a cassette is in: normal, CrO2 (high) or metal, from the cassette's detection slots | pages 5 and 14 |
| Dolby B, Dolby C | The NR setting | page 5 |
| MPX FILTER | The 19 kHz filter, for recording from FM | page 9 |
| REC | Recording or rec-pause | page 9 |
| SYNCHRO | CD synchronised recording | page 9 |
| TAPE TUNING | Auto tape tuning done | page 10 |
| MEMORY | Memory stop set | page 8 |
| INTRO ◄◄ / ►► | Intro scan, either direction | page 7 |

The transport (playing, winding, stopped) is likely shown too (arrows), but the manual doesn't say.

### Functions worth knowing for the bridge

- **Selection search:** ◄◄ or ►► together with MUTE/SEARCH skips to the previous or next song (blanks of at least 4
  s). That is `previous` and `next` in the contract.
- **Intro scan:** plays the first seconds of each song, either direction.
- **Memory stop:** winding stops at the memorised counter reading.
- **0-stop and rec return:** during recording, RESET rewinds to `0000`, ◄◄ rewinds to where the recording began.
- **Rec mute:** records 4 s of silence and pauses.
- **Auto tape tuning:** about 20 s of recording and playback in rec-pause, to set the bias and sensitivity.
- **CD synchronised recording:** with a Yamaha CD player whose remote has a SYNCHRO key, the CD starts and the deck
  records. The CD-S300's remote has no SYNCHRO key, but the bridges could do the same over Wi-Fi.

## Power (owner's manual, specifications)

- 230 V, 50 Hz (Europe and UK model). 12 W on, **5 W in standby**.
- "This unit is not disconnected from the AC power source as long as it is connected to the wall outlet, even if the
  unit itself is turned off. This state is called the standby mode." (page 2)
- Still to learn from the schematic: whether STANDBY/ON is a key read by the microcontroller (which then switches a
  relay) or a latching switch; which supply lives in standby and how much it can give (a Pico 2 W with Wi-Fi takes
  up to about 100 mA at 5 V); whether the microcontroller runs in standby.

## The remote

### The RKX1

The KX-393 was sold without a remote. The optional one is the **RKX1**, made for several decks (single and double).
Its keys, from the drawing on page 15: INTRO SCAN, DECK A/B, DIR A, DIR B, DUBBING, COUNTER RESET, SEARCH, REC/PAUSE,
REC MUTE, PLAY, STOP, and the winding keys. The double-deck keys (DECK A/B, DIR A/B, DUBBING) do nothing on the KX-393.
Range 7 m, 30°.

### The codes

No table exists for the KX-393. Remote Central has Pronto codes for the KX-W421 (a double deck that uses the RKX1), and
decoded they are **NEC, address 7A/85**. IRDB's Yamaha "Tape Deck" device 122 (`0x7A`) agrees on play, rewind, fast
forward, stop and record.

| Key | Command | Contract name | On the KX-393 |
|---|---|---|---|
| Play | `00` | `play` | Expected |
| Rew | `01` | `rewind` | Expected |
| Ffwd | `02` | `fast_forward` | Expected |
| Stop | `03` | `stop` | Expected |
| Record | `04` | `record` | Expected (REC/PAUSE) |
| Deck A/B | `06` | — | Double decks only |
| Dir A | `07` | — | Auto-reverse decks only |
| Dir B | `40` | — | Auto-reverse decks only |

Decoded with a script on 2026-11-17; each code's command and its inverse check out. None tested on the deck yet.

**Missing:** pause, rec mute, search (previous, next), intro scan, counter reset and power. The gap at `05` is a good
guess for one of them. They are found by sending candidates over the IR wire and watching the deck
(`tools/ir_sweep.py`, `POST /ir/send?code=XX`), with an unrecordable cassette.

`groove-rig` carries the five known codes (`yamaha_kx393.yaml`, "not yet field-tested"); `tools/test_ir.py` checks
the bridge's against them. Codes found here go there too.
