"""Challenge persistence ENGINE CALL SITE observer (#718, downstream #561).

Validates run logs from the #718 callsite fixture
(native/tools/p2_challenge_persistence_callsite_fixture.cpp), which drives the
real engine bridge pc_bbft_update() so the #713 recorders emit the 7 probe
markers through the pc_port/pc_bbft.cpp call site. Engine-free, hermetic,
fail-closed. No runtime, no ADMIT.

Marker grammar (exact lines, probe order):
  P2_CHALLENGE_{SAVE_KEY,LOAD_KEY,CLEAR,HIGHSCORE,UNLOCK,RECEIPT_DEDUP,REENTRY}
  stage=<cave_id>
Call-site proof also requires: the 960x540 centred window line, the recorded
stage flag, the resolved line, and PASS ...CALLSITE_RUN; each probe marker must
appear exactly once (the call site is idempotent).
"""
from __future__ import annotations

import math
import re

SCHEMA = "p2-challenge-persistence-callsite-v1"
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
PASS_RE = re.compile(r"^PASS P2_CHALLENGE_PERSISTENCE_CALLSITE_RUN markers=7$")
RESOLVED_RE = re.compile(r"^P2_CHALLENGE_PERSISTENCE_CALLSITE_RESOLVED stage=([A-Za-z0-9_]+) ui_index=27 markers=7$")
WINDOW_RE = re.compile(r"^P2_CHALLENGE_PERSISTENCE_CALLSITE_WINDOW size=960x540 .*centered=1$")
STAGE_FLAG_RE = re.compile(r"^P2_CHALLENGE_STAGE_FLAG cave=([A-Za-z0-9_]+)$")
REFUSE_RE = re.compile(r"^P2_CHALLENGE_PERSISTENCE_REFUSED reason=(\S+)$")
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "mHealth=", "Transport(")


class CallsiteError(ValueError):
    """Refusal: malformed input, unknown stage/artifact, or contract drift."""


def _check_cave_id(cave_id):
    if not isinstance(cave_id, str) or not CAVE_ID_PATTERN.fullmatch(cave_id):
        raise CallsiteError("Unsafe cave_id for key derivation: %r" % (cave_id,))


def stage_keys(cave_id):
    """Persistence keys for one stage (mirrors the #708/#713 formula verbatim)."""
    _check_cave_id(cave_id)
    return {field: "%s_%s_%s" % (KEY_PREFIX, field, cave_id)
            for field in KEY_FIELDS}


def marker_for(artifact, cave_id):
    """Exact run-log marker line for one probe artifact."""
    _check_cave_id(cave_id)
    if artifact not in STEMS:
        raise CallsiteError("Unknown probe artifact: %r" % (artifact,))
    return "P2_CHALLENGE_%s stage=%s" % (STEMS[artifact], cave_id)


def compute_score(pokos, time_left_seconds, population):
    """Result-screen score mirror (host-mode precedent, read-only)."""
    for value in (pokos, population):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise CallsiteError("Score inputs must be non-negative ints")
    if not isinstance(time_left_seconds, (int, float)) or isinstance(time_left_seconds, bool):
        raise CallsiteError("Score time must be numeric")
    if not math.isfinite(time_left_seconds) or time_left_seconds < 0:
        raise CallsiteError("Score time must be finite and non-negative")
    return pokos * 10 + int(time_left_seconds) + population * 10


def parse(text):
    """Split a run log into markers, PASS/REFUSED/window/flag lines, and flags."""
    markers, refusals, passes = [], [], []
    window = stage_flag = resolved = None
    for raw in text.splitlines():
        line = raw.strip()
        match = MARKER_RE.match(line)
        if match:
            markers.append((match.group(1), match.group(2)))
        if REFUSE_RE.match(line):
            refusals.append(line)
        if PASS_RE.match(line):
            passes.append(line)
        if WINDOW_RE.match(line):
            window = line
        flag = STAGE_FLAG_RE.match(line)
        if flag:
            stage_flag = flag.group(1)
        resolved_match = RESOLVED_RE.match(line)
        if resolved_match:
            resolved = resolved_match.group(1)
    return {
        "markers": markers,
        "refusals": refusals,
        "passes": passes,
        "window": window,
        "stage_flag": stage_flag,
        "resolved": resolved,
        "captain_down": CAPTAIN_DOWN in text,
        "injected": [t for t in INJECTED_TOKENS if t in text],
    }


def check_run(parsed, cave_id):
    """All 7 probe markers exactly once, call-site proof, nothing hostile."""
    _check_cave_id(cave_id)
    if parsed["captain_down"]:
        return False, "captain-down interruption present"
    if parsed["injected"]:
        return False, "injection markers present: %s" % ",".join(parsed["injected"])
    if parsed["window"] is None:
        return False, "centred 960x540 window line absent"
    if parsed["stage_flag"] != cave_id:
        return False, "stage flag missing or different: %r" % (parsed["stage_flag"],)
    if parsed["resolved"] != cave_id:
        return False, "call-site resolved line missing or different: %r" % (parsed["resolved"],)
    if not parsed["passes"]:
        return False, "run PASS marker absent"
    if parsed["refusals"]:
        return False, "fixture refusals present: %s" % parsed["refusals"][:2]
    missing = []
    for artifact in PROBE_ARTIFACTS:
        stem = STEMS[artifact]
        count = sum(1 for s, c in parsed["markers"] if s == stem and c == cave_id)
        if count == 0:
            missing.append(artifact)
        elif count != 1:
            return False, "marker %s emitted %d times (call site not idempotent)" % (stem, count)
    if missing:
        return False, "missing probe markers: %s" % ",".join(missing)
    return True, "engine call site PASS with exact 7/7 probe markers"


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
