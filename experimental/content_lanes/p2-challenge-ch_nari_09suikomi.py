"""P0 source-audit adapter for P2 Challenge 26: ch_NARI_09suikomi (issue #558).

Isolated metadata/import-contract boundary for exactly one content entry.
It never edits global parsers, schema, species data, or other levels, and it
never configures, builds, or launches anything.

Baseline vs decoded data (honest labeling):
- ``BASELINE_RECORD`` is the catalogued stage row from
  docs/PIKMIN2_CONTENT_INVENTORY.json (challenge/stages entry with
  table_order 23) and docs/PIKMIN_CONTENT_IMPORT_LANES.json. It is the P0
  baseline, not a fresh decode of the retail caveinfo file.
- The retail file ``user/Mukki/mapunits/caveinfo/ch_NARI_09suikomi.txt`` is
  not redistributed and was not present on this machine; see
  ``missing_prerequisites()``. No floor/generator bytes are decoded here.
  Full cave parsing stays with the existing generator owner (#129); the
  Challenge runtime framework stays with #136 and content parent #137.
- Weighted/definition rows are never expanded into actor instances here
  (cf. experimental/pikmin2_content.py roster(), which raises on weights
  instead of fabricating placements).

Load this hyphenated module without a package import::

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "suikomi",
        "experimental/content_lanes/p2-challenge-ch_nari_09suikomi.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath

SOURCE_ID = "ch_NARI_09suikomi"
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/ch_NARI_09suikomi.txt"
SOURCE_SHA256 = "9d547811bc30a8970659c501b596afbbd903e11ed3229ce3e97e60104aaa5dc5"
STAGES_PATH = "user/Matoba/challenge/stages.txt"
STAGES_SHA256 = "59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1"
LANE = "p2-challenge-ch_nari_09suikomi"
ISSUE = 558

EXPECTED_TABLE_ORDER = 23
EXPECTED_UI_INDEX = 25
EXPECTED_FLOORS = 1

# Row/column positions are opaque native indices. The inventory does not
# label which native color or maturity each position names, so this adapter
# reports them positionally and never assigns color/maturity names.
ROSTER_ROWS = 7
ROSTER_COLS = 3


class StageRecordError(ValueError):
    """A catalogued stage row violates the ch_NARI_09suikomi import contract."""


# Exact catalogued baseline (inventory challenge entry, table_order 23).
# Baseline, not a fresh source decode; see module docstring.
BASELINE_RECORD = {
    "table_order": 23,
    "cave_id": "ch_NARI_09suikomi",
    "cave_path": "user/Mukki/mapunits/caveinfo/ch_NARI_09suikomi.txt",
    "floors": 1,
    "pikmin_by_native_color_and_maturity": [
        [0, 0, 0],
        [0, 0, 30],
        [0, 0, 30],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ],
    "legacy_time": 450.0,
    "bitter_sprays": 1,
    "spicy_sprays": 2,
    "treasure_count_field": 0,
    "ui_index": 25,
    "floor_seconds": [180.0],
    "issue": 137,
}


def _finite_nonnegative(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StageRecordError(label + " must be a number")
    if value != value or value in (float("inf"), float("-inf")) or value < 0:
        raise StageRecordError(label + " must be finite and nonnegative")
    return value


def validate_stage_record(record):
    """Strictly validate a catalogued stage row against this entry's contract.

    Returns a normalized deep copy. Raises StageRecordError on any missing
    key, identity mismatch, misshapen roster matrix, negative/nonfinite
    number, or floors/timer-count disagreement. Unknown extra keys are
    rejected so silent schema drift cannot pass as this source.
    """
    if not isinstance(record, dict):
        raise StageRecordError("Stage record must be an object")
    expected_keys = set(BASELINE_RECORD)
    if set(record) != expected_keys:
        missing = sorted(expected_keys - set(record))
        extra = sorted(set(record) - expected_keys)
        raise StageRecordError(
            "Stage record keys differ (missing=%s extra=%s)" % (missing, extra))
    if record["table_order"] != EXPECTED_TABLE_ORDER:
        raise StageRecordError("table_order must be %d" % EXPECTED_TABLE_ORDER)
    if record["cave_id"] != SOURCE_ID:
        raise StageRecordError("cave_id must be " + SOURCE_ID)
    if record["cave_path"] != SOURCE_PATH:
        raise StageRecordError("cave_path must be " + SOURCE_PATH)
    if record["floors"] != EXPECTED_FLOORS:
        raise StageRecordError("floors must be %d" % EXPECTED_FLOORS)
    if record["issue"] != 137:
        raise StageRecordError("content parent issue must be 137")
    if record["ui_index"] != EXPECTED_UI_INDEX:
        raise StageRecordError("ui_index must be %d" % EXPECTED_UI_INDEX)
    matrix = record["pikmin_by_native_color_and_maturity"]
    if (not isinstance(matrix, list) or len(matrix) != ROSTER_ROWS
            or any(not isinstance(row, list) or len(row) != ROSTER_COLS
                   for row in matrix)):
        raise StageRecordError("Roster matrix must be %dx%d integers"
                               % (ROSTER_ROWS, ROSTER_COLS))
    for at, row in enumerate(matrix):
        for col, value in enumerate(row):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise StageRecordError(
                    "Roster cell [%d][%d] must be a nonnegative integer" % (at, col))
    seconds = record["floor_seconds"]
    if not isinstance(seconds, list) or len(seconds) != record["floors"]:
        raise StageRecordError("floor_seconds must list one timer per floor")
    for value in seconds:
        _finite_nonnegative(value, "floor_seconds entry")
    _finite_nonnegative(record["legacy_time"], "legacy_time")
    for key in ("bitter_sprays", "spicy_sprays", "treasure_count_field"):
        value = record[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise StageRecordError(key + " must be a nonnegative integer")
    return copy.deepcopy(record)


def floor_coverage(record):
    """Return the complete 1-based floor list; fail closed on any gap."""
    validated = validate_stage_record(record)
    floors = validated["floors"]
    covered = list(range(1, floors + 1))
    if len(validated["floor_seconds"]) != len(covered):
        raise StageRecordError("Timer coverage does not span all floors")
    return covered


def resource_closure(record):
    """Summarize starting definitions; never fabricate actor placements.

    Totals are roster/spray/timer definitions from the catalogued row, not
    spawn instances. The result intentionally carries no ``actors``,
    ``placements``, or ``slots`` keys: weighted definition rows stay
    definitions until the accepted generator (#129) resolves them.
    """
    validated = validate_stage_record(record)
    matrix = validated["pikmin_by_native_color_and_maturity"]
    by_row = [sum(row) for row in matrix]
    by_col = [sum(matrix[r][c] for r in range(ROSTER_ROWS))
              for c in range(ROSTER_COLS)]
    return {
        "source_id": SOURCE_ID,
        "floors": validated["floors"],
        "floor_seconds": list(validated["floor_seconds"]),
        "starting_roster_total": sum(by_row),
        "starting_roster_by_row": by_row,
        "starting_roster_by_col": by_col,
        "bitter_sprays": validated["bitter_sprays"],
        "spicy_sprays": validated["spicy_sprays"],
        "treasure_count_field": validated["treasure_count_field"],
        "definitions_are_not_placements": True,
    }


def verify_source_bytes(data, expected_sha256=SOURCE_SHA256):
    """Hash-gate raw source bytes; never parse unknown layouts here.

    Returns the hex digest when it matches. Raises StageRecordError on any
    mismatch (including empty input), so a foreign or truncated file can
    never pass as this source.
    """
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise StageRecordError("Source bytes are missing or empty")
    digest = hashlib.sha256(bytes(data)).hexdigest()
    if digest != expected_sha256:
        raise StageRecordError("Source hash mismatch for " + SOURCE_PATH)
    return digest


def missing_prerequisites(search_roots=()):
    """Probe local disk (read-only) for the two retail files this P0 needs.

    Returns one entry per absent/unverifiable prerequisite with the pinned
    hash and an exact supply instruction. Files are never created, fetched,
    or redistributed by this adapter; supply them from a local legal disc
    or ISO outside any worktree.
    """
    wanted = (
        (SOURCE_PATH, SOURCE_SHA256, "retail caveinfo definition"),
        (STAGES_PATH, STAGES_SHA256, "challenge stage table"),
    )
    roots = [Path(r) for r in search_roots] if search_roots else []
    missing = []
    for rel, pinned, role in wanted:
        found = None
        for root in roots:
            candidate = Path(root, *PurePosixPath(rel).parts)
            if candidate.is_file():
                found = candidate
                break
        if found is None:
            missing.append({
                "path": rel,
                "sha256": pinned,
                "role": role,
                "status": "absent",
                "supply": "Provide a local legal US GPVE01 rev0 disc/ISO path; "
                          "do not commit assets. P1 decode waits on this file.",
            })
            continue
        try:
            digest = hashlib.sha256(found.read_bytes()).hexdigest()
        except OSError:
            digest = None
        if digest != pinned:
            missing.append({
                "path": rel,
                "sha256": pinned,
                "role": role,
                "status": "hash_mismatch",
                "supply": "Local copy at %s does not match the pinned hash; "
                          "re-extract from the legal disc." % found,
            })
    return missing


def blockers():
    """Exact native/framework blockers to promotion (not to P0 preparation)."""
    return [
        {"id": "#136", "owner": "P2 Challenge runtime framework",
         "why": "Per-floor timing, keys/exits, scoring, retry and "
                "ordinary/deathless result semantics are unvalidated for this stage."},
        {"id": "#137", "owner": "P2 Challenge content parent",
         "why": "Stage-level integration and the 59-floor audit consume this "
                "packet; this lane must not duplicate parent scope."},
        {"id": "#129", "owner": "Cave generation contract",
         "why": "Floor topology, seams, holes, and weighted-row resolution "
                "require the accepted generator pin; no layout is generated here."},
        {"id": "#130/#131", "owner": "Actor/asset/species owners",
         "why": "Full resource closure (caps/helpers/held items) and any "
                "unadmitted suikomi-encounter species block promotion, not P0."},
        {"id": "source-bytes", "owner": "Local legal disc/ISO",
         "why": "Retail caveinfo bytes absent locally; P1 floor decode waits "
                "on the pinned hash " + SOURCE_SHA256[:16] + "..."},
        {"id": "display-name", "owner": "Localization audit",
         "why": "English title unresolved; source ID ch_NARI_09suikomi and UI "
                "index 25 stay authoritative, never guessed."},
    ]


def audit_packet(record=None, search_roots=()):
    """Build the reviewed P0 packet: validated baseline plus open items."""
    validated = validate_stage_record(BASELINE_RECORD if record is None else record)
    closure = resource_closure(validated)
    return {
        "schema": 1,
        "lane": LANE,
        "issue": ISSUE,
        "source_id": SOURCE_ID,
        "source_path": SOURCE_PATH,
        "source_sha256": SOURCE_SHA256,
        "stages_sha256": STAGES_SHA256,
        "baseline": "catalogued inventory row (table_order 23); "
                    "not a fresh retail-file decode",
        "record": validated,
        "floor_coverage": floor_coverage(validated),
        "resource_closure": closure,
        "missing_prerequisites": missing_prerequisites(search_roots),
        "blockers": blockers(),
        "playability": "none claimed; P1 runtime and P2 acceptance remain OPEN",
    }


def main(argv=None):
    """Print the audit packet as JSON: ``audit [--root <dir>]...``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit",))
    parser.add_argument("--root", action="append", default=[],
                        help="Local search root probed read-only for retail files")
    args = parser.parse_args(argv)
    if args.command == "audit":
        print(json.dumps(audit_packet(search_roots=args.root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
