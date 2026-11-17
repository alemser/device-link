# CD-S300 (devices/cds300)

The third modified device, after the SP103 (`devices/sp103`) and the MR 780 (`devices/mr780`): the **Yamaha CD-S300**
CD player. A Raspberry Pi Pico 2 W inside it reads what its display shows, publishes the state on the network, and
controls it over Wi-Fi by sending the remote's codes down a wire.

It is the first device that is not an amplifier, so it is also the first on the **DeviceLink contract** (`api` 2,
`device-link/docs/contract-v2.md`): it is found on the network, describes itself, and the DeviceLink app builds its screen
from that description.

## Status (2026-11-16)

**Working on the device**, case closed, on the home Wi-Fi:

| Requirement | Status |
|---|---|
| Know the exact state | The display reader (`firmware/display.py`, `vfd.py`) publishes `transport` (playing, paused, stopped, loading, open), the track and elapsed time, and the disc's track count and total time |
| Remote control over Wi-Fi | `POST /control?target=key&name=play` (30 keys), sent as NEC IR down a wire to the receiver's output |
| Easy to undo | Six wires soldered on top of existing joints; nothing removed |
| DeviceLink | Discovered by the app, screen built from `/device`, firmware updates from the GitHub release |

What is still open is in `docs/plan.md` ("Open questions") and `docs/protocol.md` (icons still to map: repeat, random,
A-B, program, USB mode, Pure Direct, dimmer).

## How it works

- **The display:** a VFD with its controller inside the glass, driven by 4 lines (`FL_/CS`, `FL_CLK`, `FL_DATA`,
  `FL_/RST`) at 3.3 V on the 15-way flat cable between the main board (`CB304`) and the front board (`CB701`). The
  microcontroller sends the 12 characters as ASCII and draws the icons as two custom characters (`docs/protocol.md`).
  The Pico listens with the PIO, never driving the lines.
- **The remote:** NEC, address 79/86, every key in the service manual (`docs/research.md`). The Pico pulls the
  receiver's output (`U701`, leg C) low, as the SP103 does.
- **Power:** the Pico runs from `D+5` (pin 5 of `CB301`), so it is on whenever the CD player is. The player has no
  standby: its front button switches the 230 V (`docs/plan.md`, "Power on and off").

## Documents

| Document | Contents |
|---|---|
| [`docs/plan.md`](docs/plan.md) | The plan, the wiring, the decisions, the ideas and the common protocol |
| [`docs/research.md`](docs/research.md) | What the service manual and the photos say: display, connectors, power supply, microcontroller, remote codes |
| [`docs/measurements.md`](docs/measurements.md) | The bench measurements and the log of what was done |
| [`docs/protocol.md`](docs/protocol.md) | The display bus as captured with the logic analyzer, and the icon map |
| [`docs/measurement-guide.html`](docs/measurement-guide.html) | The illustrated bench guide (published as an artifact), with photos in `docs/guide/` |

The service manual stays in the local copy only, in `docs/manual/` (copyrighted, not on GitHub).

## Photos (`docs/images/`, 2026-11-16)

| Photo | Shows |
|---|---|
| `20261116_082804.jpg` | The front board from behind, with the flat cable's silkscreen next to `CB701`, and part of the power supply |
| `20261116_082821.jpg` | Corner of the power supply, with `CB807` (4 wires to the front board: VFD filament and −27 V) |
| `20261116_082833.jpg` | The power supply: rectifiers, capacitors and the transformer connector |
| `20261116_082851.jpg` | Rear: analogue, coaxial and optical outputs |
| `20261116_082858.jpg` | Rear: label (230 V, 50 Hz, 13 W) and the 2-pin power inlet |
| `20261116_082908.jpg` | Front, left: power button, USB, CD/USB, PURE DIRECT |
| `20261116_082914.jpg` | Front, centre: tray and display |
| `20261116_082918.jpg` | Front, right: the transport keys |
| `20261116_083847.jpg` | `CB304` on the main board, close up: one window per line, contact visible |
| `20261116_083859.jpg` | `CB304` from the other side, with the flat's blue stiffener and the connector's joints |
| `20261116_084546.jpg` | The 15 joints of `CB701` behind the front board, and the display's series resistors |
| `20261116_084556.jpg` | The silkscreen naming the 15 lines on the front board, and `W702` (filament and −27 V) |
| `20261116_084609.jpg` | Behind the front board, around `IC702`, with the insulating plastic sheet |
| `20261116_084629.jpg` | Main board: `IC2` (LC786922) and the optical pickup connector |
| `20261116_084644.jpg` | Main board: power connector `CB301` with its names, `IC7`, `IC303`, and `CB304` with the line names |
| `20261116_084657.jpg` | The analogue output board (the two NJM2068) |
| `20261116_111148.jpg` | The display lit, without the front panel: the 12 characters, the icons and the glass's pins |
| `20261116_111152.jpg` | The USB and PURE DIRECT boards, with their LEDs and keys |
| `20261116_111202.jpg` | Overview without the front panel (chassis stamped 18 AUG 2017) |
| `20261116_111455.jpg` | Behind the PURE DIRECT board: `W701A`, `W703`, `D702` |
| `20261116_111459.jpg` | Behind the display: the traces from the glass |
| `20261116_111503.jpg` | Behind the IR receiver: the 3 legs of `U701` and the `IC702` gate |
| `20261116_111509.jpg` | Behind `CB701`: the display resistors `R701` to `R704` |
| `20261116_111519.jpg` | Behind `CB701` with the labels, `W702` (high voltage) next to it, and `CB301` on the main board |

## Folders

- `firmware/`: the Pico's program (MicroPython).
  - This project's: `ponte.py` (the program), `device.py` (`/device`), `display.py` (the PIO sniffer), `vfd.py`
    (the display parser and the player state), `ir_codes.py` (the remote codes), `ir.py` (the IR line) and
    `control.py` (the `/control` and `/ir` routes).
  - **Copies of the shared base** (`firmware-base/` at the repository's root): `wifi.py`, `web.py`, `ota.py`,
    `udp.py`, `listeners.py` and `main.py`. Change them there and copy with
    `python3 firmware-base/copy_base.py --all` from the repository's root, never here.
  - `main.py` (the update gatekeeper) only goes to the Pico by USB; everything else goes over Wi-Fi.
- `tools/`: the tests on the computer, `send.py` (update over Wi-Fi; `--publish` makes the GitHub release the app
  updates from) and `fl_decode.py` (reads logic-analyzer captures). `send.py`, `test_wifi.py` and
  `test_listeners.py` come from the base.
- `captures/`: logic-analyzer captures.

## Test on the computer

```sh
for t in wifi listeners device ir control vfd fl_decode; do python3 tools/test_$t.py; done
python3 ../../firmware-base/copy_base.py --check    # are the base copies up to date?
```

`test_ir.py` compares the codes with the `groove-rig` model (`~/Projects/groove-rig`).

## Install on the Pico (by USB, once)

```sh
mpremote fs cp firmware/*.py : + reset
```

With no saved network, the Pico opens the `AmpLink-CDS300-XXXX` network (key `amplink-setup`): in the DeviceLink app,
"Set up a new device's Wi-Fi". From then on, updates go over Wi-Fi: `python3 tools/send.py`, or from the app once a
release is published (`python3 tools/send.py --publish`).
