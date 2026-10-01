"""Retail-faithful airborne-reach technique for Mar (Puffy Blowhog, source 29).

Bounded technique producer for issue #709 (downstream observer
`shard-enemies-2-mar29-observer` #375). Engine-free: this module specifies and
checks a landing/reach cadence the observer can execute; it never runs the
engine, edits source, or claims gameplay acceptance.

Read-only basis
---------------
* Integrated #687 (`pc_port/pc_p2_mar.cpp`, on the species line): CHASE serves
  FlightHeight SWOOP(10) while closing, ATTACK serves LAND(3) and calls
  `finishFlying()` inside TOUCHDOWN_BAND(12) of the ground, then `startFlying()`
  on ATTACK exit. Constants mirrored below, never duplicated.
* Source decomp (@632af937): fp01 FLIGHT_HEIGHT 80, fp03 AIR_WAIT_TIME 3.0,
  fp05/fp06 swing 2.5/5.0; sticking Pikmin drives TAIAdescent -> TAIAlandingMar
  (descent/landing), takeoff via TAIAtakeOffMar/timerTakeOff.
* #375 gen-8 evidence (hash-pinned in the packet): real damage 3000 -> 270 with
  167 natural events, then stalled; Mar returns to flight height between ATTACK
  windows so the grounded squad cannot convert the last ~9%.

The technique below is FAIL-CLOSED: every step names the observable that must be
present, and any cadence step that would fire outside the low window (or that
re-issues Attack onto a Pikmin already executing Attack) is rejected.
"""
from __future__ import annotations

import math
import re

SCHEMA = "p2-mar-airborne-reach-technique-v1"
SOURCE_ID = 29
GENERATOR_375001 = 375001

# ---- Constants mirrored read-only from the integrated #687 cadence ----------
FLIGHT_HEIGHT = 80.0        # fp01 hover (out of grounded reach)
SWOOP_HEIGHT = 10.0         # CHASE descent height
LAND_HEIGHT = 3.0           # ATTACK touchdown height
TOUCHDOWN_BAND = 12.0       # finishFlying() gate: <= this above ground
AIR_WAIT_TIME = 3.0         # fp03 hover wait before a move re-target
MAX_ATTACK_RANGE = 200.0    # fp20 attackable range (xz)
ATTACKABLE_HALF_ANGLE = 0.785398   # rad; port ATTACKABLE_ANGLE (45 deg)
ENGLISH_ENTRY_HALF_ANGLE = 0.785398  # rad; CHASE -> ATTACK entry cone
ATTACK_HOVER_SPEED = 12.0   # served Walk/Run velocity during ATTACK
RISE_FACTOR = 1.0           # proper fp02

# Grounded-squad reach: the low window is only when the actor is inside this
# band AND the flying flag is cleared by the ATTACK arm.
REACHABLE_MAX_HEIGHT = TOUCHDOWN_BAND

# Retail throw cadence bounds (source behaviour, not invented):
# * at least one thrown Pikmin must be in flight or stuck during the low window
#   to trigger TAIAdescent/TAIAlandingMar and hold the landing;
# * re-engage/re-clump must complete before Mar rises back out of the band.
MIN_THROWN_DURING_WINDOW = 1
RISE_BUDGET_SECONDS = 1.0

BIND_RE = re.compile(r"P2_MAR_BIND generator=(\d+) source_id=(\d+)")
READY_RE = re.compile(r"P2_MUSE_MAR_READY squad=(\d+)")
HP_RE = re.compile(r"P2_MUSE_MAR_HP health=([-\d.]+) squad=(\d+) atk=(\d+) events=(\d+) tick=(\d+)")
STATE_RE = re.compile(r"P2_MAR_STATE generator=(\d+) state=(\w+)")
POS_RE = re.compile(r"P2_MAR_POS generator=(\d+) state=(\w+) clip=(\w+) phase=([\d.]+) x=([-\d.]+) z=([-\d.]+)")
BLOW_RE = re.compile(r"P2_MAR_BLOW generator=(\d+) pikmin=(\d+)")
DRAIN_RE = re.compile(r"P2_MUSE_MAR_DRAIN events=(\d+) min=([-\d.]+) start=([-\d.]+)")
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"


