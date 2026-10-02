"""Scripted-input generator with a Start press overlay (netplay #1029).

Drop-in for gen_inputs.py (same --ticks/--seed/--out), used through
skip_pair.py: it writes the normal seeded session and then ORs the Start
button (0x1000) into pad 0 for the tick ranges the environment names.

  PIKMIN_SKIPGEN_START="<seed>:<first>-<last>[+<first>-<last>...][,<seed>:...]"

Ranges are inclusive scripted-record indexes (a record index is the peer's
own input frame; with the harness delay it reaches the sim a couple of ticks
later). Unset: identical to gen_inputs.py.
"""

import os
import struct
import sys
from pathlib import Path

import gen_inputs as gi

START = 0x1000


def parse_env(seed):
    out = []
    for item in os.environ.get("PIKMIN_SKIPGEN_START", "").split(","):
        item = item.strip()
        if not item:
            continue
        s, _, rngs = item.partition(":")
        if int(s) != seed:
            continue
        for rng in rngs.split("+"):
            a, _, b = rng.partition("-")
            out.append((int(a), int(b or a)))
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    rc = gi.main(argv)
    if rc != 0:
        return rc
    seed = int(argv[argv.index("--seed") + 1])
    path = Path(argv[argv.index("--out") + 1])
    ranges = parse_env(seed)
    if not ranges:
        return 0
    data = bytearray(path.read_bytes())
    rec = gi.RECORD_SIZE_V2
    n = (len(data) - gi.PKNI_HEADER_SIZE) // rec if hasattr(gi, "PKNI_HEADER_SIZE") else (len(data) - 10) // rec
    for first, last in ranges:
        for t in range(first, min(last, n - 1) + 1):
            off = 10 + t * rec
            (b,) = struct.unpack_from("<H", data, off)
            struct.pack_into("<H", data, off, b | START)
    path.write_bytes(bytes(data))
    print(f"gen_skip_inputs: seed {seed} Start on {ranges}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
