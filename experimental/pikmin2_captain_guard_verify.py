"""Additive fail-closed captain-safety adoption verifier for guarded fixtures (#731).

Given a fixture C++ source and a native run log, asserts the #632 contract:

- the guard header (`scripts/p2_fixture_captain_guard.h`) is included, or a tested
  inline equivalent defines the same predicate (`orimaDead || deadState ||
  !isfinite(hp) || hp <= 1.0`) plus the `p2_fixture_require_captain` exit path
  (BLOCKED marker, exit 86);
- `p2_fixture_require_captain(...)` is called (guard runs before observation);
- any run containing `P2_FIXTURE_CAPTAIN_DOWN ... outcome=BLOCKED` exits non-zero
  with no `PASS ...` line;
- a `protected_observation` policy never yields an `attacks_receivers` PASS;
- `fixture_adoption.captain_safety` maps carry policy plus evidence keys present in
  the hashed evidence map.

Fail-closed: missing inputs, unparseable HP, or unknown marker grammar raise before
any verdict. The tool writes nothing except its report. No engine, no gameplay.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

ISSUE = 731
GUARD_HEADER = "p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
REQUIRE_CALL = "p2_fixture_require_captain("
DOWN_PREDICATE = "p2_fixture_captain_down("
BLOCKED_EXIT = 86

DOWN_RE = re.compile(
    r"P2_FIXTURE_CAPTAIN_DOWN\s+tick=(\d+)\s+hp=([^\s]+)\s+"
    r"orima_dead=(\d)\s+dead_state=(\d)\s+outcome=BLOCKED")
PASS_RE = re.compile(r"^PASS\s+(\S+)", re.MULTILINE)


class VerifyGapError(ValueError):
    """Inputs are missing or the grammar drifted; fail closed, never guess."""


def _need_text(value, label):
    if not isinstance(value, str):
        raise VerifyGapError("%s must be text" % label)
    return value


def source_checks(source):
    """Static adoption checks over the fixture source. Returns problem strings."""
    text = _need_text(source, "fixture source")
    problems = []
    has_include = GUARD_HEADER in text
    has_inline_down = (DOWN_PREDICATE in text and "isfinite" in text
                       and "<= 1.0" in text)
    has_inline_require = (REQUIRE_CALL in text and "_Exit(86)" in text)
    if not has_include and not (has_inline_down and has_inline_require):
        problems.append("guard header not included and no tested inline equivalent")
    elif not has_include:
        problems.append("tested inline equivalent used instead of the header (labelled)")
    if REQUIRE_CALL not in text:
        problems.append("missing p2_fixture_require_captain call (guard never runs)")
    return problems


def _parse_hp(raw):
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise VerifyGapError("unparseable hp field %r (absent/NaN handled as down)" % (raw,))


def parse_captain_down(line):
    """Parse one CAPTAIN_DOWN marker, or return None when not a marker line."""
    if "P2_FIXTURE_CAPTAIN_DOWN" not in line:
        return None
    match = DOWN_RE.search(line)
    if not match:
        raise VerifyGapError("unknown CAPTAIN_DOWN marker grammar: %r" % line[:160])
    tick, hp_raw, orima, dead = match.groups()
    hp = _parse_hp(hp_raw)
    down = bool(int(orima)) or bool(int(dead)) or not math.isfinite(hp) or hp <= 1.0
    return {"tick": int(tick), "hp": hp, "orima_dead": bool(int(orima)),
            "dead_state": bool(int(dead)), "down": down}


def log_checks(log, exit_code):
    """Dynamic checks over the run log + process exit. Returns problem strings."""
    text = _need_text(log, "run log")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        raise VerifyGapError("exit code must be an int")
    problems = []
    downs = []
    for line in text.splitlines():
        parsed = parse_captain_down(line)
        if parsed is not None:
            downs.append(parsed)
    passes = PASS_RE.findall(text)
    if downs:
        if exit_code == 0:
            problems.append("CAPTAIN_DOWN run exited 0 (must exit non-zero)")
        if passes:
            problems.append("CAPTAIN_DOWN run still claims PASS: %s" % sorted(set(passes)))
        for event in downs:
            if not event["down"]:
                problems.append("CAPTAIN_DOWN marker with live readings at tick %d"
                                % event["tick"])
    return {"problems": problems, "captain_down_events": downs, "passes": passes}


def verify_adoption(adoption, evidence, gates=None):
    """Check a fixture_adoption.captain_safety map against evidence + gates."""
    if not isinstance(adoption, dict):
        raise VerifyGapError("adoption map must be a dict")
    if not isinstance(evidence, dict):
        raise VerifyGapError("evidence map must be a dict")
    problems = []
    policy = adoption.get("policy")
    if policy not in ("unprotected", "protected_observation"):
        problems.append("unknown captain-safety policy: %r" % (policy,))
    refs = adoption.get("evidence")
    if not isinstance(refs, list) or not refs:
        problems.append("captain-safety evidence refs missing")
    else:
        for key in refs:
            if key not in evidence:
                problems.append("evidence key absent from hashed map: %r" % (key,))
    if policy == "protected_observation" and isinstance(gates, dict):
        attacks = gates.get("attacks_receivers") or {}
        if attacks.get("status") == "PASS":
            problems.append("protected observation cannot yield attacks_receivers PASS")
    return problems


def verify_fixture(source, log, exit_code, adoption=None, evidence=None, gates=None):
    """Full verdict. Returns {"ok": bool, "problems": [...], ...}."""
    problems = source_checks(source)
    logged = log_checks(log, exit_code)
    problems.extend(logged["problems"])
    if adoption is not None or evidence is not None:
        problems.extend(verify_adoption(adoption or {}, evidence or {}, gates))
    return {"ok": not problems, "problems": problems,
            "passes": logged["passes"],
            "captain_down_events": logged["captain_down_events"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--adoption", type=Path, default=None)
    parser.add_argument("--evidence", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    for label, path in (("source", args.source), ("log", args.log)):
        if not path.is_file():
            print("VERIFY_GAP missing %s file: %s" % (label, path))
            return 4
    try:
        adoption = json.loads(args.adoption.read_text(encoding="utf-8")) \
            if args.adoption else None
        evidence = json.loads(args.evidence.read_text(encoding="utf-8")) \
            if args.evidence else None
        verdict = verify_fixture(args.source.read_text(encoding="utf-8"),
                                 args.log.read_text(encoding="utf-8"),
                                 args.exit_code, adoption, evidence)
    except VerifyGapError as exc:
        print("VERIFY_GAP %s" % exc)
        return 4
    payload = json.dumps(verdict, indent=2, sort_keys=True) + "\n"
    if args.out is None:
        print(payload, end="")
    else:
        args.out.write_text(payload, encoding="utf-8")
    print("guard-verdict ok=%s problems=%d" % (verdict["ok"], len(verdict["problems"])))
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())