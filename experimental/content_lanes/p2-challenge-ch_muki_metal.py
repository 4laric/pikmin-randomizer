"""P0 source-audit / import-contract adapter for P2 Challenge 02: ch_MUKI_metal.

Lane p2-challenge-ch_muki_metal, issue #535. Implementation owner: Codex
through shared GitHub account 4laric; contributor Muse Spark 1.3 via OpenCode.

This module owns ONLY this source entry: ``ch_MUKI_metal`` (p2-challenge),
source ``user/Mukki/mapunits/caveinfo/ch_MUKI_metal.txt``. It reuses the
shared caveinfo parser (``experimental.pikmin2_cave``) and the canonical
inventory/lane records without editing them.

Authoritative metadata (from ``docs/PIKMIN2_CONTENT_INVENTORY.json``
``source_sha256`` and ``docs/PIKMIN_CONTENT_IMPORT_LANES.json`` lane
``p2-challenge-ch_muki_metal``; English title unresolved, source ID and UI
index authoritative):

- floors: 2; floor timers: [130.0, 100.0] seconds
- starting Pikmin by native color/maturity: 50 leaf (maturity 2) of color 0,
  nothing else (7x3 matrix, first row [0, 0, 50])
- bitter sprays: 1; spicy sprays: 1; legacy_time: 0.0
- treasure_count_field: 0; ui_index: 1; table_order: 6

Source honesty: no legal copy of the caveinfo bytes exists on this host
(searched: supported ISO path, bbft asset dataDir, pikmin2-research
checkout, workspace tree). Manifests therefore record the inventory hash
as the expected value and every decode path reports the exact missing
prerequisite instead of inventing values. Weighted enemy/treasure rows are
reported as definitions with counts only, never expanded into placements.

Stdlib only.
"""

import hashlib
import json
import math
import sys
from pathlib import PurePosixPath

SOURCE_ID = "ch_MUKI_metal"
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/ch_MUKI_metal.txt"
EXPECTED_SHA256 = "903b43195c5f2d53683a462af4fe1383bfe0604551f2935cb78fc3f55d0de1f1"
STAGES_TABLE_PATH = "user/Matoba/challenge/stages.txt"
STAGES_TABLE_SHA256 = "59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1"
INVENTORY_DOC = "docs/PIKMIN2_CONTENT_INVENTORY.json"
LANE_DOC = "docs/PIKMIN_CONTENT_IMPORT_LANES.json"

# Read-only candidate locations checked by locate_source, in order. None is
# written; absence of all of them is the exact missing prerequisite.
SEARCH_CANDIDATES = (
    "output/pikmin2-runtime/pikmin2-source-test.iso!/user/Mukki/mapunits/caveinfo/ch_MUKI_metal.txt",
    "C:/Users/alari/bbft/dist/cohesion/pikmin/assets/dataDir/user/Mukki/mapunits/caveinfo/ch_MUKI_metal.txt",
    "native/pikmin2-research/user/Mukki/mapunits/caveinfo/ch_MUKI_metal.txt",
)

DETAILS = {
    "cave_id": SOURCE_ID,
    "cave_path": SOURCE_PATH,
    "floors": 2,
    "floor_seconds": [130.0, 100.0],
    "pikmin_by_native_color_and_maturity": [
        [0, 0, 50],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ],
    "bitter_sprays": 1,
    "spicy_sprays": 1,
    "legacy_time": 0.0,
    "treasure_count_field": 0,
    "ui_index": 1,
    "table_order": 6,
}

# P1/P2 runtime prerequisites owned elsewhere; P0 proceeds without them.
FRAMEWORK_BLOCKERS = {
    "136": "P2 Challenge runtime framework (starting populations, sprays, per-floor timing, keys/exits, scores, retry, ordinary/deathless result semantics)",
    "137": "P2 Challenge content owner (30 per-stage children; all 59 floors audited/tested on framework/generator pins)",
    "129": "Cave generation/seams/navigation contract pin (do not fork a replacement)",
    "130": "Actor/assets/species and hazard closure (caps/helpers/held items; unresolved enemy admission blocks promotion, not preparatory work)",
    "131": "Actor/assets/species and hazard closure (see #130)",
}


