"""Tutorial challenge-row landing-request packet (issue #754, recovery e8e113b9).

Lane tutorial-row-landing-request. Diagnosis / packet only: this module
produces the exact unified landing spec for the pinned ``ch_ABEM_tutorial``
row into ``pc_bbft.cpp`` kP2ChallengeStages, the CMake membership
assessment, the #186 decision request, and the downstream record for the
blocked consumer ``p2-challenge-ch-abem-tutorial-p1-runtime-obs`` (#534).

It edits no engine/shared file, runs no build, and never claims an engine
unblock. It consumes the pinned #754 provider files read-only and the live
destination table text.
"""
import json
import re

PACKET = "p2-challenge-tutorial-row-landing-request/1"
CONSUMER_ISSUE = 534
CONSUMER_LANE = "p2-challenge-ch-abem-tutorial-p1-runtime-obs"
RECOVERY_ID = "e8e113b9"

# Pinned #754 row provider (read-only source contract).
SOURCE = {
    "issue": 754,
    "lane": "tutorial-stage-table-row-native",
    "native_commit": "b7fdfbbe36a02ff9827240c8327ecebb55a3e712",
    "handoff_gen3_sha256": "3d2df14222e7ab1e98d5a69486dbeed360788a250e080233d5d8e8f42e77ccc",
    "header_blob": "cdc8c8068fa85e714f3f08db6ada45a129e238c2",
    "source_blob": "039e1971c84864833f596960db71d292a22942f8",
    "row": {
        "cave_id": "ch_ABEM_tutorial",
        "cave_path": "user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt",
        "source_sha256": "e21f31f7fa5621a5922d9ee54ffb211a8e4f0e797866d70cc1edb98389ab097d",
        "ui_index": 0,
        "table_order": 0,
        "floors": 2,
        "floor_seconds": [100.0, 100.0],
        "roster": [[0, 0, 0], [50, 0, 0], [0, 0, 0], [0, 0, 0],
                   [0, 0, 0], [0, 0, 0], [0, 0, 0]],
        "bitter_sprays": 2,
        "spicy_sprays": 2,
        "legacy_time": 0.0,
        "treasure_count_field": 0,
    },
}

# Live destination pins at packet authoring (drift from the brief recorded).
DESTINATION = {
    "root_worktree": "output/dsw/wave-root",
    "root_head": "f2803e423b9f30ee6fcaf79004be02b2770a5a98",
    "native_worktree": "output/dsw/native-wave",
    "native_head": "b944db033a3eef7aabb135372c4656d04e47bd7d",
    "table_file": "pc_port/pc_bbft.cpp",
    "struct": "P2ChallengeStageRow",
    "table_symbol": "kP2ChallengeStages",
    "lookup_symbol": "pc_p2_challenge_stage_lookup",
    "existing_rows": ["ch_NARI_01kusachi"],
}

_TABLE_START_RE = re.compile(
    r"static\s+const\s+P2ChallengeStageRow\s+kP2ChallengeStages\s*\[\s*\]\s*=\s*\{")
_ROW_ID_RE = re.compile(r'^\s*\{\s*"(ch_[A-Za-z0-9_]+)"')


def render_row_literal(row=None):
    """Exact C++ literal for the pinned row, matching the table formatting."""
    r = dict(SOURCE["row"] if row is None else row)
    timers = ", ".join("%.1ff" % float(v) for v in
                       (list(r["floor_seconds"]) + [0.0] * 8)[:8])
    roster = ", ".join("{%d,%d,%d}" % tuple(c) for c in r["roster"])
    return "\n".join([
        '    { "%s",' % r["cave_id"],
        '      "%s",' % r["cave_path"],
        '      "%s",' % r["source_sha256"],
        "      %d, %d, %d," % (r["ui_index"], r["table_order"], r["floors"]),
        "      { %s }," % timers,
        "      { %s }," % roster,
        "      %d, %d, %.1ff, %d }," % (r["bitter_sprays"], r["spicy_sprays"],
                                       float(r["legacy_time"]),
                                       r["treasure_count_field"]),
    ])


def parse_table(text):
    """Parse the kP2ChallengeStages table from pc_bbft.cpp text.

    Returns dict(start_index, anchor_index, rows) or raises ValueError when
    the struct/table cannot be located. ``anchor_index`` is the 0-based line
    index of the closing ``};`` of the table.
    """
    lines = (text or "").splitlines()
    if not any("struct P2ChallengeStageRow" in ln for ln in lines):
        raise ValueError("missing P2ChallengeStageRow struct")
    start = next((i for i, ln in enumerate(lines)
                  if _TABLE_START_RE.search(ln)), None)
    if start is None:
        raise ValueError("missing kP2ChallengeStages table")
    anchor = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "};":
            anchor = i
            break
    if anchor is None:
        raise ValueError("missing table terminator")
    rows = []
    for ln in lines[start + 1:anchor]:
        m = _ROW_ID_RE.match(ln)
        if m:
            rows.append(m.group(1))
    return {"start_index": start, "anchor_index": anchor, "rows": rows}


