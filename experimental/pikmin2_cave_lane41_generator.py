"""Lane 41 (#480) host driver for the native cave-generator port.

The native generator (``pc_port/pc_p2_cave_generator.{h,cpp}``) consumes a
canonical lane-34 ``p2-cave-floor-table-v1`` table in the compact
``P2_CAVE_FLOOR_V1`` text form and emits a ``p2-cave-observed-layout/1`` JSON
with ``source: engine``. This module is the host glue:

* reconcile any published table shape (lane 34 canonical, lane 36 leaf table,
  lane 40 seeded table) into the canonical shape via
  :mod:`experimental.pikmin2_cave_lane41_reconcile`;
* serialise it to ``P2_CAVE_FLOOR_V1``;
* optionally invoke the built native test/generator executable to produce the
  engine layout, then hand that layout (and the equivalent lane-40 seeded table)
  to lane 40's independent checker.

It generates nothing itself: the only generator in this path is the native one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from experimental.pikmin2_cave_lane41_reconcile import to_canonical
from experimental.pikmin2_cave_schema import (
    HAZARDS,
    SPECIES_HAZARD,
    validate_floor_table,
)
from experimental.pikmin2_cave_spike import check_spike, validate_table as validate_spike_table

NATIVE_HEADER = "P2_CAVE_FLOOR_V1"
LAYOUT_SCHEMA = "p2-cave-observed-layout/1"


class Lane41Error(ValueError):
    """Raised when the host driver cannot serialise or verify a floor."""


def _seed_uint64(seed) -> int:
    if isinstance(seed, int) and not isinstance(seed, bool):
        return seed & 0xFFFFFFFFFFFFFFFF
    material = b"P2_CAVE_SEED_1\0" + str(seed).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def write_native_table(canonical: dict, path: Path) -> Path:
    """Serialise a lane-34 canonical table to the native P2_CAVE_FLOOR_V1 form."""
    validate_floor_table(canonical)
    lines = [NATIVE_HEADER]
    lines.append(f"seed {_seed_uint64(canonical['seed'])}")
    lines.append(f"cave {canonical['cave_id']}")
    lines.append(f"floor {canonical['floor']}")
    lines.append(f"unit_pool {canonical.get('unit_pool') or '-'}")
    lines.append(f"segments {len(canonical['segments'])}")
    for segment in canonical["segments"]:
        lines.append(f"{segment['slot_id']} {segment['index']}")
    lines.append(f"chokes {len(canonical['chokes'])}")
    for choke in canonical["chokes"]:
        lines.append(
            f"{choke.get('source_id', choke['slot_id'])} {choke['index']} {choke['after_segment']} "
            f"{choke['before_segment']} {choke['hazard']} {choke['kind']} "
            f"{choke['hardness']} {choke['unit']}"
        )
    lines.append(f"leaves {len(canonical['leaves'])}")
    for leaf in canonical["leaves"]:
        lines.append(
            f"{leaf.get('source_id', leaf['slot_id'])} {leaf['index']} {leaf['segment']} "
            f"{leaf['hazard']} {leaf['item_slots']}"
        )
    lines.append(f"buds {len(canonical['buds'])}")
    for bud in canonical["buds"]:
        lines.append(
            f"{bud.get('source_id', bud['slot_id'])} {bud['index']} {bud['segment']} "
            f"{bud['species']} {bud['count']}"
        )
    lines.append(f"treasures {len(canonical['treasures'])}")
    for treasure in canonical["treasures"]:
        lines.append(
            f"{treasure['treasure_id']} {treasure.get('source_id', treasure['slot_id'])} "
            f"{treasure['segment']} {treasure['leaf_hazard']}"
        )
    lines.append(f"loose {len(canonical.get('loose_treasures', []))}")
    for treasure_id in canonical.get("loose_treasures", []):
        lines.append(treasure_id)
    lines.append(f"hole {canonical['hole']['segment']}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    return path


def canonical_to_spike(canonical: dict, loose=()) -> dict:
    """Project a lane-34 canonical table onto lane 40's ``p2-cave-seeded-table/1``."""
    validate_floor_table(canonical)
    segments = [{"index": segment["index"], "name": chr(ord("A") + segment["index"])}
                for segment in canonical["segments"]]
    chokes = [{"id": choke.get("source_id", choke["slot_id"]), "kind": choke["hazard"],
               "segment_index": choke["before_segment"]} for choke in canonical["chokes"]]
    leaves = [{"id": leaf.get("source_id", leaf["slot_id"]), "hazard": leaf["hazard"],
               "segment_index": leaf["segment"], "item_slot": f"slot_{leaf['index']}"}
              for leaf in canonical["leaves"]]
    buds = []
    for bud in canonical["buds"]:
        hazard = SPECIES_HAZARD.get(bud["species"])
        if hazard is None:
            raise Lane41Error(f"bud species {bud['species']!r} has no lane-40 hazard vocabulary")
        buds.append({"hazard": hazard, "segment_index": bud["segment"], "count": bud["count"]})
    treasures = []
    for treasure in canonical["treasures"]:
        treasures.append({"id": treasure["treasure_id"], "tagged": True,
                          "hazard": treasure["leaf_hazard"], "segment_index": treasure["segment"],
                          "leaf": treasure.get("source_id", treasure["slot_id"])})
    for treasure_id in loose:
        treasures.append({"id": treasure_id, "tagged": False})
    spike = {
        "schema": "p2-cave-seeded-table/1",
        "seed": _seed_uint64(canonical["seed"]),
        "cave": canonical["cave_id"],
        "floor": canonical["floor"],
        "segments": segments,
        "chokes": chokes,
        "leaves": leaves,
        "buds": buds,
        "treasures": treasures,
        "hole": {"segment_index": canonical["hole"]["segment"]},
    }
    validate_spike_table(spike)
    return spike


