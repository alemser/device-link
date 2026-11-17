#!/usr/bin/env python3
"""Settles the remote's address on the deck: the service manual says 7F, the captured codes say 7A (ir_codes.py).

Sends PLAY (command 00) at each candidate address through the bridge (POST /ir/send?code=00&address=XX) and asks
what the deck did. The answers go to docs/ir-try.log; the address that plays becomes ir_codes.ADDRESS.

    python3 tools/ir_try.py                    # PLAY at 7F, then at 7A
    python3 tools/ir_try.py 03 --address 7A    # one command at one address

Use a cassette with both record tabs broken off: a wrong guess at the address can't record, but a typo in a
command could be 04 (REC/PAUSE). Stop the tape between tries, so a start is easy to see.

--host: default kx393.local, or KX393_HOST.
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
    ap.add_argument("command", nargs="?", default="00", help="command byte in hex (default 00, PLAY)")
    ap.add_argument("--address", help="one address in hex (default: 7F, then 7A)")
    ap.add_argument("--host", default=os.environ.get("KX393_HOST", "kx393.local"))
    args = ap.parse_args()

    command = int(args.command, 16)
    addresses = [int(args.address, 16)] if args.address else [ir_codes.ADDRESS, ir_codes.ADDRESS_CAPTURED]

    print("Record tabs broken off, or no cassette? (y/n) ", end="", flush=True)
    if input().strip().lower() != "y":
        sys.exit("Stopped: make the cassette unrecordable first.")

    with open(LOG, "a") as log:
        log.write("# %s, host %s\n" % (datetime.datetime.now().isoformat(timespec="seconds"), args.host))
        for address in addresses:
            input("\nStop the tape, then Enter to send %02X at address %02X..." % (command, address))
            send(args.host, command, address)
            seen = input("Sent. What did the deck do? (Enter = nothing) ").strip() or "-"
            log.write("%02X/%02X\t%s\n" % (address, command, seen))
            log.flush()
    print("Answers in", os.path.relpath(LOG))


if __name__ == "__main__":
    main()
