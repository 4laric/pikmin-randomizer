"""P1 floor-1 staging-plan adapter for forest_1 (lane shard-caves-forest-forest1-p1, #154).

Consumes the DONE forest_1 P0 packet (lane shard-caves-forest-forest1-p0)
read-only and turns its floor-1 decode into a deterministic, placement-free
STAGING PLAN for the native floor-1 fixture. It does not re-decode disc
bytes (that is the P0 packet's pinned output) and it never invents
placements: weighted definition rows stay definitions, exactly as P0
recorded them.

Emits:
  * ``p2-forest1-floor1.json``  - machine-readable staging plan (handoff)
  * ``p2-forest1-floor1.txt``   - line-oriented sidecar the engine-independent
                                  native fixture (native/tools/p2_forest1_p1_fixture.cpp)
                                  parses without a JSON dependency

Fail-closed: absent/malformed P0 packet raises FileNotFoundError/ValueError;
contract drift is reported as problems, never silently corrected. Higher
floors 2-5, persistence and gameplay sign-off remain out of scope.
"""
import argparse
import json
import re
from pathlib import Path

LANE = "shard-caves-forest-forest1-p1"
CAVE_ID = "forest_1"
SCHEMA = 1
SUPPORTED_FIRST = 1
SIDECAR_VERSION = "P2_FOREST1_P1_1"
UNIT_SUFFIXES = ("arc.szs", "texts.szs")


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
    if occupied != [1, 2, 3, 4, 5]:
        raise ValueError("P0 packet floor coverage is %s, expected 1-5" % occupied)
    return packet


def floor_one(packet):
    matches = [f for f in packet["floors"] if int(f["first"]) == SUPPORTED_FIRST]
    if len(matches) != 1 or int(matches[0]["last"]) != SUPPORTED_FIRST:
        raise ValueError("floor_1 range must be exactly first=last=1")
    return matches[0]


def staging_plan(packet):
    """Deterministic, placement-free floor-1 plan derived from the P0 decode."""
    floor = floor_one(packet)
    units = list(floor.get("unit_names") or [])
    if not units:
        raise ValueError("floor_1 has no unit names")
    enemies = []
    for row in floor.get("enemies") or []:
        enemy_id = row.get("enemy_id")
        if not isinstance(enemy_id, str) or not enemy_id:
            raise ValueError("floor_1 enemy row missing enemy_id")
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
            "Floors 2-5, persistence and gameplay sign-off remain out of scope.",
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


