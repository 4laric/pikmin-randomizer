"""Lane 50: host-side carry-blocking plan bridging lane-44 proxy cave rooms.

Lane 44 (:mod:`experimental.pikmin2_cave_rooms`) lays a deterministic proxy grid
over an observed cave layout and emits one node per room/unit. This module turns
those nodes into the *carry-blocking* plan the native engine consumes: an
electric gate (``hazard == "elec"``) blocks carrying until a yellow Pikmin opens
it, and a water pool (``hazard == "water"``) blocks non-blue carrying. Every
other hazard or node blocks nothing.

Node order, ids and kinds are preserved verbatim. When the lane-45 geometry plan
(:mod:`experimental.pikmin2_cave_geometry`) is available next to the rooms input
its ``geometry`` class is copied; otherwise the plan is ``proxy``. A geometry
plan whose ``cave``/``floor``/``seed`` disagree with the rooms file, whose class
is unknown, or whose nodes do not match the rooms units is rejected.

Two representations are strict inverses: the plan dict and the canonical
``P2_CAVE_GATES_1`` text the native side reads. The text is whitespace
tokenised with fixed positions and ``-`` standing in for empty values. The plan
never claims generation: ``generation`` is always ``False``.

Determinism: nothing here reads the clock, draws a random number or depends on
filesystem order.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GATES_SCHEMA = "p2-cave-gates/1"
GATES_TEXT_HEADER = "P2_CAVE_GATES_1"
REPORT_SCHEMA = "p2-cave-gates-report/1"
GEOMETRIES = ("real", "mixed", "proxy")
NODE_KINDS = ("segment", "choke", "leaf", "bud", "gate")
HAZARDS = ("none", "water", "elec", "fire", "poison")
CARRY_BLOCKS = ("none", "water", "elec")
KEYS = ("-", "yellow", "blue")
PLAN_SOURCE = "pikmin2_cave_gates"
GENERATION = False
GEOMETRY_FILE = "p2-cave-geometry.json"

CARRY = {"elec": ("elec", "yellow"), "water": ("water", "blue")}


class CaveGatesError(ValueError):
    """Fail-closed error for gate planning, validation and text parsing."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CaveGatesError(message)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _hazard(value):
    if value is None or value == "" or value == "none":
        return None
    return value


def _token(value, field: str) -> str:
    _require(isinstance(value, str) and value != "", f"{field} must be a non-empty token")
    _require(not any(ch.isspace() for ch in value), f"{field} must not contain whitespace")
    return value


def _int_text(value, field: str) -> str:
    _require(_is_int(value), f"{field} must be an integer")
    return str(value)


def _carry_for(hazard):
    return CARRY.get(hazard, ("none", "-"))


def _counts(doors) -> dict:
    elec = sum(1 for door in doors if door.get("carry_block") == "elec")
    water = sum(1 for door in doors if door.get("carry_block") == "water")
    no_block = sum(1 for door in doors if door.get("carry_block") == "none")
    return {"doors": len(doors), "elec": elec, "water": water, "no_block": no_block}


def _geometry_class(rooms, geometry) -> str:
    if geometry is None:
        return "proxy"
    _require(isinstance(geometry, dict), "geometry plan must be a mapping")
    for field in ("cave", "floor", "seed"):
        _require(geometry.get(field) == rooms.get(field),
                 f"geometry {field} disagrees with the rooms file")
    geometry_class = geometry.get("geometry")
    _require(geometry_class in GEOMETRIES, f"unknown geometry class {geometry_class!r}")
    nodes = geometry.get("nodes")
    _require(isinstance(nodes, list), "geometry plan must contain nodes")
    return geometry_class


