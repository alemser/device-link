#!/usr/bin/env python3
"""Takes a raw capture of the display's lines from the bridge (firmware/capture.py) and summarises each line.

    python3 tools/bus_capture.py volume-up                     # 2 MHz for 30 ms; saves captures/volume-up-<time>.*
    python3 tools/bus_capture.py idle --rate 500000 --ms 120   # slower and longer, to see the frame rhythm
    python3 tools/bus_capture.py --summary captures/x.bin      # summarise a saved capture again

Saves <name>.bin (the raw samples), <name>.json (rate, samples, pins) and <name>.vcd (opens in PulseView) in
captures/, then prints, per line: the level at rest, transitions, the shortest and the most common high and low
widths, and the rate of transitions, which is how the clock gives itself away.

--host: default mr780.local, or MR780_HOST.
"""

import argparse
import collections
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import capture   # noqa: E402

OUT = os.path.join(HERE, "..", "captures")


def fetch(host, rate, ms, trigger=False, key=None, wait=10):
    url = "http://%s/capture?rate=%d&ms=%d&trigger=%d&wait=%d" % (host, rate, ms, trigger, wait)
    if key:
        url += "&key=" + key
    req = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=wait + 20) as r:
            info = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit("bridge: %s" % e.read().decode())
    data = bytearray()
    for part in range(info["parts"]):
        with urllib.request.urlopen("http://%s/capture?part=%d" % (host, part), timeout=15) as r:
            data += r.read()
    if len(data) != info["bytes"]:
        sys.exit("got %d bytes, expected %d" % (len(data), info["bytes"]))
    return info, bytes(data)


def runs(values):
    """[(level, length)] of a 0/1 sequence."""
    out = []
    for v in values:
        if out and out[-1][0] == v:
            out[-1][1] += 1
        else:
            out.append([v, 1])
    return out


def summary(info, data):
    rate, samples = info["rate"], info["samples"]
    us = 1e6 / rate
    s = capture.parse(data, samples)
    lines = ["%d samples at %.3f MHz = %.1f ms; one sample = %.3f µs" % (samples, rate / 1e6, samples / rate * 1e3, us)]
    for bit, name in enumerate(info["pins"]):
        vals = [(x >> bit) & 1 for x in s]
        rs = runs(vals)
        inner = rs[1:-1]                 # the first and last runs are cut by the capture's edges
        trans = len(rs) - 1
        line = "%-5s rest=%d  transitions=%-6d" % (name, collections.Counter(vals).most_common(1)[0][0], trans)
        for level in (1, 0):
            w = [n for v, n in inner if v == level]
            if w:
                common = collections.Counter(w).most_common(3)
                line += "  %s: min %.2f µs, most %s" % ("high" if level else "low", min(w) * us,
                                                         ", ".join("%.2f µs×%d" % (n * us, c) for n, c in common))
        if trans:
            line += "  (%.1f k transitions/s)" % (trans / (samples / rate) / 1e3)
        lines.append(line)
    return "\n".join(lines)


def vcd(info, data):
    rate = info["rate"]
    s = capture.parse(data, info["samples"])
    ids = "!\"#$"
    out = ["$timescale %d ns $end" % max(1, round(1e9 / rate)), "$scope module mr780 $end"]
    out += ["$var wire 1 %s %s $end" % (ids[b], n) for b, n in enumerate(info["pins"])]
    out += ["$upscope $end", "$enddefinitions $end"]
    prev = None
    for t, x in enumerate(s):
        if x != prev:
            out.append("#%d" % t)
            for b in range(len(info["pins"])):
                if prev is None or ((x ^ prev) >> b) & 1:
                    out.append("%d%s" % ((x >> b) & 1, ids[b]))
            prev = x
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("name", nargs="?", default="capture", help="what was happening (file name)")
    ap.add_argument("--rate", type=int, default=2_000_000)
    ap.add_argument("--ms", type=int, default=30)
    ap.add_argument("--trigger", action="store_true", help="start at the first activity on A, B or C")
    ap.add_argument("--key", help="remote key the bridge sends right after arming (e.g. volume_up)")
    ap.add_argument("--wait", type=int, default=10, help="seconds to wait for the trigger")
    ap.add_argument("--host", default=os.environ.get("MR780_HOST", "mr780.local"))
    ap.add_argument("--summary", metavar="BIN", help="summarise a saved capture instead of taking one")
    args = ap.parse_args()

    if args.summary:
        with open(args.summary[:-4] + ".json") as f:
            info = json.load(f)
        with open(args.summary, "rb") as f:
            print(summary(info, f.read()))
        return

    info, data = fetch(args.host, args.rate, args.ms, args.trigger or bool(args.key), args.key, args.wait)
    os.makedirs(OUT, exist_ok=True)
    base = os.path.join(OUT, "%s-%s" % (args.name, datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
    with open(base + ".bin", "wb") as f:
        f.write(data)
    with open(base + ".json", "w") as f:
        json.dump(info, f)
    with open(base + ".vcd", "w") as f:
        f.write(vcd(info, data))
    print(summary(info, data))
    print("saved", os.path.relpath(base) + ".bin/.json/.vcd")


if __name__ == "__main__":
    main()
