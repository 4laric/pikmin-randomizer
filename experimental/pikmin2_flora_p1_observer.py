"""Flora P1 observer for the enemies-1 flora gate (issue #737).

Validates run logs from the flora P1 observer fixture
(native/tools/p2_flora_p1_observer_fixture.cpp), which observes natural
flora conversion for 47 Clover, 80 Tukushi and 89 Chiyogami through the
landed #697/#723 hookup bridge, consumed read-only and never duplicated
here. Owns the run-log grammar plus the key/score twins used to cross-check
the native emission.

Marker grammar (exact lines, session order):
  P2_FLORA_P1_SQUAD pikis=<n> colors=<csv>
  P2_FLORA_P1_SESSION identity=<flora> converted=<n> received=<n> hauled=0
  P2_FLORA_P1_DONE failures=<n>
  PASS P2_FLORA_P1_RUN sessions=3
Bridge hook lines (receipt-parseable, from the #723 bridge, exact):
  P2_FLORA_HOOKUP_ADMIT / CONVERT / SPROUT / SCENERY (see hookup observer)
Absorb-never-haul invariant: every session reports hauled=0 and
received == converted (swallowed Pikmin are absorbed into counted sprouts;
nothing is hauled off).
Key scheme mirror (verified identical to #697 by test vectors):
  p2_challenge_{save,load,clear,highscore,unlock}_{cave_id}
Score mirror (verified identical to the #651 host-mode precedent):
  score = pokos*10 + floor(timeLeftSeconds) + population*10

Engine-free, hermetic, fail-closed. No runtime, no ADMIT.
"""
from __future__ import annotations

import math
import re

SCHEMA = "p2-flora-p1-observer-v1"
FLORA = ("Clover", "Tukushi", "Chiyogami")
KEY_PREFIX = "p2_challenge"
KEY_FIELDS = ("save", "load", "clear", "highscore", "unlock")
SQUAD_RE = re.compile(r"^P2_FLORA_P1_SQUAD pikis=(\d+) colors=([A-Za-z,]+)$")
SESSION_RE = re.compile(r"^P2_FLORA_P1_SESSION identity=(\w+) converted=(\d+) received=(\d+) hauled=(\d+)$")
DONE_RE = re.compile(r"^P2_FLORA_P1_DONE failures=(\d+)$")
PASS_RE = re.compile(r"^PASS P2_FLORA_P1_RUN sessions=3$")
WINDOW_RE = re.compile(r"^P2_FLORA_P1_WINDOW size=960x540 .*centered=1$")
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "mHealth=", "Transport(")


class ObserverError(ValueError):
    """Refusal: malformed input, unknown flora, or contract drift."""


def _check_flora(identity):
    if identity not in FLORA:
        raise ObserverError("Unknown flora identity: %r" % (identity,))


def stage_keys(cave_id):
    """Persistence keys for one stage (mirrors the #697 formula verbatim)."""
    if not isinstance(cave_id, str) or not re.fullmatch(r"[A-Za-z0-9_]+", cave_id):
        raise ObserverError("Unsafe cave_id for key derivation: %r" % (cave_id,))
    return {field: "%s_%s_%s" % (KEY_PREFIX, field, cave_id)
            for field in KEY_FIELDS}


def compute_score(pokos, time_left_seconds, population):
    """Result-screen score mirror (host-mode precedent, read-only)."""
    for value in (pokos, population):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ObserverError("Score inputs must be non-negative ints")
    if not isinstance(time_left_seconds, (int, float)) or isinstance(time_left_seconds, bool):
        raise ObserverError("Score time must be numeric")
    if not math.isfinite(time_left_seconds) or time_left_seconds < 0:
        raise ObserverError("Score time must be finite and non-negative")
    return pokos * 10 + int(time_left_seconds) + population * 10


def parse(text):
    """Split a run log into P1 session lines, hook lines, and health flags."""
    squads, sessions, dones, passes = [], [], [], []
    window = None
    for raw in text.splitlines():
        line = raw.strip()
        match = SQUAD_RE.match(line)
        if match:
            squads.append((int(match.group(1)), match.group(2)))
        match = SESSION_RE.match(line)
        if match:
            sessions.append((match.group(1), int(match.group(2)),
                             int(match.group(3)), int(match.group(4))))
        match = DONE_RE.match(line)
        if match:
            dones.append(int(match.group(1)))
        if PASS_RE.match(line):
            passes.append(line)
        if WINDOW_RE.match(line):
            window = line
    return {
        "squads": squads,
        "sessions": sessions,
        "dones": dones,
        "passes": passes,
        "window": window,
        "captain_down": CAPTAIN_DOWN in text,
        "injected": [t for t in INJECTED_TOKENS if t in text],
    }


def check_run(parsed):
    """All three flora sessions observed with absorb-never-haul holding."""
    if parsed["captain_down"]:
        return False, "captain-down interruption present"
    if parsed["injected"]:
        return False, "injection markers present: %s" % ",".join(parsed["injected"])
    if parsed["window"] is None:
        return False, "centred 960x540 window line absent"
    if not parsed["squads"] or parsed["squads"][0][0] < 1:
        return False, "no live starting squad observed"
    seen = {}
    for identity, converted, received, hauled in parsed["sessions"]:
        try:
            _check_flora(identity)
        except ObserverError:
            return False, "unknown flora identity observed: %r" % (identity,)
        if hauled != 0:
            return False, "haul observed for %s (absorb-never-haul violated)" % identity
        if received != converted:
            return False, "sprout accounting open for %s" % identity
        seen[identity] = True
    missing = [f for f in FLORA if f not in seen]
    if missing:
        return False, "flora sessions missing: %s" % ",".join(missing)
    if not parsed["dones"] or parsed["dones"][-1] != 0:
        return False, "DONE failures nonzero or absent"
    if not parsed["passes"]:
        return False, "run PASS marker absent"
    return True, "three flora sessions observed with absorb-never-haul holding"


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
