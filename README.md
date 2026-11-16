# amp-link (DeviceLink)

What links the modified audio devices to everything else: the contract, the shared bridge firmware and the Android app,
now called **DeviceLink**.

A **bridge** is the board installed inside a device (an amplifier, a CD player), which reads what the device shows,
publishes it on the network and takes commands. A **client** is whoever uses the bridge: the Android app, groove-rig,
a `curl`.

| Where | What |
|---|---|
| [docs/contract-v2.md](docs/contract-v2.md) | The DeviceLink contract, `api` 2: multi-device, self-describing devices |
| [docs/contract-v1.md](docs/contract-v1.md) | The `api` 1 contract (amplifiers), which the SP103 and MR 780 bridges still speak |
| `android/` | The DeviceLink app |
| [firmware-base/](firmware-base/README.md) | What every bridge has (Wi-Fi, discovery, server, updates), copied into each project |

The app lists every device on the Wi-Fi by itself, marks a new one, and opens each one's screen: built from the
device's own description for an `api` 2 device, the amplifier tabs for an `api` 1 one. It sets up a new device's Wi-Fi
through the `AmpLink-…` network the device opens, and updates `api` 2 devices from their GitHub releases.

Each device's firmware lives in its own repository: the Acoustic Solutions SP103's in `sp103-display-proxy`, the Magnat
MR 780's in `mr780-mod` and the Yamaha CD-S300's in `cds300-mod`. The common part comes from `firmware-base/`.

A personal project: the app is Android-only, not on the Play Store.

## Build

Needs JDK 17 (`brew install openjdk@17`) and the Android SDK, with `sdk.dir` in `android/local.properties`.

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
android/gradlew -p android testDebugUnitTest assembleDebug
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

`tools/fake_bridge.py` is a fake bridge for testing the app without touching the amp. It uses the real firmware's
`names.validate`. In the emulator the computer is `10.0.2.2`, and the fake bridge must listen on port 80.