class SourceUnavailable(ValueError):
    """Raised when no legal copy of the caveinfo bytes exists on this host."""


class SourceHashMismatch(ValueError):
    """Raised when available bytes do not match the inventory hash."""


def source_candidates():
    """Return the ordered read-only locations checked for the source file."""
    return list(SEARCH_CANDIDATES)


def missing_prerequisite(checked=None):
    """Return the exact missing-prerequisite record for unavailable source."""
    return {
        "source_id": SOURCE_ID,
        "source_path": SOURCE_PATH,
        "expected_sha256": EXPECTED_SHA256,
        "checked": list(checked) if checked is not None else source_candidates(),
        "prerequisite": (
            "US GPVE01 revision 0 legal disc source providing "
            + SOURCE_PATH + " (sha256 " + EXPECTED_SHA256 + ")"
        ),
    }


def locate_source(candidates=None, exists=None):
    """Return the first available source path, else raise SourceUnavailable.

    ``exists`` is an injectable predicate (defaults to filesystem check)
    so the boundary is testable without a disc on the host.
    """
    checked = list(candidates) if candidates is not None else source_candidates()
    probe = exists if exists is not None else _filesystem_exists
    for candidate in checked:
        if probe(candidate):
            return candidate
    raise SourceUnavailable(
        "No legal copy of %s on this host; checked: %s"
        % (SOURCE_PATH, ", ".join(checked))
    )


def _filesystem_exists(candidate):
    from pathlib import Path
    if candidate.startswith("output/"):
        return False  # ISO-container member syntax, not a direct file
    if "!" in candidate:
        return False
    try:
        return Path(candidate).is_file()
    except (OSError, ValueError):
        return False


