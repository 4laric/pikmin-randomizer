"""P0 source-audit adapter for P2 Challenge 19 ch_MUKI_redblue (#551).

Concrete source-import preparation only. Reuses the existing
``cave_definition`` parser (no fork); never emits runtime placements.
Catalog metadata in docs/PIKMIN_CONTENT_IMPORT_LANES.json is baseline, not
a reimplementation target. Without actual source bytes, callers get the
exact missing prerequisite instead of invented values.
"""

import hashlib
import json
from pathlib import Path

from experimental.pikmin2_cave import cave_definition

SOURCE_PATH = "user/Mukki/mapunits/caveinfo/ch_MUKI_redblue.txt"
CAVE_ID = "ch_MUKI_redblue"
ISSUE = 551
EXPECTED_FLOORS = 2
EXPECTED_SHA256 = "f81653301ec2f1b4f5cd1e51d2e15c81608bfbea0beaaadeb623de58db791434"

EXPECTED_CHALLENGE = dict(
    table_order=17,
    ui_index=18,
    floors=2,
    floor_seconds=[200.0, 200.0],
    bitter_sprays=1,
    spicy_sprays=1,
    treasure_count_field=0,
    legacy_time=0.0,
    pikmin_by_native_color_and_maturity=[
        [0, 0, 25], [0, 0, 25], [0, 0, 0], [0, 0, 0], [0, 0, 0],
        [0, 0, 0], [0, 0, 0],
    ],
)

BLOCKERS = (
    {"issue": 136, "contract": "P2 Challenge runtime framework (roster, sprays, timers, keys/exits, scoring, retry)"},
    {"issue": 137, "contract": "P2 Challenge content (per-stage children on framework/generator pins)"},
    {"issue": 129, "contract": "cave generation, seams and navigation pin"},
    {"issue": 130, "contract": "actor/asset source closure"},
    {"issue": 131, "contract": "actor/asset source closure"},
)

MISSING_PREREQUISITE = (
    "Legal US Pikmin 2 disc image (GPVE01 rev 0) or an extracted "
    "'user/Mukki/mapunits/caveinfo/ch_MUKI_redblue.txt' file decoded as "
    "shift_jis. Provide the file bytes to decode_cave(); weighted roster "
    "rows stay source data, never actor counts."
)


def sha256_bytes(data):
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("source bytes required")
    return hashlib.sha256(bytes(data)).hexdigest()


def decode_cave(cave_text):
    """Decode caveinfo text and return the 2-floor definition list.

    Reuses the existing parser (floor framing, parameter, roster and
    gate/cap validation). Raises ValueError on malformed input or when
    floor coverage is not exactly the catalogued 2 floors.
    """
    if not isinstance(cave_text, str) or not cave_text.strip():
        raise ValueError("caveinfo text is missing or empty")
    floors = cave_definition(cave_text)
    if len(floors) != EXPECTED_FLOORS:
        raise ValueError(
            "floor coverage mismatch: got %d, expected %d" % (len(floors), EXPECTED_FLOORS))
    if [floor["number"] for floor in floors] != [1, 2]:
        raise ValueError("floor numbering mismatch")
    return floors


def summarize_roster(floors):
    """Preserve source roster IDs/weights as data (no placement resolution)."""
    summary = []
    for floor in floors:
        summary.append(dict(
            number=floor["number"],
            enemies=[dict(entry) for entry in floor["enemies"]],
            treasures=[dict(entry) for entry in floor["treasures"]],
            parameters=dict(floor["parameters"]),
        ))
    return summary


def check_challenge(challenge):
    """Validate an optional challenge row against the catalogued pin."""
    if challenge is None:
        return dict(status="baseline_catalogued", detail=dict(EXPECTED_CHALLENGE))
    if not isinstance(challenge, dict):
        raise ValueError("challenge row must be a dict")
    for key, expected in EXPECTED_CHALLENGE.items():
        if challenge.get(key) != expected:
            raise ValueError("challenge field mismatch: " + key)
    return dict(status="matches_catalogue", detail=dict(EXPECTED_CHALLENGE))


def build_manifest(cave_text, cave_sha256=None, challenge=None):
    """Build the isolated P0 metadata packet for ch_MUKI_redblue."""
    floors = decode_cave(cave_text)
    if cave_sha256 is not None:
        if not isinstance(cave_sha256, str) or len(cave_sha256) != 64:
            raise ValueError("cave_sha256 must be 64 hex chars")
    hash_status = "hash_validated" if cave_sha256 == EXPECTED_SHA256 else "hash_unvalidated"
    manifest = dict(
        schema=1,
        lane="p2-challenge-ch_muki_redblue",
        cave_id=CAVE_ID,
        issue=ISSUE,
        source=SOURCE_PATH,
        source_sha256=cave_sha256,
        expected_source_sha256=EXPECTED_SHA256,
        hash_status=hash_status,
        floors=EXPECTED_FLOORS,
        floor_coverage=[floor["number"] for floor in floors],
        roster=summarize_roster(floors),
        challenge=check_challenge(challenge),
        resource_closure=[
            dict(path=SOURCE_PATH, sha256=cave_sha256, status=hash_status),
        ],
        blockers=[dict(entry) for entry in BLOCKERS],
        placement_policy=("no runtime placements emitted; weighted roster rows "
                          "stay source data, never actor counts"),
        playable=False,
    )
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a dict")
    if manifest.get("schema") != 1:
        raise ValueError("unsupported manifest schema")
    if manifest.get("cave_id") != CAVE_ID or manifest.get("source") != SOURCE_PATH:
        raise ValueError("manifest cave/source mismatch")
    if manifest.get("floors") != EXPECTED_FLOORS:
        raise ValueError("manifest floor count mismatch")
    if manifest.get("floor_coverage") != [1, 2]:
        raise ValueError("manifest floor coverage mismatch")
    roster = manifest.get("roster")
    if not isinstance(roster, list) or len(roster) != EXPECTED_FLOORS:
        raise ValueError("manifest roster floor coverage mismatch")
    for floor in roster:
        for entry in floor.get("enemies", []):
            if set(entry) != {"id", "packed_weight", "placement_type"}:
                raise ValueError("enemy roster entry shape mismatch")
        for entry in floor.get("treasures", []):
            if set(entry) != {"id", "packed_weight"}:
                raise ValueError("treasure roster entry shape mismatch")
    if manifest.get("playable") is not False:
        raise ValueError("P0 manifest must not claim playability")
    return True


def missing_prerequisite():
    return MISSING_PREREQUISITE


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cave", type=Path, default=None,
                        help="path to extracted ch_MUKI_redblue.txt")
    parser.add_argument("--output", type=Path, default=None,
                        help="write manifest JSON here (otherwise stdout)")
    args = parser.parse_args(argv)
    if args.cave is None:
        raise SystemExit("missing prerequisite: " + MISSING_PREREQUISITE)
    raw = args.cave.read_bytes()
    manifest = build_manifest(raw.decode("shift_jis"), sha256_bytes(raw))
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