def _annotate_source_ids(canonical: dict, source: dict) -> dict:
    """Preserve the source table's slot labels as native node ids.

    Lane 40's checker looks a choke/leaf node up by the table's own ``id``, so
    the engine layout must reuse the source labels rather than lane-34's
    canonical ``<cave>:f<floor>:<class>:<index>`` slot ids. Entries gain an
    optional ``source_id``; the canonical slot ids stay unchanged for lane 34/39.
    """
    source_chokes = source.get("chokes", []) if isinstance(source, dict) else []
    for choke, origin in zip(canonical["chokes"], source_chokes):
        if isinstance(origin, dict) and isinstance(origin.get("id"), str):
            choke["source_id"] = origin["id"]
    source_leaves = source.get("leaves", []) if isinstance(source, dict) else []
    for leaf, origin in zip(canonical["leaves"], source_leaves):
        if isinstance(origin, dict):
            label = origin.get("id", origin.get("slot"))
            if isinstance(label, str):
                leaf["source_id"] = label
    source_treasures = source.get("treasures", []) if isinstance(source, dict) else []
    canonical_treasures = [t for t in canonical["treasures"]]
    tagged = [t for t in source_treasures if isinstance(t, dict) and t.get("tagged")]
    for treasure, origin in zip(canonical_treasures, tagged):
        if isinstance(origin.get("leaf"), str):
            treasure["source_id"] = origin["leaf"]
    source_buds = source.get("buds", []) if isinstance(source, dict) else []
    for bud, origin in zip(canonical["buds"], source_buds):
        if isinstance(origin, dict) and isinstance(origin.get("id"), str):
            bud["source_id"] = origin["id"]
    return canonical


def run_native_generator(tool: Path, table: Path, layout_out: Path, timeout: int = 60) -> dict:
    """Run the built native generator executable and load the emitted layout."""
    tool = Path(tool)
    if not tool.exists():
        raise Lane41Error(f"native generator executable not found: {tool}")
    result = subprocess.run([str(tool), str(table), str(layout_out)], capture_output=True, text=True,
                            timeout=timeout)
    if result.returncode != 0:
        raise Lane41Error(f"native generator failed (rc={result.returncode}): {result.stderr.strip()}")
    marker = next((line for line in result.stdout.splitlines() if line.startswith("P2_CAVE_GEN")), "")
    if not marker:
        raise Lane41Error("native generator emitted no P2_CAVE_GEN marker")
    layout = json.loads(Path(layout_out).read_text(encoding="utf-8"))
    if layout.get("schema") != LAYOUT_SCHEMA:
        raise Lane41Error(f"unexpected layout schema: {layout.get('schema')!r}")
    if layout.get("source") != "engine":
        raise Lane41Error(f"layout source is not engine: {layout.get('source')!r}")
    return {"marker": marker, "layout": layout}


def verify(tool: Path, source_table: dict, layout_out: Path, table_out: Path,
           max_rerolls: int = 1, scenarios=()) -> dict:
    """Reconcile, generate natively, and hand the result to lane 40's checker."""
    canonical = to_canonical(source_table)
    loose = [treasure["id"] for treasure in source_table.get("treasures", [])
             if isinstance(treasure, dict) and treasure.get("tagged") is False]
    canonical["loose_treasures"] = loose
    _annotate_source_ids(canonical, source_table)
    write_native_table(canonical, table_out)
    native = run_native_generator(tool, table_out, layout_out)

    layouts = [native["layout"]]
    if max_rerolls > 1:
        # Re-entry: run once more to capture a second geometry for one seed.
        reroll_out = Path(layout_out).with_name(Path(layout_out).stem + "-reroll.json")
        layouts.append(run_native_generator(tool, table_out, reroll_out)["layout"])

    if source_table.get("schema") == "p2-cave-seeded-table/1":
        spike = source_table
        validate_spike_table(spike)
    else:
        spike = canonical_to_spike(canonical, loose)
    report = check_spike(spike, layouts, scenarios)
    report["marker"] = native["marker"]
    report["canonical_seed"] = canonical["seed"]
    report["native_table"] = str(table_out)
    report["layout_paths"] = [str(layout_out)] + ([str(Path(layout_out).with_name(
        Path(layout_out).stem + "-reroll.json"))] if max_rerolls > 1 else [])
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", required=True, help="lane 34/36/40 table JSON")
    parser.add_argument("--tool", required=True, help="built native p2_cave_generator_test executable")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--rerolls", type=int, default=1)
    parser.add_argument("--report", default=None)
    args = parser.parse_args(argv)

    source = json.loads(Path(args.table).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = verify(Path(args.tool), source, out_dir / "p2-cave-observed-layout.json",
                    out_dir / "p2-cave-floor-table.txt", max_rerolls=args.rerolls)
    report_path = Path(args.report) if args.report else out_dir / "p2-cave-lane41-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "pass": report["pass"],
        "generation_pass": report["generation_invariant"]["generation_pass"],
        "evidence": report["generation_invariant"]["evidence"],
        "marker": report["marker"],
        "report": str(report_path),
    }))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
