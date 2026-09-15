"""Lane 44: proxy room/unit geometry for an observed Pikmin 2 cave layout.

This is host-side instantiation glue only. It consumes a lane-40/41
``p2-cave-observed-layout/1`` graph and lays every node out on a deterministic
2D proxy grid, so the existing port room preview has something to draw while the
real native geometry is not yet available. Node ids, kinds, hazards,
``segment_index`` values, items and every edge are preserved verbatim, so the
lane-40 checker (:mod:`experimental.pikmin2_cave_spike`) still matches node ids.

Two salts produce two *different* geometries for the same logical table: the
layer row spacing ``cell + (salt % 4)`` and a per-salt lateral stagger for
alternate layers move the world coordinates while leaving every id/kind/hazard/
edge untouched. ``logical_projection`` exists to prove exactly that.

The module also emits the strict native text grammar (``P2_CAVE_ROOMS_1``) the
C++ side reads, and parses it back losslessly. The native parser reads
whitespace tokens, so unit ids must be whitespace-free (they are:
``forest_1:f1:segment:0`` is one token).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

from experimental.pikmin2_cave_spike import CaveSpikeError, validate_layout

ROOMS_SCHEMA = "p2-cave-rooms/1"
ROOMS_TEXT_HEADER = "P2_CAVE_ROOMS_1"
PROXY_GEOMETRY = "proxy"
REPORT_SCHEMA = "p2-cave-rooms-report/1"


class CaveRoomsError(ValueError):
    """Fail-closed error for proxy room instantiation and text parsing."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CaveRoomsError(message)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _adjacency(layout) -> dict:
    adjacency = {node["id"]: [] for node in layout["nodes"]}
    for left, right in layout["edges"]:
        adjacency[left].append(right)
        adjacency[right].append(left)
    return adjacency


def _bfs_order(layout, adjacency):
    order = []
    depth = {layout["entrance"]: 0}
    queue = deque([layout["entrance"]])
    while queue:
        current = queue.popleft()
        order.append(current)
        for neighbour in adjacency[current]:
            if neighbour not in depth:
                depth[neighbour] = depth[current] + 1
                queue.append(neighbour)
    return order, depth


def rooms_from_layout(layout, salt=0, cell=48, origin=(0, 0)) -> dict:
    try:
        validate_layout(layout)
    except CaveSpikeError as exc:
        raise CaveRoomsError(str(exc)) from exc

    _require(_is_int(salt) and salt >= 0, "salt must be a non-negative integer")
    _require(_is_int(cell) and cell >= 8, "cell must be an integer >= 8")
    _require(isinstance(origin, (list, tuple)) and len(origin) == 2 and all(_is_int(v) for v in origin),
             "origin must be a pair of integers")

    nodes = {node["id"]: node for node in layout["nodes"]}
    adjacency = _adjacency(layout)
    order, depth = _bfs_order(layout, adjacency)

    unreachable = [node_id for node_id in nodes if node_id not in depth]
    _require(not unreachable, f"nodes unreachable from the entrance: {unreachable}")

    row = cell + (salt % 4)
    layer_seen = {}
    units = []
    for node_id in order:
        node = nodes[node_id]
        segment_index = node.get("segment_index")
        _require(_is_int(segment_index), f"node {node_id} needs an integer segment_index")
        layer = depth[node_id]
        index_in_layer = layer_seen.get(layer, 0)
        layer_seen[layer] = index_in_layer + 1
        stagger = (layer % 2) * ((salt % 3) + 1) * cell // 2
        units.append({
            "id": node_id,
            "kind": node["kind"],
            "hazard": node.get("hazard"),
            "segment_index": segment_index,
            "items": list(node.get("items", [])),
            "gx": index_in_layer * cell + stagger,
            "gz": layer * row,
            "doors": sorted(adjacency[node_id]),
        })

    return {
        "schema": ROOMS_SCHEMA,
        "source": layout["source"],
        "geometry": PROXY_GEOMETRY,
        "cave": layout["cave"],
        "floor": layout["floor"],
        "seed": layout["seed"],
        "salt": salt,
        "cell": cell,
        "origin": [origin[0], origin[1]],
        "entrance": layout["entrance"],
        "hole": layout["hole"],
        "units": units,
        "edges": [list(edge) for edge in layout["edges"]],
    }


def logical_projection(rooms) -> dict:
    units = rooms["units"]
    return {
        "ids": sorted(unit["id"] for unit in units),
        "kinds": {unit["id"]: unit["kind"] for unit in units},
        "hazards": {unit["id"]: unit["hazard"] for unit in units},
        "items": {unit["id"]: list(unit["items"]) for unit in units},
        "edges": sorted(sorted(edge) for edge in rooms["edges"]),
        "entrance": rooms["entrance"],
        "hole": rooms["hole"],
        "segment_index": {unit["id"]: unit["segment_index"] for unit in units},
    }


def _csv(values) -> str:
    return ",".join(values) if values else "-"


def rooms_text(rooms) -> str:
    lines = [ROOMS_TEXT_HEADER]
    lines.append(f"cave {rooms['cave']}")
    lines.append(f"floor {rooms['floor']}")
    lines.append(f"seed {rooms['seed']}")
    lines.append(f"salt {rooms['salt']}")
    lines.append(f"cell {rooms['cell']}")
    lines.append(f"origin {rooms['origin'][0]} {rooms['origin'][1]}")
    if rooms.get("source") is not None:
        lines.append(f"source {rooms['source']}")
    if rooms.get("geometry") is not None:
        lines.append(f"geometry {rooms['geometry']}")
    lines.append(f"units {len(rooms['units'])}")
    for unit in rooms["units"]:
        hazard = unit["hazard"] if unit["hazard"] is not None else "none"
        lines.append(
            f"{unit['id']} {unit['kind']} {hazard} {unit['segment_index']} "
            f"{unit['gx']} {unit['gz']} {_csv(unit['doors'])} {_csv(unit['items'])}"
        )
    lines.append(f"entrance {rooms['entrance']}")
    lines.append(f"hole {rooms['hole']}")
    lines.append(f"edges {len(rooms['edges'])}")
    for left, right in rooms["edges"]:
        lines.append(f"{left} {right}")
    return "\n".join(lines) + "\n"


