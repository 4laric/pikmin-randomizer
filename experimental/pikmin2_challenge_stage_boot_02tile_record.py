"""Pinned ch_NARI_02tile stage-boot record contract (issue #711).

Lane challenge-stage-boot-02tile-record-native. Records the exact pinned
#669 P2_CHALLENGE_STAGE_SELECT_1 record facts accepted by the generalized
#675 stage-boot fixture, the fixture allowlist contract, and the exact engine
table-row follow-on for #710. Stdlib only; no runtime, no build here.

The fixture (native/tools/p2_challenge_stage_boot_fixture.cpp) accepts only
records whose (cave_id, source path, source sha256) is one of the pinned
triples below. A record for a stage whose engine table row is not yet
serialized resolves at the record level and stops BLOCKED before boot; it is
never a fake PASS.
"""

import hashlib
import re

SCHEMA = "p2-challenge-stage-boot-02tile-record-v1"
ISSUE = 711
CONSUMER = {"lane": "p2-challenge-ch-nari-02tile-p1", "issue": 537}

PINNED_RECORDS = {
    "ch_NARI_01kusachi": {
        "cave_id": "ch_NARI_01kusachi",
        "source_path": "user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt",
        "source_sha256": "b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85",
        "ui_index": 3, "table_order": 3, "floors": 1,
        "floor_seconds": [180.0], "legacy": 0.0,
        "bitter_sprays": 1, "spicy_sprays": 2, "treasure_field": 0,
        "roster": [[0, 0, 50], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
        "engine_row": "present",
    },
    "ch_NARI_02tile": {
        "cave_id": "ch_NARI_02tile",
        "source_path": "user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt",
        "source_sha256": "d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6",
        "ui_index": 4, "table_order": 19, "floors": 2,
        "floor_seconds": [200.0, 150.0], "legacy": 0.0,
        "bitter_sprays": 0, "spicy_sprays": 5, "treasure_field": 0,
        "roster": [[0, 0, 50], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
        "engine_row": "pending-710",
    },
}

_HEX = re.compile(r"^[0-9a-f]{64}$")


def pinned_source(cave_id, source_path, source_sha256):
    """True only for a pinned (cave, path, sha) triple; fail-closed."""
    for rec in PINNED_RECORDS.values():
        if (rec["cave_id"] == cave_id and rec["source_path"] == source_path
                and rec["source_sha256"] == source_sha256):
            return True
    return False


def _int(token):
    try:
        return int(token)
    except (TypeError, ValueError):
        raise ValueError("not an integer: %r" % (token,))


def _float(token):
    try:
        return float(token)
    except (TypeError, ValueError):
        raise ValueError("not a number: %r" % (token,))


def parse_record(text):
    """Parse a P2_CHALLENGE_STAGE_SELECT_1 record; raises on any deviation."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty record")
    lines = text.splitlines()
    if not lines or lines[0] != "P2_CHALLENGE_STAGE_SELECT_1":
        raise ValueError("bad magic")
    head = lines[1].split()
    if len(head) != 8 or head[0] != "cave" or head[2] != "ui_index" or head[4] != "table_order" or head[6] != "floors":
        raise ValueError("bad header")
    cave = head[1]
    ui_index = _int(head[3])
    table_order = _int(head[5])
    floors = _int(head[7])
    if not (1 <= floors <= 8):
        raise ValueError("bad floors")
    src = lines[2].split()
    if len(src) != 3 or src[0] != "source":
        raise ValueError("bad source line")
    source_path, source_sha = src[1], src[2]
    if not _HEX.match(source_sha):
        raise ValueError("bad source sha256")
    timers = lines[3].split()
    if len(timers) != floors + 3 or timers[0] != "timers" or timers[floors + 1] != "legacy":
        raise ValueError("bad timers line")
    floor_seconds = [_float(t) for t in timers[1:floors + 1]]
    legacy = _float(timers[floors + 2])
    if floor_seconds[0] <= 0:
        raise ValueError("nonpositive first timer")
    spray_line = lines[4].split()
    # sprays bitter <b> spicy <s> treasure_field <t>
    if (len(spray_line) != 7 or spray_line[0] != "sprays" or spray_line[1] != "bitter"
            or spray_line[3] != "spicy" or spray_line[5] != "treasure_field"):
        raise ValueError("bad sprays line")
    bitter, spicy, treasure = _int(spray_line[2]), _int(spray_line[4]), _int(spray_line[6])
    roster = []
    for i in range(7):
        row = lines[5 + i].split()
        if len(row) != 4 or row[0] != "roster":
            raise ValueError("bad roster row %d" % i)
        roster.append([_int(v) for v in row[1:]])
    if len([l for l in lines if l.strip()]) != 12:
        raise ValueError("trailing data")
    record = {
        "cave_id": cave, "ui_index": ui_index, "table_order": table_order, "floors": floors,
        "source_path": source_path, "source_sha256": source_sha,
        "floor_seconds": floor_seconds, "legacy": legacy,
        "bitter_sprays": bitter, "spicy_sprays": spicy, "treasure_field": treasure,
        "roster": roster,
    }
    if not pinned_source(cave, source_path, source_sha):
        raise ValueError("unpinned source: %s %s" % (cave, source_path))
    pinned = PINNED_RECORDS[cave]
    for key in ("ui_index", "table_order", "floors", "floor_seconds", "legacy",
                "bitter_sprays", "spicy_sprays", "treasure_field", "roster"):
        if record[key] != pinned[key]:
            raise ValueError("pin mismatch: %s" % key)
    return record


def engine_table_row_followon():
    """Exact kP2ChallengeStages row to add for 02tile once #710 releases pc_bbft.cpp."""
    rec = PINNED_RECORDS["ch_NARI_02tile"]
    return {
        "owner": "#710 challenge-hostmode-engine-hook-native (owns pc_port/pc_bbft.cpp)",
        "file": "native/pc_port/pc_bbft.cpp",
        "table": "kP2ChallengeStages",
        "row": {
            "caveId": rec["cave_id"], "cavePath": rec["source_path"],
            "sourceSha256": rec["source_sha256"], "uiIndex": rec["ui_index"],
            "tableOrder": rec["table_order"], "floors": rec["floors"],
            "floorSeconds": rec["floor_seconds"], "roster": rec["roster"],
            "bitterSprays": rec["bitter_sprays"], "spicySprays": rec["spicy_sprays"],
            "legacyTime": rec["legacy"], "treasureCountField": rec["treasure_field"],
        },
        "note": "Append after #710 lands; then the #675 fixture's engine-table path resolves 02tile and full boot can be attempted.",
    }


def fixture_allowlist_ok(fixture_text):
    """True when the fixture carries both pinned triples and no kusachi-only hardcode."""
    missing = [c for c, r in PINNED_RECORDS.items()
               if r["source_sha256"] not in fixture_text or r["source_path"] not in fixture_text]
    hardcoded = 'sourcePath != "user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt"' in fixture_text
    return not missing and not hardcoded
