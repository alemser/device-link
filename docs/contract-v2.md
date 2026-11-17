# DeviceLink contract, `api` 2 (draft)

**Draft, 2026-11-16.** Successor of `docs/contract-v1.md` (`api` 1, the amplifier-only contract). Written for three
devices: the Acoustic Solutions SP103 and the Magnat MR 780 (amplifiers) and the Yamaha CD-S300 (CD player). In use
since 2026-11-16 by the CD-S300 (keys, no settings) and since 2026-11-17 by the SP103 (steps, switches, a select and 25
settings); the MR 780 bridge describes itself in `api` 2 too (no state or controls yet, not installed).

A **device** is a piece of equipment with a Pico inside (the **bridge**). The **app** (DeviceLink, today's Amp Link) finds
every device on the home Wi-Fi, shows them in one list, and builds each device's screen from what the device says about
itself: its state, its remote, and the settings a person may change. Adding a device type means writing its bridge; the
app needs no change unless the device brings a new kind of control.

## Goals

1. **Plug in and it shows up.** A device on the Wi-Fi answers discovery; the app lists it within seconds, marked new
   the first time.
2. **Self-describing.** `GET /device` says what the device is, what its state holds, which controls it takes and which
   settings can be changed. The app renders from that, not from a per-model screen.
3. **Light enough for a Pico.** Every answer is small and built once: the description is serialised on the first
   request and served as stored bytes (the CD-S300's is about 1 KB, the SP103's, with its settings, about 4.5 KB), the
   state is under 0.5 KB, and nothing is computed per request that could be cached.
4. **Compatible.** `api` 1 bridges keep working: the app shows them with today's amplifier screens until they move to
   `api` 2.

## Routes

| Route | Group | Notes |
|---|---|---|
| UDP `AMPLINK?` / `DEVICELINK?` on port 47800 | core | Discovery; a bridge answers both |
| `GET /device` | core | The description. Fixed while the bridge runs |
| `GET /state`, `GET /events` | core | The state, once or as Server-Sent Events |
| `POST /control` | `control` | Keys, steps, switches |
| `GET /settings`, `PATCH /settings` | `settings` | The values a person may change |
| `GET /update` and the upload routes | `update` | Firmware over Wi-Fi (`firmware-base/firmware/ota.py`) |
| `GET /wifi` and the setup routes | `wifi_setup` | Unchanged from `api` 1 |

Transport rules are those of `api` 1 (HTTP/1.1, LAN only, `Connection: close` except `/events`, JSON, errors as
`{"error": "..."}` in English ready to show).

## Discovery

The app broadcasts `DEVICELINK?` (a bridge also answers the older `AMPLINK?`) to port 47800 and each bridge replies:

```json
{"name": "CDS300-D85E", "ip": "192.168.178.116", "kind": "cd_player", "label": "Yamaha CD-S300", "model": "cds300", "api": 2}
```

`name` is unique and stable (the chip's id): the app keys devices by it, so a device that changes IP is the same device.
`kind` picks the icon in the list. A reply without `api` is an `api` 1 bridge.

While the device list is on screen (and only then, app in the foreground), the app repeats the broadcast every 5 s, so
a device switched on appears without a refresh, and one switched off is greyed after 3 missed rounds.

## `GET /device`

```json
{"api": 2, "kind": "cd_player", "model": "Yamaha CD-S300", "name": "CDS300-D85E", "bridge_version": "91a64081",
 "firmware": "alemser/cds300-mod", "features": ["control", "update", "wifi_setup"],
 "state": [
   {"id": "transport", "type": "enum", "values": ["playing", "paused", "stopped", "loading", "open"]},
   {"id": "media.track", "type": "int", "label": "Track"},
   {"id": "media.elapsed_s", "type": "duration", "label": "Time"},
   {"id": "disc.tracks", "type": "int", "label": "Tracks"},
   {"id": "disc.total_s", "type": "duration", "label": "Total"},
   {"id": "lcd", "type": "lines", "label": "Display"}],
 "controls": [
   {"group": "transport", "keys": ["previous", "play", "pause", "stop", "next", "eject"]},
   {"group": "modes", "keys": ["repeat", "shuffle", "repeat_a_b", "program", "display", "dimmer"]},
   {"group": "numbers", "keys": ["digit_1", "digit_2", "digit_3", "digit_4", "digit_5", "digit_6", "digit_7",
                                 "digit_8", "digit_9", "digit_0", "enter", "clear"]},
   {"group": "source", "keys": ["cd_usb", "pure_direct", "folder_down", "folder_up"]}],
 "settings": []}
```

| Field | Meaning |
|---|---|
| `api` | Contract version. Changes only when something stops being compatible |
| `kind` | `amplifier`, `cd_player`, `tape_deck`, ... Picks the icon and the default layout |
| `model`, `name` | What to show; `name` as in discovery |
| `bridge_version` | Firmware version (the `version` of `GET /update`) |
| `firmware` | The GitHub repository whose releases carry this bridge's firmware (see [Updates](#updates-from-the-app-update)) |
| `features` | Optional route groups present on this bridge |
| `state` | The state fields worth showing, in display order (below) |
| `controls` | The remote, in groups, in display order (below) |
| `settings` | What a person may change (below); empty or absent when nothing is |

### State fields

`id` is the path in the state JSON (`media.track` is `state["media"]["track"]`). `label` is optional for fields the app
knows by id.

| `type` | Extra | App shows |
|---|---|---|
| `enum` | `values` | The value (the app has words and icons for the common ones: `playing`, `on`, `standby`...) |
| `int`, `number` | `unit`, `min`, `max`, `step` | The number, with the unit |
| `duration` | | Seconds as `m:ss` |
| `bool` | | On / off |
| `text` | | The text |
| `lines` | | Monospaced lines, as on the device's own display |

### Controls

Each group is a row or a pad on the remote screen. A group holds one kind of control:

| Group content | Sent as | Example |
|---|---|---|
| `"keys": [...]` | `POST /control?target=key&name=<key>` | `play`, `power_toggle`, `select_cd` |
| `"steps": [{"target", "state"}]` | `POST /control?target=<t>&dir=up` / `down` | volume, bass, treble, balance |
| `"switches": [{"target", "state"}]` | `POST /control?target=<t>&on=1` / `0` | loudness, speakers |
| `"select": {"state", "options": [{"id", "name", "key"}]}` | the option's `key` | the amplifier's inputs |

`state` ties a step, switch or select to the state field that shows its current value. Keys are named with the
groove-rig vocabulary (`docs/catalog` there): the app has a label and an icon for each common one, and shows any other
key by its name with `_` as spaces, so a new device needs no app change. A key may also be `{"key": "...", "label": "..."}`
when the name is not enough.

Group names the app knows and lays out on purpose: `power`, `transport`, `volume`, `input`, `tone`, `modes`, `numbers`,
`source`. Any other group is shown as a plain row of buttons, in order.

### Settings

What a person may change, for example the SP103's input names and boot text, or the VU source. Each setting:

```json
{"id": "inputs.TUNER", "type": "text", "label": "TUNER", "max": 16, "charset": "lcd", "group": "Input names"}
```

| `type` | Extra |
|---|---|
| `text` | `max` (characters), `charset` (`lcd`: ASCII from space to `}`, no `\`) |
| `bool` | |
| `enum` | `values`, and optionally `labels` (the words to show, in the same order) |
| `int` | `min`, `max`, `step` |
| `ip` | IPv4, or empty |

`GET /settings` answers `{"<id>": value, ...}`. `PATCH /settings` takes only the ids that change and answers the full
object, or `400 {"error": "...", "id": "<id>"}` naming the id that was refused (without `id` when the refusal is about
several together). Unlike `api` 1's `PUT /names`, nothing left out is reset. The app waits
1 s after the last edit before sending (each write goes to flash).

## `GET /state` and `GET /events`

As in `api` 1: the same JSON from both; `/events` sends one `data:` line on connect and one per change, and `: ping`
every second. `null` or missing means unknown. Fields are grouped by meaning, and the description's `state` list points
into them:

```json
{"power": "on", "transport": "playing", "media": {"track": 3, "elapsed_s": 127},
 "disc": {"tracks": 12, "total_s": 3697}, "lcd": ["  3    2:07 "], "version": 41}
```

The amplifiers keep their `api` 1 fields (`volume_db`, `input_id`, `bass_db`, ...), which groove-rig also reads.

## Updates from the app (`update`)

The bridge side exists (`ota.py`): `GET /update` gives the running version and each file's hash; the upload routes
take files, apply them, and roll back by themselves if the new version doesn't confirm within 3 minutes. **No
password** (decided 2026-11-16): the routes are on the home LAN only, like the rest of the contract, and the rollback
protects against a bad version. `main.py` and the bridge's own Wi-Fi file still go only by USB.

The app side is new:

1. A bridge's firmware is a GitHub release of the repository named in `/device` `firmware`, tagged with its version,
   carrying a `firmware.json` asset (`{"version", "files": {"<name>.py": "<sha256>"}}`) and the files themselves
   (built by the repository's `tools/enviar.py --publish`). The app reads the latest release through the GitHub API;
   a device can therefore be updated without the app knowing it in advance.
2. The device screen shows "Update available" when the release's version differs from the bridge's `bridge_version`.
3. On "Update", the app downloads the files, uploads only those whose hash differs from `GET /update` (as `enviar.py`
   does), deletes the ones the release no longer has, applies, and follows `GET /update` until the bridge confirms or
   rolls back, showing which.

## For the app

`api` 1's client rules stand (one `/events` connection per device and only on its open screen, closed in the background,
on-demand routes, no `null` as off). Two changes:

- Discovery repeats every 5 s, but only while the device list is visible.
- With several devices, the app holds at most one `/events` connection: the one of the device on screen. The list shows
  what discovery gives (name, kind, online), not live state.

## Decided (2026-11-16)

- Firmware releases live in each device's own repository, named by `/device` `firmware`.
- Updates take no password.
- The SP103 moves to `api` 2: its `/names` configuration becomes `/settings`.

## Open

- The `kind` values beyond the three devices built so far.
