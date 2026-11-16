# Contract between bridges and clients, `api` 1

**`api` 1, the amplifier contract.** Written from the SP103's firmware and checked on the real bridge on 2026-11-04.
Its successor is the DeviceLink contract, `api` 2 (`docs/contract-v2.md`); the SP103 and MR 780 bridges still speak
this one, and the DeviceLink app shows them with the amplifier tabs.

A **bridge** is the board inside the amp. A **client** is whoever queries it. A bridge is small: it has little memory
and serves few connections, and a misbehaving client can freeze the display. That is why the rules in
[For the client](#for-the-client) are part of the contract.

## Routes

The **core** applies to every bridge. The other routes exist only if the bridge lists the feature in `features`.

| Route | Group | On the SP103 |
|---|---|---|
| `GET /device` | Core | Yes |
| `GET /state` | Core | Yes |
| `GET /events` | Core | Yes |
| `GET /names`, `PUT /names` | `config` | Yes |
| `POST /control`, `POST /ir/send` | `control` | Yes |
| `GET /bus.json`, `GET /bus.csv`, `POST /bus/clear` | `bus_log` | Yes |
| `GET /update` and the upload routes | `update` | Yes; outside the app (`tools/enviar.py`) |
| `GET /wifi`, `GET /wifi/networks`, `PUT /wifi`, `POST /wifi/setup`, `DELETE /wifi` | `wifi_setup` | Yes (2026-11-08) |

## Transport

- HTTP/1.1 without TLS, on the local network only. The client finds the bridge by [discovery](#wi-fi-and-discovery-wifi_setup)
  and keeps the IP; if it stops answering, it searches again. Don't count on `.local` names.
- The bridge has only an API. The only page is the Wi-Fi setup page, and only with the setup network open.
- No authentication, except the `update` upload routes, which take the `x-password` header (dropped in `api` 2).
- Every answer closes the connection (`Connection: close`), except `/events`.
- JSON answers, with `Cache-Control: no-store` and `Access-Control-Allow-Origin: *`.
- Errors: `400` or `403` with `{"error": "text"}`. Unknown route: `404` as plain text.

## `GET /device`

Who the bridge is and what it can do. It doesn't change while the bridge runs, so the client reads it once on
connecting and keeps it.

```json
{"api": 1, "model": "Acoustic Solutions SP103", "bridge_version": "eb50a51b",
 "volume_db": {"min": -78.75, "max": 0, "step": 1.25},
 "tone_db": {"min": -14, "max": 14, "step": 2},
 "inputs": [{"id": "phono", "name": "PHONO"}, {"id": "tuner", "name": "TUNER"}, {"id": "tape_aux", "name": "TAPE/AUX"},
            {"id": "cd", "name": "CD"}, {"id": "dvd", "name": "DVD"}, {"id": "dab", "name": "DAB"}],
 "display": {"columns": 16, "rows": 2},
 "features": ["tone", "balance", "loudness", "speakers", "config", "vu", "info_screens", "bus_log", "update", "wifi_setup",
              "control"]}
```

| Field | Meaning |
|---|---|
| `api` | Contract version. Changes only when something stops being compatible; new fields don't change it |
| `model` | Name to show |
| `bridge_version` | The bridge's firmware version (`GET /update`'s `version`). Not the state's `firmware`, which is the amp's |
| `volume_db`, `tone_db` | Range and step. `tone_db` is `null` if the amp has no tone controls |
| `inputs` | Stable `id` and the amp's own `name`, in the amp's order |
| `display` | Display size, or `null` if the bridge has no display |
| `features` | What exists on this bridge. A client ignores what it doesn't know and hides what isn't listed |

| Feature | Means |
|---|---|
| `tone`, `balance`, `loudness`, `speakers` | The amp has that control and the state carries the field |
| `config` | `GET` and `PUT /names` |
| `vu`, `info_screens` | The bridge has the VU and info screens; they need `config` |
| `bus_log` | The `/bus.*` routes |
| `control` | Commands to the amp, through `POST /control` and `POST /ir/send` |
| `update` | Updates over the network |

## `GET /state` and `GET /events`

Both carry the same JSON. `/events` is Server-Sent Events: one `data: {json}` on connecting and another on each change,
plus a `: ping` comment every second.

```json
{"power": "on", "volume_db": -20.0, "input": "DAB", "input_id": "dab", "input_name": "AirPlay/BT",
 "bass_db": 2, "treble_db": 0, "balance": {"side": "L", "db": -5.0}, "loudness": false, "speakers": true,
 "screen": "normal", "firmware": "1.0", "lcd": ["Volume -20.00 dB", "DAB             "],
 "updated_at": 3747990, "version": 5}
```

`null` or a missing field means **not known**, never off or zero. The bridge only knows a value once the amp shows it.

The fields groove-rig reads (`power`, `volume_db`, `input_id`, `bass_db`, `treble_db`, `balance`, `loudness`,
`speakers`) follow groove-rig's `docs/state-provider.md`, their authoritative text. Their meanings and values on the
SP103 are in `sp103-display-proxy`'s `docs/api-estado.md`. The others are extras:

| Field | Meaning |
|---|---|
| `input`, `input_name` | The input's own name and its custom name |
| `screen` | The screen the amp shows now. Values depend on the amp |
| `firmware` | The amp's firmware version, if it shows it |
| `lcd` | The display's lines as they are |
| `updated_at`, `version` | The bridge's clock and counter. They reset when it restarts and only compare with each other |

## `GET /names` and `PUT /names` (`config`)

`GET` returns the configuration and the status of what it switches on:

```json
{"config": {"inputs": {"TUNER": "Rega Planar 2"}, "boot": ["", ""], "about": ["Oceano Amp", "AS SP103"],
            "vu": {"on": true, "auto": true, "layout": "deck", "relay": "192.168.178.99"},
            "info": {"on": true, "mode": "temp", "show": ["stylus", "quality"],
                     "secs": 8, "clock": true, "utc_offset": 0, "eu_dst": true,
                     "source": "", "turntable": ["PHONO", "TUNER", "CD"]}},
 "inputs": ["PHONO", "TUNER", "TAPE/AUX", "CD", "DVD", "DAB"],
 "defaults": {"boot": ["ACOUSTIC", "SOLUTIONS"], "about": ["Amplifier SP103", "SW version 1.0"]},
 "proxy": {"reads": 11968, "writes": 11968, "busy_high": 0},
 "vu": {"on": true, "auto": true, "layout": "deck", "floor": -42, "top": -22, "frames": 139405, "last_frame_ms": 21,
        "music": false, "showing": false, "error": null},
 "info": {"on": true, "packets": 29362, "last_packet_ms": 578, "playing": false, "stream": null},
 "screens": {"on": true, "mode": "temp", "showing": null, "error": null}}
```

`PUT` takes the `config` object and answers as `GET` does, or `400` with `{"error": "..."}`, in English, ready to show.

**`PUT` replaces everything.** Whatever is missing from the body goes back to its default: sending only
`{"inputs": {...}}` switches off the VU and the info screens. To change one field, the client reads `config`, changes
the field and sends the whole `config` (`api` 2's `PATCH /settings` fixes this).

`config` rules:

| Field | Rule |
|---|---|
| `inputs` | Keys are the **original** names (`"TAPE/AUX"`), not the `id`s. Empty text = original name |
| `boot`, `about` | A list of 2 lines. Empty text = original text |
| Every LCD text | Up to 16 characters, ASCII from `" "` to `"}"`, no `"\"` and no accents |
| `vu.on` | Boolean |
| `vu.layout` | `bars`, `deck`, `scale` or `kx393` |
| `vu.relay` | IPv4 of the VU source. Empty by default; required with `vu.on` true |
| `vu.auto` | Always `true`; the bridge ignores the value sent |
| `info.on`, `clock`, `eu_dst` | Booleans |
| `info.mode` | `temp` (each screen comes in for `secs`) or `fixed` (the current input's screen all the time; no VU) |
| `info.show` | A list with `stylus` (the `turntable` inputs) and/or `quality` (Bluetooth on DAB). `track`, `pos` and `side` (screens removed on 2026-11-07) are accepted and ignored, as are `fixed`, `alert` and `scroll` |
| `info.secs` | Integer from 3 to 60 |
| `info.utc_offset` | Hours from −12 to 14, in quarter hours |
| `info.source` | IPv4, or empty to use `vu.relay`'s |
| `info.turntable` | A list of inputs, by their original names |

## `control`

The client asks for the result, and the bridge does the clicks on the amp.

| Route | What it does |
|---|---|
| `POST /control?target=<t>&dir=<up or down>` | One step. `t`: `volume`, `bass`, `treble` or `balance` |
| `POST /control?target=<t>&on=<1 or 0>` | On or off. `t`: `loudness` or `speakers` |
| `POST /control?target=key&name=<key>` | One remote key, such as `power_toggle` or `select_cd`. Also works in standby |
| `POST /ir/send?cmd=<command>` | One remote key, such as `power_toggle` or `select_cd`. The list is at `GET /ir` |

`/control` answers with the state after the change, or `400` with `{"error": "..."}`, in English, ready to show. The
answer may take a few seconds: balance, loudness and speakers go through the amp's menu, and the volume waits for an
open menu to close. One request at a time and, except `target=key`, only with `power` = `on`. Steps in a row reuse
the open menu.

`power_toggle` switches on and off: the client should check `power` first. On the SP103, a menu click sometimes also
switches the input to PHONO for about 1 s, until the bridge puts the previous one back.

## `bus_log`

| Route | What |
|---|---|
| `GET /bus.json` | Statistics of the display bus |
| `GET /bus.csv?tz=<minutes>` | The last words read, as CSV (up to 8192 lines, no `Content-Length`) |
| `POST /bus/clear` | Clears the log and the statistics |

```json
{"since_s": 146828, "words": 23936, "writes": 11968, "reads": 11968, "power_ons": 0, "screens": 172,
 "unknown_screens": 0, "last_screen_s": 299, "max_gap_ms": 10033, "max_batch": 1152, "maybe_lost": false,
 "log_words": 8192, "log_size": 8192, "log_span_s": 7586, "clock": "2026-11-04 14:21:35.236",
 "lcd": ["Volume -38.75 dB", "DAB             "]}
```

`max_gap_ms` is the bridge loop's longest pause. Close to 10000 is lwIP's 10 s freeze.

## Wi-Fi and discovery (`wifi_setup`)

To set up a bridge's Wi-Fi without a cable and find it without typing an IP. Decided and bench-tested on 2026-11-08;
the bridge side's details are in sp103-display-proxy's `docs/wifi.md`.

**Discovery.** The client sends `AMPLINK?` by UDP broadcast to port **47800**, three times over about 2 s (the first
packet is sometimes lost), and each bridge answers the sender:

```json
{"name": "SP103-D85E", "model": "sp103", "ip": "192.168.1.77"}
```

Bridges built on `firmware-base/` (2026-11-16) add `label`, the full name to show in a list (`"Yamaha CD-S300"`, the
same as `GET /device`'s `model`), and `kind`, the type of device (`amplifier` or `cd_player`); `api` 2 bridges also
add `api` and answer `DEVICELINK?`. All of these may be missing: the SP103 doesn't send them yet. The answer fits a
packet easily (under 200 bytes).

**The setup network.** With no saved network, or unable to connect for 2 minutes, the bridge opens its own network
`AmpLink-<name>` (e.g. `AmpLink-SP103-D85E`), WPA2, fixed key **`amplink-setup`**, and keeps trying the home network.
On it, the bridge is `192.168.4.1`. Every setup network starts with `AmpLink-`: on Android, the app asks for a network
with that prefix (`WifiNetworkSpecifier`) and the system shows the matching ones, without location permission.

| Route | What |
|---|---|
| `GET /wifi` | `{"state", "detail", "ip", "ssid", "setup": {"open", "ssid"}}`. `state` and `detail`: the last attempt (`idle`, `connecting`, `connected`, or `failed` with the reason, to show as is). `ip`: the address on the home network now. `ssid`: the saved network |
| `GET /wifi/networks` | The networks the bridge sees, `[{"ssid", "rssi", "secure"}]`, strongest first, up to 20. Takes ~1 s |
| `PUT /wifi` | `{"ssid", "psk"}` (empty `psk` = open network; otherwise 8 to 63 characters). `202` at once; the outcome comes in `GET /wifi`. Only with the setup network open, otherwise `403` |
| `POST /wifi/setup` | Opens the setup network for 10 minutes, without leaving the home network. For switching networks while connected |
| `DELETE /wifi` | Forgets the saved network. Only with the setup network open |

**The app's flow:**

1. Join the `AmpLink-…` network and read `GET /wifi/networks`.
2. `PUT /wifi` with the chosen network, and read `GET /wifi` every second until `connected` or `failed`. Some answers
   get lost along the way: the bridge's radio moves to the home network's channel, and the setup network moves with
   it. The bridge gives up a network after 15 s and then goes back to the previous one; wait up to about 40 s.
3. With `connected`, keep the `ip`, leave the setup network (it closes by itself 60 s later) and check `GET /device` at
   that IP. If it doesn't answer, find the bridge by discovery, by `name`.
4. With `failed`, show the `detail` and let the person choose again: the bridge went back to the previous network, and
   the setup network stays open.

## For the client

1. **One `/events` connection per client**, and only on the screen that shows the live state. The bridge keeps one
   connection per IP and few in total (3 on the SP103): a new connection from the same IP drops the old one, and with
   the cap reached the oldest goes.
2. **Close `/events` when the app goes to the background.** A dead connection, such as a sleeping phone's, holds the
   bridge's network memory and can freeze the display for 10 s.
3. **With nothing for 5 s, consider the state unknown** and reconnect with a growing wait, from 1 s to 30 s.
4. **The other routes are on demand:** one request when opening the section, no repeating. The exception is
   `/bus.json`, at most every 2 s while its screen is open.
5. **Wait at least 1 s after the last edit before `PUT /names`.** Each `PUT` writes to flash and redraws the display,
   so the bridge must not get one per keystroke.
6. **Download `/bus.csv` only on request.** It is the bridge's heaviest answer.
7. **Don't treat `null` as off.** After the bridge restarts with the amp in standby, `power` stays `null`.
8. **Discovery is on request:** when the app opens and the saved IP doesn't answer, or when the person asks. (`api` 2
   relaxes this: discovery repeats every 5 s while the device list is on screen.)

## Open

Settled by `api` 2 (`docs/contract-v2.md`):

- **`/names`:** becomes `/settings`, with `PATCH`.
- **`/bus.*`** and **`screen`:** per device.
