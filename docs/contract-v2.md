# DeviceLink contract, `api` 2

**2026-11-17.** The one contract between the bridges and the DeviceLink app. It replaced `api` 1 (the amplifier-only
contract, removed on 2026-11-17; it is in the git history). Spoken by the Yamaha CD-S300 (keys, since 2026-11-16), the
Acoustic Solutions SP103 (steps, switches and a select, since 2026-11-17), the Magnat MR 780 (keys, a volume step, a select,
power with its warm-up and the display's lines, installed 2026-11-18) and the Yamaha KX-393 (keys, no state yet, installed 2026-11-18).

A **device** is a piece of equipment with a Pico inside (the **bridge**). The **app** (DeviceLink) finds every device on
the home Wi-Fi, shows them in one list, and builds each device's screen from what the device says about itself: **what
it is, its state and its remote (IR)**. Nothing more: the contract is the same lean one for every device, the one the
CD-S300 set. Adding a device type means writing its bridge; the app needs no change unless the device brings a new
kind of control.

What is particular to one device (the SP103's display texts, VU meter and info screens) stays out of the contract. Such
a bridge serves [its own page](#a-devices-own-page) for it; the app neither shows nor links it.

## Goals

1. **Plug in and it shows up.** A device on the Wi-Fi answers discovery; the app lists it within seconds, marked new
   the first time.
2. **Self-describing.** `GET /device` says what the device is, what its state holds and which controls it takes. The
   app renders from that, not from a per-model screen.
3. **The same lean interface everywhere.** Device information, state and remote; no per-device configuration.
4. **Light enough for a Pico.** Every answer is small and built once: the description is serialised on the first
   request and served as stored bytes (the CD-S300's is about 1 KB, the SP103's about 1.7 KB), the state is under
   0.5 KB, and nothing is computed per request that could be cached.

## Routes

| Route | Group | Notes |
|---|---|---|
| UDP `DEVICELINK?` on port 47800 | core | [Discovery](#discovery) |
| `GET /device` | core | The description. Changes only when the bridge restarts or when the device's own page renames something it shows (the SP103's input names in its input chips); the app reads it on opening the device |
| `GET /state`, `GET /events` | core | The state, once or as Server-Sent Events |
| `POST /control` | `control` | Keys, steps, switches |
| `GET /update` and the upload routes | `update` | Firmware over Wi-Fi (`firmware-base/firmware/ota.py`) |
| `GET /wifi` and the setup routes | `wifi_setup` | [Wi-Fi setup](#wi-fi-setup-wifi_setup) |

A bridge may have routes of its own, outside the contract: for diagnosis with curl (the SP103's `/status`, `/bus`,
`/ir`) and for [its own page](#a-devices-own-page) (the SP103's `/settings`). The app doesn't use them.

## Transport

- HTTP/1.1 without TLS, on the local network only, no authentication. Don't count on `.local` names: the app finds a
  bridge by discovery and keeps its IP.
- The contract is an API only. A bridge's pages are its own: the Wi-Fi setup page (at `/`, only with the setup network
  open) and, where a device has extras, [its own page](#a-devices-own-page).
- Every answer closes the connection (`Connection: close`), except `/events`.
- JSON answers, with `Cache-Control: no-store` and `Access-Control-Allow-Origin: *`.
- Errors: `400` (or `403`, `404`) with `{"error": "text"}`, in English, ready to show as they are (`web.not_found`
  for a 404). A request the bridge can't read (a bad request line or `Content-Length`) gets `400` too.
- Query values are percent-encoded (`URLEncoder`); the bridge decodes them. Ids and key names are `snake_case`, so
  they never need it in practice.

## Discovery

The app broadcasts `DEVICELINK?` to port 47800, three times over about 2 s (the first packet is sometimes lost), and
each bridge answers the sender:

```json
{"name": "CDS300-D85E", "ip": "192.168.178.116", "kind": "cd_player", "label": "Yamaha CD-S300", "model": "cds300", "api": 2}
```

`name` is unique and stable (the chip's id): the app keys devices by it, so a device that changes IP is the same device.
`kind` picks the icon in the list, `label` is the name to show. The answer fits a packet easily (under 200 bytes).

While the device list is on screen (and only then, app in the foreground), the app repeats the broadcast every 5 s, so
a device switched on appears without a refresh, and one switched off is greyed after 3 missed rounds.

## `GET /device`

```json
{"api": 2, "kind": "cd_player", "model": "Yamaha CD-S300", "name": "CDS300-D85E", "bridge_version": "91a64081",
 "firmware": "alemser/device-link/cds300", "features": ["control", "update", "wifi_setup"],
 "state": [
   {"id": "transport", "type": "enum", "values": ["playing", "paused", "stopped", "loading", "open"]},
   {"id": "media.track", "type": "int", "label": "Track"},
   {"id": "media.elapsed_s", "type": "duration", "label": "Time"},
   {"id": "disc.tracks", "type": "int", "label": "Tracks"},
   {"id": "disc.total_s", "type": "duration", "label": "Total"},
   {"id": "lcd", "type": "lines", "label": "Display", "columns": 12}],
 "controls": [
   {"group": "transport", "keys": ["previous", "rewind", "play", "pause", "stop", "fast_forward", "next", "eject"]},
   {"group": "modes", "keys": ["repeat", "shuffle", "repeat_a_b", "program", "display", "dimmer"]},
   {"group": "numbers", "keys": ["digit_1", "digit_2", "digit_3", "digit_4", "digit_5", "digit_6", "digit_7",
                                 "digit_8", "digit_9", "digit_0", "enter", "clear"]},
   {"group": "source", "keys": ["cd_usb", "pure_direct", "folder_down", "folder_up"]}]}
```

| Field | Meaning |
|---|---|
| `api` | Contract version. Changes only when something stops being compatible |
| `kind` | One of `amplifier`, `cd_player`, `tape_deck`, `tuner`, `turntable`, `streamer`, `dac`, or `other`. Picks the icon and the word in the list; an app that doesn't know a value shows a generic icon and the value with `_` as spaces |
| `model`, `name` | What to show; `name` as in discovery |
| `bridge_version` | Firmware version (the `version` of `GET /update`) |
| `firmware` | Where this bridge's firmware is released: `owner/repo/device`, the releases of `owner/repo` tagged `<device>-<version>` (see [Updates](#updates-from-the-app-update)) |
| `features` | Optional route groups present on this bridge |
| `state` | The state fields worth showing, in display order (below) |
| `controls` | The remote, in groups, in display order (below) |

That is the whole description. (Until 2026-11-17 it also had `settings`; the app ignores the field from an older
bridge.)

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
| `lines` | `columns` | Monospaced lines, as on the device's own display, `columns` characters wide (16 if absent) |

A field that a control already shows (the volume next to its − and +) is not repeated in the status.

### Controls

Each group is a row or a pad on the remote screen. A group holds one kind of control:

| Group content | Sent as | Example |
|---|---|---|
| `"keys": [...]` | `POST /control?target=key&name=<key>` | `play`, `power_toggle`, `select_cd` |
| `"steps": [{"target", "state", "label"}]` | `POST /control?target=<t>&dir=up` / `down` | volume, bass, treble, balance |
| `"switches": [{"target", "state", "label"}]` | `POST /control?target=<t>&on=1` / `0` | loudness, speakers |
| `"select": {"state", "options": [{"id", "name", "key"}]}` | the option's `key` | the amplifier's inputs |

`state` ties a step, switch or select to the state field that shows its current value (a select marks the option whose
`id` equals it). Keys are named with the groove-rig vocabulary (`docs/catalog` there): the app has a label and an icon
for each common one, and shows any other key by its name with `_` as spaces, so a new device needs no app change. A key
may also be `{"key": "...", "label": "..."}` when the name is not enough.

`/control` answers when the device has done it, or `400` with `{"error": "..."}`. It may take a few seconds (the SP103's
balance, loudness and speakers go through the amp's menu): one request at a time. Keys also work with the device in
standby; a key such as `power_toggle` switches both ways, so the app labels it by the known `power` and offers it even
when `power` is unknown.

Group names the app knows and lays out on purpose: `power`, `transport`, `volume`, `input`, `tone`, `modes`, `numbers`,
`source`. Any other group is shown as a plain row of buttons, in order.

## A device's own page

What only one device has, and what changes how the device itself behaves rather than what it plays, stays out of the
contract: the SP103's input names, boot and about screens, VU meter and info screens, for instance. A bridge with such
extras serves its own web page, opened in a browser at the bridge's IP:

- At `/` (while the setup network is open, `/` is the Wi-Fi setup page instead) and at a fixed path of its own that
  always answers (the SP103's `/config`).
- Over routes of its own (the SP103's `GET`/`PATCH /settings`, `GET /settings/fields`), documented in the device's
  repository. Nothing in this contract depends on them, and they may change with the bridge.
- The page is part of the bridge's firmware (a `.py` holding the HTML, so it goes in the same updates), small (under
  6 KB) and sent in chunks like any answer.

The app doesn't show, read or link these. A change made there reaches the app only through the contract: as state (the
display's `lcd` lines) or, rarely, a new description (the SP103's input chips carry the input names chosen on its page).

## `GET /state` and `GET /events`

The same JSON from both. `/events` sends one `data:` line on connect, then at most one every 0.25 s while the state
changes (always the latest), and a `: ping` comment every second. `null` or missing means unknown. Fields are grouped by
meaning, and the description's `state` list points into them:

```json
{"power": "on", "transport": "playing", "media": {"track": 3, "elapsed_s": 127},
 "disc": {"tracks": 12, "total_s": 3697}, "lcd": ["  3    2:07 "], "version": 41}
```

The amplifiers' fields are flat (`volume_db`, `input_id`, `bass_db`, ...) because groove-rig reads them too; the SP103's
are in `devices/sp103/docs/api-state.md`. A bridge keeps one `/events` connection per IP and few in total (3 on the SP103): a new
connection from the same IP drops the old one, and with the cap reached the oldest goes.

## Updates from the app (`update`)

The bridge side is `ota.py`: `GET /update` gives the running version, each file's hash, the `state` (`ok`,
`trial`, `rolled_back`) and `tried`, the version the last update applied (kept after a rollback, so a client tells
its own update's outcome from an older one); the upload routes take
files, apply them, and roll back by themselves if the new version doesn't confirm within 3 minutes. **No password**
(decided 2026-11-16): the routes are on the home LAN only, like the rest of the contract, and the rollback protects
against a bad version. `main.py` and `secrets.py` go only by USB.

1. A bridge's firmware is a GitHub release where `/device` `firmware` says. Every device lives in the device-link
   repository (`devices/<device>/`), so `firmware` is `alemser/device-link/<device>` and its releases are tagged
   `<device>-<version>` (`sp103-c59be28d`), never marked "latest" (that one is the app's own `app-<n>`). Each carries a
   `firmware.json` asset (`{"version", "files": {"<name>.py": "<sha256>"}}`) and the files themselves, built by the
   device's `tools/send.py --publish`. The app takes the newest release with the device's prefix through the GitHub
   API, so a device can be updated without the app knowing it in advance. A bare `owner/repo` (bridges from before
   2026-11-17, when each device had its own repository) means that repository's latest release.
2. The device screen shows "Version ... is available" when the release's version differs from `bridge_version`.
3. On "Update", the app downloads the files, uploads only those whose hash differs from `GET /update` (as `send.py`
   does), deletes the ones the release no longer has, applies, and follows `GET /update` until the bridge confirms or
   rolls back, showing which.

## Wi-Fi setup (`wifi_setup`)

To set up a bridge's Wi-Fi without a cable. The bridge side's details are in `devices/sp103/docs/wifi.md`.

**The setup network.** With no saved network, or unable to connect for 2 minutes, the bridge opens its own network
`DeviceLink-<name>` (e.g. `DeviceLink-SP103-D85E`), WPA2, fixed key **`amplink-setup`**, and keeps trying the home
network. On it, the bridge is `192.168.4.1`. The app also recognizes the legacy `AmpLink-` prefix during the
transition. Android asks for a matching network (`WifiNetworkSpecifier`) and shows the available choices without
location permission.

| Route | What |
|---|---|
| `GET /wifi` | `{"state", "detail", "ip", "ssid", "setup": {"open", "ssid"}}`. `state` and `detail`: the last attempt (`idle`, `connecting`, `connected`, or `failed` with the reason, to show as is). `ip`: the address on the home network now. `ssid`: the saved network |
| `GET /wifi/networks` | The networks the bridge sees, `[{"ssid", "rssi", "secure"}]`, strongest first, up to 20. Takes ~1 s |
| `PUT /wifi` | `{"ssid", "psk"}` (empty `psk` = open network; otherwise 8 to 63 characters). `202` at once; the outcome comes in `GET /wifi`. Only with the setup network open, otherwise `403` |
| `POST /wifi/setup` | Opens the setup network for 10 minutes, without leaving the home network. For switching networks while connected |
| `DELETE /wifi` | Forgets the saved network. Only with the setup network open |

**The app's flow:**

1. Join the `DeviceLink-…` network (or the legacy `AmpLink-…`) and read `GET /wifi/networks`.
2. `PUT /wifi` with the chosen network, and read `GET /wifi` every second until `connected` or `failed`. Some answers
   get lost along the way: the bridge's radio moves to the home network's channel, and the setup network moves with
   it. The bridge gives up a network after 15 s and then goes back to the previous one; wait up to about 40 s.
3. With `connected`, keep the `ip`, leave the setup network (it closes by itself 60 s later) and check `GET /device` at
   that IP. If it doesn't answer, find the bridge by discovery, by `name`.
4. With `failed`, show the `detail` and let the person choose again: the bridge went back to the previous network, and
   the setup network stays open.

## For the app

1. **At most one `/events` connection, and only on the open device's screen.** The list shows what discovery gives
   (name, kind, online), not live state.
2. **Close `/events` when the app goes to the background.** A dead connection, such as a sleeping phone's, holds the
   bridge's network memory and can freeze it for 10 s.
3. **With nothing for 5 s, consider the state unknown** and reconnect with a growing wait, from 1 s to 30 s.
4. **The other routes are on demand:** one request when opening the screen or the section, no repeating.
5. **Don't treat `null` as off.** After a bridge restarts with its device in standby, `power` stays `null`.
6. **Discovery repeats every 5 s, but only while the device list is visible.**

## Decided (2026-11-16 and 17)

- One repository for everything (2026-11-17): the contract, the app, the shared base and every device
  (`devices/<device>/`). Firmware releases are tagged by device in it, named by `/device` `firmware`. The old
  per-device repositories are archived.
- Updates take no password.
- The SP103 moved to `api` 2 (2026-11-17).
- `api` 1 was removed from the bridges and the app on 2026-11-17 (the `AMPLINK?` probe, `/names`, the amplifier tabs).
- **The contract is the lean one the CD-S300 set: device, state and remote (2026-11-17).** The `settings` field and
  route group left the contract and the app; the SP103 keeps its display configuration, now on [its own
  page](#a-devices-own-page). `api` stays 2: an older app shows no settings for a bridge that sends none, and this app
  ignores `settings` from an older bridge.

- **`kind` values (2026-11-18):** `amplifier`, `cd_player`, `tape_deck`, `tuner`, `turntable`, `streamer`, `dac`,
  `other`. A new kind of device adds its value here and an icon in the app; until then the app shows it generically.
- **`GET /update` says `tried` (2026-11-18).** A bridge from before doesn't; a client then takes `rolled_back` as is.

## Open

Nothing.
