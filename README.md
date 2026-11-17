# device-link (DeviceLink)

The modified audio devices and what links them: the contract, the shared bridge firmware, each device's bridge and the
Android app, **DeviceLink**. One repository for all of it since 2026-11-17.

A **bridge** is the board installed inside a device (an amplifier, a CD player), which reads what the device shows,
publishes it on the network and takes commands. A **client** is whoever uses the bridge: the Android app, groove-rig,
a `curl`.

| Where | What |
|---|---|
| [docs/contract-v2.md](docs/contract-v2.md) | The DeviceLink contract, `api` 2: multi-device, self-describing devices |
| `android/` | The DeviceLink app |
| [firmware-base/](firmware-base/README.md) | What every bridge has (Wi-Fi, discovery, server, updates), copied into each device |
| [devices/sp103/](devices/sp103/README.md) | Acoustic Solutions SP103 amplifier: display, VU meter, IR control (installed) |
| [devices/cds300/](devices/cds300/README.md) | Yamaha CD-S300 CD player: state and IR remote (installed) |
| [devices/mr780/](devices/mr780/README.md) | Magnat MR 780 hybrid receiver (not installed yet) |
| [devices/kx393/](devices/kx393/README.md) | Yamaha KX-393 tape deck (no hardware yet) |

The app lists every device on the Wi-Fi by itself, marks a new one, and opens each one's screen, built from the
device's own description. It sets up a new device's Wi-Fi through the `AmpLink-…` network the device opens, and updates
each device from its GitHub releases. (`api` 1, the first amplifier-only contract, was removed on 2026-11-17.)

Each device folder holds its bridge's firmware (`firmware/`, exactly what goes on its Pico, base copies included), its
tools and tests (`tools/`), its docs and its captures. The devices had their own repositories until 2026-11-17
(`sp103-mod`, `cds300-mod`, `mr780-mod`, `kx393-mod`, now archived); the CD-S300's, MR 780's and KX-393's history came
along, the SP103 came as its latest version only.

## Working on a device

```sh
cd devices/sp103
python3 tools/test_device.py                     # its tests (each tools/test_*.py)
python3 tools/send.py                          # send what changed to its Pico over Wi-Fi
python3 tools/send.py --publish                # release sp103-<version> here, for the app's "Update"
cd ../.. && python3 firmware-base/copy_base.py --all --check   # base copies up to date in every device?
```

A base file is changed in `firmware-base/` and copied with `python3 firmware-base/copy_base.py --all`, never edited in a
device.

A personal project: the app is Android-only, not on the Play Store.

## Build

Needs JDK 17 (`brew install openjdk@17`) and the Android SDK, with `sdk.dir` in `android/local.properties`.

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
android/gradlew -p android testDebugUnitTest assembleDebug
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

**Updates without a cable.** `python3 tools/publish_app.py` (after commit and push) builds the APK and publishes it as
the release `app-<n>` of this repository, where `n` is the commit count (the devices' firmware releases share the
repository, tagged `<device>-<version>` and never marked "latest"). Every installed app below `n` shows "App update
available" on its device list; Android asks to confirm, and the first time, to allow installs from DeviceLink. The APK
is signed with this computer's debug key (`~/.android/debug.keystore`): keep a copy, since Android only accepts an
update signed with the same key.

The app's tests run against a fake device (MockWebServer) with the SP103's real description
(`android/app/src/test/resources/sp103-device.json`, written by `devices/sp103/firmware/device.py`).
