"""Challenge persistence hookup observer (#713, downstream #561).

Validates run logs from the native persistence fixture
(native/tools/p2_challenge_persistence_fixture.cpp) against the #708
key/marker contract, consumed read-only and never duplicated here. The #708
adapter owns the 30-stage retail pins; this module owns the run-log grammar
plus the key/score twins used to cross-check the native emission.

Marker grammar (exact lines, probe order):
  P2_CHALLENGE_{SAVE_KEY,LOAD_KEY,CLEAR,HIGHSCORE,UNLOCK,RECEIPT_DEDUP,REENTRY}
  stage=<cave_id>
Key scheme mirror (verified identical to #708 by test vectors):
  p2_challenge_{save,load,clear,highscore,unlock}_{cave_id}
Score mirror (verified identical to the #651 host-mode precedent):
  score = pokos*10 + floor(timeLeftSeconds) + population*10

Engine-free, hermetic, fail-closed. No runtime, no ADMIT.
"""
from __future__ import annotations

import math
import re

SCHEMA = "p2-challenge-persistence-hookup-v1"
KEY_PREFIX = "p2_challenge"
KEY_FIELDS = ("save", "load", "clear", "highscore", "unlock")
PROBE_ARTIFACTS = ("challenge_save_key", "challenge_load_key", "clear_flag",
                   "highscore", "unlock", "receipt_dedup", "reentry")
STEMS = {
    "challenge_save_key": "SAVE_KEY",
    "challenge_load_key": "LOAD_KEY",
    "clear_flag": "CLEAR",
    "highscore": "HIGHSCORE",
    "unlock": "UNLOCK",
    "receipt_dedup": "RECEIPT_DEDUP",
    "reentry": "REENTRY",
}
CAVE_ID_PATTERN = re.compile(r"[A-Za-z0-9_]+")
MARKER_RE = re.compile(r"^P2_CHALLENGE_([A-Z_]+) stage=([A-Za-z0-9_]+)$")
PASS_RE = re.compile(r"^PASS P2_CHALLENGE_PERSISTENCE_RUN markers=7$")
REFUSE_RE = re.compile(r"^P2_CHALLENGE_PERSISTENCE_REFUSED reason=(\S+)$")
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "mHealth=", "Transport(")


class HookupError(ValueError):
    """Refusal: malformed input, unknown stage/artifact, or contract drift."""


def _check_cave_id(cave_id):
    if not isinstance(cave_id, str) or not CAVE_ID_PATTERN.fullmatch(cave_id):
        raise HookupError("Unsafe cave_id for key derivation: %r" % (cave_id,))


def stage_keys(cave_id):
    """Persistence keys for one stage (mirrors the #708 formula verbatim)."""
    _check_cave_id(cave_id)
    return {field: "%s_%s_%s" % (KEY_PREFIX, field, cave_id)
            for field in KEY_FIELDS}


def marker_for(artifact, cave_id):
    """Exact run-log marker line for one probe artifact."""
    _check_cave_id(cave_id)
    if artifact not in STEMS:
        raise HookupError("Unknown probe artifact: %r" % (artifact,))
    return "P2_CHALLENGE_%s stage=%s" % (STEMS[artifact], cave_id)


def compute_score(pokos, time_left_seconds, population):
    """Result-screen score mirror (host-mode precedent, read-only)."""
    for value in (pokos, population):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise HookupError("Score inputs must be non-negative ints")
    if not isinstance(time_left_seconds, (int, float)) or isinstance(time_left_seconds, bool):
        raise HookupError("Score time must be numeric")
    if not math.isfinite(time_left_seconds) or time_left_seconds < 0:
        raise HookupError("Score time must be finite and non-negative")
    return pokos * 10 + int(time_left_seconds) + population * 10


def parse(text):
    """Split a run log into markers, PASS/REFUSED lines, and health flags."""
    markers, refusals, passes = [], [], []
    for line in text.splitlines():
        match = MARKER_RE.match(line.strip())
        if match:
            markers.append((match.group(1), match.group(2)))
        if REFUSE_RE.match(line.strip()):
            refusals.append(line.strip())
        if PASS_RE.match(line.strip()):
            passes.append(line.strip())
    return {
        "markers": markers,
        "refusals": refusals,
        "passes": passes,
        "captain_down": CAPTAIN_DOWN in text,
        "injected": [t for t in INJECTED_TOKENS if t in text],
    }


def check_run(parsed, cave_id):
    """All 7 probe markers for one stage, PASS present, nothing hostile."""
    _check_cave_id(cave_id)
    if parsed["captain_down"]:
        return False, "captain-down interruption present"
    if parsed["injected"]:
        return False, "injection markers present: %s" % ",".join(parsed["injected"])
    if not parsed["passes"]:
        return False, "run PASS marker absent"
    if parsed["refusals"]:
        return False, "fixture refusals present: %s" % parsed["refusals"][:2]
    missing = []
    for artifact in PROBE_ARTIFACTS:
        stem = STEMS[artifact]
        if not any(s == stem and c == cave_id for s, c in parsed["markers"]):
            missing.append(artifact)
    if missing:
        return False, "missing probe markers: %s" % ",".join(missing)
    return True, "run PASS with exact 7/7 probe markers"


def gate_status(text, cave_id):
    """Tooling gate grades for a fixture run log (never a gameplay claim)."""
    _check_cave_id(cave_id)
    parsed = parse(text)
    run_ok, run_why = check_run(parsed, cave_id)
    return {
        "run_markers": (run_ok, run_why),
        "captain_guard": (not parsed["captain_down"],
                          "no CAPTAIN_DOWN" if not parsed["captain_down"] else "CAPTAIN_DOWN fired"),
        "no_inject": (not parsed["injected"],
                      "no injection markers" if not parsed["injected"] else "injection present"),
    }