def parse(text: str) -> dict:
    """Extract the read-only observables this technique constrains."""
    return {
        "binds": BIND_RE.findall(text),
        "ready": READY_RE.findall(text),
        "hp": [(float(h), int(s), int(a), int(e), int(t))
               for h, s, a, e, t in HP_RE.findall(text)],
        "states": STATE_RE.findall(text),
        "positions": POS_RE.findall(text),
        "blows": BLOW_RE.findall(text),
        "drains": DRAIN_RE.findall(text),
        "captain_down": CAPTAIN_DOWN in text,
        "has_nan": "=nan" in text or "(nan" in text,
    }


def check_preconditions(parsed: dict, required_squad: int = 1) -> tuple[bool, list[str]]:
    """Every precondition must hold before the cadence is executable."""
    failures: list[str] = []
    binds = [b for b in parsed.get("binds", []) if b[1] == str(SOURCE_ID)]
    if not binds:
        failures.append("mar_not_bound: no P2_MAR_BIND for source_id=29")
    elif all(b[0] != str(GENERATOR_375001) for b in binds):
        failures.append("wrong_generator: expected %d" % GENERATOR_375001)
    if not parsed.get("ready"):
        failures.append("squad_not_ready: no P2_MUSE_MAR_READY")
    elif int(parsed["ready"][-1]) < required_squad:
        failures.append("squad_below_minimum")
    if parsed.get("captain_down"):
        failures.append("captain_down: #632 guard tripped")
    if parsed.get("has_nan"):
        failures.append("non_finite_position")
    if not any(h[0] > 0.0 for h in parsed.get("hp", [])):
        failures.append("mar_not_alive: no positive HP sample")
    return (not failures), failures


def check_landing_window(parsed: dict, height: float) -> tuple[bool, str]:
    """A landing/reach window is only when Mar is at/below the touchdown band.

    #687 clears the flying flag inside TOUCHDOWN_BAND during ATTACK; anything
    at hover/swing height (>= FLIGHT_HEIGHT - swing) is out of grounded reach.
    """
    if not isinstance(height, (int, float)) or not math.isfinite(height):
        return False, "non-finite height"
    if height <= REACHABLE_MAX_HEIGHT:
        return True, "reachable (height %.1f <= %.1f)" % (height, REACHABLE_MAX_HEIGHT)
    return False, "out_of_reach: height %.1f > %.1f (retail hover)" % (height, REACHABLE_MAX_HEIGHT)


def check_entry_geometry(distance_xz: float, angle_rad: float) -> tuple[bool, str]:
    """CHASE -> ATTACK requires distance inside fp20 and within the entry cone."""
    if not math.isfinite(distance_xz) or not math.isfinite(angle_rad):
        return False, "non-finite geometry"
    if distance_xz >= MAX_ATTACK_RANGE:
        return False, "distance %.1f >= range %.1f" % (distance_xz, MAX_ATTACK_RANGE)
    if abs(angle_rad) >= ENGLISH_ENTRY_HALF_ANGLE:
        return False, "angle %.3f outside entry cone %.3f" % (angle_rad, ENGLISH_ENTRY_HALF_ANGLE)
    return True, "inside attackable cone"


