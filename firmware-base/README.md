# The bridges' shared base

What every bridge has, whatever the device: cable-free Wi-Fi setup, discovery, updates over Wi-Fi and the HTTP server.
It lives here in one place. Each bridge project gets an **identical copy**, made by `copy_base.py`, and the Pico's
MicroPython runs the copy.

## What's in it

| File | What it does |
|---|---|
| `firmware/wifi.py` | The home network, the `AmpLink-…` setup network and discovery (`docs/contract-v2.md`, Discovery) |
| `firmware/web.py` | The HTTP server: `/state`, `/events` and the routes the bridge registers; `/device` from the bridge's `describe()` (`serve_description`), JSON errors (`not_found`), query decoding (`hex_byte` for `/ir/send?code=`) |
| `firmware/listeners.py` | Who may stay on `/events` |
| `firmware/ota.py` | Updates over Wi-Fi, with automatic rollback, no password |
| `firmware/main.py` | The update gatekeeper. Imports the project's `ponte.py`. Goes to the Pico by USB only |
| `firmware/udp.py` | Reading a UDP socket without waiting |
| `firmware/waits.py` | `until(ready, ms)`: waiting for something (an IR key to go out, a screen) without stopping the bridge |
| `tools/send.py` | Sends the new program to the Pico over Wi-Fi; `--publish` makes the GitHub release the DeviceLink app updates from |
| `tools/test_wifi.py`, `tools/test_listeners.py`, `tools/test_web.py` | The base's tests, on the computer |

## What each device needs

- `firmware/device.py` with `NAME` (e.g. `"mr780"`, the bridge's name in discovery and on the network) and, for
  `--publish`, `FIRMWARE` (`alemser/device-link/<device>`: releases of this repository tagged `<device>-<version>`).
  `tools/send.py` reads both.
- `firmware/ponte.py`: the bridge's program, which `main.py` imports.

## Use

From the repository's root:

```sh
python3 firmware-base/copy_base.py --all           # copies what changed into every device
python3 firmware-base/copy_base.py --all --check   # only checks (before a commit)
```

Then the devices' tests, and one commit with the base and its copies.

**Changing a base file:** change it here, run the tests here (`python3 firmware-base/tools/test_wifi.py`,
`test_listeners.py` and `test_web.py`), and copy it with `--all`. Never change a copy: the next copy overwrites it, and `--check`
reports it.

The program file keeps its Portuguese name, `ponte.py` ("bridge"; the SP103's is `escuta.py`, "listener"): a Pico's
`main.py` imports it and only changes over USB, so renaming it means re-copying `main.py` to every Pico by USB first.

## Who uses it

| Device | Status |
|---|---|
| `devices/mr780` | Uses the base (2026-11-16) |
| `devices/cds300` | Uses the base (2026-11-16) |
| `devices/kx393` | Uses the base (2026-11-17) |
| `devices/sp103` | Uses the base (2026-11-17) except `main.py` (its own imports `escuta.py` and shows errors on the LCD): `copy_base.py` keeps it (`KEEP`) |
