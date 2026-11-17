# MR 780 mod

The same improvements as on the SP103 (repository `sp103-mod`), now on the **Magnat MR 780** hybrid receiver: a
Raspberry Pi Pico 2 W inside the amp that reads what the amp shows on its display, publishes the state on the network
and controls the amp over Wi-Fi.

The name is no longer "display proxy" because the project does much more than swap texts on the display: state,
commands, VU meter and information screens.

## Status (2026-11-16)

Still in **phase 1: read the state only** (what goes to the display, on or standby), without cutting anything. The
display is a **dot-matrix VFD, 2 lines × 16 characters**, with its controller inside the glass, connected to the main
board by a 21-way flat cable with 1.0 mm pitch (`docs/research.md`). On 2026-11-07, with the multimeter and the amp
unplugged, the GND lines, all the buttons, VOLUME, SOURCE and the remote's signal were mapped on the flat
(`docs/measurements.md`). Next step: the voltages with the amp powered, then the logic analyzer (`docs/plan.md`).

The firmware started on 2026-11-09, without the amp: the **bridge base** (`firmware/ponte.py`), which sets up Wi-Fi
without a cable through the `AmpLink-MR780-XXXX` network, is found by the DeviceLink app with no IP typed in, and
updates itself over Wi-Fi. It already runs on the shared base from the `amp-link` repository (see "Folders"); updates
over Wi-Fi take no password (a contract v2 decision; `firmware/secrets.example.py` explains). The bridge is on the
DeviceLink contract `api` 2 since 2026-11-17 (`firmware/device.py`), with no state, controls or settings yet, and
`/state` still comes back all `null`: reading the display and
controlling the amp depend on the captures (the plan's open steps 2 to 4). Even so, the Pico can already go inside the
amp and get the rest over Wi-Fi.

## What comes from the SP103

| On the SP103 | On the MR 780 | Notes |
|---|---|---|
| Custom names for the inputs ("TUNER" becomes "Rega Planar 2") | Yes | The MR 780 has 15 sources: PHONO, CD, DVD, AUX 1/2, TAPE, LINE IN, FM, DAB, OPT 1/2, COAX 1/2, USB, BT |
| Amp state on the network (`/state`, `/device`) | Yes | The same contract as the app (repository `amp-link`) |
| Control over Wi-Fi: remote codes straight into the IR line | Yes | By wire, no Broadlink. Plus the panel buttons (DIRECT, DIM), which the remote does not have |
| Power the amp on from standby | Yes | On the MR 780 the amp warms up the valves for ~30 s at power-on |
| VU meter on the display while playing | Likely | 2×16 as on the SP103; depends on the VFD controller accepting custom characters |
| Information screens (needle, Bluetooth quality) | Yes | Same screen size as the SP103 |
| Bass and treble over Wi-Fi | Hard | Knobs, probably analogue. DIRECT (tone on and off) is feasible |
| Powered by the amp itself, also in standby | To be measured | The Pico from `D5V` |
| Raspberry Pi Zero 2 W inside the amp | No | Dropped on 2026-11-08: no new power supply inside the amp and no risk of interference with the electronics |

All of this is detailed in `docs/plan.md`.

## Documents

| Document | Contents |
|---|---|
| [`docs/plan.md`](docs/plan.md) | The plan, step by step, and the questions the first measurements need to answer |
| [`docs/research.md`](docs/research.md) | What is known about the MR 780 from the web, the manual and the photos: display, boards, buttons, remote |
| [`docs/measurements.md`](docs/measurements.md) | All the multimeter readings, with the table of the flat cable's 21 lines |
| [`docs/history/brief-2026-10.md`](docs/history/brief-2026-10.md) | The brief of 2026-10-28 to 30: first photos, flat cable measurements and the phase decisions. It does not describe the current state |

The official manual stays in the local copy only, in `docs/manual/` (copyrighted, not on GitHub).

## Folders

- `firmware/`: the Pico's program (MicroPython).
  - This project's: `ponte.py` (the program) and `device.py` (`/device`).
  - **Copies of the shared base** (repository `amp-link`, folder `firmware-base/`): `wifi.py`, `web.py`, `ota.py`,
    `udp.py`, `listeners.py` and `main.py`. Change them there and copy with
    `python3 ../amp-link/firmware-base/copiar.py`, never here.
  - `main.py` (the update gatekeeper) only goes to the Pico by USB; everything else goes over Wi-Fi.
- `tools/`: the tests on the computer and `enviar.py` (update over Wi-Fi). `enviar.py`, `test_wifi.py` and
  `test_listeners.py` come from the base; `test_device.py` is this project's.
- `captures/`: logic-analyzer captures.
- `docs/img/`: photos of the boards.

## Test on the computer

```sh
for t in wifi listeners device; do python3 tools/test_$t.py; done
python3 ../amp-link/firmware-base/copiar.py --check    # are the base copies up to date?
```

## Install on the Pico (by USB, once)

```sh
mpremote fs cp firmware/*.py : + reset
```

With no saved network, the Pico opens the `AmpLink-MR780-XXXX` network (key `amplink-setup`): in the DeviceLink app,
"Set up a new device's Wi-Fi". From then on, updates go over Wi-Fi: `python3 tools/enviar.py`.