def build_gates(rooms, geometry=None) -> dict:
    """Build the carry-blocking plan for a lane-44 rooms dict.

    ``geometry`` is an optional lane-45 real-geometry plan. A mismatched
    ``cave``/``floor``/``seed``, an unknown class or a node set that does not
    match the rooms units is a hard ``CaveGatesError``.
    """
    _require(isinstance(rooms, dict), "rooms must be a mapping")
    units = rooms.get("units")
    _require(isinstance(units, list), "rooms must contain a units list")
    for field in ("cave", "entrance", "hole"):
        _token(rooms.get(field), field)
    for field in ("floor", "seed"):
        _require(_is_int(rooms.get(field)), f"rooms {field} must be an integer")

    seen = set()
    doors = []
    for unit in units:
        _require(isinstance(unit, dict), "each room unit must be a mapping")
        unit_id = _token(unit.get("id"), "unit id")
        _require(unit_id not in seen, f"duplicate door id {unit_id}")
        seen.add(unit_id)
        kind = _token(unit.get("kind"), f"kind for {unit_id}")
        _require(kind in NODE_KINDS, f"unknown kind {kind!r} for {unit_id}")
        hazard = _hazard(unit.get("hazard"))
        _require(hazard is None or hazard in HAZARDS, f"unknown hazard {hazard!r} for {unit_id}")
        carry_block, key = _carry_for(hazard)
        doors.append({
            "id": unit_id,
            "kind": kind,
            "hazard": hazard,
            "carry_block": carry_block,
            "key": key,
        })

    _require(rooms["entrance"] in seen, "entrance is not a known door")
    _require(rooms["hole"] in seen, "hole is not a known door")

    geometry_class = _geometry_class(rooms, geometry)
    if geometry is not None:
        geometry_ids = set()
        for node in geometry["nodes"]:
            _require(isinstance(node, dict), "each geometry node must be a mapping")
            node_id = _token(node.get("id"), "geometry node id")
            _require(node_id not in geometry_ids, f"duplicate geometry node id {node_id}")
            geometry_ids.add(node_id)
        _require(geometry_ids == seen, "geometry nodes do not match the rooms units")

    plan = {
        "schema": GATES_SCHEMA,
        "generation": GENERATION,
        "source": PLAN_SOURCE,
        "cave": rooms["cave"],
        "floor": rooms["floor"],
        "seed": rooms["seed"],
        "geometry": geometry_class,
        "doors": doors,
        "entrance": rooms["entrance"],
        "hole": rooms["hole"],
    }
    validate_gates(plan)
    return plan


def _fmt_hazard(hazard) -> str:
    return hazard if hazard else "none"


def gates_text(plan) -> str:
    """Render the canonical ``P2_CAVE_GATES_1`` text (newline terminated)."""
    _require(isinstance(plan, dict), "plan must be a mapping")
    doors = plan.get("doors")
    _require(isinstance(doors, list), "plan must contain doors")
    geometry = plan.get("geometry")
    _require(geometry in GEOMETRIES, f"unknown geometry class {geometry!r}")

    lines = [
        GATES_TEXT_HEADER,
        f"cave {_token(plan.get('cave'), 'cave')}",
        f"floor {_int_text(plan.get('floor'), 'floor')}",
        f"seed {_int_text(plan.get('seed'), 'seed')}",
        f"geometry {geometry}",
        f"doors {len(doors)}",
    ]
    for door in doors:
        door_id = _token(door.get("id"), "door id")
        kind = _token(door.get("kind"), f"kind for {door_id}")
        _require(kind in NODE_KINDS, f"unknown kind {kind!r} for {door_id}")
        hazard = _hazard(door.get("hazard"))
        _require(hazard is None or hazard in HAZARDS, f"unknown hazard {hazard!r} for {door_id}")
        expected_carry, expected_key = _carry_for(hazard)
        _require(door.get("carry_block") == expected_carry,
                 f"door {door_id} carry_block must be {expected_carry!r}")
        _require(door.get("key") == expected_key, f"door {door_id} key must be {expected_key!r}")
        lines.append(
            f"{door_id} {kind} {_fmt_hazard(hazard)} {expected_carry} {expected_key}"
        )

    lines.append(f"entrance {_token(plan.get('entrance'), 'entrance')}")
    lines.append(f"hole {_token(plan.get('hole'), 'hole')}")
    return "\n".join(lines) + "\n"


def parse_gates_text(text) -> dict:
    """Parse the canonical text strictly; ``CaveGatesError`` on any mismatch."""
    _require(isinstance(text, str), "gates text must be a string")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    _require(bool(lines) and lines[0] == GATES_TEXT_HEADER, "bad gates text header")
    index = 1

    def take(prefix):
        nonlocal index
        _require(index < len(lines), f"missing {prefix.strip()} section")
        line = lines[index]
        _require(line.startswith(prefix), f"expected {prefix.strip()} section, got {line!r}")
        index += 1
        return line[len(prefix):]

    cave = take("cave ").strip()
    _require(cave != "", "cave must be non-empty")
    try:
        floor = int(take("floor ").strip())
        seed = int(take("seed ").strip())
    except ValueError as exc:
        raise CaveGatesError(f"malformed numeric section: {exc}") from exc

    geometry = take("geometry ").strip()
    _require(geometry in GEOMETRIES, f"unknown geometry class {geometry!r}")

    try:
        door_count = int(take("doors ").strip())
    except ValueError as exc:
        raise CaveGatesError(f"malformed doors count: {exc}") from exc
    _require(door_count >= 0, "doors count must be >= 0")

    doors = []
    seen = set()
    for _ in range(door_count):
        _require(index < len(lines), "truncated doors section")
        parts = lines[index].split()
        index += 1
        _require(len(parts) == 5, f"malformed door row: {parts!r}")
        door_id, kind, hazard, carry_block, key = parts
        _require(door_id not in seen, f"duplicate door id {door_id}")
        seen.add(door_id)
        _require(kind in NODE_KINDS, f"unknown kind {kind!r} for {door_id}")
        hazard_value = _hazard(hazard)
        _require(hazard_value in (None,) or hazard_value in HAZARDS,
                 f"unknown hazard {hazard!r} for {door_id}")
        _require(carry_block in CARRY_BLOCKS, f"unknown carry_block {carry_block!r}")
        _require(key in KEYS, f"unknown key {key!r}")
        doors.append({
            "id": door_id,
            "kind": kind,
            "hazard": hazard_value,
            "carry_block": carry_block,
            "key": key,
        })

    entrance = take("entrance ").strip()
    hole = take("hole ").strip()
    _require(index == len(lines), "trailing content after the hole line")

    plan = {
        "schema": GATES_SCHEMA,
        "generation": GENERATION,
        "source": PLAN_SOURCE,
        "cave": cave,
        "floor": floor,
        "seed": seed,
        "geometry": geometry,
        "doors": doors,
        "entrance": entrance,
        "hole": hole,
    }
    validate_gates(plan)
    return plan


