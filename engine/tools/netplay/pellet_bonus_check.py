"""Assert the seed credit in a native.log written under PIKMIN_TEST_ONLY_PELLET_BONUS (issue #1034).

Reads the "[pellet] onion=.. kind=pellet type=.. seeds=.. matching=.. match_seeds=.. nonmatch_seeds=.."
lines and fails unless, for every delivery:
  - matching == (onion == type), and
  - seeds == match_seeds when matching, else nonmatch_seeds, and
  - for number pellets the (match, nonmatch) pair is the vanilla one for its size (2/1, 5/3, 10/6, 20/10).
With --expect N it also requires at least N deliveries. Prints a per-(onion, pellet colour, size) table.

Usage: py -3.12 tools/netplay/pellet_bonus_check.py native.log [more.log ...] [--expect N]
"""

import re
import sys

LINE = re.compile(
    r"\[pellet\] onion=(\d+) kind=pellet type=(\d+) size=(\w+) seeds=(-?\d+) matching=(\d+) "
    r"pcolor=(-?\d+) match_seeds=(-?\d+) nonmatch_seeds=(-?\d+)"
)
VANILLA = {"10": (2, 1), "50": (5, 3), "01": (10, 6), "02": (20, 10)}  # model id is stored reversed: pb01 -> "10bp"
NAMES = ("blue", "red", "yellow")


def main(argv):
    expect = 0
    paths = []
    it = iter(argv)
    for a in it:
        if a == "--expect":
            expect = int(next(it))
        else:
            paths.append(a)
    if not paths:
        print(__doc__)
        return 2
    bad = []
    rows = {}
    total = 0
    for path in paths:
        with open(path, errors="replace") as f:
            for n, line in enumerate(f, 1):
                m = LINE.search(line)
                if not m:
                    continue
                onion, ptype, size, seeds, matching, pcolor, mseeds, nseeds = m.groups()
                onion, ptype, seeds, matching, pcolor, mseeds, nseeds = map(int, (onion, ptype, seeds, matching, pcolor, mseeds, nseeds))
                total += 1
                want_match = int(onion == ptype)
                want_seeds = mseeds if want_match else nseeds
                if matching != want_match or seeds != want_seeds:
                    bad.append(f"{path}:{n}: onion={onion} type={ptype} matching={matching} (want {want_match}) seeds={seeds} (want {want_seeds})")
                number = size[:2] in VANILLA and size[2:] in ("rp", "bp", "yp") and pcolor == ptype
                if number and (mseeds, nseeds) != VANILLA[size[:2]]:
                    bad.append(f"{path}:{n}: {size} config seeds {mseeds}/{nseeds}, vanilla {VANILLA[size[:2]]}")
                key = (NAMES[onion] if 0 <= onion < 3 else onion, NAMES[pcolor] if 0 <= pcolor < 3 else pcolor, size)
                rows.setdefault(key, []).append(seeds)
    for key in sorted(rows, key=str):
        print(f"onion={key[0]:<6} pellet={key[1]:<6} size={key[2]:<5} seeds={sorted(set(rows[key]))} n={len(rows[key])}")
    print(f"pellet_bonus_check: {total} deliveries, {len(bad)} bad")
    for b in bad:
        print("BAD", b)
    if total < expect:
        print(f"pellet_bonus_check: FAIL: {total} deliveries < expected {expect}")
        return 1
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
