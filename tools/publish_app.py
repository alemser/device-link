#!/usr/bin/env python3
"""Publishes the DeviceLink app as a GitHub release of this repository, for the app's self-update.

    python3 tools/publish_app.py

Builds the APK from the committed code (the versionCode is the number of commits, android/app/build.gradle.kts), and
creates the release app-<versionCode> with devicelink-<versionCode>.apk. Every installed app at a lower versionCode
offers the update on its device list (android/.../core/AppUpdate.kt).

The APK is signed with this computer's debug key (~/.android/debug.keystore). Android only installs an update signed
with the same key as the installed app: keep a copy of that file; with another key, the app must be uninstalled first.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID = os.path.join(ROOT, "android")
APK = os.path.join(ANDROID, "app", "build", "outputs", "apk", "debug", "app-debug.apk")
REPO = "alemser/device-link"
JAVA_HOME = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"


def git(*args):
    return subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, text=True, check=True).stdout.strip()


def main():
    if git("status", "--porcelain"):
        sys.exit("Commit first: the version comes from the commit count, and the release must match the code.")
    git("fetch", "-q", "origin")
    if git("rev-list", "--count", "origin/main..HEAD") != "0":
        sys.exit("Push first: the release should point at code that is on GitHub.")
    code = int(git("rev-list", "--count", "HEAD"))
    tag = "app-%d" % code
    if subprocess.run(["gh", "release", "view", tag, "--repo", REPO], capture_output=True).returncode == 0:
        sys.exit("Release %s already exists: commit something new first." % tag)
    env = dict(os.environ, JAVA_HOME=os.environ.get("JAVA_HOME", JAVA_HOME))
    subprocess.run([os.path.join(ANDROID, "gradlew"), "-p", ANDROID, "--console=plain", "-q",
                    ":app:testDebugUnitTest", ":app:assembleDebug"], env=env, check=True)
    named = os.path.join(os.path.dirname(APK), "devicelink-%d.apk" % code)
    os.replace(APK, named)
    notes = "DeviceLink %d. Latest change: %s" % (code, git("log", "-1", "--format=%s"))
    subprocess.run(["gh", "release", "create", tag, "--repo", REPO, "--title", "DeviceLink app %d" % code,
                    "--notes", notes, "--target", git("rev-parse", "HEAD"), named], check=True)
    print("Published %s. Installed apps below %d will offer it." % (tag, code))


if __name__ == "__main__":
    main()