def parse_rooms_text(text) -> dict:
    _require(isinstance(text, str), "rooms text must be a string")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    _require(bool(lines) and lines[0] == ROOMS_TEXT_HEADER, "bad rooms text header")
    index = 1

    def take(prefix):
        nonlocal index
        _require(index < len(lines), f"missing {prefix.strip()} section")
        line = lines[index]
        _require(line.startswith(prefix), f"expected {prefix.strip()} section, got {line!r}")
        index += 1
        return line[len(prefix):]

    try:
        cave = take("cave ").strip()
        floor = int(take("floor "))
        seed = int(take("seed "))
        salt = int(take("salt "))
        cell = int(take("cell "))
        origin_x, origin_y = take("origin ").split()
        origin = [int(origin_x), int(origin_y)]
    except ValueError as exc:
        raise CaveRoomsError(f"malformed numeric section: {exc}") from exc

    source = None
    geometry = None
    if index < len(lines) and lines[index].startswith("source "):
        source = lines[index][len("source "):].strip()
        index += 1
    if index < len(lines) and lines[index].startswith("geometry "):
        geometry = lines[index][len("geometry "):].strip()
        index += 1

    try:
        unit_count = int(take("units "))
        _require(unit_count >= 0, "units count must be >= 0")
    except ValueError as exc:
        raise CaveRoomsError(f"malformed units count: {exc}") from exc

    units = []
    for _ in range(unit_count):
        _require(index < len(lines), "truncated units section")
        parts = lines[index].split(None, 7)
        index += 1
        _require(len(parts) == 8, f"malformed unit line: {parts!r}")
        unit_id, kind, hazard, segment, gx, gz, doors, items = parts
        try:
            segment_index = int(segment)
            gx_value = int(gx)
            gz_value = int(gz)
        except ValueError as exc:
            raise CaveRoomsError(f"malformed unit numbers: {exc}") from exc
        units.append({
            "id": unit_id,
            "kind": kind,
            "hazard": None if hazard == "none" else hazard,
            "segment_index": segment_index,
            "items": [] if items == "-" else items.split(","),
            "gx": gx_value,
            "gz": gz_value,
            "doors": [] if doors == "-" else doors.split(","),
        })

    entrance = take("entrance ").strip()
    hole = take("hole ").strip()
    try:
        edge_count = int(take("edges "))
        _require(edge_count >= 0, "edges count must be >= 0")
    except ValueError as exc:
        raise CaveRoomsError(f"malformed edges count: {exc}") from exc

    edges = []
    for _ in range(edge_count):
        _require(index < len(lines), "truncated edges section")
        parts = lines[index].split()
        index += 1
        _require(len(parts) == 2, f"malformed edge line: {parts!r}")
        edges.append([parts[0], parts[1]])

    _require(index == len(lines), "trailing content after the edges section")
    ids = {unit["id"] for unit in units}
    _require(entrance in ids, "entrance is not a known unit")
    _require(hole in ids, "hole is not a known unit")

    return {
        "schema": ROOMS_SCHEMA,
        "source": source,
        "geometry": geometry,
        "cave": cave,
        "floor": floor,
        "seed": seed,
        "salt": salt,
        "cell": cell,
        "origin": origin,
        "entrance": entrance,
        "hole": hole,
        "units": units,
        "edges": edges,
    }


def write_rooms(rooms, path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rooms_text(rooms), encoding="utf-8", newline="\n")


def instantiation_report(rooms, layout) -> dict:
    unit_ids = {unit["id"] for unit in rooms["units"]}
    node_ids = {node["id"] for node in layout["nodes"]}
    rooms_edges = sorted(tuple(sorted(edge)) for edge in rooms["edges"])
    layout_edges = sorted(tuple(sorted(edge)) for edge in layout["edges"])
    return {
        "schema": REPORT_SCHEMA,
        "geometry": PROXY_GEOMETRY,
        "source": rooms["source"],
        "cave": rooms["cave"],
        "floor": rooms["floor"],
        "seed": rooms["seed"],
        "salt": rooms["salt"],
        "units": len(rooms["units"]),
        "edges": len(rooms["edges"]),
        "ids_preserved": unit_ids == node_ids,
        "edges_preserved": rooms_edges == layout_edges,
    }


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", required=True, help="p2-cave-observed-layout/1 JSON")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--salt", type=int, default=0)
    parser.add_argument("--cell", type=int, default=48)
    args = parser.parse_args(argv)

    layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    rooms = rooms_from_layout(layout, salt=args.salt, cell=args.cell)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    text_path = out_dir / "p2-cave-rooms.txt"
    json_path = out_dir / "p2-cave-rooms.json"
    report_path = out_dir / "p2-cave-rooms-report.json"
    write_rooms(rooms, text_path)
    _write_json(json_path, rooms)
    _write_json(report_path, instantiation_report(rooms, layout))

    print(json.dumps({
        "rooms": str(json_path),
        "units": len(rooms["units"]),
        "geometry": PROXY_GEOMETRY,
        "salt": args.salt,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
