#!/usr/bin/env python3
"""Reads a LogicAnalyzer capture (gusmanb, .lac file) taken on the CD-S300's flat cable and shows what went by.

    python3 tools/fl_decode.py captures/02-playing.lac
    python3 tools/fl_decode.py captures/02-playing.lac --bits          # each frame's raw bits
    python3 tools/fl_decode.py captures/02-playing.lac --edge falling  # data read on the falling clock edge

Written on 2026-11-16, before any capture, so it assumes nothing about the glass's protocol: it cuts the traffic into
frames and measures it (docs/protocol.md has what it showed):

- Display (`FL_/CS`, `FL_CLK`, `FL_DATA`, `FL_/RST`): each frame is a stretch with `FL_/CS` at 0. Inside it, one bit
  per clock edge (rising by default). The bytes come out in both bit orders (MSB first and LSB first). It also shows
  the clock speed, the bits in each frame, the groups of frames (split by silence) and how often a group comes back.
- Remote (`REM`, or the `U701` output): decodes NEC (docs/research.md) and names the key from firmware/ir_codes.py.

Default wiring (analyzer channel → flat line), as in docs/protocol.md:

    CH1 = FL_/CS   CH2 = FL_CLK   CH3 = FL_DATA   CH4 = FL_/RST   CH5 = REM

Channel names set in the analyzer program (CS, CLK, DATA, RST, REM) take precedence over the numbers.
"""

import argparse
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware"))

import ir_codes   # noqa: E402

DEFAULT_MAP = {"CS": 1, "CLK": 2, "DATA": 3, "RST": 4, "REM": 5}
ALIASES = {"FL_/CS": "CS", "FL_CS": "CS", "/CS": "CS", "FL_CLK": "CLK", "FL_DATA": "DATA", "DA": "DATA",
           "FL_/RST": "RST", "FL_RST": "RST", "RESET": "RST", "IR": "REM", "U701": "REM"}

GROUP_GAP_US = 1000             # a silence longer than this between frames splits two groups (one "write" of the screen)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def load_lac(path):
    """A .lac is the JSON of File > Save. Returns the frequency and each signal's samples (bytes of 0 and 1)."""
    with open(path, encoding="utf-8-sig") as f:
        settings = json.load(f)["Settings"]
    by_number, by_name = {}, {}
    for ch in settings["CaptureChannels"]:
        raw = ch.get("Samples")
        if raw is None:
            continue
        samples = base64.b64decode(raw) if isinstance(raw, str) else bytes(raw)
        by_number[ch["ChannelNumber"] + 1] = samples
        name = (ch.get("ChannelName") or "").strip().upper()
        if name:
            by_name[ALIASES.get(name, name)] = samples
    signals = {}
    for sig, number in DEFAULT_MAP.items():
        if sig in by_name:
            signals[sig] = by_name[sig]
        elif number in by_number:
            signals[sig] = by_number[number]
    return settings["Frequency"], signals


def edges(samples):
    """(index, new value) of each level change."""
    out = []
    prev = samples[0] if samples else 0
    for i in range(1, len(samples)):
        v = samples[i]
        if v != prev:
            out.append((i, v))
            prev = v
    return out


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def frames(cs, clk, data, edge="rising"):
    """The display's frames: each stretch with /CS at 0. Returns dicts with start, end (in samples) and the bits."""
    want = 1 if edge == "rising" else 0
    out = []
    start = None
    bits = []
    for i in range(1, len(cs)):
        if cs[i - 1] == 1 and cs[i] == 0:
            start, bits = i, []
        elif start is not None and cs[i] == 0 and clk[i - 1] != clk[i] and clk[i] == want:
            bits.append(data[i])
        elif start is not None and cs[i - 1] == 0 and cs[i] == 1:
            out.append({"start": start, "end": i, "bits": bits})
            start = None
    return out


def to_bytes(bits, msb_first):
    out = []
    for k in range(0, len(bits) - len(bits) % 8, 8):
        b = 0
        for j, bit in enumerate(bits[k:k + 8]):
            b |= bit << (7 - j if msb_first else j)
        out.append(b)
    return out


def clock_stats(clk, cs, freq):
    """Typical (median) length of the clock's high and low parts, in µs, only with /CS at 0."""
    highs, lows = [], []
    last = None
    for i, v in edges(clk):
        if last is not None and cs[i] == 0 and cs[last[0]] == 0:
            (highs if v == 0 else lows).append((i - last[0]) * 1e6 / freq)
        last = (i, v)
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None   # noqa: E731
    return med(highs), med(lows), len(highs) + len(lows)


def groups(frs, freq, gap_us=GROUP_GAP_US):
    """Joins frames less than gap_us apart: one write of the screen is usually several frames in a row."""
    out = []
    for fr in frs:
        if out and (fr["start"] - out[-1][-1]["end"]) * 1e6 / freq < gap_us:
            out[-1].append(fr)
        else:
            out.append([fr])
    return out


def pulses_low(samples, freq):
    """(start in ms, length in µs) of each stretch at 0, for /RST."""
    out = []
    start = None
    for i, v in edges(samples):
        if v == 0:
            start = i
        elif start is not None:
            out.append((start * 1e3 / freq, (i - start) * 1e6 / freq))
            start = None
    return out


# ---------------------------------------------------------------------------
# Remote control (NEC, line idle high)
# ---------------------------------------------------------------------------

