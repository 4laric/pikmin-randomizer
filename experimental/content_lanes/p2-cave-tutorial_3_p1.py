"""P1 floor-1 staging-plan adapter for tutorial_3 (lane p2-cave-tutorial_3-p1-runtime, #153).

Consumes the DONE tutorial_3 P0 import packet (lane `cave-tutorial3-p0-source-decode`,
read-only, schema `p2-cave-import-p0-1`) and the hash-pinned tutorial_3 source
locator (lane `p2-cave-tutorial_3-p1-source-recovery`, read-only, sha256
``adcc8166...``), and turns the floor-1 decode into a deterministic,
placement-free STAGING PLAN for the native floor-1 fixture. It never re-derives
the P0 catalog and never invents placements: definition rows stay definitions
exactly as P0 recorded them.

Consumes the shared cave runtime input package builder
(experimental/pikmin2_cave_runtime_inputs.py, #642) to emit the guarded boot
fixture inputs (`p2-cave-entry.txt` + `p2-cave-generate.txt` +
`p2-cave-runtime-inputs.json`) into a private run layout, plus the line-oriented
`p2-tutorial3-floor1.txt` staging sidecar.

Floor-1 note: the committed P0 packet decodes 13 exact enemy tokens for floor 1
(all `carried_treasure=None`, `drop_mode=0`), pool
`3_MAT_nor4_hit2_blk1_snow.txt`, 2 treasures and 2 cap slots. Per-floor treasure
ids are enumerated in the packet (Xmas_item, teala_dia_a); the plan records the
count and keeps the ids in a separate unresolved-sidecar field so the floor-1
slice does not claim treasure transport.

Fail-closed: absent/malformed P0 packet raises FileNotFoundError/ValueError;
contract drift is reported as problems, never silently corrected. Floor 2-8,
persistence and gameplay sign-off remain out of scope.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

LANE = "p2-cave-tutorial_3-p1-runtime"
CAVE_ID = "tutorial_3"
SCHEMA = 1
SUPPORTED_FIRST = 1
SIDECAR_VERSION = "P2_TUTORIAL3_P1_1"
PACKET_SCHEMA = "p2-cave-import-p0-1"
EXPECTED_FLOOR_COUNT = 8
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/tutorial_3.txt"
SOURCE_SHA256 = "adcc816653957fbf00919c313291142cb110b5479c7790d997399e380c9b1abb"


def load_packet(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("Missing P0 packet: " + str(path))
    packet = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA:
        raise ValueError("P0 packet schema must be %r" % PACKET_SCHEMA)
    if packet.get("cave") != CAVE_ID:
        raise ValueError("P0 packet cave must be %r" % CAVE_ID)
    if packet.get("source_sha256") != SOURCE_SHA256:
        raise ValueError("P0 packet source_sha256 must match the pinned locator hash")
    floors = packet.get("floors")
    if not isinstance(floors, list) or not floors:
        raise ValueError("P0 packet must carry a non-empty floors list")
    numbers = sorted({int(f["first_floor"]) for f in floors})
    if numbers != list(range(1, EXPECTED_FLOOR_COUNT + 1)):
        raise ValueError("P0 packet floor coverage is %s, expected 1..%d"
                         % (numbers, EXPECTED_FLOOR_COUNT))
    return packet


def floor_one(packet):
    matches = [f for f in packet["floors"]
               if int(f["first_floor"]) <= SUPPORTED_FIRST <= int(f["last_floor"])]
    if len(matches) != 1:
        raise ValueError("floor 1 must be covered by exactly one definition")
    return matches[0]


def staging_plan(packet):
    """Deterministic, placement-free floor-1 plan derived from the P0 decode."""
    floor = floor_one(packet)
    try:
        pool = floor["parameters"]["f008"]
    except (TypeError, KeyError):
        raise ValueError("floor 1 has no unit pool parameter")
    if not isinstance(pool, str) or not pool:
        raise ValueError("floor 1 has no unit pool")
    rows = floor.get("enemies") or []
    if not rows:
        raise ValueError("floor 1 has no enemy definitions")
    counts = Counter()
    for row in rows:
        source = row.get("source") if isinstance(row, dict) else None
        if not isinstance(source, dict):
            raise ValueError("floor 1 carries a malformed definition row: %r" % (row,))
        base = source.get("enemy_id")
        if not isinstance(base, str) or not base:
            raise ValueError("floor 1 definition row missing enemy_id")
        if source.get("carried_treasure") is not None or int(source.get("drop_mode", 0)) != 0:
            raise ValueError("floor 1 carries a non-exact token: %r" % (source.get("source_token"),))
        counts[base] += 1
    enemies = [{"enemy_id": base, "count": counts[base],
                "carried_treasure": None, "drop": 0}
               for base in sorted(counts)]
    treasures = floor.get("treasures") or []
    treasure_ids = sorted({str(t.get("treasure_id")) for t in treasures
                           if isinstance(t, dict) and t.get("treasure_id")})
    caps = floor.get("caps") or []
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "cave_id": CAVE_ID,
        "source": SOURCE_PATH,
        "source_sha256": SOURCE_SHA256,
        "unit_pool": pool,
        "unit_names": [],
        "enemies": enemies,
        "treasure_count": len(treasures),
        "treasures": treasure_ids,
        "treasure_ids_unresolved": False,
        "gates": list(floor.get("gates") or []),
        "cap_count": len(caps),
        "generated": False,
        "placements": [],
        "limitations": [
            "Weighted rows are definitions, not spawn instances or placements.",
            "No seeded topology, holes or placements are generated.",
            "Floor 2-8, persistence and gameplay sign-off remain out of scope.",
            "Treasure ids are recorded from the P0 decode but no transport/reward is claimed.",
        ],
    }


def validate_plan(plan, unit_assets=None):
    """Invariant checks. Returns a list of problem strings (empty == clean)."""
    problems = []
    if plan.get("schema") != SCHEMA or plan.get("lane") != LANE:
        problems.append("plan schema/lane mismatch")
    if plan.get("cave_id") != CAVE_ID:
        problems.append("plan cave_id mismatch")
    if plan.get("source_sha256") != SOURCE_SHA256:
        problems.append("plan source hash must match the pinned locator hash")
    if plan.get("generated") is not False:
        problems.append("plan must not claim generated content")
    if plan.get("placements"):
        problems.append("plan must not contain invented placements")
    pool = plan.get("unit_pool")
    if not isinstance(pool, str) or not pool:
        problems.append("unit_pool missing")
    for row in plan.get("enemies") or []:
        enemy_id = row.get("enemy_id")
        if not isinstance(enemy_id, str) or not enemy_id:
            problems.append("enemy row missing enemy_id")
        if not re.fullmatch(r"[A-Za-z0-9_]+", enemy_id or ""):
            problems.append("enemy_id not a source token: %r" % enemy_id)
        count = row.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            problems.append("enemy %s count must be a positive int" % enemy_id)
    if not isinstance(plan.get("treasure_count"), int) or plan.get("treasure_count") < 0:
        problems.append("treasure_count must be a non-negative int")
    if unit_assets is not None and plan.get("unit_names"):
        have = set(unit_assets)
        for name in plan["unit_names"]:
            if name not in have:
                problems.append("missing unit asset: " + name)
    return problems


def sidecar_text(plan):
    lines = [SIDECAR_VERSION,
             "cave " + plan["cave_id"],
             "floor 1",
             "unit_pool " + str(plan["unit_pool"]),
             "source_sha256 " + str(plan["source_sha256"])]
    for row in plan["enemies"]:
        lines.append("enemy %s count=%d" % (row["enemy_id"], row["count"]))
    lines.append("treasure_count %d" % plan["treasure_count"])
    lines.append("cap_count " + str(plan["cap_count"]))
    lines.append("end")
    return "\n".join(lines) + "\n"


def build_runtime_inputs(plan, output_dir, entry_builder=None):
    """Emit the shared #642 guarded-boot input package for this plan.

    ``entry_builder`` defaults to the integrated
    ``experimental.pikmin2_cave_runtime_inputs`` render pair; tests inject a
    stub. Returns the emitted paths plus a provenance dict.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if entry_builder is None:
        import importlib.util
        import sys
        repo = Path(__file__).resolve().parents[2]
        if str(repo) not in sys.path:
            sys.path.insert(0, str(repo))
        shared_path = repo / "experimental" / "pikmin2_cave_runtime_inputs.py"
        if not shared_path.is_file():
            raise FileNotFoundError("Shared #642 input builder missing: " + str(shared_path))
        spec = importlib.util.spec_from_file_location("pikmin2_cave_runtime_inputs_shared", shared_path)
        entry_builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry_builder)
    cave = plan["cave_id"]
    entry_text = entry_builder.render_entry(_shared_preset(plan))
    generate_text = entry_builder.render_generate(_shared_preset(plan))
    entry_path = output_dir / "p2-cave-entry.txt"
    generate_path = output_dir / "p2-cave-generate.txt"
    entry_path.write_text(entry_text, encoding="utf-8")
    generate_path.write_text(generate_text, encoding="utf-8")
    provenance = {
        "schema": "p2-cave-runtime-inputs-1",
        "cave": cave,
        "floor": 1,
        "entry_sha256": hashlib.sha256(entry_text.encode()).hexdigest(),
        "generate_sha256": hashlib.sha256(generate_text.encode()).hexdigest(),
        "source_sha256": plan.get("source_sha256"),
        "plan_sha256": hashlib.sha256(
            json.dumps(plan, sort_keys=True).encode()).hexdigest(),
    }
    (output_dir / "p2-cave-runtime-inputs.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return {"entry": str(entry_path), "generate": str(generate_path),
            "provenance": provenance}


