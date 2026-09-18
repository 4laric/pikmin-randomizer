"""Leafchappy stage-table row contract for the #550 consumer (issue #774).

Lane challenge-2-leafchappy-bridge-row. This module is the Python half of the
provider: the pinned ch_ABEM_LeafChappy row values, the fixture marker
grammar (RESOLVED/REFUSED with exactly-once accounting), and the
machine-readable contract. It stages nothing, injects nothing, and emits
no markers.

The BEHAVIORAL proof lives in native/tools/p2_leafchappy_stage_table_fixture.cpp
(checks against the real row + lookup plus guard self-test/negative). A log
grammar agreement here alone can never pass acceptance; validate_log exists
so the #550 consumer gets deterministic verdicts on fixture logs.
"""
import json
import re
import sys

PROVIDER = "p2-challenge-leafchappy-stage-row/1"
CONSUMER_ISSUE = 550

# Pinned row, transcribed from the lane-plan source contract (read-only).
PINNED = {
    "cave_id": "ch_ABEM_LeafChappy",
    "cave_path": "user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt",
    "source_sha256": "49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf",
    "ui_index": 17,
    "table_order": 4,
    "floors": 2,
    "floor_seconds": [85.0, 100.0],
    "roster": [[10, 0, 0], [10, 0, 0], [10, 0, 0],
               [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
    "bitter_sprays": 1,
    "spicy_sprays": 1,
    "legacy_time": 400.0,
    "treasure_count_field": 11,
}

_RESOLVED_RE = re.compile(
    r"P2_LEAFCHAPPY_STAGE_RESOLVED cave=(\S+) ui=(\d+) floors=(\d+)")
_REFUSED_RE = re.compile(r"P2_LEAFCHAPPY_STAGE_REFUSED reason=(\S+)")

_INJECTED_MARKERS = (
    "P2_LEAFCHAPPY_INJECT",
    "p2-leafchappy-inject",
    "injection=1",
)


def provider_contract():
    """Machine-readable provider contract for the #550 consumer."""
    return {
        "schema": PROVIDER,
        "consumer_issue": CONSUMER_ISSUE,
        "native_api": "native/pc_port/pc_p2_challenge_leafchappy_stage.h",
        "native_test": "native/tools/p2_leafchappy_stage_table_fixture.cpp",
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
