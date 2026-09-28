"""Lane 49: real water/elec cave-unit meshes for the generated cavity floor.

Lane 45 (:mod:`experimental.pikmin2_cave_geometry`) drew real converted unit
models at the hazard nodes but reused the dry forest_1 unit ``room_north3_1_tsuchi``
for the water choke/leaf because the lane-09 importer refused any unit with a
non-empty ``texts/waterbox.txt``. This module regenerates the geometry plan with
the *intended* unit identities:

* water choke/leaf -> ``room_kingchap_b_tsuchi`` (forest_3, intrinsic water), and
* the electric leaf -> ``room_north2x2_1_metal`` (tutorial_2, dry actor alcove),

while the electric-gate door keeps lane 45's converted P2 gate model. The
converter now emits a ``water.json`` sidecar per unit and tags P1 ``ATTR_Water``
on the submerged floor collision (see :mod:`experimental.pikmin2_cave_water` and
:mod:`experimental.pikmin2_collision`); the plan and its models are the same
files the native geometry engine already consumes, so no native change is needed.

Nothing here reads the clock or draws random numbers. The unit meshes come from
the disc; the plan is a pure function of the lane-44 rooms JSON and the chosen
model names.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave_geometry import build_geometry, geometry_text, validate_geometry
from experimental.pikmin2_convert import convert
from experimental.pikmin2_selected_units import import_units

WATER_UNIT = "room_kingchap_b_tsuchi"
ELEC_UNIT = "room_north2x2_1_metal"
WATER_CAVE = "forest_3"
ELEC_CAVE = "tutorial_2"
GATE_SOURCE = "user/Kando/objects/gates/e-gate-arc.szs"
GATE_MEMBER = "e-gate.bmd"
GATE_MODEL = "courses/pikmin2room/p2cave_e_gate.mod"
MODEL_DIR = "courses/pikmin2room"
UNIT_KINDS = ("choke", "leaf", "gate")

READY_MARKER = "P2_CAVE_WATER_READY"
UNIT_MARKER = "P2_CAVE_WATER_UNIT"


class WaterUnitsError(ValueError):
    """Fail-closed error for the lane-49 real water/elec unit slice."""


def unit_model_path(name: str) -> str:
    """Staged model path for a converted cave unit (native model namespace)."""
    if not name or any(ch.isspace() for ch in name):
        raise WaterUnitsError(f"invalid unit name {name!r}")
    return f"{MODEL_DIR}/p2cave_{name}.mod"


def assign_models(rooms, *, water_model, elec_model, gate_model) -> dict:
    """Map every hazard-bearing node to a real model by hazard and kind.

    Water nodes take the intrinsic water unit; gate nodes take the converted P2
    electric gate; any other choke/leaf (a dry actor alcove) takes the elec unit.
    Segment nodes never get a model, so lane 45 keeps drawing them as proxies.
    """
    for label, value in (("water_model", water_model), ("elec_model", elec_model),
                         ("gate_model", gate_model)):
        if not isinstance(value, str) or not value or any(ch.isspace() for ch in value):
            raise WaterUnitsError(f"{label} must be a non-empty token")
    units = rooms.get("units") if isinstance(rooms, dict) else None
    if not isinstance(units, list):
        raise WaterUnitsError("rooms must contain a units list")
    models = {}
    for unit in units:
        kind = unit.get("kind")
        if kind not in UNIT_KINDS:
            continue
        hazard = unit.get("hazard")
        if hazard == "water":
            models[unit["id"]] = water_model
        elif kind == "gate":
            models[unit["id"]] = gate_model
        else:
            models[unit["id"]] = elec_model
    return models


def _read_member(iso, archive_path: str, member: str) -> bytes:
    files = disc_files(iso)
    if archive_path not in files:
        raise WaterUnitsError(f"missing disc archive {archive_path}")
    offset, size = files[archive_path]
    with iso.open("rb") as disc:
        disc.seek(offset)
        data = disc.read(size)
    if len(data) != size:
        raise WaterUnitsError("truncated disc archive")
    members = archive_files(data)
    if member not in members:
        raise WaterUnitsError(f"{archive_path} has no {member}")
    return members[member]


def convert_e_gate(iso, output: Path) -> dict:
    """Extract and convert the retail P2 electric gate to a MOD (approx materials).

    The strict converter rejects the multi-joint/multi-stage gate, so this uses
    lane 45's ``approximate_materials + bake_rigid`` policy and records it.
    """
    output = Path(output)
    source = output.with_suffix(".bmd")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(_read_member(iso, GATE_SOURCE, GATE_MEMBER))
    report = convert(source, output, approximate_materials=True, bake_rigid=True)
    report["conversion_policy"] = "approximate_materials+rigid_bind_pose_bake"
    return report


def stage_render(unit_dir: Path, models_dir: Path, name: str) -> Path:
    """Stage a converted unit's static render mesh under the native model root."""
    source = Path(unit_dir) / "render.mod"
    if not source.is_file() or source.stat().st_size <= 0:
        raise WaterUnitsError(f"missing converted render mesh for {name}")
    target = Path(models_dir) / unit_model_path(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _unit_record(manifest, name: str) -> dict:
    return manifest["units"][name]


def _require_converted(manifest, name: str) -> dict:
    record = _unit_record(manifest, name)
    if record["status"] != "converted" or not record.get("assembly_ready"):
        raise WaterUnitsError(f"{name} did not convert: {record.get('failure')}")
    return record


def run(iso, catalog, dependencies, rooms_path, out_dir) -> dict:
    iso = Path(iso)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    units_root = out / "units"

    water_manifest = import_units(iso, Path(catalog), Path(dependencies),
                                  units_root / WATER_CAVE, WATER_CAVE, False)
    elec_manifest = import_units(iso, Path(catalog), Path(dependencies),
                                 units_root / ELEC_CAVE, ELEC_CAVE, True)
    water_unit = _require_converted(water_manifest, WATER_UNIT)
    elec_unit = _require_converted(elec_manifest, ELEC_UNIT)

    models = out / "models"
    stage_render(units_root / WATER_CAVE / "units" / WATER_UNIT, models, WATER_UNIT)
    stage_render(units_root / ELEC_CAVE / "units" / ELEC_UNIT, models, ELEC_UNIT)
    gate_report = convert_e_gate(iso, models / GATE_MODEL)

    rooms = json.loads(Path(rooms_path).read_text(encoding="utf-8"))
    mapping = assign_models(rooms, water_model=unit_model_path(WATER_UNIT),
                            elec_model=unit_model_path(ELEC_UNIT), gate_model=GATE_MODEL)
    plan = build_geometry(rooms, models=mapping)
    validation = validate_geometry(plan, model_root=models)
    if not validation["valid"]:
        raise WaterUnitsError("geometry plan is not valid: " + "; ".join(validation["errors"]))

    geometry_dir = out / "geometry"
    geometry_dir.mkdir(parents=True, exist_ok=True)
    (geometry_dir / "p2-cave-geometry.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (geometry_dir / "p2-cave-geometry.txt").write_text(
        geometry_text(plan), encoding="utf-8", newline="\n")

    units = {}
    for name, manifest, cave, staged in (
        (WATER_UNIT, water_manifest, WATER_CAVE, unit_model_path(WATER_UNIT)),
        (ELEC_UNIT, elec_manifest, ELEC_CAVE, unit_model_path(ELEC_UNIT)),
    ):
        record = _unit_record(manifest, name)
        units[name] = {
            "cave": cave,
            "status": record["status"],
            "material_status": record.get("material_status"),
            "collision_triangles": record.get("collision_triangles"),
            "water_collision_triangles": record.get("water_collision_triangles", 0),
            "water": record["water"],
            "model": staged,
            "model_sha256": _sha256(models / staged),
        }

    manifest = {
        "schema": 1,
        "cave": plan["cave"],
        "floor": plan["floor"],
        "seed": plan["seed"],
        "salt": plan["salt"],
        "water_unit": WATER_UNIT,
        "elec_unit": ELEC_UNIT,
        "units": units,
        "gate": {
            "model": GATE_MODEL,
            "model_sha256": _sha256(models / GATE_MODEL),
            "conversion_policy": gate_report["conversion_policy"],
            "strict_rejected": True,
        },
        "geometry": plan["geometry"],
        "nodes": len(plan["nodes"]),
        "water_nodes": sum(1 for n in plan["nodes"] if n.get("hazard") == "water"),
        "elec_nodes": sum(1 for n in plan["nodes"] if n.get("hazard") == "elec"),
        "validation": validation,
        "limitations": [
            "The preview fixture draws the real meshes but exercises no water query; "
            "P1 ATTR_Water tagging is proven offline, not live.",
            "The electric gate mesh uses approximate materials and a rigid bind-pose "
            "bake (the strict converter rejects its multi-joint/multi-stage model).",
            "Water boxes are unit-local; cross-unit carry blocking stays lane 50.",
        ],
    }
    (out / "water-units.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                          encoding="utf-8")

    print(f"{READY_MARKER} cave={manifest['cave']} floor={manifest['floor']} "
          f"seed={manifest['seed']} salt={manifest['salt']} water_unit={WATER_UNIT} "
          f"elec_unit={ELEC_UNIT} nodes={manifest['nodes']} "
          f"water_nodes={manifest['water_nodes']} elec_nodes={manifest['elec_nodes']}")
    for name, record in units.items():
        print(f"{UNIT_MARKER} name={name} cave={record['cave']} class="
              f"{'water' if name == WATER_UNIT else 'elec'} boxes={record['water']['count']} "
              f"surface={record['water']['surface']} model={record['model']} "
              f"sha256={record['model_sha256']}")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--rooms", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    run(args.iso, args.catalog, args.dependencies, args.rooms, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
