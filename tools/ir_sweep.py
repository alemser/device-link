#!/usr/bin/env python3
"""Finds the remote codes with no published value (pause, rec mute, search, intro scan, counter reset, power).

Sends command bytes one at a time to the bridge (POST /ir/send?code=XX) and asks, after each one, what the deck did.
The answers go to docs/ir-sweep.log; each code found then goes into firmware/ir_codes.py.

    python3 tools/ir_sweep.py                  # the likely range first: 05 to 1F, then 40 to 4F
    python3 tools/ir_sweep.py 05 08 0A         # only these
    python3 tools/ir_sweep.py --all            # 00 to FF

BEFORE STARTING: a cassette with BOTH record tabs broken off, or no cassette at all. Command 04 is REC/PAUSE, and an
unknown code may well start recording too; with the tabs off the deck refuses to record (owner's manual, page 16).
Start each code from a known state (stop, tape in the middle), so a transport change is easy to see.

--host: default kx393.local, or KX393_HOST. Without explicit codes, the known ones (00 to 04) are not sent.
"""

import argparse
import datetime
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import ir_codes   # noqa: E402

LOG = os.path.join(HERE, "..", "docs", "ir-sweep.log")
LIKELY = list(range(0x05, 0x20)) + list(range(0x40, 0x50))


def send(host, command):
    req = urllib.request.Request("http://%s/ir/send?code=%02X" % (host, command), data=b"", method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("codes", nargs="*", help="command bytes in hex (default: the likely range)")
    ap.add_argument("--all", action="store_true", help="every byte, 00 to FF")
    ap.add_argument("--host", default=os.environ.get("KX393_HOST", "kx393.local"))
    args = ap.parse_args()

    if args.codes:
        codes = [int(c, 16) for c in args.codes]
    else:
        codes = list(range(256)) if args.all else LIKELY
        known = set(ir_codes.COMMANDS.values())
        codes = [c for c in codes if c not in known]

    print("Record tabs broken off, or no cassette? (y/n) ", end="", flush=True)
    if input().strip().lower() != "y":
        sys.exit("Stopped: make the cassette unrecordable first.")

    with open(LOG, "a") as log:
        log.write("# %s, host %s\n" % (datetime.datetime.now().isoformat(timespec="seconds"), args.host))
        for command in codes:
            input("\nSet the deck to a known state, then Enter to send %02X..." % command)
            send(args.host, command)
            seen = input("%02X sent. What did the deck do? (Enter = nothing, r = repeat, q = quit) " % command)
            while seen.strip() == "r":
                send(args.host, command)
                seen = input("%02X sent again. What did the deck do? " % command)
            if seen.strip() == "q":
                break
            log.write("%02X\t%s\n" % (command, seen.strip() or "-"))
            log.flush()
    print("Answers in", os.path.relpath(LOG))


if __name__ == "__main__":
    main()
