#!/usr/bin/env python3
"""Yakushima engine-hook pin-discovery registry (lane yakushima-engine-hook-pin-discovery).

Read-only audit result for the #150 fixture UNSUPPORTED boundaries on the wired
yakushima surface session: each boundary maps to an exact engine hook point or
a verified ABSENT verdict with the nearest foothold, landing owner/files (or
deferral). Stdlib only. Fail-closed: anything unexpected is reported, never passed.
Downstream: recovery bd5aaf22, p2-overworld-yakushima-p1-native-runtime (#150).
"""

import argparse
import json
import sys

SCHEMA = "p2-yakushima-engine-hook-pins-1"

BOUNDARIES = {
    "boot_yakushima_surface": {
        "fixture_reason": "no-overworld-course-boot-in-port",
        "verdict": "ABSENT",
        "evidence": "no CourseBoot/OverworldBoot/cave-course boot symbol in pc_port or plugPikiColin",
        "nearest_foothold": [
            "pc_pikipelago_room_preview (pc_bbft.h; room boot used by pc_main.cpp/pc_bbft.cpp)",
            "pc_p2_cave_setup/tick/request (pc_p2_cave.h:4-6; cave boot path, not overworld)",
        ],
        "owner": "new overworld-boot provider (unowned) + #186 shared review of the boot path",
    },
    "day_transition": {
        "fixture_reason": "no-day-advance-api-in-port",
        "verdict": "ABSENT",
        "evidence": "port has only pc_randomizer_next_day (pc_randomizer.h:17-18, diary repeat) "
                    "and pc_settings_get_day_minutes (pc_settings.h:63-64); no callable session day-advance",
        "nearest_foothold": [
            "retail day-end flow ogScrResultMgr RESULT_Active/RESULT_ExitToMapSelect (ogResult.cpp:602-638)",
            "pc_photo_mode.h:9 notes the day clock is not stopped by photo mode (clock exists, no advance API)",
        ],
        "owner": "new day-advance provider (unowned) + #186 shared review",
    },
    "receipt_replay": {
        "fixture_reason": "no-engine-receipt-hooks-in-port-#186-pending",
        "verdict": "ABSENT",
        "evidence": "P2Economy ledger exists (pc_p2_economy.h:5-13: load/credit/total) but only "
                    "pc_p2_preview.cpp references it; zero engine session-event callers of credit()",
        "nearest_foothold": [
            "P2Economy::credit (pc_p2_economy.h) - needs engine call sites",
            "pc_p2_cave_receipt_prefix (pc_p2_cave.h:9; cave-scoped, not surface session)",
        ],
        "owner": "#186 shared-hook review for receipt driver call sites + receipt provider",
    },
    "exit_reentry": {
        "fixture_reason": "no-exit-reentry-path-in-port",
        "verdict": "ABSENT",
        "evidence": "no exitCourse/ExitCourse/goToTitle/returnToTitle in pc_port or plugPikiColin",
        "nearest_foothold": [
            "retail ogResult exit states RESULT_ExitToMapSelect/RESULT_ExitToCardSelect (ogResult.cpp:626-636)",
        ],
        "owner": "new exit/reentry provider (unowned) + #186 shared review",
    },
}

REGISTRY = {
    "schema": SCHEMA,
    "stage": "yakushima surface session (overworld)",
    "fixture": "native/tools/p2_yakushima_p1_runtime_fixture.cpp at native d01b89a7",
    "destination_pins": {
        "root": "f2803e423b9f30ee6fcaf79004be02b2770a5a98",
        "native": "b944db033a3eef7aabb135372c4656d04e47bd7d",
    },
    "boundaries": BOUNDARIES,
    "decision_request": "#186: approve per-boundary hook approach (new provider scopes + shared "
                        "call-site review) against the destination pins; see review doc",
    "downstream": ["recovery bd5aaf22", "p2-overworld-yakushima-p1-native-runtime (#150)"],
}


def registry():
    """Return a deep copy of the pins registry."""
    return json.loads(json.dumps(REGISTRY))


def check_boundary(name):
    """Fail-closed lookup of one boundary verdict."""
    entry = BOUNDARIES.get(name)
    if entry is None:
        return {"verdict": "REFUSED", "problems": ["unknown-boundary:" + str(name)]}
    return {"boundary": name, "verdict": entry["verdict"],
            "owner": entry["owner"], "problems": []}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pins")
    check = sub.add_parser("check")
    check.add_argument("--boundary", required=True)
    args = parser.parse_args(argv)
    if args.command == "pins":
        print(json.dumps(registry(), indent=1, sort_keys=True))
        return 0
    result = check_boundary(args.boundary)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["verdict"] == "ABSENT" and not result["problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())