def write_plan(packet_path, output_dir):
    import hashlib
    packet = load_packet(packet_path)
    plan = staging_plan(packet)
    problems = validate_plan(plan)
    if problems:
        raise ValueError("staging plan problems: " + "; ".join(problems))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "p2-forest1-floor1.json"
    txt_path = output_dir / "p2-forest1-floor1.txt"
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
    args = parser.parse_args(argv)
    result = write_plan(args.packet, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "plan"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


SIDECAR_VERSION_GENERATE = "P2_CAVE_GENERATE_1"


def parse_generate_sidecar(text):
    if not isinstance(text, str):
        raise ValueError("sidecar must be text")
    tokens = text.split()
    pos = [0]

    def take():
        if pos[0] >= len(tokens):
            raise ValueError("truncated sidecar")
        token = tokens[pos[0]]
        pos[0] += 1
        return token

    def expect(word):
        if take() != word:
            raise ValueError("expected section marker")

    def take_int(lo, hi, what):
        token = take()
        try:
            value = int(token)
        except ValueError:
            raise ValueError("bad number")
        if isinstance(value, bool) or not lo <= value <= hi:
            raise ValueError("number out of range")
        return value

    def take_number(what):
        token = take()
        try:
            value = float(token)
        except ValueError:
            raise ValueError("bad number")
        if value != value or abs(value) > 100000:
            raise ValueError("number not finite")
        return value

    expect(SIDECAR_VERSION_GENERATE)
    expect("pool")
    pool = take()
    nunits = take_int(1, 64, "nunits")
    units = []
    for i in range(nunits):
        expect("unit")
        idx = take_int(0, 63, "unit idx")
        name = take()
        w = take_number("unit w")
        d = take_number("unit d")
        kind = take_int(0, 255, "unit kind")
        if idx != i or not name or w <= 0 or d <= 0:
            raise ValueError("bad unit row")
        units.append({"name": name, "w": w, "d": d, "kind": kind})
    expect("rooms")
    nrooms = take_int(1, 256, "nrooms")
    rooms = []
    for i in range(nrooms):
        expect("room")
        idx = take_int(0, 255, "room idx")
        unit = take_int(0, nunits - 1, "room unit")
        turn = take_int(0, 3, "room turn")
        ox, oy, oz = take_number("ox"), take_number("oy"), take_number("oz")
        if idx != i:
            raise ValueError("bad room idx")
        rooms.append({"unit": unit, "turn": turn, "offset": [ox, oy, oz]})
    expect("doors")
    ndoors = take_int(0, 4096, "ndoors")
    doors = []
    for _ in range(ndoors):
        expect("door")
        doors.append({"unit": take_int(0, nunits - 1, "door unit"),
                      "id": take_int(0, 1024, "door id"),
                      "dir": take_int(0, 3, "door dir")})
    expect("links")
    nlinks = take_int(0, 4096, "nlinks")
    links = []
    for _ in range(nlinks):
        expect("link")
        links.append({"unit": take_int(0, nunits - 1, "link unit"),
                      "door": take_int(0, 4096, "link door"),
                      "peer_unit": take_int(0, nunits - 1, "peer unit"),
                      "peer_door": take_int(0, 4096, "peer door"),
                      "dist": take_number("link dist")})
    expect("spawns")
    nspawns = take_int(1, 256, "nspawns")
    spawns = []
    for _ in range(nspawns):
        expect("spawn")
        ident = take()
        count = take_int(1, 10000, "spawn count")
        if not ident:
            raise ValueError("empty spawn id")
        spawns.append({"id": ident, "count": count})
    expect("anchor")
    anchor = take()
    if anchor not in ("hole", "geyser"):
        raise ValueError("anchor must be hole|geyser")
    if pos[0] != len(tokens):
        raise ValueError("trailing tokens after anchor")
    return {"pool": pool, "units": units, "rooms": rooms, "doors": doors,
            "links": links, "spawns": spawns, "anchor": anchor}


def check_generate_against_floor_one(packet, sidecar_text):
    try:
        manifest = parse_generate_sidecar(sidecar_text)
    except ValueError as error:
        return (["malformed sidecar: " + str(error)], [])
    problems, notes = [], []
    try:
        floor = floor_one(packet)
    except ValueError as error:
        return (["bad P0 packet: " + str(error)], [])
    if manifest["pool"] != floor.get("unit_pool"):
        problems.append("pool mismatch vs floor-1 pool")
    known_units = set(floor.get("unit_names") or [])
    for unit in manifest["units"]:
        if unit["name"] not in known_units:
            problems.append("STAGED-EXTRA unit not in floor-1 decode: " + unit["name"])
    pool_hash = (packet.get("unit_pool_sha256") or {}).get(floor.get("unit_pool"))
    notes.append("STAGED unit dimensions/doors come from the unit-blob decode (pinned hash %s), not the P0 packet" % pool_hash)
    notes.append("STAGED room topology: %d room(s); turns/offsets are staged, not retail facts" % len(manifest["rooms"]))
    notes.append("STAGED anchor kind: %s (not in P0 decode)" % manifest["anchor"])
    minima = {}
    for row in floor.get("enemies") or []:
        if row.get("minimum_count") is not None:
            minima[row["enemy_id"]] = minima.get(row["enemy_id"], 0) + row["minimum_count"]
    known_ids = {row["enemy_id"] for row in floor.get("enemies") or []}
    for spawn in manifest["spawns"]:
        if spawn["id"] not in known_ids:
            problems.append("spawn id not in floor-1 roster: " + spawn["id"])
        elif spawn["count"] < minima.get(spawn["id"], 0):
            problems.append("spawn count below roster minimum: " + spawn["id"])
    for row in floor.get("enemies") or []:
        if row.get("target_count") is not None:
            got = sum(s["count"] for s in manifest["spawns"] if s["id"] == row["enemy_id"])
            if got != row["target_count"]:
                notes.append("target deviation: %s staged %d vs P0 target %d" % (row["enemy_id"], got, row["target_count"]))
    return (problems, notes)
