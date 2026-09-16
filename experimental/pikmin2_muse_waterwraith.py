"""Autonomous-movement + birth observer for Waterwraith (BlackMan 99 / Tyre 98).

Muse lane l63 (#503), child of #443. This module parses a native run log and
reports two fail-closed verdicts over the markers the lane-63 actor/encounter
slice emits:

- Gate 1 (identity_spawn): ``P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99
  helper=98`` (observed actor birth state: Fall phase, single Tyre child
  attached, source IDs) plus the fixed-placement profile
  (``P2_WATERWRAITH_REGISTER_PROFILE``) and the two-species visual bank
  (``P2_WATERWRAITH_VISUAL_READY species=2``). Scope honesty: this is the
  FIXED natural encounter birth audited against source onInit
  (blackMan.cpp:147-169); ordinary generated admission (placement slot /
  seed resolve / actor bind triple) belongs to muse-placement (l52) and is
  NOT claimed here.
- Gate 2 (movement_animation): at least one ``P2_WATERWRAITH_STEER`` line in
  ``mode=chase`` (actor-owned steering to the live captain, source walkFunc
  :873-929) with a locomotion motion (``walk``/``run``) and measured planar
  travel above threshold. Route-only or hold-only logs fail; a pinned actor
  (chase markers but no travel) fails.

Fail-closed: any missing leg yields False. Pure functions over log text;
stdlib only. Nothing here emits markers, so it cannot fabricate acceptance.
Read-only with respect to legacy lane 31: gates 3-6 evidence is cited from
the lane-31 handoff/logs, never re-derived here.
"""

import json
import sys

SOURCE_ID = 99
SOURCE_NAME = "BlackMan"
HELPER_ID = 98
HELPER_NAME = "Tyre"

BIRTH = "P2_WATERWRAITH_BIRTH"
REGISTER_PROFILE = "P2_WATERWRAITH_REGISTER_PROFILE"
VISUAL_READY = "P2_WATERWRAITH_VISUAL_READY"
STEER = "P2_WATERWRAITH_STEER"

TRAVEL_THRESHOLD = 1.0
CHASE_MOTIONS = ("walk", "run")


def _fields(tokens):
    fields = {}
    for token in tokens:
        key, sep, value = token.partition("=")
        if sep:
            fields[key] = value
    return fields


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse(text):
    """Return the gate-1/gate-2 fixed-encounter verdicts for run-log text."""
    birth_ok = False
    profile_seen = False
    visual_seen = False
    escape_phases = set()
    modes_seen = set()
    motions_seen = set()
    chase_lines = 0
    chase_travel_max = 0.0
    tired_seen = False
    route_refresh_seen = False
    steer_lines = 0

    for line in (text or "").splitlines():
        tokens = line.split()
        if not tokens:
            continue
        fields = _fields(tokens)
        if BIRTH in tokens:
            if (
                fields.get("phase") == "fall"
                and fields.get("attached") == "1"
                and fields.get("id") == str(SOURCE_ID)
                and fields.get("helper") == str(HELPER_ID)
            ):
                birth_ok = True
        if REGISTER_PROFILE in tokens and "placement=" in line:
            profile_seen = True
        if VISUAL_READY in tokens and _int(fields.get("species")) == 2:
            visual_seen = True
        if STEER in tokens:
            steer_lines += 1
            mode = fields.get("mode")
            motion = fields.get("motion")
            if mode:
                modes_seen.add(mode)
            if motion:
                motions_seen.add(motion)
            escape = _int(fields.get("escape"))
            if escape is not None:
                escape_phases.add(escape)
            travel = _float(fields.get("travel"))
            if mode == "chase":
                chase_lines += 1
                if travel is not None and travel > chase_travel_max:
                    chase_travel_max = travel
        if "P2_WATERWRAITH_TIRED" in tokens:
            tired_seen = True
        if "P2_WATERWRAITH_ROUTE_REFRESH" in tokens:
            route_refresh_seen = True

    gate1_ok = birth_ok and profile_seen and visual_seen
    gate2_ok = (
        chase_lines >= 1
        and any(m in CHASE_MOTIONS for m in motions_seen)
        and chase_travel_max >= TRAVEL_THRESHOLD
        and 2 in escape_phases
    )

    return {
        "birth_ok": birth_ok,
        "profile_seen": profile_seen,
        "visual_seen": visual_seen,
        "gate1_ok": gate1_ok,
        "gate1_scope": "fixed natural encounter birth; generated admission open",
        "steer_lines": steer_lines,
        "modes_seen": sorted(modes_seen),
        "motions_seen": sorted(motions_seen),
        "escape_phases": sorted(escape_phases),
        "chase_lines": chase_lines,
        "chase_travel_max": chase_travel_max,
        "tired_seen": tired_seen,
        "route_refresh_seen": route_refresh_seen,
        "gate2_ok": gate2_ok,
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Run-log path (defaults to stdin)")
    args = parser.parse_args(argv)
    if args.path:
        with open(args.path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    print(json.dumps(parse(text), indent=2))


if __name__ == "__main__":
    main()