def validate_gates(plan) -> None:
    """Fail-closed validation of a plan; raises ``CaveGatesError`` or returns None."""
    _require(isinstance(plan, dict), "plan must be a mapping")
    _require(plan.get("generation") is False, "gates plan must not claim generation")
    _require(plan.get("geometry") in GEOMETRIES, f"unknown geometry class {plan.get('geometry')!r}")
    _token(plan.get("cave"), "cave")
    _require(_is_int(plan.get("floor")), "floor must be an integer")
    _require(_is_int(plan.get("seed")), "seed must be an integer")

    doors = plan.get("doors")
    _require(isinstance(doors, list), "plan must contain doors")
    seen = set()
    for door in doors:
        _require(isinstance(door, dict), "each door must be a mapping")
        door_id = _token(door.get("id"), "door id")
        _require(door_id not in seen, f"duplicate door id {door_id}")
        seen.add(door_id)
        kind = _token(door.get("kind"), f"kind for {door_id}")
        _require(kind in NODE_KINDS, f"unknown kind {kind!r} for {door_id}")
        hazard = _hazard(door.get("hazard"))
        _require(hazard is None or hazard in HAZARDS, f"unknown hazard {hazard!r} for {door_id}")
        carry_block, key = _carry_for(hazard)
        _require(door.get("carry_block") == carry_block,
                 f"door {door_id} carry_block must be {carry_block!r}")
        _require(door.get("key") == key, f"door {door_id} key must be {key!r}")

    _require(plan.get("entrance") in seen, "entrance is not a known door")
    _require(plan.get("hole") in seen, "hole is not a known door")
    return None


def gates_report(plan) -> dict:
    """Counts (and boolean mirrors) describing a gates plan's blocking doors."""
    validate_gates(plan)
    counts = _counts(plan["doors"])
    return {
        "schema": REPORT_SCHEMA,
        "generation": GENERATION,
        "source": plan.get("source"),
        "geometry": plan.get("geometry"),
        "cave": plan.get("cave"),
        "floor": plan.get("floor"),
        "seed": plan.get("seed"),
        "doors": counts["doors"],
        "elec": counts["elec"],
        "water": counts["water"],
        "no_block": counts["no_block"],
        "has_doors": counts["doors"] > 0,
        "has_elec": counts["elec"] > 0,
        "has_water": counts["water"] > 0,
        "has_no_block": counts["no_block"] > 0,
    }


def gates_marker(plan) -> str:
    """One-line stdout marker describing a plan."""
    validate_gates(plan)
    counts = _counts(plan["doors"])
    return (
        "P2_CAVE_GATES_READY doors=%d elec=%d water=%d no_block=%d geometry=%s "
        "cave=%s floor=%s seed=%s"
        % (counts["doors"], counts["elec"], counts["water"], counts["no_block"],
           plan.get("geometry"), plan.get("cave"), plan.get("floor"), plan.get("seed"))
    )


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rooms", required=True, help="lane-44 p2-cave-rooms.json")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--geometry", default=None,
                        help="optional lane-45 p2-cave-geometry.json")
    args = parser.parse_args(argv)

    rooms_path = Path(args.rooms)
    rooms = json.loads(rooms_path.read_text(encoding="utf-8"))

    geometry = None
    if args.geometry:
        geometry_path = Path(args.geometry)
        _require(geometry_path.is_file(), f"geometry file not found: {geometry_path}")
        geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
    else:
        candidate = rooms_path.parent / GEOMETRY_FILE
        if candidate.is_file():
            geometry = json.loads(candidate.read_text(encoding="utf-8"))

    plan = build_gates(rooms, geometry)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    text_path = out_dir / "p2-cave-gates.txt"
    json_path = out_dir / "p2-cave-gates.json"
    report_path = out_dir / "p2-cave-gates-report.json"
    text_path.write_text(gates_text(plan), encoding="utf-8", newline="\n")
    _write_json(json_path, plan)
    _write_json(report_path, gates_report(plan))

    print(gates_marker(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
