# KX-393 mod

The fourth modified device, after the SP103 (`sp103-mod`), the MR 780 (`mr780-mod`) and the CD-S300 (`cds300-mod`):
the **Yamaha KX-393** cassette deck. A Raspberry Pi Pico 2 W inside it will publish the deck's state on the network
and control it over Wi-Fi by sending the remote's codes down a wire.

It joins the **DeviceLink contract** (`api` 2, `device-link/docs/contract-v2.md`) as a `tape_deck`: found on the
network, it describes itself, and the DeviceLink app builds its screen from that description.

## Status (2026-11-17)

**Started away from the deck**: both manuals read, no photos or measurements yet.

| Requirement | Status |
|---|---|
| Know the state | Planned: from the microcontroller's 5 V mode pins and the port expander's bus; the display is driven directly, with no bus (`docs/plan.md`) |
| Remote control over Wi-Fi | In code, not tested: `POST /control?target=key&name=play`, the 11 keys of the service manual's table. The address (7F or 7A) is settled on the deck with `tools/ir_try.py` |
| Power over Wi-Fi | In code, not tested: `power_toggle` pulls the `KEY1` line low, which is what STANDBY/ON does |
| Easy to undo | Planned: wires on existing joints, nothing removed |
| DeviceLink | `/device`, discovery, Wi-Fi setup and updates from the shared base |

Next: the photos (`docs/plan.md`, step 1), then the multimeter guide.

## Documents

| Document | Contents |
|---|---|
| [`docs/plan.md`](docs/plan.md) | The plan, the safety rules, the open decisions and the ideas |
| [`docs/research.md`](docs/research.md) | What the owner's manual and the service manual say: the microcontroller's pins, the display map, the flat, the power supply, the remote codes |
| [`docs/measurements.md`](docs/measurements.md) | The bench measurements and the log of what was done |

The manuals stay in the local copy only, in `docs/manual/` (copyrighted, not on GitHub). The service manual is
`Yamaha-KX493-tape-sm.pdf` from audiocircuit.dk (covers both models).

## Folders

- `firmware/`: the Pico's program (MicroPython).
  - This project's: `ponte.py` (the program), `device.py` (`/device`), `ir_codes.py` (the remote codes), `ir.py`
    (the IR line), `panel.py` (STANDBY/ON on the `KEY1` line) and `control.py` (the `/control` and `/ir` routes).
  - **Copies of the shared base** (repository `device-link`, folder `firmware-base/`): `wifi.py`, `web.py`, `ota.py`,
    `udp.py`, `listeners.py` and `main.py`. Change them there and copy with
    `python3 ../device-link/firmware-base/copiar.py`, never here.
  - `main.py` (the update gatekeeper) only goes to the Pico by USB; everything else goes over Wi-Fi.
- `tools/`: the tests on the computer, `enviar.py` (update over Wi-Fi; `--publish` makes the GitHub release the app
  updates from) and `ir_try.py` (settles the remote's address on the deck). `enviar.py`, `test_wifi.py` and
  `test_listeners.py` come from the base.
- `captures/`: logic-analyzer captures, when there are any.

## Test on the computer

```sh
for t in wifi listeners device ir control; do python3 tools/test_$t.py; done
python3 ../device-link/firmware-base/copiar.py --check    # are the base copies up to date?
```

`test_ir.py` compares the codes with the `groove-rig` model (`~/Projects/groove-rig`).

## Install on the Pico (by USB, once)

```sh
mpremote fs cp firmware/*.py : + reset
```

With no saved network, the Pico opens the `AmpLink-KX393-XXXX` network (key `amplink-setup`): in the DeviceLink app,
"Set up a new device's Wi-Fi". From then on, updates go over Wi-Fi: `python3 tools/enviar.py`, or from the app once a
release is published (`python3 tools/enviar.py --publish`).
