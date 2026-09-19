"""Damage-throughput technique for the Jigumo63 natural kill (#729).

Derives, from the #689 EAT-receiver review plus the #374 pass1 evidence
(read-only), the stimulus technique that lets a 20-Pikmin squad finish the
500-HP host before EAT attrition empties the squad. No family/shared change:
the receiver works (9 bites / 7 eats observed); the kill fails on throughput.

Core inequality (pass1-measured): a kill needs more than 500/20 = 25 HP drained
per Pikmin lost. Pass1 achieved ~17.1 (120 HP for 7 eaten), so it timed out at
HP floor 380 with 0 DEAD. The technique raises the ratio above break-even via
latched sustained blows instead of ~1-HP throw impacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ISSUE = 729
DOWNSTREAM_LANE = "shard-enemies-4-jigumo63-observer"
DOWNSTREAM_ISSUE = 374

HP_TOTAL = 500.0
SQUAD_SIZE = 20
BREAK_EVEN = HP_TOTAL / SQUAD_SIZE

# Pass1 measured baseline (#374 death-run1/pass1, read-only evidence).
PASS1 = {
    "throws": 117, "hp_start": 500.0, "hp_end": 380.0,
    "bites": 9, "eats": 7, "flicks": 1, "deaths": 0,
    "squad_start": 20, "squad_end": 0,
}

# Source anchors (decomp + port, read-only references).
ANCHORS = (
    {"area": "life", "file": "pc_port/pc_p2_jigumo.cpp", "lines": "88",
     "note": "LIFE = 500.0f (general fp00)"},
    {"area": "receiver", "file": "pc_port/pc_p2_jigumo.cpp", "lines": "489,496-499",
     "note": "ATTACK bite captures nearest live Pikmin inside 200 at key event 2 / frame 26"},
    {"area": "receiver", "file": "pc_port/pc_p2_jigumo.cpp", "lines": "266-273,553-555,601-603",
     "note": "resolveKill + EAT swallow at dive1 key 8 / frame 80 and sattack1 key 10 / frame 115"},
    {"area": "receiver", "file": "src/plugProjectMorimuraU/jigumo.cpp", "lines": "325",
     "note": "damageCallBack part rule (port accepts damage while alive)"},
    {"area": "flick", "file": "pc_port/pc_p2_jigumo.cpp", "lines": "100-102,189-199,562-569",
     "note": "flick when Pikmin inside radius 25; shake clears inside 100 at key event 2"},
    {"area": "death", "file": "pc_port/pc_p2_jigumo.cpp", "lines": "425",
     "note": "Dead entered when mHealth <= 0"},
)


class TechniqueGapError(ValueError):
    """Inputs are malformed or the run cannot beat break-even; fail closed."""


def throughput_ratio(hp_drained, pikmin_lost):
    """HP drained per Pikmin lost; must exceed BREAK_EVEN for a kill."""
    if not isinstance(hp_drained, (int, float)) or not isinstance(pikmin_lost, int):
        raise TechniqueGapError("hp_drained must be numeric and pikmin_lost an int")
    if hp_drained < 0 or pikmin_lost <= 0:
        raise TechniqueGapError("need positive drain and at least one lost Pikmin")
    return float(hp_drained) / pikmin_lost


def meets_break_even(hp_drained, pikmin_lost):
    """True only when the observed ratio strictly beats 25 HP per Pikmin."""
    return throughput_ratio(hp_drained, pikmin_lost) > BREAK_EVEN


def pass1_ratio():
    """The measured pass1 ratio (below break-even by construction of the evidence)."""
    drained = PASS1["hp_start"] - PASS1["hp_end"]
    return throughput_ratio(drained, PASS1["eats"])


def check_preconditions(run):
    """Check a run-stats dict against the technique gates; return problems."""
    if not isinstance(run, dict):
        raise TechniqueGapError("run stats must be a dict")
    problems = []
    for key in ("hp_drained", "pikmin_lost", "latched_attackers",
                "captain_down", "injected"):
        if key not in run:
            problems.append("missing run stat: %s" % key)
    if problems:
        return problems
    if run["captain_down"]:
        problems.append("captain-down taints every observation (guard 86)")
    if run["injected"]:
        problems.append("injected state cannot close a natural gate")
    if not run["latched_attackers"]:
        problems.append("no latched attackers: throw impacts alone measured ~1 HP each")
    try:
        if not meets_break_even(run["hp_drained"], run["pikmin_lost"]):
            problems.append("ratio %.1f <= break-even %.1f"
                            % (throughput_ratio(run["hp_drained"], run["pikmin_lost"]),
                               BREAK_EVEN))
    except TechniqueGapError as exc:
        problems.append(str(exc))
    return problems


def validation_plan():
    """Executable gates for the #374 observer (same fixture + arena)."""
    return [
        "stage the identical fixture and arena with latch-first stimulus: thrown Pikmin "
        "re-thrown to latch inside the 200-unit sweep instead of scattering",
        "keep non-attacking Pikmin out of the sweep to bound the bite rate below "
        "pass1 9-per-117-throws; re-latch promptly after each flick",
        "assert natural DEAD + corpse/disappearance with zero captain-down and zero injections",
        "assert hp_drained / pikmin_lost strictly above 25.0 from the run log",
        "fail closed on any violated gate; do not relabel UNTESTED rows",
    ]


def packet():
    """Machine-readable technique packet for the downstream consumer."""
    return {
        "schema": 1, "issue": ISSUE, "downstream_lane": DOWNSTREAM_LANE,
        "downstream_issue": DOWNSTREAM_ISSUE,
        "break_even_hp_per_pikmin": BREAK_EVEN,
        "pass1_ratio": pass1_ratio(),
        "anchors": [dict(row) for row in ANCHORS],
        "technique": ["latch-first sustained blows over throw impacts",
                      "EAT-rate bound via sweep discipline",
                      "flick/re-latch discipline"],
        "family_change": "none required (per #689: no shared edit needed)",
        "validation_plan": validation_plan(),
        "gates": "all six UNTESTED by this technique slice",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    payload = json.dumps(packet(), indent=2, sort_keys=True) + "\n"
    if args.out is None:
        print(payload, end="")
    else:
        args.out.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())