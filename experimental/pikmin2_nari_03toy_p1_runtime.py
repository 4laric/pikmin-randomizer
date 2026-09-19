"""P1 runtime acceptance for P2 Challenge 06 ch_NARI_03toy (issue #746).

Reuses the done P0 import base (issue #540, read-only) and the landed #743
gap-stages stage-select extension (read-only; never duplicated or edited).
Stages a fresh run layout (stage manifest, input package with unique
generator IDs and recorded positions, ordinary kusachi control, hashed run
plan) plus a dependency-free run-log reader and a six-gate evaluator.

Stage-boot resolution for ch_NARI_03toy now succeeds at the Python level
through the #743 extension (provenance "gap"). The NATIVE engine table in
the pinned base still names no P2 challenge stage (zero hits for
ch_NARI/kusachi/02tile in pc_port), so a headed boot must fail closed with
BLOCKED engine-table-row-pending until a shared engine-table row lands
(owner #710 mechanics + #186 review). No engine/family/shared edits here.
All six gates stay UNTESTED unless genuinely observed; no ADMIT, no ledger
writes, no playability claim beyond observed evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

STAGE_ID = "ch_NARI_03toy"
CONTROL_ID = "ch_NARI_01kusachi"
SCHEMA = "p2-nari-03toy-p1-runtime-v1"

# Landed #743 extension, consumed read-only from its committed worktree.
GAP_SELECT_PATH = ("output/workflow/autofill/planning-shards/challenge-3/"
                   "prepared/gap-stages-select-root/experimental/"
                   "pikmin2_challenge_gap_stages_select.py")
GAP_SELECT_COMMIT = "5843b98ca2155ef46272c4e2a4e1980b3521bba5"

# Catalogued P0 pin for ch_NARI_03toy (P0 spec + canonical plan/inventory,
# read-only): 2 floors, timers 100.0 + 150.0 s, table order 2, UI index 5,
# 100 flower Blue (native color/maturity row 2), bitter 2 / spicy 2,
# treasure-count field 0, legacy 0.0.
PIN = {
    "floors": 2,
    "table_order": 2,
    "ui_index": 5,
    "floor_seconds": [100.0, 150.0],
    "bitter_sprays": 2,
    "spicy_sprays": 2,
    "roster_row2": [0, 0, 100],
    "treasure_count": 0,
    "legacy_time": 0.0,
    "source_sha256": "d74b49ac3d9a2388288b9cb868dd8717ff893fd522453b309740519be841f03c",
    "cave_path": "user/Mukki/mapunits/caveinfo/ch_NARI_03toy.txt",
}

GUARD_HEADER = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

# Receipt-parseable markers the guarded fixture must emit.
WINDOW_PREFIX = "P2_NARI_03TOY_P1_WINDOW"
ENTRY_MARKER = "P2CHALLENGE_STAGE_ENTRY"
ROOM_MARKER = "P2_ROOM_READY"
BLOCKED_MARKER = "BLOCKED NARI_03TOY_P1_BOOT engine-table-row-pending"
PASS_MARKER = "PASS NARI_03TOY_P1_BOOT"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "mHealth=", "Transport(")


class P1Error(ValueError):
    """Fail-closed P1 rejection: bad identity, pin drift, or missing base."""


def _root():
    return Path("C:/Users/alari/pikmin-randomizer")


def load_gap_select(root=None):
    """Load the landed #743 extension read-only from its committed worktree."""
    base = Path(root) if root is not None else _root()
    path = base / GAP_SELECT_PATH
    if not path.is_file():
        raise P1Error("landed #743 extension unreadable: %s" % path)
    spec = importlib.util.spec_from_file_location(
        "pikmin2_challenge_gap_stages_select_adopted", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("select_stage_extended", "render_boot_request_extended"):
        if not callable(getattr(module, name, None)):
            raise P1Error("landed #743 extension lacks API: %s" % name)
    return module


def resolve_stage(root=None):
    """Resolve ch_NARI_03toy through the landed #743 extension (gap key)."""
    module = load_gap_select(root)
    record, provenance = module.select_stage_extended(STAGE_ID, root)
    if record.get("cave_id") != STAGE_ID:
        raise P1Error("extension resolved the wrong stage: %r" % record.get("cave_id"))
    if provenance != "gap":
        raise P1Error("expected #743 gap provenance, got %r" % (provenance,))
    return record


def validate_stage_record(record):
    """Validate a stage record against the catalogued P0 pin."""
    if not isinstance(record, dict):
        raise P1Error("stage record must be a dict")
    if record.get("cave_id") != STAGE_ID:
        raise P1Error("wrong cave_id: %r" % record.get("cave_id"))
    for key in ("floors", "table_order", "ui_index", "treasure_count_field"):
        if record.get(key) != PIN[key if key != "treasure_count_field" else "treasure_count"]:
            raise P1Error("%s mismatch: %r" % (key, record.get(key)))
    if [float(v) for v in (record.get("floor_seconds") or [])] != PIN["floor_seconds"]:
        raise P1Error("floor_seconds mismatch: %r" % (record.get("floor_seconds"),))
    if record.get("bitter_sprays") != 2 or record.get("spicy_sprays") != 2:
        raise P1Error("spray counts mismatch")
    matrix = record.get("pikmin_by_native_color_and_maturity")
    if (not isinstance(matrix, list) or len(matrix) != 7
            or [list(r) for r in matrix][2] != PIN["roster_row2"]
            or any(sum(r) != (100 if i == 2 else 0) for i, r in enumerate(matrix))):
        raise P1Error("starting roster mismatch (want 100 flower Blue, row 2)")
    if record.get("cave_path") != PIN["cave_path"]:
        raise P1Error("cave_path mismatch: %r" % record.get("cave_path"))
    if record.get("source_sha256") != PIN["source_sha256"]:
        raise P1Error("source pin mismatch")
    if float(record.get("legacy_time", -1)) != PIN["legacy_time"]:
        raise P1Error("legacy_time mismatch")
    return dict(record)


def _generators(record):
    """Deterministic staged generator slots (staged layout, NOT observed)."""
    generators = []
    per_floor = 4
    for floor in range(1, int(record["floors"]) + 1):
        for slot in range(per_floor):
            generators.append({
                "id": "%s-f%d-g%02d" % (STAGE_ID, floor, slot),
                "floor": floor,
                "position": [float(100 * floor + 25 * slot), 0.0, float(50 * slot)],
                "observed": False,
            })
    ids = [g["id"] for g in generators]
    if len(set(ids)) != len(ids):
        raise P1Error("generator IDs not unique")
    return generators


def stage_run_layout(outdir, record=None, root=None):
    """Stage a fresh hashed run layout; returns (files, manifest_sha256)."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    staged = validate_stage_record(dict(record) if record else resolve_stage(root))
    module = load_gap_select(root)
    control, control_prov = module.select_stage_extended(CONTROL_ID, root)
    if control.get("cave_id") != CONTROL_ID:
        raise P1Error("ordinary control resolved the wrong stage")
    manifest = {
        "schema": SCHEMA,
        "stage_id": STAGE_ID,
        "record": staged,
        "boot_request": module.render_boot_request_extended(staged),
        "control": {"cave_id": CONTROL_ID, "provenance": control_prov,
                    "boot_request": module.render_boot_request_extended(control)},
        "guard": {"header": GUARD_HEADER, "sha256": GUARD_SHA256},
        "native_engine_row": "pending (no ch_NARI row in pinned native base; owner #710 + #186 review)",
    }
    package = {
        "schema": SCHEMA,
        "stage_id": STAGE_ID,
        "generators": _generators(staged),
        "starting_squad": {"colors": ["Blue"], "maturity": "flower", "count": 100},
        "observed": False,
    }
    plan = {
        "schema": SCHEMA,
        "stage_id": STAGE_ID,
        "steps": ["leased build of pinned native + replacement-main fixture",
                  "headed boot with --experimental-pikmin2-room in a fresh run dir",
                  "fail closed BLOCKED engine-table-row-pending until the native row lands"],
        "expected_markers": [WINDOW_PREFIX, ENTRY_MARKER, ROOM_MARKER,
                             BLOCKED_MARKER, PASS_MARKER],
    }
    files = {}
    for name, payload in (("stage-manifest.json", manifest),
                          ("p1-input-package.json", package),
                          ("run-plan.json", plan)):
        text = json.dumps(payload, indent=1, sort_keys=True) + "\n"
        (out / name).write_text(text, encoding="utf-8")
        files[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return files, hashlib.sha256(
        json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()


def parse_run_log(text):
    """Split a fixture run log into marker facts and health flags."""
    lines = [l.strip() for l in text.splitlines()]
    return {
        "window": [l for l in lines if l.startswith(WINDOW_PREFIX)],
        "entries": [l for l in lines if l.startswith(ENTRY_MARKER)],
        "rooms": [l for l in lines if l.startswith(ROOM_MARKER)],
        "blocked": [l for l in lines if BLOCKED_MARKER in l],
        "passes": [l for l in lines if l.strip() == PASS_MARKER],
        "captain_down": CAPTAIN_DOWN in text,
        "injected": [t for t in INJECTED_TOKENS if t in text],
    }


def evaluate_gates(parsed):
    """Honest six-gate disposition over a parsed run log."""
    if parsed["captain_down"]:
        return {name: ("BLOCKED", "captain-down interruption; run cannot substantiate gates")
                for name in ("identity_spawn", "movement_animation", "attacks_receivers",
                             "death_corpse", "transport_reward", "cleanup_reentry")}
    if parsed["injected"]:
        return {name: ("BLOCKED", "injection markers present: %s" % ",".join(parsed["injected"]))
                for name in ("identity_spawn", "movement_animation", "attacks_receivers",
                             "death_corpse", "transport_reward", "cleanup_reentry")}
    if parsed["blocked"]:
        reason = "native boot refused fail-closed (engine-table-row-pending); nothing observed"
        return {name: ("BLOCKED", reason)
                for name in ("identity_spawn", "movement_animation", "attacks_receivers",
                             "death_corpse", "transport_reward", "cleanup_reentry")}
    if parsed["passes"] and parsed["entries"] and parsed["rooms"]:
        return {
            "identity_spawn": ("PASS", "stage entry + room live observed"),
            "movement_animation": ("UNTESTED", "no motion markers in scope"),
            "attacks_receivers": ("UNTESTED", "protected observation claims no combat"),
            "death_corpse": ("UNTESTED", "no death markers in scope"),
            "transport_reward": ("UNTESTED", "no haul markers in scope"),
            "cleanup_reentry": ("UNTESTED", "no reentry markers in scope"),
        }
    return {name: ("UNTESTED", "no observation for this gate")
            for name in ("identity_spawn", "movement_animation", "attacks_receivers",
                         "death_corpse", "transport_reward", "cleanup_reentry")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("stage", "read"))
    parser.add_argument("--outdir", default="")
    parser.add_argument("--log", default="")
    args = parser.parse_args(argv)
    if args.command == "stage":
        if not args.outdir:
            raise P1Error("--outdir required for stage")
        files, digest = stage_run_layout(args.outdir)
        print("STAGED files=%d manifest=%s" % (len(files), digest))
        return 0
    text = Path(args.log).read_text(encoding="utf-8", errors="replace") if args.log else sys.stdin.read()
    parsed = parse_run_log(text)
    for name, (status, why) in evaluate_gates(parsed).items():
        print("%s %s: %s" % (status, name, why))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
