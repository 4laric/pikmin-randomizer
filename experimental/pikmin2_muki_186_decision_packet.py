"""Machine-readable #186 decision packet for the MUKI stage-table wiring (issue #777).

Lane muki-186-decision-packet. Diagnosis only: this module emits the exact
review artifact the #186 owner needs to decide the serialized
pc_bbft.cpp/CMakeLists.txt landing for producer #748 — the unified diff of
the two MUKI rows, file hashes, destination pins, consumer refs #735/#744
and review metadata. It performs no engine change, grants no approval, and
claims no gameplay acceptance.

Inputs are explicit pinned values (never invented): the #748 native commits
(cae86d4e + 3c50ca44), the destination pins (#710 db245877 for the boot
table shape, #736 38305eea for the CMakeLists membership policy), and the
lane-plan source pins for the two stages. Every input is format-checked and
cross-checked; malformed pins, unknown files and hash drift are refused
fail-closed with no packet emitted.
"""
import json
import re
import sys

PACKET_SCHEMA = "p2-muki-186-decision-packet/1"
CONSUMER_ISSUES = (735, 744)
PRODUCER_ISSUE = 748

# Pinned #748 native commits (read-only refs).
PRODUCER_COMMITS = (
    "cae86d4e46d22f6f579df38ac86ca5c62afde613",
    "3c50ca44faad976d91cf790da8adbe6e3f508c4a",
)

# Destination pins (read-only refs).
DEST_BOOT_TABLE_PIN = "db245877"
DEST_CMAKE_PIN = "38305eea"

# Files needing the #186 decision (serialized wiring, producer-owned scope).
DECISION_FILES = (
    "native/pc_port/pc_bbft.cpp",
    "native/CMakeLists.txt",
)

_FULL_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
_SHORT_SHA_RE = re.compile(r"[0-9a-f]{7,40}\Z")

