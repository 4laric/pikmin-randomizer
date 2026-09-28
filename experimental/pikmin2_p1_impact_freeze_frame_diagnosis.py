"""P1 impact post-PARK freeze-frame attribution (diagnosis, issue #797).

Reads a gen-4-style native run log (path argument) and attributes the
observed post-PARK freeze to EITHER the observer throttle OR an engine-owner
cause, with exact file:symbol pins and owner routing. Consumes the blocked
#565 evidence read-only; never an engine unblock; no runtime claim beyond
the packet.

Attribution logic (fail-closed):
- The #649 guarded fixture (`native/tools/p2_challenge_guarded_boot_fixture.cpp`)
  increments `observed` once per idle tick past its pre-increment gates
  (:68-72, all of which emit `P2_CHALLENGE_GATE_DIAG` via :62-65 on the
  throttled `frames%300` / 48-mark budget). `P2_CHALLENGE_SQUAD` fires at
  observed==60 (:86); BOOT at >=120; PASS at >=180.
- PARK (`P2_CHALLENGE_PARK`) + `P2_CHALLENGE_PARK_ALIVE` (:82-85) prove
  `observed` reached 1. If SQUAD never fires:
  - GATE_DIAG present -> a named pre-increment gate held `observed` down;
    verdict THROTTLE-ARTIFACT only if the 300-frame/48-mark budget can
    explain the silence, else ENGINE-OWNER (gate never clears).
  - GATE_DIAG absent over a full bounded window -> ENGINE-OWNER loop freeze:
    a persistent pre-increment stall MUST emit within ~300 frames at rate, so
    zero markers means the idle loop itself stopped advancing (hang/crawl),
    not a throttle artifact.
- CAPTAIN_DOWN or FAIL rows -> BLOCKED/REFUSED (safety / fixture abort), never
  an attribution.
- Missing PARK, empty input, or unreadable path -> REFUSED (malformed/missing).

Owner routing: ENGINE-OWNER -> #649/engine owner (deadlock/loop-freeze
investigation) with a longer-run prescription (unthrottled gate diagnostics
to exclude extreme slowness); THROTTLE -> longer run with unthrottled
diagnostics; either -> #52 follow-on scope 1 per the brief. Gate verdicts
are tooling-only (all six gates UNTESTED); captain safety #632 labelling
applies to any observation handling (this tool only reads logs).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "p1-impact-freeze-frame-diagnosis-v1"
PARK_RE = re.compile(r"^P2_CHALLENGE_PARK nx=(-?[\d.]+) ny=(-?[\d.]+) nz=(-?[\d.]+)$")
PARK_ALIVE_RE = re.compile(r"^P2_CHALLENGE_PARK_ALIVE pikis=(\d+)$")
SQUAD_RE = re.compile(r"^P2_CHALLENGE_SQUAD pikis=(\d+)$")
BOOT_RE = re.compile(r"^P2_CHALLENGE_BOOT level=(\d+) slot=(\w+)$")
PASS_RE = re.compile(r"^PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive$")
GATE_DIAG_RE = re.compile(r"^P2_CHALLENGE_GATE_DIAG gate=(\w+) observed=(\d+) alive=(-?\d+) frames=(\d+)$")
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
FAIL_MARK = "FAIL "

# Read-only pins (native fixture, consumed, never edited).
PIN_GATE_DIAG = "native/tools/p2_challenge_guarded_boot_fixture.cpp:62-65"
PIN_GATES = "native/tools/p2_challenge_guarded_boot_fixture.cpp:68-72"
PIN_PARK = "native/tools/p2_challenge_guarded_boot_fixture.cpp:82-85"
PIN_SQUAD = "native/tools/p2_challenge_guarded_boot_fixture.cpp:86"


class DiagnosisError(ValueError):
    """Refusal: malformed input, missing input, or safety abort."""


def read_log(path):
    """Read a run log as text (fail-closed on missing/unreadable)."""
    p = Path(path)
    if not p.is_file():
        raise DiagnosisError("missing input log: " + str(path))
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise DiagnosisError("unreadable input log: " + str(error)) from error
    if not text.strip():
        raise DiagnosisError("missing input: empty log")
    return text


def parse(text):
    """Split a run log into marker facts."""
    if not isinstance(text, str) or not text.strip():
        raise DiagnosisError("missing input: empty log")
    parks, alive, squads, boots, passes, diags = [], [], [], [], [], []
    for raw in text.splitlines():
        line = raw.strip()
        m = PARK_RE.match(line)
        if m:
            parks.append(tuple(map(float, m.groups())))
        m = PARK_ALIVE_RE.match(line)
        if m:
            alive.append(int(m.group(1)))
        m = SQUAD_RE.match(line)
        if m:
            squads.append(int(m.group(1)))
        m = BOOT_RE.match(line)
        if m:
            boots.append((int(m.group(1)), m.group(2)))
        if PASS_RE.match(line):
            passes.append(line)
        m = GATE_DIAG_RE.match(line)
        if m:
            diags.append({"gate": m.group(1), "observed": int(m.group(2)),
                          "alive": int(m.group(3)), "frames": int(m.group(4))})
    return {
        "parks": parks, "alive": alive, "squads": squads, "boots": boots,
        "passes": passes, "diags": diags,
        "captain_down": CAPTAIN_DOWN in text,
        "failed": any(l.strip().startswith(FAIL_MARK) for l in text.splitlines()),
    }


def attribute(parsed):
    """Attribution verdict with pins and owner routing (never a fix)."""
    if parsed["captain_down"]:
        return {"verdict": "blocked", "cause": "captain-safety trip",
                "detail": "P2_FIXTURE_CAPTAIN_DOWN present; observation interrupted, never an attribution.",
                "route": "captain-safety #632 owner (parked captain, guard); no PASS claim.",
                "pins": []}
    if parsed["failed"]:
        return {"verdict": "refused", "cause": "fixture abort",
                "detail": "FAIL marker present; the run aborted before any attribution.",
                "route": "fixture owner (abort signature); no attribution.",
                "pins": []}
    if not parsed["parks"] or not parsed["alive"]:
        return {"verdict": "refused", "cause": "malformed log",
                "detail": "PARK/PARK_ALIVE baseline absent; cannot separate never-spawned from frozen.",
                "route": "none (refused).",
                "pins": [PIN_PARK]}
    if parsed["passes"]:
        return {"verdict": "passing", "cause": "boot observed",
                "detail": "PASS marker present; no freeze to attribute.",
                "route": "none (passing).",
                "pins": []}
    if parsed["squads"] or parsed["boots"]:
        return {"verdict": "unattributable", "cause": "partial progress",
                "detail": "SQUAD/BOOT fired but no PASS; not the post-PARK silence signature.",
                "route": "lane owner (partial-run triage); no throttle/engine claim.",
                "pins": [PIN_PARK, PIN_SQUAD]}
    # Post-PARK silence: PARK_ALIVE fired, SQUAD/BOOT/PASS all absent.
    baseline = parsed["alive"][0]
    if parsed["diags"]:
        gates = sorted({d["gate"] for d in parsed["diags"]})
        return {"verdict": "throttle-or-gate", "cause": "named pre-increment gate",
                "detail": ("observed stuck with GATE_DIAG from gate(s) %s; "
                           "the frames%%300/48-mark budget bounds this signal - a "
                           "longer unthrottled run decides throttle artifact vs a "
                           "gate that never clears. PARK baseline pikis=%d.")
                % (",".join(gates), baseline),
                "route": "longer-run prescription (unthrottled gate diagnostics); then #649/engine owner if the gate never clears; #52 follow-on scope 1.",
                "pins": [PIN_GATE_DIAG, PIN_GATES, PIN_PARK, PIN_SQUAD]}
    return {"verdict": "engine-owner", "cause": "idle-loop freeze/crawl",
            "detail": ("observed reached 1 (PARK baseline pikis=%d) but SQUAD "
                       "(observed==60) never fired and zero GATE_DIAG appeared. "
                       "A persistent pre-increment stall must emit within ~300 "
                       "frames at rate under the %s budget, so the silence "
                       "proves the idle loop itself stopped advancing (hang or "
                       "crawl), not a throttle artifact. Squad loss alone cannot "
                       "explain it: a dead squad still advances observed (the "
                       "fixture only gates squad count at PASS).")
            % (baseline, PIN_GATE_DIAG),
            "route": "#649/engine owner (deadlock/loop-freeze investigation) with a longer-run prescription (unthrottled diagnostics to exclude extreme slowness); #52 follow-on scope 1.",
            "pins": [PIN_GATE_DIAG, PIN_GATES, PIN_PARK, PIN_SQUAD]}


def packet(parsed, verdict, log_path=None, log_sha256=None):
    """Hashed attribution packet (tooling evidence, never acceptance)."""
    return {
        "schema": SCHEMA,
        "verdict": verdict["verdict"],
        "cause": verdict["cause"],
        "detail": verdict["detail"],
        "route": verdict["route"],
        "pins": verdict["pins"],
        "park_baseline_pikis": parsed["alive"][0] if parsed["alive"] else None,
        "gates": "UNTESTED",
        "log": {"path": str(log_path) if log_path else None, "sha256": log_sha256},
    }


def main(argv=None):
    """CLI: analyze a run log and print the packet JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="native run log to attribute")
    args = parser.parse_args(argv)
    try:
        text = read_log(args.log)
        parsed = parse(text)
        verdict = attribute(parsed)
    except DiagnosisError as error:
        print(json.dumps({"schema": SCHEMA, "verdict": "refused",
                          "cause": str(error), "gates": "UNTESTED"}))
        return 2
    sha = hashlib.sha256(args.log.read_bytes()).hexdigest()
    print(json.dumps(packet(parsed, verdict, args.log, sha), indent=2))
    return 0 if verdict["verdict"] in ("passing", "engine-owner", "throttle-or-gate") else 1


if __name__ == "__main__":
    raise SystemExit(main())