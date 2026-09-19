"""Gap-stages stage-select extension over the verified #669/#705 selectors (#743).

Wraps the committed selectors read-only (no re-derivation, no duplication, no
shared edits) and extends stage resolution to the six gap P2 challenge keys
whose P1 lanes cannot boot because the #705 table refuses everything but
kusachi/02tile. Each gap key resolves to a validated boot-selection record
cross-checked against its done P0 import base (canonical plan + inventory);
kusachi/02tile still resolve unchanged through the wrapped selectors; unknown
keys (including P1 chal<N> slots) are refused fail-closed.
"""
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

SCHEMA = "p2-challenge-gap-stages-select-v1"
SELECTOR_COMMIT = "01a35f3a5a74ed2a3fe1e07ddcde23184804010e"
SELECTOR_PATH = "experimental/pikmin2_challenge_stage_select_boot.py"
SELECTOR_BLOB_SHA256 = "d8c2413cb60616571e3df02be1f9ef0b40ced36f9580a513fb760fa4203410f0"
LANDING_COMMIT = "2cf2141868e98c561d633c1bcfd41560da64c223"
LANDING_PATH = "experimental/pikmin2_challenge_02tile_stage_select_landing.py"
LANDING_BLOB_SHA256 = "ff376f49917c2a3c9178cc03d3f30223bc79a470ad07f4f55cea79ca2faf7722"
KUSACHI_KEY = "ch_NARI_01kusachi"
TILE_KEY = "ch_NARI_02tile"
GAP_KEYS = (
    "ch_MUKI_damagumo",
    "ch_MUKI_houdai",
    "ch_NARI_03toy",
    "ch_NARI_06start3hard",
    "ch_MUKI_redblue",
    "ch_NARI_07whitepurple",
)
CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")


class GapStagesError(ValueError):
    """Refusal: unknown key, pin drift, or unreadable baseline."""


def _pinned_source(commit, path, expected_sha256):
    proc = subprocess.run(
        ["git", "-C", str(CANONICAL_ROOT), "show", "%s:%s" % (commit, path)],
        capture_output=True, timeout=60)
    if proc.returncode != 0:
        raise GapStagesError("committed selector unreadable at " + commit)
    if hashlib.sha256(proc.stdout).hexdigest() != expected_sha256:
        raise GapStagesError("committed selector bytes drifted; refusing substitute")
    return proc.stdout


def load_base_selector():
    """The committed #669 selector, byte-pinned and read-only."""
    blob = _pinned_source(SELECTOR_COMMIT, SELECTOR_PATH, SELECTOR_BLOB_SHA256)
    module = types.ModuleType("pikmin2_challenge_stage_select_boot_pinned")
    exec(compile(blob, SELECTOR_PATH, "exec"), module.__dict__)
    return module


def load_tile_landing():
    """The committed #705 landing adapter, byte-pinned and read-only."""
    blob = _pinned_source(LANDING_COMMIT, LANDING_PATH, LANDING_BLOB_SHA256)
    module = types.ModuleType("pikmin2_challenge_02tile_stage_select_landing_pinned")
    exec(compile(blob, LANDING_PATH, "exec"), module.__dict__)
    return module


def base_records(root=None):
    """Re-verification record: kusachi via #669 and 02tile via #705, unchanged."""
    base_root = Path(root) if root is not None else CANONICAL_ROOT
    selector = load_base_selector()
    landing = load_tile_landing()
    kusachi = selector.select_stage(KUSACHI_KEY, base_root)
    tile, provenance = landing.select_stage_extended(TILE_KEY, base_root)
    if kusachi["cave_id"] != KUSACHI_KEY or tile["cave_id"] != TILE_KEY:
        raise GapStagesError("base selector resolution drifted")
    return {"kusachi": kusachi, "tile": tile, "tile_provenance": provenance}


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as stream:
            return json.load(stream)
    except (OSError, ValueError) as error:
        raise GapStagesError("unreadable canonical baseline: " + str(path)) from error


def gap_baseline(stage_key, root=None):
    """One gap key's boot-selection fields from the canonical plan+inventory."""
    base_root = Path(root) if root is not None else CANONICAL_ROOT
    plan = _read_json(base_root / "docs/PIKMIN_CONTENT_IMPORT_LANES.json")
    lane = None
    for entry in plan.get("lanes", []):
        if entry.get("source_id") == stage_key and entry.get("category") == "p2-challenge":
            lane = entry
            break
    if lane is None:
        raise GapStagesError("stage %s missing from canonical plan" % stage_key)
    details = lane.get("details") or {}
    inventory = _read_json(base_root / "docs/PIKMIN2_CONTENT_INVENTORY.json")
    inv = None
    for stage in inventory.get("challenge", {}).get("stages", []):
        if stage.get("cave_id") == stage_key:
            inv = stage
            break
    if inv is None:
        raise GapStagesError("stage %s missing from canonical inventory" % stage_key)
    for key in ("cave_id", "cave_path", "floors", "pikmin_by_native_color_and_maturity",
                "legacy_time", "bitter_sprays", "spicy_sprays", "treasure_count_field",
                "ui_index", "floor_seconds", "table_order"):
        if details.get(key) != inv.get(key):
            raise GapStagesError("stage key %r drifts between plan and inventory" % (key,))
    if lane.get("source") != inv.get("cave_path"):
        raise GapStagesError("source path drift for challenge stage")
    source_sha = inv.get("source_sha256") or lane.get("source_sha256")
    if not source_sha:
        raise GapStagesError("recorded source pin missing for %s" % stage_key)
    return {"details": details, "source_sha256": source_sha}


