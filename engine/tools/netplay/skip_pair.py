"""run_pair.py with a Start press overlay on the scripted inputs (#1029).

  skip_pair.py [--host-start A-B[+C-D]] [--join-start A-B[+C-D]] <run_pair.py arguments>

Presses Start (inclusive scripted-record range) on the host's and/or the
joiner's scripted pad 0, then runs run_pair.py unchanged. The default seeds
(101 host, 202 joiner) are the run_pair defaults; --seed-a/--seed-b still
work and are honoured.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_pair  # noqa: E402


def main():
    argv = sys.argv[1:]
    take = {}
    rest = []
    i = 0
    while i < len(argv):
        if argv[i] in ("--host-start", "--join-start") and i + 1 < len(argv):
            take[argv[i]] = argv[i + 1]
            i += 2
        else:
            rest.append(argv[i])
            i += 1

    def opt(flag, default):
        return int(rest[rest.index(flag) + 1]) if flag in rest else default

    seed_a, seed_b = opt("--seed-a", 101), opt("--seed-b", 202)
    items = []
    if "--host-start" in take:
        items.append(f"{seed_a}:{take['--host-start']}")
    if "--join-start" in take:
        items.append(f"{seed_b}:{take['--join-start']}")
    os.environ["PIKMIN_SKIPGEN_START"] = ",".join(items)
    run_pair.GEN = HERE / "gen_skip_inputs.py"
    sys.argv = [sys.argv[0]] + rest
    return run_pair.main()


if __name__ == "__main__":
    raise SystemExit(main())
