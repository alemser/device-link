# MR 780: the display and what is known about the amp (2026-11-07)

Summary: the web does not say what the MR 780's display is (there is no public service manual). **The photos of the
open amp answered it:** it is a **dot-matrix VFD, 2 lines × 16 characters**, with no chip at all on the display board.

## What the photos show (2026-11-07)

Photos in `docs/img/`.

### The display (`placa-display-frente-vfd.jpg`)

- A VFD (vacuum fluorescent display) glass tube with **2 lines of 16 characters**. Each character is a dot matrix
  (5×7 or similar), not segments. No fixed icons appear.
- The glass is soldered straight to the display board, by a row of pins along its bottom edge.
- **There is no chip on the display board**, neither on the front nor on the back (`placa-display-tras-1.jpg`): only
  transistors, diodes, capacitors and a regulator (Q1). That is the VFD's power supply (filament and the grids' high
  voltage).
- A 2×16 dot-matrix VFD with no external chip would need more than 100 wires to drive. Since the glass has far fewer
  pins, **the controller is inside the glass itself** ("chip-in-glass", CIG). These VFDs receive **commands and
  character codes over a 3- or 4-wire serial line** (clock, data, select and sometimes reset). Examples of the kind:
  the Futaba "BT" series with an internal driver, or similar Chinese modules.
- Consequence: it is probably a **character display**, like the SP103's, only serial. The amp sends letters, not dots.
  Many of these controllers also accept **custom characters** (CGRAM), which would allow the VU meter.
- Board: `MR780-DISPLAY-D.DDB`, P/N `0021-0101-0002`, dated 2020-09-24.

### The display's connection to the main board

- A **flat cable (FFC)** runs from the display board to the main board (connector CN8, near the microcontroller).
  **21 lines, 1.0 mm pitch** (measured on 2026-10-30). The VFD wires go through it and, probably, the buttons and the
  remote receiver.
- A pair of yellow wires leaves the transformer and goes to the display board: it should be the power for the filament
  or for the VFD's supply (low-voltage AC). Do not touch.

### The main board (`placa-principal-1.jpg`, `placa-principal-2.jpg`)

- Board `MR780_Main_PCB`, P/N `0021-0100-2000`, dated 2021-12-21.
- **Main microcontroller (U17)**: a square 64-pin chip (LQFP-64) near the flat cable, with a 25 MHz crystal beside
  it. The marking cannot be read in the photos: needs a close-up photo.
- A SOIC-16 chip (U15) between the microcontroller and the flat cable: it may be a level shifter (3.3 V ↔ 5 V) for
  the display. Needs a close-up photo.
- **Wolfson WM8740 DAC** (confirms the forum rumour).
- **XMOS** (the computer USB input).
- **Green Frontier Silicon DAB/FM module** (the chip looks like a Kino4), with the antenna on the thin coaxial cable.
- **Blue Bluetooth module** (X-FTB01, with aptX).
- One connector with the wires `D+5V`, `APD`, `SYS`, and another with `POW/OF` and `DGND` going to the power supply:
  that is how the microcontroller switches the amp on and off. `D+5V` may be the 5 V that stays on in standby:
  **measure**.

### Power supply and other boards

- Switch-mode supply `MR780-SMPS-D` (2018-03-10), with a relay: it is the one that stays on in standby and switches the
  rest on.
- Valve preamp `TUBE PAMP PCB` (the two ECC81 under the plate).
- Toroidal transformer `Magnat MT 900`.
- Small boards in the panel for the knobs (SOURCE, BALANCE, BASS, MID, TREBLE).

## The display, from the user manual

Source: the official manual (`docs/manual/MR-780_Manual_022025.pdf`, local copy; text in `.txt` beside it).

