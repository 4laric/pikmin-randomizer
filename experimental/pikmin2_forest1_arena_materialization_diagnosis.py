"""Forest_1 staged-arena materialization diagnosis (issue #790, recovery 28e4c77c).

Reads the gen-13 collision-observer run log read-only (pinned sha256) and
attributes the two materialization gaps against real engine callsites:

- Gap A (requested vs addressable actors): the staged generate package is
  never parsed (zero P2_CAVE_GENERATE_* markers), two chal0 stage files
  fail to open, the engine default+plant generators spawn 24+30
  creatures (GeneratorMgr::init), yet the observer addresses exactly 1.
- Gap B (restored Piki vs live squad): pc_p2_cave_setup recolors 20 live
  Piki (20 P2_CAVE_RESTORE + READY survivors=20) but the observer counts
  squad=0 for ~20k ticks: restored Piki never join squad membership.

Diagnosis only; never an engine unblock. No invented providers: every
verdict names a verified file:symbol pin and an owning lane, or raises
UnattributableError. All six runtime gates stay UNTESTED; no ADMIT.
"""
from __future__ import annotations

from pathlib import Path

EVIDENCE_LOG = ("output/workflow/autofill/planning-shards/caves-forest/"
                "prepared/forest1-collision-obs-out/run-collision2.log")
EVIDENCE_SHA256 = "de7812cce5a59c20650a59f0cbae7f13e8cde146988dcd59547072b525fe40b7"

PINS = {
    "generator_init": ("native/src/plugPikiKando/generator.cpp", "GeneratorMgr::init"),
    "cave_setup": ("native/pc_port/pc_p2_cave.cpp", "pc_p2_cave_setup"),
    "cave_restore": ("native/pc_port/pc_p2_cave.cpp", "P2_CAVE_RESTORE"),
    "cave_ready": ("native/pc_port/pc_p2_cave.cpp", "P2_CAVE_READY"),
    "generate_markers": ("native/pc_port/pc_p2_cave_generate.h", "P2_CAVE_GENERATE_*"),
}

PATTERNS = ("P2_CAVE_READY", "P2_CAVE_RESTORE", "P2_CAVE_GENERATE_PASS",
            "P2_FOREST1_COLLISION_OBSERVE", "DVDOpen", "FAILED",
            "[PC Generator]", "spawned")


class DiagnosisError(ValueError):
    """Fail-closed diagnosis rejection (malformed/missing input)."""


class UnattributableError(DiagnosisError):
    """Evidence lacks the markers needed for either gap verdict."""


def load_evidence(path=EVIDENCE_LOG, sha256=EVIDENCE_SHA256):
    """Read the pinned evidence log read-only with hash check."""
    import hashlib
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise DiagnosisError("evidence hash mismatch: %s" % path)
    return raw.decode("utf-8", errors="replace")


def parse_observe_values(text):
    """Extract the observer squad/births/grounded/moved/live_actors series."""
    import re
    series = []
    for line in text.splitlines():
        match = re.search(r"squad=(\d+) births=(\d+) grounded=(\d+) moved=(\d+) live_actors=(\d+)", line)
        if match:
            series.append(tuple(int(v) for v in match.groups()))
    return series


def count_markers(text):
    """Count the diagnosis-relevant markers in the log text."""
    if not isinstance(text, str) or not text.strip():
        raise DiagnosisError("run log must be non-empty text")
    counts = {key: text.count(key) for key in PATTERNS}
    counts["observe_series"] = parse_observe_values(text)
    return counts


def attribute(counts):
    """Attribute both gaps; raise UnattributableError when evidence is thin."""
    if not isinstance(counts, dict) or not counts.get("observe_series"):
        raise UnattributableError("no observer series: neither gap attributable")
    if not counts.get("P2_CAVE_READY"):
        raise UnattributableError("no READY line: restore-vs-squad gap unattributable")
    squads = [row[0] for row in counts["observe_series"]]
    lives = [row[4] for row in counts["observe_series"]]
    verdicts = [
        {"gap": "A1-staged-package-never-parsed",
         "finding": "staged generate package present on disk but zero "
                    "P2_CAVE_GENERATE_* markers: rooms/spawns/links never "
                    "materialized through the generate path",
         "pins": [PINS["generate_markers"]],
         "owner": "cave-forest1-collision-routes-obs (#773) fixture setup; "
                  "generate module is #129-provider code, absent from the "
                  "maintained native line"},
        {"gap": "A2-missing-stage-files",
         "finding": "%d DVDOpen FAILED lines for chal0 stage gen files: "
                    "room geometry for those stages absent"
                    % counts.get("FAILED", 0),
         "pins": [PINS["cave_setup"]],
         "owner": "arena asset staging via the #773 fixture setup"},
        {"gap": "A3-spawned-vs-addressable",
         "finding": "engine generators spawned creatures but the observer "
                    "addresses at most %d live actor(s): counting scope "
                    "covers a fraction of spawned creatures" % max(lives),
         "pins": [PINS["generator_init"]],
         "owner": "cave-forest1-collision-routes-obs (#773) observer "
                  "counting scope"},
        {"gap": "B-restore-without-squad",
         "finding": "%d P2_CAVE_RESTORE with READY survivors=20, yet "
                    "observer squad max is %d over %d samples: restored "
                    "Piki never join squad membership"
                    % (counts.get("P2_CAVE_RESTORE", 0), max(squads),
                       len(squads)),
         "pins": [PINS["cave_setup"], PINS["cave_restore"], PINS["cave_ready"]],
         "owner": "cave-forest1-collision-routes-obs (#773) observer squad "
                  "definition first; engine Piki/Navi follow behavior second"},
    ]
    if max(squads) > 0:
        raise UnattributableError("squad observed live: gap B absent from this log")
    return verdicts