def _shared_preset(plan):
    """Map a staging plan onto the shared builder's exact preset shape.

    Token is the source hash prefix; squad is the schema-valid harness
    placeholder (same policy as the shared presets), never claimed as a
    retail spawn instance. Spawns use the real floor-1 enemy ids and counts.
    """
    token = (plan.get("source_sha256") or "")[:32]
    spawns = [[row["enemy_id"], int(row["count"])] for row in plan["enemies"]]
    return {
        "token": token,
        "floor": 1,
        "health": 1.0,
        "squad": [[1, 1]] * 20,
        "pool": plan["unit_pool"],
        "units": [[plan["unit_pool"], 200.0, 200.0, 0]],
        "rooms": [[0, 0, 0.0, 0.0, 0.0]],
        "spawns": spawns,
        "anchor": "hole",
    }


def write_plan(packet_path, output_dir):
    packet = load_packet(packet_path)
    plan = staging_plan(packet)
    problems = validate_plan(plan)
    if problems:
        raise ValueError("staging plan problems: " + "; ".join(problems))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "p2-tutorial3-floor1.json"
    txt_path = output_dir / "p2-tutorial3-floor1.txt"
    json_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    txt_path.write_text(sidecar_text(plan), encoding="utf-8")
    return {
        "plan": plan,
        "json": str(json_path),
        "sidecar": str(txt_path),
        "plan_sha256": hashlib.sha256(json.dumps(plan, sort_keys=True).encode("utf-8")).hexdigest(),
        "sidecar_sha256": hashlib.sha256(sidecar_text(plan).encode("utf-8")).hexdigest(),
        "problems": problems,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--runtime-inputs", action="store_true",
                        help="also emit the shared #642 guarded-boot input package")
    args = parser.parse_args(argv)
    result = write_plan(args.packet, args.output)
    if args.runtime_inputs:
        result["runtime_inputs"] = build_runtime_inputs(result["plan"], args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "plan"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
