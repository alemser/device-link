#!/usr/bin/env python3
"""Copies the shared base into a bridge's project, or checks that the copies are up to date.

Run from the project folder (the one with firmware/ and tools/), or pass it:

    python3 ../device-link/firmware-base/copiar.py                # copies what changed
    python3 ../device-link/firmware-base/copiar.py --check        # only checks; fails if anything differs
    python3 ../device-link/firmware-base/copiar.py --skip firmware/main.py    # leaves that file as it is

The files go byte for byte. A copy that differs from the base means someone changed it in the project: take the
change to the base before copying, because the copy overwrites it. The old Portuguese flags (--conferir, --sem) still
work.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDERS = ("firmware", "tools")


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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project", nargs="?", default=".", help="the project folder (default: the current one)")
    ap.add_argument("--check", "--conferir", dest="check", action="store_true",
                    help="don't copy: only say what differs")
    ap.add_argument("--skip", "--sem", dest="skip", action="append", default=[], metavar="FILE",
                    help="a file this project keeps on its own (repeatable)")
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    if not os.path.isdir(os.path.join(project, "firmware")):
        sys.exit("%s has no firmware/ folder: run it in the bridge's project folder." % project)
    if os.path.samefile(project, HERE):
        sys.exit("This is the base itself. Run it in the bridge's project folder.")
    for skipped in args.skip:
        if skipped not in base_files():
            sys.exit("--skip %s: the base has no such file." % skipped)

    differs = 0
    for rel in base_files():
        if rel in args.skip:
            print("  %-28s kept by the project" % rel)
            continue
        want = read(os.path.join(HERE, rel))
        target = os.path.join(project, rel)
        have = read(target)
        if have == want:
            continue
        differs += 1
        what = "missing" if have is None else "differs from the base"
        if args.check:
            print("  %-28s %s" % (rel, what))
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(want)
        print("  %-28s copied (%s)" % (rel, "new" if have is None else "was different"))

    if not differs:
        print("Up to date with the base.")
    elif args.check:
        sys.exit("%d file(s) out of date with the base." % differs)


if __name__ == "__main__":
    main()
