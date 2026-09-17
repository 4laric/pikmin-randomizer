"""Flora hookup engine-callsite observer (#723).

Validates run logs from the flora hookup fixture
(native/tools/p2_flora_hookup_fixture.cpp) against the ported #697 converter
contract, consumed read-only and never duplicated here. Owns the run-log
grammar plus the key/score twins used to cross-check the native emission.

Marker grammar (exact lines, bridge order):
  P2_FLORA_HOOKUP_ADMIT species=<name> swallowed=<n> ok=<0/1>
  P2_FLORA_HOOKUP_CONVERT species=<name> [sprouts=<n> slots=<n> refund=<0/1> | ok=0]
  P2_FLORA_HOOKUP_SPROUT species=<name> index=<i> received=1
  P2_FLORA_HOOKUP_SCENERY identity=<id> slot=<n> bound=<0+>
  P2_FLORA_HOOKUP_DONE failures=<n>
  PASS P2_FLORA_HOOKUP_RUN suites=3
Key scheme mirror (verified identical to #697 by test vectors):
  p2_challenge_{save,load,clear,highscore,unlock}_{cave_id}
Score mirror (verified identical to the #651 host-mode precedent):
  score = pokos*10 + floor(timeLeftSeconds) + population*10

Engine-free, hermetic, fail-closed. No runtime, no ADMIT.
"""
from __future__ import annotations

import math
import re

SCHEMA = "p2-flora-hookup-engine-callsite-v1"
KEY_PREFIX = "p2_challenge"
KEY_FIELDS = ("save", "load", "clear", "highscore", "unlock")
SPECIES = ("Pelplant", "BluePom", "RedPom", "YellowPom", "BlackPom",
           "WhitePom", "RandPom")
ADMIT_RE = re.compile(r"^P2_FLORA_HOOKUP_ADMIT species=(\w+) swallowed=(-?\d+) ok=([01])$")
CONVERT_RE = re.compile(r"^P2_FLORA_HOOKUP_CONVERT species=(\w+)(?: sprouts=(\d+) slots=(\d+) refund=([01])| ok=0)$")
SPROUT_RE = re.compile(r"^P2_FLORA_HOOKUP_SPROUT species=(\w+) index=(\d+) received=1$")
SCENERY_RE = re.compile(r"^P2_FLORA_HOOKUP_SCENERY identity=(\S+) slot=(-?\d+) bound=(-?\d+)$")
DONE_RE = re.compile(r"^P2_FLORA_HOOKUP_DONE failures=(\d+)$")
PASS_RE = re.compile(r"^PASS P2_FLORA_HOOKUP_RUN suites=3$")
WINDOW_RE = re.compile(r"^P2_FLORA_HOOKUP_WINDOW size=960x540 .*centered=1$")
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "mHealth=", "Transport(")


class HookupError(ValueError):
    """Refusal: malformed input, unknown species/artifact, or contract drift."""


def _check_species(species):
    if species not in SPECIES:
        raise HookupError("Unknown species: %r" % (species,))


def stage_keys(cave_id):
    """Persistence keys for one stage (mirrors the #697 formula verbatim)."""
    if not isinstance(cave_id, str) or not re.fullmatch(r"[A-Za-z0-9_]+", cave_id):
        raise HookupError("Unsafe cave_id for key derivation: %r" % (cave_id,))
    return {field: "%s_%s_%s" % (KEY_PREFIX, field, cave_id)
            for field in KEY_FIELDS}


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
    """Split a run log into hook lines, PASS/DONE lines, and health flags."""
    admits, converts, sprouts, sceneries, dones, passes = [], [], [], [], [], []
    for raw in text.splitlines():
        line = raw.strip()
        match = ADMIT_RE.match(line)
        if match:
            admits.append((match.group(1), int(match.group(2)), match.group(3) == "1"))
        match = CONVERT_RE.match(line)
        if match:
            converts.append(line)
        match = SPROUT_RE.match(line)
        if match:
            sprouts.append((match.group(1), int(match.group(2))))
        match = SCENERY_RE.match(line)
        if match:
            sceneries.append((match.group(1), int(match.group(2)), int(match.group(3))))
        match = DONE_RE.match(line)
        if match:
            dones.append(int(match.group(1)))
        if PASS_RE.match(line):
            passes.append(line)
    window = any(WINDOW_RE.match(line.strip()) for line in text.splitlines())
    return {
        "admits": admits,
        "converts": converts,
        "sprouts": sprouts,
        "sceneries": sceneries,
        "dones": dones,
        "passes": passes,
        "window": window,
        "captain_down": CAPTAIN_DOWN in text,
        "injected": [t for t in INJECTED_TOKENS if t in text],
    }


def check_run(parsed):
    """Bridge fired end-to-end: window, hook lines, DONE 0, PASS, nothing hostile."""
    if parsed["captain_down"]:
        return False, "captain-down interruption present"
    if parsed["injected"]:
        return False, "injection markers present: %s" % ",".join(parsed["injected"])
    if not parsed["window"]:
        return False, "centred 960x540 window line absent"
    if not parsed["admits"]:
        return False, "no ADMIT lines"
    if not parsed["converts"]:
        return False, "no CONVERT lines"
    if not parsed["sprouts"]:
        return False, "no SPROUT lines"
    if not parsed["sceneries"]:
        return False, "no SCENERY lines"
    if not parsed["dones"] or parsed["dones"][-1] != 0:
        return False, "DONE failures nonzero or absent"
    if not parsed["passes"]:
        return False, "run PASS marker absent"
    return True, "bridge fired end-to-end with hook markers"


def gate_status(text):
    """Tooling gate grades for a fixture run log (never a gameplay claim)."""
    parsed = parse(text)
    run_ok, run_why = check_run(parsed)
    return {
        "run_markers": (run_ok, run_why),
        "captain_guard": (not parsed["captain_down"],
                          "no CAPTAIN_DOWN" if not parsed["captain_down"] else "CAPTAIN_DOWN fired"),
        "no_inject": (not parsed["injected"],
                      "no injection markers" if not parsed["injected"] else "injection present"),
    }
