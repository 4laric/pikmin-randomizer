"""02tile stage-select landing adapter (lane challenge-02tile-stage-select-landing, #705)."""
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

SCHEMA = "p2-challenge-02tile-stage-select-landing-v1"
SELECTOR_COMMIT = "01a35f3a5a74ed2a3fe1e07ddcde23184804010e"
SELECTOR_PATH = "experimental/pikmin2_challenge_stage_select_boot.py"
SELECTOR_BLOB_SHA256 = "d8c2413cb60616571e3df02be1f9ef0b40ced36f9580a513fb760fa4203410f0"
TILE_KEY = "ch_NARI_02tile"
TILE_UI_INDEX = 4
CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")


class LandingError(ValueError):
    """Refusal: unknown key, pin drift, or unreadable baseline."""


def selector_source():
    proc = subprocess.run(
        ["git", "-C", str(CANONICAL_ROOT), "show",
         "%s:%s" % (SELECTOR_COMMIT, SELECTOR_PATH)],
        capture_output=True, timeout=60)
    if proc.returncode != 0:
        raise LandingError("committed #669 selector unreadable at " + SELECTOR_COMMIT)
    return proc.stdout


def load_selector():
    blob = selector_source()
    if hashlib.sha256(blob).hexdigest() != SELECTOR_BLOB_SHA256:
        raise LandingError("committed #669 selector bytes drifted; refusing substitute")
    module = types.ModuleType("pikmin2_challenge_stage_select_boot_pinned")
    exec(compile(blob, SELECTOR_PATH, "exec"), module.__dict__)
    return module


def selector_record():
    """Re-verification record for the committed #669 selector (read-only)."""
    module = load_selector()
    kusachi = module.select_stage("ch_NARI_01kusachi", CANONICAL_ROOT)
    return {
        "commit": SELECTOR_COMMIT,
        "path": SELECTOR_PATH,
        "blob_sha256": SELECTOR_BLOB_SHA256,
        "kusachi_resolves": kusachi["cave_id"] == "ch_NARI_01kusachi",
        "kusachi_ui_index": kusachi["ui_index"],
        "module": module,
    }


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as stream:
            return json.load(stream)
    except (OSError, ValueError) as error:
        raise LandingError("unreadable canonical baseline: " + str(path)) from error


def tile_baseline(root=None):
    """02tile boot-selection fields from the canonical plan+inventory (cross-checked)."""
    root = Path(root) if root is not None else CANONICAL_ROOT
    plan = _read_json(root / "docs/PIKMIN_CONTENT_IMPORT_LANES.json")
    lane = None
    for entry in plan.get("lanes", []):
        if entry.get("source_id") == TILE_KEY and entry.get("category") == "p2-challenge":
            lane = entry
            break
    if lane is None:
        raise LandingError("stage %s missing from canonical plan" % TILE_KEY)
    details = lane.get("details") or {}
    inventory = _read_json(root / "docs/PIKMIN2_CONTENT_INVENTORY.json")
    inv = None
    for stage in inventory.get("challenge", {}).get("stages", []):
        if stage.get("cave_id") == TILE_KEY:
            inv = stage
            break
    if inv is None:
        raise LandingError("stage %s missing from canonical inventory" % TILE_KEY)
    for key in ("cave_id", "cave_path", "floors", "pikmin_by_native_color_and_maturity",
                "legacy_time", "bitter_sprays", "spicy_sprays", "treasure_count_field",
                "ui_index", "floor_seconds", "table_order"):
        if details.get(key) != inv.get(key):
            raise LandingError("stage key %r drifts between plan and inventory" % (key,))
    if lane.get("source") != inv.get("cave_path"):
        raise LandingError("source path drift for challenge stage")
    source_sha = inv.get("source_sha256") or lane.get("source_sha256")
    if not source_sha:
        raise LandingError("recorded source pin missing for %s" % TILE_KEY)
    return {"details": details, "source_sha256": source_sha}


def tile_record(root=None):
    """Validated 02tile boot-selection record (same shape as #669 records)."""
    base = tile_baseline(root)
    details = base["details"]
    matrix = details["pikmin_by_native_color_and_maturity"]
    if (not isinstance(matrix, list) or len(matrix) != 7
            or any(not isinstance(row, list) or len(row) != 3
                   or any(type(v) is not int or v < 0 for v in row) for row in matrix)):
        raise LandingError("baseline roster matrix malformed")
    seconds = details["floor_seconds"]
    if (not isinstance(seconds, list) or len(seconds) != details["floors"]
            or any(not isinstance(v, (int, float)) or not v > 0 for v in seconds)):
        raise LandingError("baseline floor timers malformed")
    return {
        "cave_id": TILE_KEY,
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
    """Resolve kusachi via #669 untouched, else 02tile; refuse everything else."""
    if not isinstance(stage_key, str) or not stage_key:
        raise LandingError("stage key must be a nonempty string")
    module = load_selector()
    base_root = Path(root) if root is not None else CANONICAL_ROOT
    try:
        return module.select_stage(stage_key, base_root), "base"
    except Exception:
        pass
    if stage_key == TILE_KEY:
        return tile_record(root), "extended"
    if isinstance(stage_key, str) and stage_key.startswith("chal"):
        raise LandingError("P1 challenge slots are a different namespace (owner: p1-challenge lanes)")
    raise LandingError("unknown P2 challenge stage: %r" % (stage_key,))


def render_boot_request_extended(record):
    """Canonical boot-request text for kusachi or 02tile records."""
    required = ("cave_id", "cave_path", "source_sha256", "ui_index", "table_order",
                "floors", "floor_seconds", "pikmin_by_native_color_and_maturity",
                "bitter_sprays", "spicy_sprays", "legacy_time", "treasure_count_field")
    missing = [k for k in required if k not in record]
    if missing:
        raise LandingError("boot record missing fields: %s" % sorted(missing))
    if record["cave_id"] not in ("ch_NARI_01kusachi", TILE_KEY):
        raise LandingError("boot record identity mismatch")
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


def staged_pins():
    """#537 staged layout pins consumed read-only from the blocker record."""
    return {
        "stage-manifest.json":
            "d8634b9c31574f3a4ab383b248d75ec7396ed14ffed7cd15427a6c7f09e7d2cb",
        "p1-input-package.json":
            "5dea109ebb84ba7bbb6386f0b147d6c35b02e1c05ce3609385f56f0bd6ca634c",
        "run-plan.json":
            "7193bedb3198490fc2f11adc76328c596a7faec96faa367dca728ee0351cbeaa",
        "run_layout_dir": ("output/workflow/autofill/planning-shards/challenge-3/"
                           "prepared/p1-nari02tile-output/run-layout"),
    }