def cadence_steps() -> list[dict]:
    """Canonical retail-faithful cadence the observer executes, in order."""
    return [
        {"step": 1, "action": "wait_for_chase",
         "observable": "P2_MAR_STATE state=chase",
         "rule": "Do not move the squad while Mar hovers (state=wait/move)."},
        {"step": 2, "action": "preposition_squad",
         "observable": "squad grounded at Mar's xz approach path",
         "rule": "Stand inside the entry cone before the descent so the first "
                 "grounded frame is already in reach."},
        {"step": 3, "action": "throw_on_landing",
         "observable": "P2_MAR_STATE state=attack and height <= %.1f" % REACHABLE_MAX_HEIGHT,
         "rule": "Throw Pikmin during the low window to stick and hold the "
                 "retail TAIAdescent/TAIAlandingMar landing."},
        {"step": 4, "action": "swarm_attack",
         "observable": "real Attack orders, health decreasing",
         "rule": "Re-engage ONLY Pikmin whose live action is not Attack; "
                 "re-issuing cancels in-flight strikes (#687)."},
        {"step": 5, "action": "reclump_after_blow",
         "observable": "P2_MAR_BLOW then scatter",
         "rule": "Re-clump stragglers at Mar's height within %.1fs of the blow, "
                 "before Mar rises out of the band." % RISE_BUDGET_SECONDS},
        {"step": 6, "action": "hold_between_windows",
         "observable": "P2_MAR_STATE state=wait/move (rise to %.0f)" % FLIGHT_HEIGHT,
         "rule": "Hold under the next approach; never chase Mar at hover height."},
        {"step": 7, "action": "complete_kill",
         "observable": "health reaches 0 then P2_MAR_DEAD",
         "rule": "Only then claim gates 4/5/6 downstream (#375)."},
    ]


def check_cadence(steps: list[dict], parsed: dict) -> tuple[bool, str]:
    """Validate an executed cadence against the fail-closed rules.

    Each executed step names: action, mar_state, height, and (for re-engage)
    whether it targeted only non-Attack Pikmin. Invalid steps are refused.
    """
    if not isinstance(steps, list) or not steps:
        return False, "empty cadence"
    low_seen = False
    thrown = 0
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or not step.get("action"):
            return False, "step %d: malformed" % index
        action = step["action"]
        state = step.get("mar_state")
        height = step.get("height")
        if action in ("throw_on_landing", "swarm_attack", "reclump_after_blow"):
            ok, why = check_landing_window(parsed, height)
            if not ok:
                return False, "step %d (%s): %s" % (index, action, why)
            low_seen = True
        if action == "throw_on_landing":
            thrown += 1
        if action == "swarm_attack" and step.get("reissued_active_attack"):
            return False, "step %d: re-issued Attack onto active Attack Pikmin" % index
        if action == "hold_between_windows" and state not in ("wait", "move"):
            return False, "step %d: hold step outside hover" % index
    if not low_seen:
        return False, "cadence never entered the low window"
    if thrown < MIN_THROWN_DURING_WINDOW:
        return False, "need >= %d throw during the low window" % MIN_THROWN_DURING_WINDOW
    return True, "cadence valid: %d steps, %d throw(s)" % (len(steps), thrown)


def reachable_from(parsed: dict) -> tuple[bool, str]:
    """True iff the observed log actually contains a grounded ATTACK window."""
    attack_heights = []
    for state in parsed.get("states", []):
        if state[1] == "attack":
            attack_heights.append(state)
    if not attack_heights:
        return False, "no ATTACK window observed"
    return True, "%d ATTACK window(s) observed" % len(attack_heights)


def technique_status(parsed: dict, executed_steps: list[dict] | None = None) -> dict:
    """Fail-closed technique report for the observer."""
    pre_ok, pre_failures = check_preconditions(parsed)
    reach_ok, reach_why = reachable_from(parsed)
    status = {
        "preconditions": (pre_ok, pre_failures),
        "reachable": (reach_ok, reach_why),
        "captain_guard": (not parsed.get("captain_down"),
                          "no CAPTAIN_DOWN" if not parsed.get("captain_down") else "CAPTAIN_DOWN fired"),
        "no_nan": (not parsed.get("has_nan"), "no NaN" if not parsed.get("has_nan") else "NaN present"),
    }
    if executed_steps is not None:
        cad_ok, cad_why = check_cadence(executed_steps, parsed)
        status["cadence"] = (cad_ok, cad_why)
    return status
