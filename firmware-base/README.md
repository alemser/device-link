# The bridges' shared base

What every bridge has, whatever the device: cable-free Wi-Fi setup, discovery, updates over Wi-Fi and the HTTP server.
It lives here in one place. Each bridge project gets an **identical copy**, made by `copiar.py`, and the Pico's
MicroPython runs the copy.

## What's in it

| File | What it does |
|---|---|
| `firmware/wifi.py` | The home network, the `AmpLink-…` setup network and discovery (`docs/contract-v2.md`, Discovery) |
| `firmware/web.py` | The HTTP server: `/state`, `/events` and the routes the bridge registers |
| `firmware/listeners.py` | Who may stay on `/events` |
| `firmware/ota.py` | Updates over Wi-Fi, with automatic rollback, no password |
| `firmware/main.py` | The update gatekeeper. Imports the project's `ponte.py`. Goes to the Pico by USB only |
| `firmware/udp.py` | Reading a UDP socket without waiting |
| `tools/enviar.py` | Sends the new program to the Pico over Wi-Fi; `--publish` makes the GitHub release the DeviceLink app updates from |
| `tools/test_wifi.py`, `tools/test_listeners.py` | The base's tests, on the computer |

## What each project needs

- `firmware/device.py` with `NAME` (e.g. `"mr780"`, the bridge's name in discovery and on the network) and, for
  `--publish`, `FIRMWARE` (the GitHub repository whose releases carry the firmware). `tools/enviar.py` reads both.
- `firmware/ponte.py`: the bridge's program, which `main.py` imports.

## Use

From the bridge's project folder:

```sh
python3 ../amp-link/firmware-base/copiar.py           # copies what changed
python3 ../amp-link/firmware-base/copiar.py --check   # only checks
```

Then the project's tests, and a commit of the copies in its repository.

**Changing a base file:** change it here, run the tests here (`python3 firmware-base/tools/test_wifi.py` and
`test_listeners.py`), and copy it into each project. Never change a copy: the next copy overwrites it, and `--check`
reports it.

The tools keep their Portuguese file names (`copiar.py`, `enviar.py`, the projects' `ponte.py`) because projects and
the Picos refer to them; a bridge's `main.py` imports `ponte` and only changes over USB.

## Who uses it

| Project | Status |
|---|---|
| `mr780-mod` | Uses the base (2026-11-16) |
| `cds300-mod` | Uses the base (2026-11-16), on contract `api` 2 |
| `sp103-mod` | Uses the base (2026-11-17) except `main.py` (its own imports `escuta.py` and shows errors on the LCD): copy with `copiar.py --skip firmware/main.py`. On contract `api` 2 |
