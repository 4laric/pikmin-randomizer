"""Tutorial stage-table row contract for the #534 consumer (issue #754).

Lane tutorial-stage-table-row-native. This module is the Python half of the
provider: the pinned ch_ABEM_tutorial row values, the P2_TUTORIAL_STAGE_SELECT_1
record stager consumed by the game-linked guarded fixture, the fixture marker
grammar (RESOLVED/REFUSED with exactly-once accounting), and the
machine-readable contract. It stages the record file, injects nothing into the
game, and emits no markers itself.

The BEHAVIORAL proof lives in native/tools/p2_tutorial_stage_guarded_fixture.cpp
(row resolution by the real lookup plus a guarded room-preview boot against
native pin b805d9c6's descendant line). A log grammar agreement here alone can
never pass acceptance; validate_log exists so the #534 consumer gets
deterministic verdicts on fixture logs.
"""
import json
import re

PROVIDER = "p2-challenge-tutorial-stage-row/1"
CONSUMER_ISSUE = 534

# Pinned row, transcribed from the #534 P1 import contract (read-only).
PINNED = {
    "cave_id": "ch_ABEM_tutorial",
    "cave_path": "user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt",
    "source_sha256": "e21f31f7fa5621a5922d9ee54ffb211a8e4f0e797866d70cc1edb98389ab097d",
    "ui_index": 0,
    "table_order": 0,
    "floors": 2,
    "floor_seconds": [100.0, 100.0],
    "roster": [[0, 0, 0], [50, 0, 0],
               [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
    "bitter_sprays": 2,
    "spicy_sprays": 2,
    "legacy_time": 0.0,
    "treasure_count_field": 0,
}

RECORD_MAGIC = "P2_TUTORIAL_STAGE_SELECT_1"
RECORD_FILE = "p2-tutorial-stage-select.txt"

_RESOLVED_RE = re.compile(
    r"P2_TUTORIAL_STAGE_RESOLVED cave=(\S+) ui_index=(\d+) floors=(\d+)")
_REFUSED_RE = re.compile(r"P2_TUTORIAL_STAGE_REFUSED reason=(\S+)")

_INJECTED_MARKERS = (
    "P2_TUTORIAL_INJECT",
    "p2-tutorial-inject",
    "injection=1",
)


def provider_contract():
    """Machine-readable provider contract for the #534 consumer."""
    return {
        "schema": PROVIDER,
        "consumer_issue": CONSUMER_ISSUE,
        "native_api": "native/pc_port/pc_p2_challenge_tutorial_stage.h",
        "native_test": "native/tools/p2_tutorial_stage_guarded_fixture.cpp",
        "pinned": dict(PINNED),
        "exactly_once": True,
        "integration": "SERIALIZED follow-on: append the row to "
                       "pc_bbft.cpp kP2ChallengeStages with #186 review; "
                       "this module never edits shared files.",
        "runtime_claim": False,
    }


def render_record(pinned=None):
    """Render the exact P2_TUTORIAL_STAGE_SELECT_1 record text the guarded
    fixture consumes (field layout mirrors the #669 selector record)."""
    row = dict(PINNED if pinned is None else pinned)
    lines = [RECORD_MAGIC,
             "cave %s ui_index %d table_order %d floors %d"
             % (row["cave_id"], row["ui_index"], row["table_order"],
                row["floors"]),
             "source %s %s" % (row["cave_path"], row["source_sha256"]),
             "timers %s legacy %s"
             % (" ".join(repr(float(v)) for v in row["floor_seconds"]),
                repr(float(row["legacy_time"]))),
             "sprays bitter %d spicy %d treasure_field %d"
             % (row["bitter_sprays"], row["spicy_sprays"],
                row["treasure_count_field"])]
    for color in row["roster"]:
        lines.append("roster %d %d %d" % tuple(color))
    return "\n".join(lines) + "\n"


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
    parser.add_argument("command", choices=("contract", "validate", "record"))
    parser.add_argument("path", nargs="?", help="Log path for validate, "
                        "output path for record")
    args = parser.parse_args(argv)
    if args.command == "contract":
        print(json.dumps(provider_contract(), indent=2, sort_keys=True))
        return 0
    if args.command == "record":
        if not args.path:
            parser.error("record requires an output path")
        with open(args.path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(render_record())
        return 0
    if not args.path:
        parser.error("validate requires a log path")
    with open(args.path, encoding="utf-8", errors="replace") as handle:
        result = validate_log(handle.read())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] else 1


if __name__ == "__main__":
    main()