def gap_record(stage_key, root=None):
    """Validated boot-selection record for one gap key (same shape as #669 records)."""
    if stage_key not in GAP_KEYS:
        raise GapStagesError("not a gap stage key: %r" % (stage_key,))
    base = gap_baseline(stage_key, root)
    details = base["details"]
    matrix = details["pikmin_by_native_color_and_maturity"]
    if (not isinstance(matrix, list) or len(matrix) != 7
            or any(not isinstance(row, list) or len(row) != 3
                   or any(type(v) is not int or v < 0 for v in row) for row in matrix)):
        raise GapStagesError("baseline roster matrix malformed")
    seconds = details["floor_seconds"]
    if (not isinstance(seconds, list) or len(seconds) != details["floors"]
            or any(not isinstance(v, (int, float)) or not v > 0 for v in seconds)):
        raise GapStagesError("baseline floor timers malformed")
    return {
        "cave_id": stage_key,
        "cave_path": details["cave_path"],
        "source_sha256": base["source_sha256"],
        "ui_index": details["ui_index"],
        "table_order": details["table_order"],
        "floors": details["floors"],
        "floor_seconds": [float(v) for v in seconds],
        "pikmin_by_native_color_and_maturity": [list(row) for row in matrix],
        "bitter_sprays": details["bitter_sprays"],
        "spicy_sprays": details["spicy_sprays"],
        "legacy_time": float(details["legacy_time"]),
        "treasure_count_field": details["treasure_count_field"],
    }


def select_stage_extended(stage_key, root=None):
    """Resolve kusachi/02tile via the wrapped selectors, else a gap key; refuse the rest."""
    if not isinstance(stage_key, str) or not stage_key:
        raise GapStagesError("stage key must be a nonempty string")
    base_root = Path(root) if root is not None else CANONICAL_ROOT
    try:
        return load_base_selector().select_stage(stage_key, base_root), "base"
    except Exception:
        pass
    try:
        record, provenance = load_tile_landing().select_stage_extended(stage_key, base_root)
        return record, "landing-" + provenance
    except Exception:
        pass
    if stage_key in GAP_KEYS:
        return gap_record(stage_key, root), "gap"
    if isinstance(stage_key, str) and stage_key.startswith("chal"):
        raise GapStagesError("P1 challenge slots are a different namespace (owner: p1-challenge lanes)")
    raise GapStagesError("unknown P2 challenge stage: %r" % (stage_key,))


def render_boot_request_extended(record):
    """Canonical boot-request text for kusachi, 02tile or gap records."""
    required = ("cave_id", "cave_path", "source_sha256", "ui_index", "table_order",
                "floors", "floor_seconds", "pikmin_by_native_color_and_maturity",
                "bitter_sprays", "spicy_sprays", "legacy_time", "treasure_count_field")
    missing = [k for k in required if k not in record]
    if missing:
        raise GapStagesError("boot record missing fields: %s" % sorted(missing))
    if record["cave_id"] not in (KUSACHI_KEY, TILE_KEY) + GAP_KEYS:
        raise GapStagesError("boot record identity mismatch")
    if not isinstance(record["cave_path"], str) or not record["cave_path"].endswith(
            "/" + record["cave_id"] + ".txt"):
        raise GapStagesError("boot record path/identity mismatch")
    lines = ["P2_CHALLENGE_STAGE_SELECT_1",
             "cave %s ui_index %d table_order %d floors %d" % (
                 record["cave_id"], record["ui_index"], record["table_order"], record["floors"]),
             "source %s %s" % (record["cave_path"], record["source_sha256"]),
             "timers %s legacy %s" % (
                 " ".join(str(v) for v in record["floor_seconds"]), record["legacy_time"]),
             "sprays bitter %d spicy %d treasure_field %d" % (
                 record["bitter_sprays"], record["spicy_sprays"], record["treasure_count_field"])]
    for row in record["pikmin_by_native_color_and_maturity"]:
        lines.append("roster %d %d %d" % tuple(row))
    return "\n".join(lines) + "\n"