- "Large two-line display", according to Magnat.
- **DIM** button: 3 brightness levels.
- What appears on the display (panel item 17):
  - the valve warm-up, for ~30 s after power-on (a countdown, according to a hifi-forum.de user);
  - the selected input;
  - the volume;
  - station and reception on FM and DAB (the remote's INFO button).
- Texts quoted in the manual, exactly as they appear: `DIRECT ON`, `STORED PRESET`, `APO MODE OFF`, `APO MODE ON`,
  `BT` (blinks while pairing, steady when connected), `N/A`.
- On FM, INFO shows in sequence: PS (station name), RT (text), PTY (type), time/date.
- On DAB, INFO shows: station name, DLS (text, often artist and song), programme type, multiplex and frequency,
  time/date, bit rate, multiplex name.
- On USB/Bluetooth: the device identification, the data rate and the ID3 tags (title, artist, album).
- On the digital inputs, it shows the sample rate for ~5 s.

## Front panel

1 status LED (green on, red standby) · 2 ON/STBY · 3 headphones (mutes the speakers) · 4/5 ◄◄ ►► · 6 MONO ·
7 SOURCE · 8 LINE IN · 9 BALANCE · 10/11/12 BASS/MID/TREBLE · 13 DIRECT · 14 remote sensor · 15 VOLUME · 16 DIM ·
17 display.

An important difference from the SP103: **BASS, MID, TREBLE and BALANCE are knobs**, not menu settings. So the Pico
will not be able to change the bass over Wi-Fi as it does on the SP103 (only if they are read by a microcontroller, to
be seen).

## Rear panel

Analogue inputs: PHONO (MM or high-output MC), CD, DVD, TAPE, AUX 1/2, and REC OUT. Digital: 2 optical, 2 coaxial,
USB type B (sound card for the computer). DAB/FM antenna. An **UPDATE** input (USB) and a **NORMAL/SERVICE** switch
(for firmware updates only).

## Remote

Amp buttons: AMP (on/standby), SOURCE, TUNING ▲▼, AUTO (DAB scan), INFO, VOLUME ▲▼, MUTE, numbers 0–9 and +10
(presets), ◄◄ ►► and PLAY/PAUSE (USB/Bluetooth), Disconnect (Bluetooth). The other buttons are for the Magnat MCD 750
CD player. The protocol (NEC or other) is not given anywhere: we will capture it.

## Firmware

According to the audio.com.pl forum (2020): the file `MR-780.bin` goes in the root of a FAT32 USB stick; rear switch
to SERVICE; switch off, put the stick in the UPDATE input, switch on; the amp updates and goes to standby; switch back
to NORMAL. DIM + DIRECT for 3 s shows the version (the same post warns this may erase the presets).

This indicates there is a main microcontroller with its own firmware. We will not touch Magnat's firmware.

## Other things said in forums (unconfirmed)

- Preamp with two ECC81/12AT7 valves (new units with JJ); transistor power stage.
- Wolfson DAC (the photos confirm it: WM8740).
- The tuner would be Grundig's (rumour).
- On power-up: 30 s of warm-up on the display, then a relay switches the rest on.
- The volume used to "jump" before a firmware update: this indicates the volume knob is read by the microcontroller
  (an encoder or a potentiometer read by an ADC), and not a potentiometer directly in the signal. Good for us: it can
  be controlled.

## The three possible cases (before the photos)

This table was written before the photos. The photos point to the **second case** (a character VFD with its own
controller), only with the controller inside the glass instead of on a separate board:

| Type | How to recognise it in the photo | How the controller talks to it | For us |
|---|---|---|---|
| Parallel character module (HD44780 or compatible) | 14- to 16-pin connector, as on the SP103 | 8 or 4 data wires + RS, E | Same as the SP103. Reuses almost everything |
| Character VFD module (Noritake, Futaba) | A board with a glass tube and its own chip; connector with few wires | Serial (SPI or UART) or parallel | Medium: another protocol, same idea |
| "Bare" VFD with a driver chip on the amp's board (PT6311, PT6312, HT16515 and similar) | Glass tube soldered to the front board, a 44- to 52-pin chip nearby | 3-wire serial (DIN, CLK, STB), sending segments, not letters | Larger: the display may have icons and fixed segments, and what can be drawn depends on the glass's grid |

## Sources

- [Official MR 780 manual (PDF)](https://magnat.com/wp-content/uploads/2025/09/MR-780_Manual_022025.pdf)
- [The MR 780 page at Magnat](https://www.magnat.de/en/electronics/mr-780/)
- [son-video.com, MR 780 description](https://www.son-video.com/article/amplis-connectes/magnat/mr-780)
- [audio.com.pl forum, MR 780 thread, page 61 (firmware update)](https://forum.audio.com.pl/topic/61267-magnat-mr780/page/61/)
- [hifi-forum.de, MR 780 thread](http://www.hifi-forum.de/viewthread-111-5374.html)
- [RepData, MR 780 with noise on the right channel](https://www.repdata.de/wbb2/forum/index.php?thread%2F83330-nagelneuer-hifi-r%C3%B6hren-receiver-magnat-mr-780-kratzt-und-bummst-im-rechten-lauts%2F=)
