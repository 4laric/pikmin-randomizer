"""Rover stage-table row contract for the persistence call site (issue #734).

Lane rover-stage-table-row-native. This module is the Python half of the
provider: the pinned ch_MAT_route_rover row values, the fixture marker
grammar (RESOLVED/REFUSED with exactly-once accounting), and the
machine-readable contract. It stages nothing, injects nothing, and emits
no markers.

The BEHAVIORAL proof lives in native/tools/p2_rover_stage_table_fixture.cpp
(26 checks against the real row + lookup). A log grammar agreement here
alone can never pass acceptance; validate_log exists so the persistence
call-site owner (#561 consumer) gets deterministic verdicts on fixture logs.
"""
import json
import re
import sys

PROVIDER = "p2-challenge-rover-stage-row/1"
CONSUMER_ISSUE = 561

# Pinned row, transcribed from the #561 source contract (read-only).
PINNED = {
    "cave_id": "ch_MAT_route_rover",
    "cave_path": "user/Mukki/mapunits/caveinfo/ch_MAT_route_rover.txt",
    "source_sha256": "e03eb33a78526adb13eebd08af453555bc9cd219f6a3e624b28a0771ea12cb79",
    "ui_index": 27,
    "table_order": 21,
    "floors": 1,
    "floor_seconds": [90.0],
    "roster": [[0, 0, 20], [0, 0, 20], [0, 0, 20],
               [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
    "bitter_sprays": 2,
    "spicy_sprays": 2,
    "legacy_time": 300.0,
    "treasure_count_field": 0,
}

_RESOLVED_RE = re.compile(
    r"P2_ROVER_STAGE_RESOLVED cave=(\S+) ui=(\d+) floors=(\d+)")
_REFUSED_RE = re.compile(r"P2_ROVER_STAGE_REFUSED reason=(\S+)")

_INJECTED_MARKERS = (
    "P2_ROVER_INJECT",
    "p2-rover-inject",
    "injection=1",
)


def provider_contract():
    """Machine-readable provider contract for the persistence call site."""
    return {
        "schema": PROVIDER,
        "consumer_issue": CONSUMER_ISSUE,
        "native_api": "native/pc_port/pc_p2_challenge_rover_stage.h",
        "native_test": "native/tools/p2_rover_stage_table_fixture.cpp",
        "pinned": dict(PINNED),
        "exactly_once": True,
        "integration": "SERIALIZED follow-on: append the row to "
                       "pc_bbft.cpp kP2ChallengeStages with #186 review; "
                       "this module never edits shared files.",
        "runtime_claim": False,
    }


def _fields(pattern, line):
    match = pattern.search(line)
    return match.groups() if match else None


def validate_log(text):
    """Validate one fixture log against the provider grammar.

    Returns the verdict: True only when the log shows exactly one
    RESOLVED line for the pinned cave/ui/floors, zero injected markers,
    and no contradictory second resolution.
    """
    resolved = []
    refused = 0
    injected = False
    for line in (text or "").splitlines():
        if any(marker in line for marker in _INJECTED_MARKERS):
            injected = True
        fields = _fields(_RESOLVED_RE, line)
        if fields:
            resolved.append({"cave": fields[0], "ui": int(fields[1]),
                             "floors": int(fields[2])})
        if _fields(_REFUSED_RE, line):
            refused += 1

    problems = []
    if injected:
        problems.append("injected-markers-present")
    if len(resolved) != 1:
        problems.append("resolved-count-%d" % len(resolved))
    else:
        row = resolved[0]
        if row["cave"] != PINNED["cave_id"]:
            problems.append("wrong-cave:%s" % row["cave"])
        if row["ui"] != PINNED["ui_index"]:
            problems.append("wrong-ui:%d" % row["ui"])
        if row["floors"] != PINNED["floors"]:
            problems.append("wrong-floors:%d" % row["floors"])
    return {
        "resolved": resolved,
        "refused_lines": refused,
        "injected": injected,
        "problems": problems,
        "verdict": not problems,
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("contract", "validate"))
    parser.add_argument("path", nargs="?", help="Log path for validate")
    args = parser.parse_args(argv)
    if args.command == "contract":
        print(json.dumps(provider_contract(), indent=2, sort_keys=True))
        return 0
    if not args.path:
        parser.error("validate requires a log path")
    with open(args.path, encoding="utf-8", errors="replace") as handle:
        result = validate_log(handle.read())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] else 1


if __name__ == "__main__":
    main()
