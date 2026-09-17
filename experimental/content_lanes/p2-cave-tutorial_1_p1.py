"""P1 floor-1 staging-plan adapter for tutorial_1 (lane p2-cave-tutorial_1-p1-runtime, #114).

Consumes the DONE tutorial_1 P0 packet (lane cave-tutorial1-p0-source-decode,
read-only) and turns its floor-1 decode into a deterministic, placement-free
STAGING PLAN for the native floor-1 fixture. It never re-decodes disc bytes and
never invents placements: weighted rows stay definitions exactly as P0 recorded
them.

Consumes the shared cave runtime input package builder
(experimental/pikmin2_cave_runtime_inputs.py, #642) to emit the guarded boot
fixture inputs (`p2-cave-entry.txt` + `p2-cave-generate.txt` +
`p2-cave-runtime-inputs.json`) into a private run layout, plus the line-oriented
`p2-tutorial1-floor1.txt` staging sidecar.

Fail-closed: absent/malformed P0 packet raises FileNotFoundError/ValueError;
contract drift is reported as problems, never silently corrected. Floor 2,
persistence and gameplay sign-off remain out of scope.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

LANE = "p2-cave-tutorial_1-p1-runtime"
CAVE_ID = "tutorial_1"
SCHEMA = 1
SUPPORTED_FIRST = 1
SIDECAR_VERSION = "P2_TUTORIAL1_P1_1"
UNIT_SUFFIXES = ("arc.szs", "texts.szs")
EXPECTED_FLOORS = (1, 2)


def load_packet(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("Missing P0 packet: " + str(path))
    packet = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(packet, dict) or packet.get("schema") != 1:
        raise ValueError("P0 packet schema must be 1")
    if packet.get("cave_id") != CAVE_ID:
        raise ValueError("P0 packet cave_id must be %r" % CAVE_ID)
    floors = packet.get("floors")
    if not isinstance(floors, list) or not floors:
        raise ValueError("P0 packet must carry a non-empty floors list")
    try:
        occupied = sorted({n for f in floors
                           for n in range(int(f["first"]), int(f["last"]) + 1)})
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Malformed floor range: " + str(error))
    if occupied != list(EXPECTED_FLOORS):
        raise ValueError("P0 packet floor coverage is %s, expected %s"
                         % (occupied, list(EXPECTED_FLOORS)))
    return packet


def floor_one(packet):
    matches = [f for f in packet["floors"] if int(f["first"]) == SUPPORTED_FIRST]
    if len(matches) != 1 or int(matches[0]["last"]) != SUPPORTED_FIRST:
        raise ValueError("floor 1 range must be exactly first=last=1")
    return matches[0]


def staging_plan(packet):
    """Deterministic, placement-free floor-1 plan derived from the P0 decode."""
    floor = floor_one(packet)
    units = list(floor.get("unit_names") or [])
    if not units:
        raise ValueError("floor 1 has no unit names")
    enemies = []
    for row in floor.get("enemies") or []:
        enemy_id = row.get("enemy_id")
        if not isinstance(enemy_id, str) or not enemy_id:
            raise ValueError("floor 1 enemy row missing enemy_id")
        enemies.append({
            "enemy_id": enemy_id,
            "carried_treasure": row.get("carried_treasure"),
            "minimum_count": row.get("minimum_count"),
            "selection_weight": row.get("selection_weight"),
            "target_count": row.get("target_count"),
        })
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "cave_id": CAVE_ID,
        "source": packet.get("source"),
        "source_sha256": packet.get("source_sha256"),
        "unit_pool": floor.get("unit_pool"),
        "unit_pool_sha256": (packet.get("unit_pool_sha256") or {}).get(floor.get("unit_pool")),
        "unit_names": units,
        "unit_assets": ["%s/%s" % (name, suffix) for name in units for suffix in UNIT_SUFFIXES],
        "enemies": enemies,
        "treasures": list(floor.get("treasures") or []),
        "gates": list(floor.get("gates") or []),
        "cap_count": int(floor.get("cap_count") or 0),
        "generated": False,
        "placements": [],
        "limitations": [
            "Weighted rows are definitions, not spawn instances or placements.",
            "No seeded topology, hole selection or radial distribution is generated.",
            "Floor 2, persistence and gameplay sign-off remain out of scope.",
        ],
    }


def validate_plan(plan, unit_assets=None):
    """Invariant checks. Returns a list of problem strings (empty == clean)."""
    problems = []
    if plan.get("schema") != SCHEMA or plan.get("lane") != LANE:
        problems.append("plan schema/lane mismatch")
    if plan.get("cave_id") != CAVE_ID:
        problems.append("plan cave_id mismatch")
    if plan.get("generated") is not False:
        problems.append("plan must not claim generated content")
    if plan.get("placements"):
        problems.append("plan must not contain invented placements")
    pool = plan.get("unit_pool")
    if not isinstance(pool, str) or not pool:
        problems.append("unit_pool missing")
    if not plan.get("unit_pool_sha256"):
        problems.append("unit_pool_sha256 missing")
    units = plan.get("unit_names") or []
    if not units or len(set(units)) != len(units):
        problems.append("unit_names must be non-empty and unique")
    for row in plan.get("enemies") or []:
        enemy_id = row.get("enemy_id")
        if not isinstance(enemy_id, str) or not enemy_id:
            problems.append("enemy row missing enemy_id")
        if not re.fullmatch(r"[A-Za-z0-9_]+", enemy_id or ""):
            problems.append("enemy_id not a source token: %r" % enemy_id)
        minimum = row.get("minimum_count")
        target = row.get("target_count")
        if minimum is None and target is None:
            problems.append("enemy %s has neither minimum nor target count" % enemy_id)
        for label, value in (("minimum_count", minimum), ("target_count", target)):
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                problems.append("enemy %s %s must be a non-negative int" % (enemy_id, label))
    if unit_assets is not None:
        have = set(unit_assets)
        for asset in plan.get("unit_assets") or []:
            if asset not in have:
                problems.append("missing unit asset: " + asset)
    return problems


def sidecar_text(plan):
    lines = [SIDECAR_VERSION,
             "cave " + plan["cave_id"],
             "floor 1",
             "unit_pool " + str(plan["unit_pool"]),
             "unit_pool_sha256 " + str(plan["unit_pool_sha256"])]
    for name in plan["unit_names"]:
        lines.append("unit " + name)
    for row in plan["enemies"]:
        lines.append("enemy %s min=%s weight=%s target=%s" % (
            row["enemy_id"],
            "-" if row["minimum_count"] is None else row["minimum_count"],
            "-" if row["selection_weight"] is None else row["selection_weight"],
            "-" if row["target_count"] is None else row["target_count"]))
    for treasure in plan["treasures"]:
        lines.append("treasure " + treasure)
    for gate in plan["gates"]:
        lines.append("gate " + gate)
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
        from experimental import pikmin2_cave_runtime_inputs as shared
        entry_builder = shared
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

    Token is the source hash prefix; squad/unit transforms are schema-valid
    harness placeholders (same policy as the shared forest1/yakushima4
    presets), never claimed as retail spawn instances.
    """
    token = (plan.get("source_sha256") or "")[:32]
    units = [[name, 200.0, 200.0, 0] for name in plan["unit_names"]]
    spawns = []
    for row in plan["enemies"]:
        count = row.get("minimum_count")
        if count is None:
            count = row.get("target_count") or 1
        spawns.append([row["enemy_id"], int(count)])
    return {
        "token": token,
        "floor": 1,
        "health": 1.0,
        "squad": [[1, 1]] * 20,
        "pool": plan["unit_pool"],
        "units": units,
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
    json_path = output_dir / "p2-tutorial1-floor1.json"
    txt_path = output_dir / "p2-tutorial1-floor1.txt"
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