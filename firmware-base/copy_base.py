#!/usr/bin/env python3
"""Copies the shared base into the devices (devices/<name>/), or checks that the copies are up to date.

From the repository's root:

    python3 firmware-base/copy_base.py --all            # every device under devices/
    python3 firmware-base/copy_base.py --all --check    # only checks; fails if anything differs (run it before a commit)
    python3 firmware-base/copy_base.py devices/sp103    # one device

The files go byte for byte, so each devices/<name>/firmware/ stays exactly what goes on its Pico. A copy that differs
from the base means someone changed it in the device: take the change to the base before copying, because the copy
overwrites it. A device that keeps a base file of its own is listed in KEEP (the SP103's main.py); a base file only
some devices use is listed in ONLY, with those devices.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEVICES = os.path.join(HERE, "..", "devices")
FOLDERS = ("firmware", "tools")
# Base files a device keeps on its own. The SP103's main.py imports escuta.py and shows errors on the LCD.
KEEP = {"sp103": ("firmware/main.py",)}
# Base files only some devices use, and which: the others don't get them.
ONLY = {"firmware/clocked_bus.py": ("cds300", "mr780")}


def base_files():
    """The base's files, as "firmware/wifi.py"."""
    out = []
    for folder in FOLDERS:
        for name in sorted(os.listdir(os.path.join(HERE, folder))):
            if name.endswith(".py"):
                out.append(folder + "/" + name)
    return out


def read(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def devices():
    return sorted(os.path.join(DEVICES, d) for d in os.listdir(DEVICES)
                  if os.path.isdir(os.path.join(DEVICES, d, "firmware")))


def sync(project, skip, check):
    """Copies (or checks) one device; returns how many files differed."""
    name = os.path.basename(project)
    skip = set(skip) | set(KEEP.get(name, ())) | {rel for rel, users in ONLY.items() if name not in users}
    differs = 0
    for rel in base_files():
        if rel in skip:
            continue
        want = read(os.path.join(HERE, rel))
        target = os.path.join(project, rel)
        have = read(target)
        if have == want:
            continue
        differs += 1
        what = "missing" if have is None else "differs from the base"
        if check:
            print("  %s: %-28s %s" % (name, rel, what))
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(want)
        print("  %s: %-28s copied (%s)" % (name, rel, "new" if have is None else "was different"))
    return differs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project", nargs="?", help="one device's folder (default: the current one)")
    ap.add_argument("--all", action="store_true", help="every device under devices/")
    ap.add_argument("--check", dest="check", action="store_true",
                    help="don't copy: only say what differs")
    ap.add_argument("--skip", dest="skip", action="append", default=[], metavar="FILE",
                    help="a base file to leave as it is (repeatable)")
    args = ap.parse_args()

    projects = devices() if args.all else [os.path.abspath(args.project or ".")]
    for project in projects:
        if not os.path.isdir(os.path.join(project, "firmware")):
            sys.exit("%s has no firmware/ folder: pass a device's folder, or --all." % project)
        if os.path.samefile(project, HERE):
            sys.exit("This is the base itself. Pass a device's folder, or --all.")
    for skipped in args.skip:
        if skipped not in base_files():
            sys.exit("--skip %s: the base has no such file." % skipped)

    differs = sum(sync(p, args.skip, args.check) for p in projects)
    if not differs:
        print("Up to date with the base: %s." % ", ".join(os.path.basename(p) for p in projects))
    elif args.check:
        sys.exit("%d file(s) out of date with the base." % differs)


if __name__ == "__main__":
    main()
