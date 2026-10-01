"""ch_MAT_yellow_purple_white P1 private runtime-import path
(lane p2-challenge-ch-mat-yellow-purple-white-p1, #552).

P1 only adds staging/validation on top of the reviewed P0 adapter. It never
forks the parser: the P0 module (reserved filename with hyphens) is loaded by
path and its real-source decode helpers, baseline cross-check and hash pin are
reused verbatim. This module stages the decoded stage manifest into a private
run layout and emits the run plan the guarded private runtime consumes,
including the integrated host-mode consumer contract
(native/pc_port/pc_p2_challenge_mode.{h,cpp}: select by ui_index, squad/spray
application, per-floor timer, retry) and the captain-safety #632 ordering.

No runtime state is fabricated: placements/actors/spawn layouts/scores/results
are refused, exactly as in P0. No native build, no shared edits, no ADMIT.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

P1_SCHEMA = "p2-challenge-ch_mat_yellow_purple_white-p1-v1"

_P0_FILENAME = "p2-challenge-ch_mat_yellow_purple_white.py"
_HOST_MODE_HEADER = "pc_port/pc_p2_challenge_mode.h"
_HOST_MODE_TU = "pc_port/pc_p2_challenge_mode.cpp"


def workspace_root():
    """Repository root derived from this file's reserved location."""
    return Path(__file__).resolve().parents[2]


