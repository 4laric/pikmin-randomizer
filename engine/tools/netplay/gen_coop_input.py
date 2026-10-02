"""Segment-scripted PKNI v2 input for one local pad (netplay co-op tests).

Each --seg is TICKS:BUTTONS:SX:SY where BUTTONS is a '+'-joined list of
A B X Z R L (or '-' / 0 for none). Stick (SX, SY) is s8, yaw is held at 0, so
stick maps to world x/z the way gen_directed.py documents. Pad 0 is the local
pad; pads 1-3 are neutral. Start and Y are refused. The last segment repeats
to --ticks. Example: --seg 120:-:0:0 --seg 30:B:0:0 --seg 60:-:0:0
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_inputs as gi  # noqa: E402

BTN = {"A": gi.BTN_A, "B": gi.BTN_B, "X": gi.BTN_X, "Z": gi.TRIG_Z, "R": gi.TRIG_R, "L": gi.TRIG_L}


def parse_seg(text):
    parts = text.split(":")
    if len(parts) != 4:
        raise SystemExit(f"bad --seg {text!r}: want TICKS:BUTTONS:SX:SY")
    ticks = int(parts[0])
    buttons = 0
    if parts[1] not in ("-", "0", ""):
        for name in parts[1].split("+"):
            if name not in BTN:
                raise SystemExit(f"bad button {name!r} (A B X Z R L only)")
            buttons |= BTN[name]
    return ticks, buttons, int(parts[2]), int(parts[3])


def ticks_for(total, segs):
    out = []
    for n, buttons, sx, sy in segs:
        out.extend([(buttons, sx, sy, 0, 0, 0, 0)] * n)
    while len(out) < total:
        out.append(out[-1] if out else (0, 0, 0, 0, 0, 0, 0))
    for t in out[:total]:
        yield (t, None, [0, 0, 0, 0])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ticks", type=int, required=True)
    p.add_argument("--seg", action="append", default=[], metavar="TICKS:BUTTONS:SX:SY")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    segs = [parse_seg(s) for s in a.seg]
    gi.write_file(a.out, ticks_for(a.ticks, segs))
    print(f"gen_coop_input: wrote {a.ticks} ticks ({len(segs)} segments) to {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
