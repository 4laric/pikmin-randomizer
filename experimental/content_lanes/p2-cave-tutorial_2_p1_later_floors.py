"""P1 later-floor staging-plan adapter for tutorial_2 (lane p2-cave-tutorial_2-p1-later-floors, #747).

Consumes the DONE tutorial_2 P0 packet (schema p2-cave-tutorial_2-p0/1, 9
floors, read-only) and the hash-pinned tutorial_2 source locator (read-only),
and turns floors 2-9 into deterministic, placement-free STAGING PLANS for the
native floor fixture. It never re-derives the P0 catalog and never invents
placements: definition rows stay definitions exactly as P0 recorded them.

Floor-1 is owned by the DONE floor-1 lane (implementation-ready); this module
refuses floor 1 to avoid duplicate ownership. The open P0 light_a cargo
blocker is floor 9; floor 9 staging records it unresolved.

Persistence: the adapter emits the descend-chain plan (floor N -> N+1 via the
engine cave checkpoint path) but performs no save writes itself; the native
fixture observes the checkpoint markers. If the engine entry policy refuses a
floor, that floor is reported BLOCKED with the exact policy reason, never
simulated.

Fail-closed: absent/malformed P0 packet raises FileNotFoundError/ValueError;
contract drift is reported as problems, never silently corrected.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

LANE = "p2-cave-tutorial_2-p1-later-floors"
CAVE_ID = "tutorial_2"
SCHEMA = 1
PACKET_SCHEMA = "p2-cave-tutorial_2-p0/1"
EXPECTED_FLOOR_COUNT = 9
LATER_FLOORS = tuple(range(2, EXPECTED_FLOOR_COUNT + 1))
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/tutorial_2.txt"
SOURCE_SHA256 = "05a38ab1e37c4ad11b5f48425bec3c2101ff199a4ea0b926fc9f35fde5620049"
ENTRY_VERSION = "P2_CAVE_ENTRY_1"
ENTRY_VERSION_LATER = "P2_CAVE_ENTRY_4"
ENTRY_FLOORS = (1, 2)
ENTRY_FLOORS_LATER = tuple(range(3, 9))
# Floor-9 Houdai_light_a staging resolution (#805, read-only pin).
HOUDAI_LIGHT_A_TOKEN = "Houdai_light_a"
HOUDAI_LIGHT_A_ENEMY = "Houdai"
HOUDAI_LIGHT_A_ENEMY_ID = 66
HOUDAI_LIGHT_A_CARGO = "light_a"
HOUDAI_LIGHT_A_POOL = "1_units_houdai_metal.txt"
HOUDAI_LIGHT_A_PIN_SHA = "7fa6df04dc8a28b380844582494aa4937818a6bebb32b32b3e6ab36c0cc993df"
DESCEND_POLICY_PIN_SHA = "3cacd9ac4cb778db1147e37ad71d257cd797d37f23bc6154b6bdebe2739f0128"


def load_packet(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("Missing P0 packet: " + str(path))
    packet = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA:
        raise ValueError("P0 packet schema must be %r" % PACKET_SCHEMA)
    if packet.get("source_id") != CAVE_ID:
        raise ValueError("P0 packet source_id must be %r" % CAVE_ID)
    floors = packet.get("floors")
    if not isinstance(floors, list) or not floors:
        raise ValueError("P0 packet must carry a non-empty floors list")
    numbers = sorted({int(f["floor"]) for f in floors})
    if numbers != list(range(1, EXPECTED_FLOOR_COUNT + 1)):
        raise ValueError("P0 packet floor coverage is %s, expected 1..%d"
                         % (numbers, EXPECTED_FLOOR_COUNT))
    return packet


def floor_plan(packet, number):
    if number not in LATER_FLOORS:
        raise ValueError("floor %r is not in later-floor scope %s" % (number, LATER_FLOORS))
    matches = [f for f in packet["floors"] if int(f["floor"]) == number]
    if len(matches) != 1:
        raise ValueError("floor %d must appear exactly once" % number)
    floor = matches[0]
    pool = floor.get("unit_pool")
    if not isinstance(pool, str) or not pool:
        raise ValueError("floor %d has no unit pool" % number)
    tokens = floor.get("tokens") or []
    if not tokens:
        raise ValueError("floor %d has no enemy tokens" % number)
    resolved_cargo = []
    if number == 9:
        for token in tokens:
            if token.get("kind") == "unknown_cargo":
                if (token.get("source_token") == HOUDAI_LIGHT_A_TOKEN and token.get("base") == HOUDAI_LIGHT_A_ENEMY and token.get("carried") == HOUDAI_LIGHT_A_CARGO and floor.get("unit_pool") == HOUDAI_LIGHT_A_POOL):
                    token["kind"] = "carrier"
                    resolved_cargo.append({"token": HOUDAI_LIGHT_A_TOKEN, "enemy": HOUDAI_LIGHT_A_ENEMY, "enemy_id": HOUDAI_LIGHT_A_ENEMY_ID, "cargo": HOUDAI_LIGHT_A_CARGO, "pool": HOUDAI_LIGHT_A_POOL, "pin_sha256": HOUDAI_LIGHT_A_PIN_SHA})
                else:
                    raise ValueError("floor 9 unresolvable token")
    for token in tokens:
        if token.get("kind") not in ("exact", "carrier", "generator_variant"):
            raise ValueError("floor unresolvable token")
        if not token.get("base"):
            raise ValueError("floor token missing base id")
    counts = Counter(t["base"] for t in tokens)
    for base in counts:
        if not re.fullmatch(r"[A-Za-z0-9_]+", base):
            raise ValueError("enemy id not a source token: %r" % base)
    treasure_count = floor.get("treasure_tokens")
    if not isinstance(treasure_count, int) or treasure_count < 0:
        raise ValueError("floor %d treasure count missing" % number)
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "cave_id": CAVE_ID,
        "floor": number,
        "source": SOURCE_PATH,
        "source_sha256": SOURCE_SHA256,
        "unit_pool": pool,
        "enemies": [{"enemy_id": b, "count": c, "carried": sorted({x.get("carried") for x in tokens if x["base"] == b and x.get("carried")}), "variant": any(x.get("kind") == "generator_variant" for x in tokens if x["base"] == b)} for b, c in sorted(counts.items())],
        "treasure_count": treasure_count,
        "resolved_cargo": resolved_cargo,
        "treasure_ids_unresolved": True,
        "missing_treasure": list(floor.get("missing_treasure") or []),
        "generated": False,
        "placements": [],
        "entry_bootable": number in ENTRY_FLOORS or number in ENTRY_FLOORS_LATER,
        "limitations": [
            "Weighted rows are definitions, not spawn instances or placements.",
            "No seeded topology, holes or placements are generated.",
            "Per-floor treasure ids are not enumerated in the P0 packet; only counts are recorded.",
            "Direct engine entry supports floors 1-2 only; floors 3+ need the descend chain or stay blocked.",
        ],
    }


def validate_plan(plan):
    problems = []
    if plan.get("schema") != SCHEMA or plan.get("lane") != LANE:
        problems.append("plan schema/lane mismatch")
    if plan.get("cave_id") != CAVE_ID:
        problems.append("plan cave_id mismatch")
    if plan.get("source_sha256") != SOURCE_SHA256:
        problems.append("plan source hash must match the pinned locator hash")
    if plan.get("floor") not in LATER_FLOORS:
        problems.append("plan floor outside later-floor scope")
    if plan.get("generated") is not False:
        problems.append("plan must not claim generated content")
    if plan.get("placements"):
        problems.append("plan must not contain invented placements")
    if not isinstance(plan.get("unit_pool"), str) or not plan["unit_pool"]:
        problems.append("unit_pool missing")
    for row in plan.get("enemies") or []:
        if not re.fullmatch(r"[A-Za-z0-9_]+", row.get("enemy_id") or ""):
            problems.append("enemy_id not a source token")
        count = row.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            problems.append("enemy count must be a positive int")
    return problems


def sidecar_text(plan):
    lines = ["P2_TUTORIAL2_LATER_1",
             "cave " + plan["cave_id"],
             "floor %d" % plan["floor"],
             "unit_pool " + str(plan["unit_pool"]),
             "source_sha256 " + str(plan["source_sha256"])]
    for row in plan["enemies"]:
        lines.append("enemy %s count=%d" % (row["enemy_id"], row["count"]))
    lines.append("treasure_count %d (ids unresolved in P0 packet)" % plan["treasure_count"])
    lines.append("entry_bootable %d" % int(plan["entry_bootable"]))
    lines.append("end")
    return "\n".join(lines) + "\n"


def descend_plan(from_floor):
    if from_floor < 1 or from_floor >= EXPECTED_FLOOR_COUNT:
        raise ValueError("descend origin out of range")
    return {"from": from_floor, "to": from_floor + 1,
            "mechanism": "engine cave checkpoint/descent path (observed, not written here)"}


def build_runtime_inputs(plan, output_dir, entry_builder=None):
    if not plan["entry_bootable"]:
        raise ValueError("floor %d is not entry-bootable on this pin" % plan["floor"])
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
    entry_text = entry_builder.render_entry(_shared_preset(plan))
    if plan["floor"] >= 3:
        # Adapted #757 descend policy admits P2_CAVE_ENTRY_4 for staged
        # floors 3-8 under the identical 32-hex token contract; the shared
        # builder only renders ENTRY_1, so swap the version token and
        # re-validate the exact header shape below.
        head, _, rest = entry_text.partition(" ")
        assert head == "P2_CAVE_ENTRY_1"
        entry_text = ENTRY_VERSION_LATER + " " + rest
        fields = entry_text.split()
        assert fields[0] == ENTRY_VERSION_LATER and int(fields[2]) == plan["floor"]
        assert len(fields[1]) == 32
    generate_text = entry_builder.render_generate(_shared_preset(plan))
    entry_path = output_dir / "p2-cave-entry.txt"
    generate_path = output_dir / "p2-cave-generate.txt"
    entry_path.write_text(entry_text, encoding="utf-8")
    generate_path.write_text(generate_text, encoding="utf-8")
    provenance = {
        "schema": "p2-cave-runtime-inputs-1",
        "cave": plan["cave_id"],
        "floor": plan["floor"],
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
    token = (plan.get("source_sha256") or "")[:32]
    spawns = [[row["enemy_id"], int(row["count"])] for row in plan["enemies"]]
    return {
        "token": token,
        "floor": plan["floor"],
        "health": 1.0,
        "squad": [[1, 1]] * 20,
        "pool": plan["unit_pool"],
        "units": [[plan["unit_pool"], 200.0, 200.0, 0]],
        "rooms": [[0, 0, 0.0, 0.0, 0.0]],
        "spawns": spawns,
        "anchor": "hole",
    }


def write_floor(packet_path, output_dir, number):
    packet = load_packet(packet_path)
    plan = floor_plan(packet, number)
    problems = validate_plan(plan)
    if problems:
        raise ValueError("staging plan problems: " + "; ".join(problems))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / ("p2-tutorial2-floor%d.json" % number)
    txt_path = output_dir / ("p2-tutorial2-floor%d.txt" % number)
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
    parser.add_argument("--floors", default="2,3,4,5,6,7,8,9")
    parser.add_argument("--runtime-inputs", action="store_true")
    args = parser.parse_args(argv)
    numbers = [int(v) for v in args.floors.split(",")]
    results = {}
    for number in numbers:
        result = write_floor(args.packet, args.output, number)
        if args.runtime_inputs:
            result["runtime_inputs"] = build_runtime_inputs(
                result["plan"], Path(args.output) / ("floor%d" % number))
        results[number] = {k: v for k, v in result.items() if k != "plan"}
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
