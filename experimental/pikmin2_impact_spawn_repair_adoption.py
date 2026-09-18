"""Impact spawn-repair adoption staging/verification adapter (#786).

Verifies headed rerun logs for the receipt-parseable marker grammar of the
repaired challenge boot fixture (PARK -> SQUAD -> BOOT -> PASS) plus the
captain-safety #632 contract. Fail-closed: non-text input, a captain-down
interruption, or a missing PASS marker never yields a PASS verdict.

Fail-closed: the adapter claims nothing about gameplay; gates are claimed
solely on observed markers. The #565 consumer owns the acceptance verdict.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ISSUE = 786
CONSUMER_ISSUE = 565
GUARD_PATH = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

WINDOW_RE = re.compile(
    r"SDL2 Window & OpenGL Context initialized successfully \(960x540\)")
CENTERED_RE = re.compile(
    r"Experimental preview window set to 960x540 windowed and centered")
PARK_ALIVE_RE = re.compile(r"P2_CHALLENGE_PARK_ALIVE\s+pikis=(\d+)")
SQUAD_RE = re.compile(r"P2_CHALLENGE_SQUAD\s+pikis=(\d+)")
BOOT_RE = re.compile(r"P2_CHALLENGE_BOOT\s+level=(\d+)\s+slot=(\S+)")
DOWN_RE = re.compile(
    r"P2_FIXTURE_CAPTAIN_DOWN\s+tick=(\d+)\s+hp=([^\s]+)\s+"
    r"orima_dead=(\d)\s+dead_state=(\d)\s+outcome=BLOCKED")
PASS_RE = re.compile(r"^PASS\s+P2_CHALLENGE_GUARDED_BOOT\b", re.MULTILINE)


class AdoptionGapError(ValueError):
    """A run log cannot support the adoption verdict; fail closed."""


def verify_run_log(log_text):
    """Map a headed run log to the PARK->SQUAD->BOOT->PASS verdict."""
    if not isinstance(log_text, str):
        raise AdoptionGapError("run log must be text")
    window = bool(WINDOW_RE.search(log_text))
    centered = bool(CENTERED_RE.search(log_text))
    park = [int(n) for n in PARK_ALIVE_RE.findall(log_text)]
    squads = [int(n) for n in SQUAD_RE.findall(log_text)]
    boots = BOOT_RE.findall(log_text)
    downs = DOWN_RE.findall(log_text)
    passed = bool(PASS_RE.search(log_text))
    squad_ok = any(n > 0 for n in squads)
    overall = (window and centered and bool(park) and squad_ok and
               bool(boots) and passed and not downs)
    return {"window_960x540": window, "window_centered": centered,
            "park_alive_counts": park, "squad_counts": squads,
            "boots": [{"level": int(level), "slot": slot}
                      for level, slot in boots],
            "captain_down": bool(downs), "passed": passed,
            "overall_pass": overall}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-log", required=True)
    args = parser.parse_args(argv)
    try:
        verdict = verify_run_log(
            Path(args.verify_log).read_text(encoding="utf-8", errors="replace"))
    except (AdoptionGapError, OSError) as exc:
        print("refused: %s" % exc)
        return 2
    print(json.dumps(verdict, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())