def p0(root=None):
    """Load the reviewed P0 adapter by path (no fork, no package glue).

    The P0 reserved filename contains hyphens, so it is never importable as a
    module name; loading it by path is the deliberate reuse channel.
    """
    base = Path(root) if root is not None else workspace_root()
    path = base / "experimental" / "content_lanes" / _P0_FILENAME
    if not path.is_file():
        raise FileNotFoundError("P0 adapter missing: %s" % path)
    spec = importlib.util.spec_from_file_location("ch_mat_yellow_purple_white_p0", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def default_manifest(root=None):
    """A valid P1 manifest built from the canonical baseline (no retail guesses).

    This is what a decoded real-source manifest must contain; the values come
    from the P0 baseline cross-check (plan + inventory agree) at runtime.
    """
    adapter = p0(root)
    details = adapter.baseline_details(root)
    return {
        "cave_id": adapter.CAVE_ID,
        "table_order": details["table_order"],
        "ui_index": details["ui_index"],
        "floors": details["floors"],
        "pikmin_by_native_color_and_maturity": [list(r) for r in details["pikmin_by_native_color_and_maturity"]],
        "legacy_time": float(details["legacy_time"]),
        "bitter_sprays": details["bitter_sprays"],
        "spicy_sprays": details["spicy_sprays"],
        "treasure_count_field": details["treasure_count_field"],
        "floor_seconds": [float(v) for v in details["floor_seconds"]],
    }


def _check_roster(matrix):
    if (not isinstance(matrix, list) or len(matrix) != 7
            or any(not isinstance(row, list) or len(row) != 3
                   or any(type(v) is not int or v < 0 for v in row)
                   for row in matrix)):
        raise ValueError("P1 roster must be a 7x3 non-negative int matrix")
    return [list(row) for row in matrix]


def validate_p1_manifest(manifest, root=None):
    """Check a manifest against the canonical baseline before staging.

    Fails closed on any drift; refuses runtime-shaped keys outright. Returns a
    normalized staging summary consumable by the run layout.
    """
    if not isinstance(manifest, dict):
        raise ValueError("P1 manifest must be a dict")
    adapter = p0(root)
    spec = adapter.baseline_details(root)
    if manifest.get("cave_id") != adapter.CAVE_ID:
        raise ValueError("P1 stage mismatch")
    floors = manifest.get("floors")
    if type(floors) is not int or floors != spec["floors"]:
        raise ValueError("P1 needs exactly %d decoded floor(s)" % spec["floors"])
    for key in ("table_order", "ui_index", "bitter_sprays", "spicy_sprays",
                "treasure_count_field"):
        value = manifest.get(key)
        if type(value) is not int or value != spec[key]:
            raise ValueError("P1 %s must be %r" % (key, spec[key]))
    if type(manifest.get("legacy_time")) is not float or manifest["legacy_time"] != spec["legacy_time"]:
        raise ValueError("P1 legacy_time must be %r" % (spec["legacy_time"],))
    timers = manifest.get("floor_seconds")
    if (not isinstance(timers, list) or len(timers) != spec["floors"]
            or any(type(v) is not float or v <= 0 for v in timers)):
        raise ValueError("P1 floor timers must be one positive float per floor")
    if timers != [float(v) for v in spec["floor_seconds"]]:
        raise ValueError("P1 floor_seconds must be %r" % (spec["floor_seconds"],))
    matrix = _check_roster(manifest.get("pikmin_by_native_color_and_maturity"))
    if matrix != [list(r) for r in spec["pikmin_by_native_color_and_maturity"]]:
        raise ValueError("P1 roster differs from baseline")
    squad_total = sum(sum(row) for row in matrix)
    if squad_total <= 0:
        raise ValueError("P1 starting squad is empty")
    for key in adapter.FORBIDDEN_MANIFEST_KEYS:
        if key in manifest:
            raise ValueError("P1 %s refused: stage definitions are not runtime state" % (key,))
    return {
        "cave_id": adapter.CAVE_ID,
        "floors": floors,
        "floor_seconds": [float(v) for v in timers],
        "squad_total": squad_total,
        "sprays": {"bitter": spec["bitter_sprays"], "spicy": spec["spicy_sprays"]},
        "ui_index": spec["ui_index"],
    }


def host_mode_pins(native_root):
    """Hash-pin the integrated host-mode consumer module (read-only)."""
    if native_root is None:
        return {"host_mode": None, "reason": "no native root supplied"}
    base = Path(native_root)
    pins = {}
    for rel in (_HOST_MODE_HEADER, _HOST_MODE_TU):
        path = base / Path(*rel.split("/"))
        pins[rel] = sha256_file(path) if path.is_file() else None
    return {"host_mode": pins, "reason": None}


def stage_run_layout(manifest, output, root=None, native_root=None):
    """Stage the validated manifest + input package + run plan into a run dir."""
    staging = validate_p1_manifest(manifest, root=root)
    adapter = p0(root)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    files = {}

    def write(name, payload):
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        (output / name).write_text(text, encoding="utf-8")
        files[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()

    write("stage-manifest.json", manifest)
    write("p1-input-package.json", {
        "schema": P1_SCHEMA,
        "cave_id": staging["cave_id"],
        "floors": staging["floors"],
        "floor_seconds": staging["floor_seconds"],
        "squad_total": staging["squad_total"],
        "sprays": staging["sprays"],
        "ui_index": staging["ui_index"],
        "p0_source_pin": adapter.RECORDED_SHA256,
        "host_mode_pins": host_mode_pins(native_root),
    })
    write("run-plan.json", {
        "schema": P1_SCHEMA,
        "order": [
            "boot the private runtime over this run layout (fresh arena, current starting-Pikmin overlay, centred 960x540)",
            "captain guard #632 FIRST after idle (orimaDead/NaviDead/HP<=1, CAPTAIN_DOWN + BLOCKED, parked captain)",
            "observe live starting squad (no immediate extinction)",
            "observe actual collision/routes/actors with receipt-parseable markers",
            "record honest six-gate evidence; no playability claim beyond observed evidence",
        ],
        "host_mode_contract": "select by ui_index; applySquadAndSprays; per-floor timer; retry/reset",
        "gates": "all six UNTESTED unless genuinely observed",
        "captain_safety": "scripts/p2_fixture_captain_guard.h or tested equivalent",
    })
    return {"files": files, "cave_id": staging["cave_id"], "floors": staging["floors"],
            "squad_total": staging["squad_total"]}


def p1_main(manifest_path, output, root=None, native_root=None):
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("P1 manifest unreadable: %s" % exc) from None
    result = stage_run_layout(manifest, output, root=root, native_root=native_root)
    print("P1 staged cave=%s floors=%d squad_total=%d files=%s" % (
        result["cave_id"], result["floors"], result["squad_total"], sorted(result["files"])))
    return result


if __name__ == "__main__":
    import sys

    p1_main(sys.argv[1], sys.argv[2],
            native_root=(sys.argv[3] if len(sys.argv) > 3 else None))
