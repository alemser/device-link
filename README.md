# device-link (DeviceLink)

What links the modified audio devices to everything else: the contract, the shared bridge firmware and the Android app,
now called **DeviceLink**.

A **bridge** is the board installed inside a device (an amplifier, a CD player), which reads what the device shows,
publishes it on the network and takes commands. A **client** is whoever uses the bridge: the Android app, groove-rig,
a `curl`.

| Where | What |
|---|---|
| [docs/contract-v2.md](docs/contract-v2.md) | The DeviceLink contract, `api` 2: multi-device, self-describing devices |
| `android/` | The DeviceLink app |
| [firmware-base/](firmware-base/README.md) | What every bridge has (Wi-Fi, discovery, server, updates), copied into each project |

The app lists every device on the Wi-Fi by itself, marks a new one, and opens each one's screen, built from the
device's own description. It sets up a new device's Wi-Fi through the `AmpLink-…` network the device opens, and updates
each device from its GitHub releases. (`api` 1, the first amplifier-only contract, was removed on 2026-11-17.)

Each device's firmware lives in its own repository: the Acoustic Solutions SP103's in `sp103-mod`, the Magnat
MR 780's in `mr780-mod` and the Yamaha CD-S300's in `cds300-mod`. The common part comes from `firmware-base/`.

A personal project: the app is Android-only, not on the Play Store.

## Build

Needs JDK 17 (`brew install openjdk@17`) and the Android SDK, with `sdk.dir` in `android/local.properties`.

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
android/gradlew -p android testDebugUnitTest assembleDebug
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

**Updates without a cable.** `python3 tools/publish_app.py` (after commit and push) builds the APK and publishes it as
the release `app-<n>` of this repository, where `n` is the commit count. Every installed app below `n` shows "App update
available" on its device list; Android asks to confirm, and the first time, to allow installs from DeviceLink. The APK
is signed with this computer's debug key (`~/.android/debug.keystore`): keep a copy, since Android only accepts an
update signed with the same key.

The app's tests run against a fake device (MockWebServer) with the SP103's real description
(`android/app/src/test/resources/sp103-device.json`, written by sp103-mod's `firmware/device.py`).
