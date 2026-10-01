"""P1 private runtime import for P2 Challenge 05 ch_NARI_02tile (issue #537).

Extends the P0 import contract with a P1 path that validates the decoded
stage manifest against the canonical baseline, stages it into a private run
layout (stage-manifest.json + p1-input-package.json + run-plan.json, all
hashed), and emits the run plan that boots the stage with a live starting
squad and centred 960x540 startup.

The P0 adapter (experimental/content_lanes/p2-challenge-ch_nari_02tile.py) is
loaded BY PATH and never edited; its real-source decode/baseline helpers are
reused, never forked. The integrated host-mode module
(native/pc_port/pc_p2_challenge_mode.{h,cpp}) is consumed read-only by exact
commit pin; this lane owns no native/shared files and performs no native
build. Captain safety #632 is mandatory for any runtime run executed from the
staged plan (orimaDead/NaviDead/HP<=1, CAPTAIN_DOWN + BLOCKED, parked captain,
recorded hashes). All six runtime gates stay UNTESTED unless genuinely
observed; no playability claim beyond observed evidence; no ADMIT, no ledger
writes. If no engine stage-boot path exists for this stage, the staged plan
records the exact blocker rather than overclaiming.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

CAVE_ID = "ch_NARI_02tile"
P0_ADAPTER_REL = "experimental/content_lanes/p2-challenge-ch_nari_02tile.py"
DEFAULT_SOURCE_REL = "output/workflow/content-expansion/p2-challenge-ch_nari_02tile/ch_NARI_02tile.txt"

# Integrated host-mode module pins (native repo, branch
# codex/autofill-host-mode-runtime-wiring-native-native, issue #702).
HOST_MODE_COMMIT = "ada6bda4"
HOST_MODE_FILES = {
    "pc_port/pc_p2_challenge_mode.h":
        "d543c6fef4d63dccfceb384e40c08abe0d24f23969bc85ae02353b8d06706b68",
    "pc_port/pc_p2_challenge_mode.cpp":
        "6576858f1f67b5c450aaf29a86026424f7326eb7859a7d660140d924a8e36ca1",
}
HOST_MODE_API = (
    "hostModeStart(mode, level, ui_index, time_limit): select by ui_index",
    "hostModeTick(mode, seconds, squad_alive, ...): per-floor timer countdown",
    "hostModeRetry(mode): retry entry",
    "deliverStageEntry(entry): P2CHALLENGE_STAGE_ENTRY observed marker",
)

GUARD_HEADER = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

RUN_FILES = ("stage-manifest.json", "p1-input-package.json", "run-plan.json")

# Receipt-parseable markers a real stage boot must emit (mirrors the #675
# stage-boot fixture marker set, consumed read-only).
EXPECTED_MARKERS = (
    "P2CHALLENGE_STAGE_ENTRY",
    "P2_ROOM_READY",
    "P2_FIXTURE_CAPTAIN_DOWN",
)


class P1Error(ValueError):
    """Fail-closed P1 import rejection."""


def repo_root_here():
    return Path(__file__).resolve().parents[3]


def load_p0_adapter(repo_root):
    """Import the P0 adapter BY PATH; the file is never edited or copied."""
    path = Path(repo_root) / P0_ADAPTER_REL
    if not path.is_file():
        raise P1Error("P0 adapter missing: " + str(path))
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    spec = importlib.util.spec_from_file_location(
        "p2_challenge_ch_nari_02tile_p0", str(path))
    if spec is None or spec.loader is None:
        raise P1Error("cannot load P0 adapter: " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decode_stage(adapter, source_path):
    """Run the P0 real-source decode and return (scan, contract)."""
    data = adapter.source_bytes(source_path)
    adapter.verify_source(data)
    text = adapter.decode_text(data)
    scan = adapter.structural_scan(text)
    try:
        from experimental.pikmin2_cave_catalog import rows as _rows  # noqa: F401
    except Exception as error:
        raise P1Error("shared catalog unavailable: " + str(error)) from None
    return scan, adapter.import_contract(scan, None)


def validate_manifest(contract, baseline=None):
    """Validate the decoded manifest against the canonical P0 baseline."""
    baseline = dict(baseline) if baseline is not None else None
    if contract.get("schema") != 1:
        raise P1Error("contract schema must be 1")
    if contract.get("cave_id") != CAVE_ID:
        raise P1Error("wrong cave_id: %r" % contract.get("cave_id"))
    floors = contract.get("floor_coverage") or []
    if len(floors) != 2:
        raise P1Error("expected 2 floors, got %d" % len(floors))
    manifest = contract.get("floor_manifest") or []
    if len(manifest) != 2:
        raise P1Error("floor_manifest must list 2 floors")
    if contract.get("ui_index") != 4:
        raise P1Error("expected ui_index 4, got %r" % contract.get("ui_index"))
    base = contract.get("timer_roster_spray_baseline") or {}
    for key in ("floor_seconds", "bitter_sprays", "spicy_sprays", "ui_index"):
        if key not in base:
            raise P1Error("baseline missing key: " + key)
    if list(base["floor_seconds"]) != [200.0, 150.0]:
        raise P1Error("floor_seconds differ from canonical baseline")
    if base["bitter_sprays"] != 0 or base["spicy_sprays"] != 5:
        raise P1Error("spray baseline differs from canonical baseline")
    return {
        "cave_id": contract["cave_id"],
        "source": contract.get("source"),
        "source_sha256": contract.get("source_sha256"),
        "ui_index": contract["ui_index"],
        "floors": [
            {"floor": row["floor"], "unit_pool": row["unit_pool"],
             "enemy_rows": row["enemy_rows"], "treasure_rows": row["treasure_rows"],
             "gate_rows": row["gate_rows"], "cap_rows": row["cap_rows"]}
            for row in manifest
        ],
        "timer_roster_spray_baseline": {
            "floor_seconds": list(base["floor_seconds"]),
            "bitter_sprays": base["bitter_sprays"],
            "spicy_sprays": base["spicy_sprays"],
        },
    }


def host_mode_pins():
    """Hash-pinned host-mode module consumed read-only (no native checkout)."""
    return {
        "commit": HOST_MODE_COMMIT,
        "files": dict(HOST_MODE_FILES),
        "api": list(HOST_MODE_API),
    }


def stage_run_layout(validated, outdir):
    """Write stage-manifest.json + p1-input-package.json + run-plan.json."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    stage_manifest = {
        "schema": 1,
        "cave_id": validated["cave_id"],
        "source": validated["source"],
        "source_sha256": validated["source_sha256"],
        "ui_index": validated["ui_index"],
        "floors": validated["floors"],
        "timer_roster_spray_baseline": validated["timer_roster_spray_baseline"],
    }
    input_package = {
        "schema": 1,
        "cave_id": validated["cave_id"],
        "source_sha256": validated["source_sha256"],
        "host_mode": host_mode_pins(),
        "guard": {"header": GUARD_HEADER, "sha256": GUARD_SHA256},
        "window": {"width": 960, "height": 540, "centred": True},
        "squad": {"live_starting_squad_required": True},
    }
    run_plan = {
        "schema": 1,
        "cave_id": validated["cave_id"],
        "ui_index": validated["ui_index"],
        "window": {"width": 960, "height": 540, "centred": True},
        "squad": {"live_starting_squad_required": True},
        "captain_safety": {
            "guard": GUARD_HEADER,
            "guard_sha256": GUARD_SHA256,
            "checks": ["orimaDead", "NaviDead", "HP<=1"],
            "on_down": "emit CAPTAIN_DOWN and exit BLOCKED",
            "parked_captain": True,
        },
        "host_mode": {
            "select": "hostModeStart by ui_index=%d" % validated["ui_index"],
            "timer": "hostModeTick per-floor countdown",
            "retry": "hostModeRetry",
            "markers": ["P2CHALLENGE_STAGE_ENTRY"],
        },
        "expected_markers": list(EXPECTED_MARKERS),
        "blocker": (
            "No engine stage-boot path is claimed here: the staged plan boots "
            "through the existing #675 stage-boot fixture (--stage ch_NARI_02tile). "
            "If that fixture boots the room-preview stage instead of this stage's "
            "content, all six gates stay UNTESTED and this plan records that exact "
            "blocker."
        ),
    }
    hashes = {}
    for name, payload in (("stage-manifest.json", stage_manifest),
                          ("p1-input-package.json", input_package),
                          ("run-plan.json", run_plan)):
        data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        (outdir / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    return hashes


def run_import(repo_root, source_path, outdir):
    """Full P1 import: decode, validate, stage. Returns file hashes."""
    adapter = load_p0_adapter(repo_root)
    scan, contract = decode_stage(adapter, source_path)
    validated = validate_manifest(contract)
    return stage_run_layout(validated, outdir)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        hashes = run_import(args.repo, args.source, args.out)
    except P1Error as error:
        print("P1 import rejected: " + str(error))
        return 2
    print(json.dumps(hashes, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())