# Lane-plan source pins for the two MUKI stages (read-only).
STAGES = (
    {
        "cave_id": "ch_MUKI_houdai",
        "cave_path": "user/Mukki/mapunits/caveinfo/ch_MUKI_houdai.txt",
        "source_sha256": "07cdf2cd492024548b9982a6ed63c40ba6c781bd114814339aefc9b8b35232f3",
        "ui_index": 8,
        "table_order": 24,
        "floors": 2,
        "floor_seconds": [100.0, 150.0],
        "roster": [[0, 0, 10], [0, 0, 10], [0, 0, 10], [0, 0, 10], [0, 0, 10],
                   [0, 0, 0], [0, 0, 0]],
        "bitter_sprays": 1,
        "spicy_sprays": 1,
        "legacy_time": 0.0,
        "treasure_count_field": 0,
    },
    {
        "cave_id": "ch_MUKI_redblue",
        "cave_path": "user/Mukki/mapunits/caveinfo/ch_MUKI_redblue.txt",
        "source_sha256": "f81653301ec2f1b4f5cd1e51d2e15c81608bfbea0beaaadeb623de58db791434",
        "ui_index": 18,
        "table_order": 17,
        "floors": 2,
        "floor_seconds": [200.0, 200.0],
        "roster": [[0, 0, 25], [0, 0, 25],
                   [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
        "bitter_sprays": 1,
        "spicy_sprays": 1,
        "legacy_time": 0.0,
        "treasure_count_field": 0,
    },
)


def _check_sha(value, label):
    if not isinstance(value, str) or not _FULL_SHA_RE.match(value):
        raise ValueError(label + " must be a 40-hex commit")


def _check_short_sha(value, label):
    if not isinstance(value, str) or not _SHORT_SHA_RE.match(value):
        raise ValueError(label + " must be a hex pin")


def _fmt_float(value):
    text = repr(float(value))
    return text if "." in text else text + ".0"


def _row_block(stage):
    seconds = ", ".join(_fmt_float(v) + "f" for v in
                        list(stage["floor_seconds"]) + [0.0] * (8 - len(stage["floor_seconds"])))
    roster = ", ".join("{%d,%d,%d}" % tuple(cell) for cell in stage["roster"])
    return (
        '    { "%s",\n'
        '      "%s",\n'
        '      "%s",\n'
        '      %d, %d, %d,\n'
        '      { %s },\n'
        '      { %s },\n'
        '      %d, %d, %sf, %d },\n'
    ) % (stage["cave_id"], stage["cave_path"], stage["source_sha256"],
         stage["ui_index"], stage["table_order"], stage["floors"],
         seconds, roster, stage["bitter_sprays"], stage["spicy_sprays"],
         _fmt_float(stage["legacy_time"]), stage["treasure_count_field"])


def unified_diff(producer_commits=PRODUCER_COMMITS, dest_boot_pin=DEST_BOOT_TABLE_PIN):
    """Render the exact serialized diff for #186 review.

    Appends the two MUKI rows to kP2ChallengeStages in P2ChallengeStageRow
    field order plus the CMakeLists membership line. Inputs are validated;
    anything malformed raises instead of emitting a half-diff.
    """
    if not isinstance(producer_commits, (list, tuple)) or len(producer_commits) != 2:
        raise ValueError("exactly two producer commits required")
    for commit in producer_commits:
        _check_sha(commit, "producer commit")
    _check_short_sha(dest_boot_pin, "destination boot pin")
    rows = "".join("+" + line + "\n" for line in
                   "".join(_row_block(stage) for stage in STAGES).splitlines())
    return (
        "--- a/native/pc_port/pc_bbft.cpp\n"
        "+++ b/native/pc_port/pc_bbft.cpp\n"
        "@@ kP2ChallengeStages: append MUKI rows (producer %s) @@\n"
        "%s"
        "--- a/native/CMakeLists.txt\n"
        "+++ b/native/CMakeLists.txt\n"
        "@@ membership: add MUKI stage-table module to the owning target @@\n"
        "+pc_port/pc_p2_challenge_muki_stages.cpp\n"
    ) % ("/".join(c[:8] for c in producer_commits), rows)


def build_packet(producer_commits=PRODUCER_COMMITS,
                 dest_boot_pin=DEST_BOOT_TABLE_PIN,
                 dest_cmake_pin=DEST_CMAKE_PIN):
    """Assemble the machine-readable decision packet (fail-closed)."""
    diff = unified_diff(producer_commits, dest_boot_pin)
    _check_short_sha(dest_cmake_pin, "destination cmake pin")
    return {
        "schema": PACKET_SCHEMA,
        "producer_issue": PRODUCER_ISSUE,
        "producer_commits": list(producer_commits),
        "destination": {
            "boot_table_pin": dest_boot_pin,
            "cmake_pin": dest_cmake_pin,
        },
        "decision_files": list(DECISION_FILES),
        "unified_diff": diff,
        "stages": [dict(s) for s in STAGES],
        "consumer_issues": list(CONSUMER_ISSUES),
        "review": {
            "owner": "shared #186 review",
            "status": "requested-not-granted",
        },
        "runtime_claim": False,
    }


def validate_packet(packet):
    """Fail-closed packet self-check; returns True only when complete."""
    if not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA:
        return False
    if packet.get("producer_issue") != PRODUCER_ISSUE:
        return False
    if packet.get("consumer_issues") != [735, 744]:
        return False
    if packet.get("decision_files") != list(DECISION_FILES):
        return False
    try:
        rebuilt = build_packet(packet.get("producer_commits", []),
                               packet.get("destination", {}).get("boot_table_pin", ""),
                               packet.get("destination", {}).get("cmake_pin", ""))
    except (ValueError, TypeError, AttributeError):
        return False
    return rebuilt["unified_diff"] == packet.get("unified_diff")


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("packet", "diff"))
    args = parser.parse_args(argv)
    if args.command == "diff":
        print(unified_diff())
        return 0
    print(json.dumps(build_packet(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