def nec(rem, freq):
    """The NEC keys on the line: dicts with the time (ms), the 4 bytes and the name. Repeats (key held) too."""
    runs = []                   # (level, start, length in µs)
    prev_i, prev_v = 0, rem[0] if rem else 1
    for i, v in edges(rem):
        runs.append((prev_v, prev_i, (i - prev_i) * 1e6 / freq))
        prev_i, prev_v = i, v
    near = lambda x, ref: abs(x - ref) < ref * 0.3   # noqa: E731
    names = {code: key for key, code in ir_codes.COMMANDS.items()}
    out = []
    k = 0
    while k + 1 < len(runs):
        lvl, start, dur = runs[k]
        if lvl == 0 and near(dur, 9000) and runs[k + 1][0] == 1:
            space = runs[k + 1][2]
            at = start * 1e3 / freq
            if near(space, 2250):
                out.append({"at_ms": at, "repeat": True})
                k += 2
                continue
            if near(space, 4500) and k + 2 + 64 <= len(runs):
                bits = []
                for b in range(32):
                    mark, sp = runs[k + 2 + 2 * b], runs[k + 3 + 2 * b]
                    if not (mark[0] == 0 and near(mark[2], 560)):
                        break
                    bits.append(1 if sp[2] > 1100 else 0)
                if len(bits) == 32:
                    by = to_bytes(bits, msb_first=False)
                    ok = by[0] ^ by[1] == 0xFF and by[2] ^ by[3] == 0xFF
                    key = names.get(by[2]) if by[0] == ir_codes.ADDRESS and ok else None
                    out.append({"at_ms": at, "repeat": False, "bytes": by, "valid": ok, "key": key})
                    k += 66
                    continue
        k += 1
    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def hexs(bs):
    return " ".join(f"{b:02X}" for b in bs)


def report(path, edge="rising", show_bits=False, limit=40):
    freq, sig = load_lac(path)
    n = max((len(s) for s in sig.values()), default=0)
    print(f"{path}: {n} samples at {freq / 1e6:g} MHz ({n * 1e3 / freq:.1f} ms). Signals: {', '.join(sorted(sig))}")

    if all(s in sig for s in ("CS", "CLK", "DATA")):
        cs, clk, data = sig["CS"], sig["CLK"], sig["DATA"]
        high, low, count = clock_stats(clk, cs, freq)
        print("\n## Display")
        print(f"Idle: /CS={cs[0]} CLK={clk[0]} DATA={data[0]}")
        if count:
            period = (high or 0) + (low or 0)
            print(f"Clock: high {high:.2f} µs, low {low:.2f} µs (~{1e3 / period:.0f} kHz). "
                  f"Captured at {freq / 1e6:g} MHz, a clock below ~{freq / 4e6:g} MHz reads reliably.")
        frs = frames(cs, clk, data, edge)
        sizes = {}
        for fr in frs:
            sizes[len(fr["bits"])] = sizes.get(len(fr["bits"]), 0) + 1
        print(f"Frames (/CS at 0): {len(frs)}. Bits per frame: "
              + ", ".join(f"{b} bits × {c}" for b, c in sorted(sizes.items())))
        gs = groups(frs, freq)
        if len(gs) > 1:
            gaps = [(gs[i + 1][0]["start"] - gs[i][0]["start"]) * 1e3 / freq for i in range(len(gs) - 1)]
            print(f"Groups (silence > {GROUP_GAP_US} µs): {len(gs)}. Interval between groups: "
                  f"min {min(gaps):.1f} ms, median {sorted(gaps)[len(gaps) // 2]:.1f} ms, max {max(gaps):.1f} ms")
        shown = 0
        for gi, g in enumerate(gs):
            if shown >= limit:
                print(f"... ({len(gs) - gi} more groups; use --limit)")
                break
            print(f"\nGroup {gi + 1} at {g[0]['start'] * 1e3 / freq:.3f} ms, {len(g)} frames")
            for fr in g:
                b = fr["bits"]
                line = f"  {len(b):3d} bits  MSB: {hexs(to_bytes(b, True)):<24}  LSB: {hexs(to_bytes(b, False))}"
                if len(b) % 8:
                    line += f"  (+{len(b) % 8} loose bits)"
                print(line)
                if show_bits:
                    print("           " + "".join(map(str, b)))
            shown += 1
        if "RST" in sig:
            rst = pulses_low(sig["RST"], freq)
            print(f"\n/RST at 0: {len(rst)} times" + "".join(f"\n  at {t:.3f} ms for {d:.1f} µs" for t, d in rst[:10]))

    if "REM" in sig:
        print("\n## Remote (NEC)")
        keys = nec(sig["REM"], freq)
        if not keys:
            print("No NEC code.")
        for k in keys:
            if k["repeat"]:
                print(f"  {k['at_ms']:9.1f} ms  repeat (key held)")
            else:
                ok = "" if k["valid"] else "  (inverse bytes don't match)"
                print(f"  {k['at_ms']:9.1f} ms  {hexs(k['bytes'])}  {k['key'] or '?'}{ok}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("capture")
    ap.add_argument("--edge", choices=("rising", "falling"), default="rising",
                    help="clock edge the data is read on (default: rising)")
    ap.add_argument("--bits", action="store_true", help="show each frame's raw bits")
    ap.add_argument("--limit", type=int, default=40, help="how many groups to show (default 40)")
    a = ap.parse_args()
    report(a.capture, a.edge, a.bits, a.limit)


if __name__ == "__main__":
    main()
