#!/usr/bin/env python3
"""Finds remote keys not learned yet (ir_codes.py has ten): sends one command byte at a time to the amp,
through the bridge (POST /ir/send?code=XX), and asks what the amp did. The answers go to docs/ir-try.log; each key
found goes into firmware/ir_codes.py (COMMANDS, KEYS) and firmware/device.py (CONTROLS).

    python3 tools/ir_try.py 12              # one command byte at the amp's address (40)
    python3 tools/ir_try.py 10 1F           # every byte from 10 to 1F, one at a time
    python3 tools/ir_try.py 12 --address 41

Volume low before starting: an unknown byte may be volume up, and pressing it again won't be undone by itself.
Known bytes (ir_codes.COMMANDS) are skipped.

--host: default mr780.local, or MR780_HOST.
"""

import argparse
import datetime
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import ir_codes   # noqa: E402

LOG = os.path.join(HERE, "..", "docs", "ir-try.log")


def send(host, command, address):
    url = "http://%s/ir/send?code=%02X&address=%02X" % (host, command, address)
    req = urllib.request.Request(url, data=b"", method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("first", help="command byte in hex")
    ap.add_argument("last", nargs="?", help="last command byte in hex (default: only the first)")
    ap.add_argument("--address", default="%02X" % ir_codes.ADDRESS, help="address in hex (default 40)")
    ap.add_argument("--host", default=os.environ.get("MR780_HOST", "mr780.local"))
    args = ap.parse_args()

    first = int(args.first, 16)
    last = int(args.last, 16) if args.last else first
    address = int(args.address, 16)
    known = {v: k for k, v in ir_codes.COMMANDS.items()} if address == ir_codes.ADDRESS else {}

    print("Volume low? (y/n) ", end="", flush=True)
    if input().strip().lower() != "y":
        sys.exit("Stopped: turn the volume down first.")

    with open(LOG, "a") as log:
        log.write("# %s, host %s\n" % (datetime.datetime.now().isoformat(timespec="seconds"), args.host))
        for command in range(first, last + 1):
            if command in known:
                print("%02X is %s, skipped" % (command, known[command]))
                continue
            input("\nEnter to send %02X at address %02X (Ctrl-C to stop)..." % (command, address))
            send(args.host, command, address)
            seen = input("Sent. What did the amp do? (Enter = nothing) ").strip() or "-"
            log.write("%02X/%02X\t%s\n" % (address, command, seen))
            log.flush()
    print("Answers in", os.path.relpath(LOG))


if __name__ == "__main__":
    main()
