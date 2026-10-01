"""Mar family corpse-type check for enemies-2 (issue #772).

Validates run logs from the Mar corpse-type probe fixture
(native/tools/p2_mar_corpse_type_fixture.cpp), which instantiates the REAL
TAImarParameters and reads back TPI_CorpseType through the engine accessor,
then evaluates the exact BTeki::dieSoon predicate gating becomePellet on
natural Mar death. This closes the exact #716 gen-3 failing check
(becomePellet bound no pellet: no corpse). No actor, no HP, no injection.

Marker grammar (exact lines):
  P2_MAR_CORPSE_TYPE_WINDOW size=960x540 ... centered=1
  P2_MAR_CORPSE_TYPE value=<n> expected=<m>
  P2_MAR_BECOME_PELLET_BOUND bound=1
  P2_MAR_DONE failures=0
  PASS P2_MAR_CORPSE_TYPE_RUN

Engine-free, hermetic, fail-closed. No runtime world boot, no ADMIT.
"""
from __future__ import annotations

import re

SCHEMA = "p2-mar-corpse-type-check-v1"
WINDOW_RE = re.compile(r"^P2_MAR_CORPSE_TYPE_WINDOW size=960x540 .*centered=1$")
TYPE_RE = re.compile(r"^P2_MAR_CORPSE_TYPE value=(\d+) expected=(\d+)$")
BOUND_RE = re.compile(r"^P2_MAR_BECOME_PELLET_BOUND bound=([01])$")
DONE_RE = re.compile(r"^P2_MAR_DONE failures=(\d+)$")
PASS_RE = re.compile(r"^PASS P2_MAR_CORPSE_TYPE_RUN$")
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "mHealth=", "Transport(")


class CheckError(ValueError):
    """Refusal: malformed input or contract drift."""


def parse(text):
    """Split a run log into probe facts and health flags."""
    types, bounds, dones, passes = [], [], [], []
    window = None
    for raw in text.splitlines():
        line = raw.strip()
        match = TYPE_RE.match(line)
        if match:
            types.append((int(match.group(1)), int(match.group(2))))
        match = BOUND_RE.match(line)
        if match:
            bounds.append(int(match.group(1)))
        match = DONE_RE.match(line)
        if match:
            dones.append(int(match.group(1)))
        if PASS_RE.match(line):
            passes.append(line)
        if WINDOW_RE.match(line):
            window = line
    return {
        "types": types, "bounds": bounds, "dones": dones,
        "passes": passes, "window": window,
        "captain_down": CAPTAIN_DOWN in text,
        "injected": [t for t in INJECTED_TOKENS if t in text],
    }


def check_run(parsed):
    """Corpse type matches LeaveCorpse and the pellet path is bound."""
    if parsed["captain_down"]:
        return False, "captain-down interruption present"
    if parsed["injected"]:
        return False, "injection markers present: %s" % ",".join(parsed["injected"])
    if parsed["window"] is None:
        return False, "centred 960x540 window line absent"
    if not parsed["types"]:
        return False, "corpse-type probe line absent"
    value, expected = parsed["types"][-1]
    if value != expected:
        return False, "corpse type %d != expected %d" % (value, expected)
    if not parsed["bounds"] or parsed["bounds"][-1] != 1:
        return False, "becomePellet path not bound"
    if not parsed["dones"] or parsed["dones"][-1] != 0:
        return False, "DONE failures nonzero or absent"
    if not parsed["passes"]:
        return False, "run PASS marker absent"
    return True, "corpse type = LeaveCorpse and pellet path bound"


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