def _unified_spec(text, anchor, insertion):
    lines = (text or "").splitlines()
    before = lines[max(0, anchor - 2):anchor]
    after = lines[anchor:anchor + 1]
    a_start = max(1, anchor - 1)
    a_count = len(before) + len(after)
    b_count = a_count + len(insertion)
    body = ([" " + ln for ln in before]
            + ["+" + ln for ln in insertion]
            + [" " + ln for ln in after])
    header = "@@ -%d,%d +%d,%d @@" % (a_start, a_count, a_start, b_count)
    return "\n".join(["--- a/" + DESTINATION["table_file"],
                      "+++ b/" + DESTINATION["table_file"],
                      header] + body) + "\n"


def landing_spec(text, row=None):
    """Exact unified landing spec for the pinned row into the destination.

    Refuses (ValueError) when the table cannot be parsed or the row is
    already present.
    """
    parsed = parse_table(text)
    if SOURCE["row"]["cave_id"] in parsed["rows"]:
        raise ValueError("row already present: " + SOURCE["row"]["cave_id"])
    insertion = render_row_literal(row).splitlines()
    return {
        "packet": PACKET,
        "source_commit": SOURCE["native_commit"],
        "destination_head": DESTINATION["native_head"],
        "table_file": DESTINATION["table_file"],
        "table_symbol": DESTINATION["table_symbol"],
        "anchor": "after last kP2ChallengeStages row, before its closing '};'",
        "anchor_line": parsed["anchor_index"] + 1,
        "existing_rows": list(parsed["rows"]),
        "insert_line_count": len(insertion),
        "unified_spec": _unified_spec(text, parsed["anchor_index"], insertion),
    }


def cmake_membership_assessment():
    """CMake assessment: the row append needs no new target membership."""
    return {
        "needs_new_source_membership": False,
        "reason": "Appending a data row to kP2ChallengeStages edits the "
                  "already-compiled pc_port/pc_bbft.cpp translation unit; no "
                  "new .cpp joins the pikmin_pc source list. The #754 "
                  "pc_p2_challenge_tutorial_stage.cpp module is a separate "
                  "serialized integration concern.",
        "do_not_edit": ["native/CMakeLists.txt",
                        "native/pc_port/pc_bbft.cpp"],
        "owned_by": "challenge-pc-bbft-followon (#755) / #736 line",
    }


def decision_request():
    """The #186 decision request required BEFORE any landing."""
    return {
        "issue": 186,
        "scope": "Append the pinned ch_ABEM_tutorial row to pc_bbft.cpp "
                 "kP2ChallengeStages (serialized shared-file change).",
        "file": "native/pc_port/pc_bbft.cpp",
        "source_pins": {
            "provider_commit": SOURCE["native_commit"],
            "row_blob": SOURCE["source_blob"],
            "handoff_gen3_sha256": SOURCE["handoff_gen3_sha256"],
        },
        "options": ["approve", "approve-with-changes", "reject"],
        "required_before": "any landing/batch of the row",
        "not_granted_by": "this packet",
    }


def downstream_record():
    """Downstream recovery record for the blocked #534 consumer."""
    return {
        "recovery_id": RECOVERY_ID,
        "consumer_lane": CONSUMER_LANE,
        "consumer_issue": CONSUMER_ISSUE,
        "input": "pinned ch_ABEM_tutorial row landing spec + #186 decision",
        "still_blocked_on": ["#186 decision on the pc_bbft.cpp row append",
                             "serialized owner #755/#736 landing"],
        "runtime_claim": False,
    }


def validate(text, row=None):
    """Fail-closed packet checks against a destination table text.

    Returns dict(problems, verdict). verdict is True only when the table
    parses, only the known existing rows are present, the pinned row is
    absent, and the emitted spec round-trips the row literal.
    """
    problems = []
    try:
        parsed = parse_table(text)
    except ValueError as exc:
        return {"problems": [str(exc)], "verdict": False}
    if parsed["rows"] != DESTINATION["existing_rows"]:
        problems.append("existing-rows:%s" % ",".join(parsed["rows"]))
    if SOURCE["row"]["cave_id"] in parsed["rows"]:
        problems.append("row-already-present")
    try:
        spec = landing_spec(text, row)
        literal = render_row_literal(row)
        prefixed = "\n".join("+" + ln for ln in literal.splitlines())
        if prefixed not in spec["unified_spec"]:
            problems.append("literal-not-in-spec")
        if SOURCE["row"]["source_sha256"] not in spec["unified_spec"]:
            problems.append("source-sha-not-in-spec")
    except ValueError as exc:
        problems.append(str(exc))
    return {"problems": problems, "verdict": not problems}


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",
                        choices=("packet", "landing", "decision",
                                 "downstream", "cmake", "validate"))
    parser.add_argument("path", nargs="?", help="pc_bbft.cpp path")
    args = parser.parse_args(argv)

    if args.command == "packet":
        print(json.dumps({"packet": PACKET, "source": SOURCE,
                          "destination": DESTINATION}, indent=2,
                         sort_keys=True))
        return 0
    if args.command == "decision":
        print(json.dumps(decision_request(), indent=2, sort_keys=True))
        return 0
    if args.command == "downstream":
        print(json.dumps(downstream_record(), indent=2, sort_keys=True))
        return 0
    if args.command == "cmake":
        print(json.dumps(cmake_membership_assessment(), indent=2,
                         sort_keys=True))
        return 0
    if not args.path:
        parser.error(args.command + " requires a pc_bbft.cpp path")
    with open(args.path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    if args.command == "landing":
        print(json.dumps(landing_spec(text), indent=2, sort_keys=True))
        return 0
    result = validate(text)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] else 1


if __name__ == "__main__":
    main()