def verify_bytes(data):
    """Validate raw source bytes against the inventory hash; return digest."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise SourceHashMismatch("Empty or non-bytes source payload")
    digest = hashlib.sha256(bytes(data)).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SourceHashMismatch(
            "Source hash %s does not match inventory %s" % (digest, EXPECTED_SHA256)
        )
    return digest


def decode_definitions(text):
    """Decode caveinfo text with the shared parser; return floor records.

    Raises ValueError on malformed input (from the shared parser). Weighted
    rows stay definitions with counts; nothing here emits placements.
    """
    from experimental.pikmin2_cave import cave_definition
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Empty caveinfo text")
    return cave_definition(text)


def validate_details(details=None):
    """Validate the lane details record shape; return a normalized copy."""
    record = DETAILS if details is None else details
    if not isinstance(record, dict):
        raise ValueError("Details record must be a mapping")
    floors = record.get("floors")
    if type(floors) is not int or floors <= 0 or floors > 128:
        raise ValueError("Invalid floor count")
    timers = record.get("floor_seconds")
    if (not isinstance(timers, list) or len(timers) != floors
            or any(type(t) not in (int, float) or not math.isfinite(t) or t <= 0
                   for t in timers)):
        raise ValueError("floor_seconds must list one positive finite timer per floor")
    for key in ("bitter_sprays", "spicy_sprays", "treasure_count_field",
                "ui_index", "table_order"):
        if type(record.get(key)) is not int or record.get(key) < 0:
            raise ValueError("Invalid non-negative integer field: " + key)
    matrix = record.get("pikmin_by_native_color_and_maturity")
    if (not isinstance(matrix, list) or len(matrix) != 7
            or any(not isinstance(row, list) or len(row) != 3
                   or any(type(v) is not int or v < 0 for v in row)
                   for row in matrix)):
        raise ValueError("Pikmin roster must be a 7x3 matrix of non-negative ints")
    if record.get("cave_id") != SOURCE_ID or record.get("cave_path") != SOURCE_PATH:
        raise ValueError("Details record names another source entry")
    return dict(record, floor_seconds=list(timers),
                pikmin_by_native_color_and_maturity=[list(r) for r in matrix])


def floor_coverage(floors, expected=2):
    """Check decoded floors cover 1..expected with no gap or duplication."""
    numbers = []
    for floor in floors or []:
        number = floor.get("number") if isinstance(floor, dict) else None
        if type(number) is not int:
            return {"complete": False, "reason": "floor record lacks integer number"}
        numbers.append(number)
    if sorted(numbers) != list(range(1, expected + 1)):
        return {"complete": False,
                "reason": "floor numbers %s do not cover 1..%d" % (sorted(numbers), expected)}
    return {"complete": True, "floors": sorted(numbers)}


def audit(source_bytes=None, details=None, exists=None):
    """Build the P0 audit report for this source entry.

    Without source bytes this records the exact missing prerequisite and
    validates the authoritative metadata record; with bytes it additionally
    hash-verifies and decodes definitions. Never invents values.
    """
    record = validate_details(details)
    report = {
        "source_id": SOURCE_ID,
        "source_path": SOURCE_PATH,
        "expected_sha256": EXPECTED_SHA256,
        "details": record,
        "source": None,
        "definitions": None,
        "floor_coverage": {"complete": False, "reason": "source unavailable"},
        "weighted_definitions": "not decoded (source unavailable); rows stay definitions, never placements",
        "unsupported": [
            "gate/cap rosters: unevaluated without source bytes",
            "enemy admission per floor: unevaluated without source bytes; unresolved admission blocks P1 promotion, not P0",
        ],
        "framework_blockers": dict(FRAMEWORK_BLOCKERS),
        "playability": "no claim: metadata audit only",
    }
    if source_bytes is None:
        try:
            found = locate_source(exists=exists)
        except SourceUnavailable:
            report["source"] = {"available": False,
                                "missing_prerequisite": missing_prerequisite()}
            return report
        report["source"] = {"available": True, "located": found,
                            "note": "bytes not loaded; pass source_bytes to verify and decode"}
        return report
    report["source"] = {"available": True, "sha256": verify_bytes(source_bytes)}
    text = bytes(source_bytes).decode("shift_jis", errors="strict") \
        if isinstance(source_bytes, (bytes, bytearray)) else None
    try:
        floors = decode_definitions(text)
    except (ValueError, UnicodeDecodeError) as error:
        report["definitions"] = {"decoded": False, "error": str(error)}
        return report
    enemies = sum(len(f.get("enemies", [])) for f in floors)
    treasures = sum(len(f.get("treasures", [])) for f in floors)
    report["definitions"] = {
        "decoded": True,
        "floor_count": len(floors),
        "weighted_enemy_rows": enemies,
        "weighted_treasure_rows": treasures,
    }
    report["weighted_definitions"] = (
        "%d weighted enemy rows and %d weighted treasure rows across %d floors; "
        "definitions with counts only, never placements" % (enemies, treasures, len(floors))
    )
    coverage = floor_coverage(floors, record["floors"])
    report["floor_coverage"] = coverage
    if len(floors) != record["floors"]:
        coverage["complete"] = False
        coverage["reason"] = "decoded %d floors, lane record expects %d" % (
            len(floors), record["floors"])
    report["unsupported"] = [
        "gate/cap rosters: shared parser rejects non-'0' gate/cap rows at decode; decoded file is clean" if coverage.get("complete")
        else "gate/cap rosters: unevaluated (floor coverage incomplete)",
        "enemy admission per floor: decoded enemy ids require #130/#131 closure before P1 promotion",
    ]
    return report


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-bytes", help="Path to local caveinfo bytes (optional)")
    parser.add_argument("--locate-only", action="store_true")
    args = parser.parse_args(argv)
    if args.locate_only:
        try:
            print(json.dumps({"located": locate_source()}, indent=2))
        except SourceUnavailable as error:
            print(json.dumps({"available": False, "error": str(error),
                              "missing_prerequisite": missing_prerequisite()}, indent=2))
            return 1
        return 0
    payload = None
    if args.source_bytes:
        with open(args.source_bytes, "rb") as handle:
            payload = handle.read()
    print(json.dumps(audit(source_bytes=payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
