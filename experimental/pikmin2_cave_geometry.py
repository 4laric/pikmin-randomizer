"""Lane 45: host-side real-geometry plan bridging lane-44 proxy cave rooms.

Lane 44 (:mod:`experimental.pikmin2_cave_rooms`) lays a deterministic *proxy*
square grid over an observed cave layout. This module is the host-side bridge
the native port consumes to replace the proxy squares for the hazard-bearing
units (``choke``/``leaf``/``gate``) with real converted unit models, and to
place a real electric-gate actor on the electric leaf door.

The plan keeps lane-44's ``cave``/``floor``/``seed``/``salt``/``entrance``/
``hole`` and the unit order. Every unit gains a ``class`` in ``{"real","proxy"}``
and a ``model`` path (``""`` for proxies). Electric gates carry a ``gate`` record
with ``kind="elec"``, ``actor``, ``model`` and ``placed``.

Two representations are produced and are strict inverses of each other: the
plan dict and the canonical ``P2_CAVE_GEOMETRY_1`` text the native side reads.
The text is whitespace-tokenised with fixed positions and ``-`` standing in for
empty values, so ids and model paths must be whitespace-free.

Determinism: nothing here reads the clock, draws a random number or depends on
filesystem order. ``model_root`` only affects ``validate_geometry``'s on-disk
existence check, never the plan shape or the text.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GEOMETRY_SCHEMA = "P2_CAVE_GEOMETRY_1"
TEXT_HEADER = GEOMETRY_SCHEMA
GEOMETRIES = ("real", "mixed", "proxy")
REQUIRED_KINDS = ("choke", "leaf", "gate")
DEFAULT_GATE_ACTOR = "p2_elec_gate"
ELECTRIC = "elec"


class GeometryError(ValueError):
    """Fail-closed error for geometry planning and text parsing."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GeometryError(message)


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


def _node_model(node_id, kind, models) -> str:
    """Resolve a unit's own model. Only hazard-bearing kinds may carry one."""
    if kind not in REQUIRED_KINDS:
        return ""
    if node_id not in models:
        return ""
    value = models[node_id]
    _require(isinstance(value, str) and value.strip() != "",
             f"model for {node_id} must be a non-empty string")
    _require(not any(ch.isspace() for ch in value),
             f"model for {node_id} must not contain whitespace")
    return value


def _classify(nodes) -> str:
    """Derive real/mixed/proxy from the nodes alone (never trusts a claim)."""
    required = [node for node in nodes if node.get("kind") in REQUIRED_KINDS]
    if not required:
        return "proxy"
    real_required = [node for node in required if node.get("class") == "real" and node.get("model")]
    placed = [node for node in nodes if node.get("gate") and node["gate"].get("placed")]
    gates_all_placed = all(node.get("gate") is None or node["gate"].get("placed") for node in nodes)
    if len(real_required) == len(required) and gates_all_placed:
        return "real"
    if real_required or placed:
        return "mixed"
    return "proxy"


def _host_gate_map(units, edges) -> dict:
    """Map a non-gate node id to the kind=="gate" node attached to it."""
    gate_ids = {unit["id"] for unit in units if unit.get("kind") == "gate"}
    host_to_gate = {}
    for edge in edges:
        _require(isinstance(edge, (list, tuple)) and len(edge) == 2,
                 f"edge must be a pair, got {edge!r}")
        left, right = edge
        left_gate = left in gate_ids
        right_gate = right in gate_ids
        if left_gate and not right_gate:
            host_to_gate.setdefault(right, left)
        elif right_gate and not left_gate:
            host_to_gate.setdefault(left, right)
    return host_to_gate


def _gate_record(kind: str, actor: str, model: str) -> dict:
    return {"kind": kind, "actor": actor, "model": model, "placed": bool(model)}


def build_geometry(rooms, *, models, gate_actor=DEFAULT_GATE_ACTOR, model_root=None) -> dict:
    """Build the real-geometry plan for a lane-44 rooms dict.

    ``models`` maps a ``choke``/``leaf``/``gate`` node id to its model path.
    A node whose model is absent stays a proxy square; a *present but malformed*
    mapping (non-string or empty) is a hard ``GeometryError`` for that kind.
    ``model_root`` is accepted for call-site symmetry and is not read here.
    """
    _require(isinstance(rooms, dict), "rooms must be a mapping")
    _require(isinstance(models, dict), "models must be a mapping")
    _token(gate_actor, "gate_actor")

    units = rooms.get("units")
    _require(isinstance(units, list), "rooms must contain a units list")
    edges = rooms.get("edges", [])
    _require(isinstance(edges, list), "rooms edges must be a list")

    for field in ("cave", "entrance", "hole"):
        _token(rooms.get(field), field)
    for field in ("floor", "seed", "salt"):
        _require(_is_int(rooms.get(field)), f"rooms {field} must be an integer")

    seen = set()
    for unit in units:
        _require(isinstance(unit, dict), "each room unit must be a mapping")
        _token(unit.get("id"), "unit id")
        _require(unit["id"] not in seen, f"duplicate unit id {unit['id']}")
        seen.add(unit["id"])
        _token(unit.get("kind"), f"kind for {unit['id']}")
        _require(_is_int(unit.get("gx")) and _is_int(unit.get("gz")),
                 f"unit {unit['id']} needs integer gx/gz")

    host_to_gate = _host_gate_map(units, edges)

    nodes = []
    for unit in units:
        unit_id = unit["id"]
        kind = unit["kind"]
        hazard = _hazard(unit.get("hazard"))
        model = _node_model(unit_id, kind, models)
        classify = "real" if kind in REQUIRED_KINDS and model else "proxy"

        gate = None
        if kind == "gate" and hazard == ELECTRIC:
            gate = _gate_record(ELECTRIC, gate_actor, model)
        elif kind == "leaf" and hazard == ELECTRIC:
            actor_id = host_to_gate.get(unit_id)
            actor_model = _node_model(actor_id, "gate", models) if actor_id else ""
            gate = _gate_record(ELECTRIC, gate_actor, actor_model)

        nodes.append({
            "id": unit_id,
            "kind": kind,
            "hazard": hazard,
            "class": classify,
            "model": model,
            "gate": gate,
            "gx": unit["gx"],
            "gz": unit["gz"],
        })

    return {
        "schema": GEOMETRY_SCHEMA,
        "cave": rooms["cave"],
        "floor": rooms["floor"],
        "seed": rooms["seed"],
        "salt": rooms["salt"],
        "geometry": _classify(nodes),
        "nodes": nodes,
        "entrance": rooms["entrance"],
        "hole": rooms["hole"],
    }


def _gate_rows(nodes) -> list:
    rows = []
    for node in nodes:
        gate = node.get("gate")
        if not gate:
            continue
        rows.append({
            "node_id": node["id"],
            "hazard": node.get("hazard"),
            "actor": gate["actor"],
            "model": gate.get("model", ""),
            "placed": bool(gate.get("placed")),
        })
    return rows


def _fmt_hazard(hazard) -> str:
    return hazard if hazard else "none"


def _fmt_opt(value) -> str:
    return value if value else "-"


def geometry_text(plan) -> str:
    """Render the canonical ``P2_CAVE_GEOMETRY_1`` text (newline terminated)."""
    _require(isinstance(plan, dict), "plan must be a mapping")
    nodes = plan.get("nodes")
    _require(isinstance(nodes, list), "plan must contain nodes")
    geometry = plan.get("geometry")
    _require(geometry in GEOMETRIES, f"unknown geometry {geometry!r}")

    lines = [
        TEXT_HEADER,
        f"cave {_token(plan.get('cave'), 'cave')}",
        f"floor {_int_text(plan.get('floor'), 'floor')}",
        f"seed {_int_text(plan.get('seed'), 'seed')}",
        f"salt {_int_text(plan.get('salt'), 'salt')}",
        f"geometry {geometry}",
        f"units {len(nodes)}",
    ]
    for node in nodes:
        unit_id = _token(node.get("id"), "node id")
        kind = _token(node.get("kind"), f"kind for {unit_id}")
        classify = node.get("class")
        _require(classify in ("real", "proxy"), f"bad class for {unit_id}: {classify!r}")
        model = node.get("model") or ""
        if model:
            _require(not any(ch.isspace() for ch in model),
                     f"model for {unit_id} must not contain whitespace")
        lines.append(
            f"{unit_id} {kind} {_fmt_hazard(node.get('hazard'))} {classify} "
            f"{_fmt_opt(model)} {_int_text(node.get('gx'), 'gx')} {_int_text(node.get('gz'), 'gz')}"
        )

    rows = _gate_rows(nodes)
    lines.append(f"gates {len(rows)}")
    for row in rows:
        lines.append(
            f"{_token(row['node_id'], 'gate node')} {_fmt_hazard(row['hazard'])} "
            f"{_token(row['actor'], 'gate actor')} {_fmt_opt(row['model'])} "
            f"{1 if row['placed'] else 0}"
        )

    lines.append(f"entrance {_token(plan.get('entrance'), 'entrance')}")
    lines.append(f"hole {_token(plan.get('hole'), 'hole')}")
    return "\n".join(lines) + "\n"


def parse_geometry_text(text) -> dict:
    """Parse the canonical text strictly; ``GeometryError`` on any mismatch."""
    _require(isinstance(text, str), "geometry text must be a string")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    _require(bool(lines) and lines[0] == TEXT_HEADER, "bad geometry text header")
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
        salt = int(take("salt ").strip())
    except ValueError as exc:
        raise GeometryError(f"malformed numeric section: {exc}") from exc

    geometry = take("geometry ").strip()
    _require(geometry in GEOMETRIES, f"unknown geometry {geometry!r}")

    try:
        unit_count = int(take("units ").strip())
    except ValueError as exc:
        raise GeometryError(f"malformed units count: {exc}") from exc
    _require(unit_count >= 0, "units count must be >= 0")

    nodes = []
    seen = set()
    for _ in range(unit_count):
        _require(index < len(lines), "truncated units section")
        parts = lines[index].split()
        index += 1
        _require(len(parts) == 7, f"malformed unit row: {parts!r}")
        unit_id, kind, hazard, classify, model, gx, gz = parts
        _require(classify in ("real", "proxy"), f"bad class token {classify!r}")
        _require(unit_id not in seen, f"duplicate unit id {unit_id}")
        seen.add(unit_id)
        try:
            gx_value = int(gx)
            gz_value = int(gz)
        except ValueError as exc:
            raise GeometryError(f"malformed unit numbers: {exc}") from exc
        nodes.append({
            "id": unit_id,
            "kind": kind,
            "hazard": None if hazard == "none" else hazard,
            "class": classify,
            "model": "" if model == "-" else model,
            "gate": None,
            "gx": gx_value,
            "gz": gz_value,
        })

    try:
        gate_count = int(take("gates ").strip())
    except ValueError as exc:
        raise GeometryError(f"malformed gates count: {exc}") from exc
    _require(gate_count >= 0, "gates count must be >= 0")

    by_id = {node["id"]: node for node in nodes}
    for _ in range(gate_count):
        _require(index < len(lines), "truncated gates section")
        parts = lines[index].split()
        index += 1
        _require(len(parts) == 5, f"malformed gate row: {parts!r}")
        node_id, hazard, actor, model, placed = parts
        _require(node_id in by_id, f"gate references unknown node {node_id}")
        _require(placed in ("0", "1"), f"bad placed token {placed!r}")
        _require(actor != "-", "gate actor must not be empty")
        node = by_id[node_id]
        _require(node["gate"] is None, f"duplicate gate for {node_id}")
        node["gate"] = {
            "kind": None if hazard == "none" else hazard,
            "actor": actor,
            "model": "" if model == "-" else model,
            "placed": placed == "1",
        }

    entrance = take("entrance ").strip()
    hole = take("hole ").strip()
    _require(entrance in by_id, "entrance is not a known unit")
    _require(hole in by_id, "hole is not a known unit")
    _require(index == len(lines), "trailing content after the hole line")

    return {
        "schema": GEOMETRY_SCHEMA,
        "cave": cave,
        "floor": floor,
        "seed": seed,
        "salt": salt,
        "geometry": geometry,
        "nodes": nodes,
        "entrance": entrance,
        "hole": hole,
    }


def validate_geometry(plan, *, model_root=None) -> dict:
    """Fail-closed validation of a plan; never claims real for proxy nodes."""
    _require(isinstance(plan, dict), "plan must be a mapping")
    nodes = plan.get("nodes")
    _require(isinstance(nodes, list), "plan must contain nodes")

    errors = []
    if plan.get("geometry") not in GEOMETRIES:
        errors.append(f"unknown geometry {plan.get('geometry')!r}")

    true_geometry = _classify(nodes)
    if plan.get("geometry") != true_geometry:
        errors.append(
            f"declared geometry {plan.get('geometry')!r} does not match nodes ({true_geometry})"
        )

    for node in nodes:
        if node.get("kind") not in REQUIRED_KINDS:
            continue
        if node.get("class") != "real":
            errors.append(f"{node.get('kind')} node {node.get('id')} is not real")
        if not node.get("model"):
            errors.append(f"{node.get('kind')} node {node.get('id')} has no model")

    for node in nodes:
        if node.get("hazard") != ELECTRIC or node.get("kind") not in ("leaf", "gate"):
            continue
        gate = node.get("gate")
        if not isinstance(gate, dict):
            errors.append(f"elec {node.get('kind')} node {node.get('id')} has no gate actor")
            continue
        if not gate.get("actor"):
            errors.append(f"elec {node.get('kind')} node {node.get('id')} gate actor is unnamed")
        if not gate.get("placed"):
            errors.append(f"elec {node.get('kind')} node {node.get('id')} gate actor is not placed")

    if model_root is not None:
        root = Path(model_root)
        for node in nodes:
            for label, model in (("model", node.get("model")),
                                 ("gate model", node["gate"].get("model")
                                  if isinstance(node.get("gate"), dict) else None)):
                if not model:
                    continue
                target = root / model
                if not target.is_file():
                    errors.append(f"{label} missing on disk: {model}")
                elif target.stat().st_size <= 0:
                    errors.append(f"{label} is empty: {model}")

    real_nodes = sum(1 for node in nodes if node.get("class") == "real")
    proxy_nodes = sum(1 for node in nodes if node.get("class") == "proxy")
    gate_actors = sum(1 for node in nodes if node.get("gate") and node["gate"].get("placed"))

    return {
        "valid": true_geometry == "real" and not errors,
        "geometry": true_geometry,
        "errors": errors,
        "real_nodes": real_nodes,
        "proxy_nodes": proxy_nodes,
        "gate_actors": gate_actors,
    }


def geometry_marker(plan) -> str:
    """One-line stdout marker describing a plan."""
    _require(isinstance(plan, dict), "plan must be a mapping")
    nodes = plan.get("nodes")
    _require(isinstance(nodes, list), "plan must contain nodes")
    real = sum(1 for node in nodes if node.get("class") == "real")
    proxy = sum(1 for node in nodes if node.get("class") == "proxy")
    gate_actors = sum(1 for node in nodes if node.get("gate") and node["gate"].get("placed"))
    return (
        "P2_CAVE_GEOMETRY_READY nodes=%d real=%d proxy=%d gate_actors=%d geometry=%s "
        "cave=%s floor=%s seed=%s salt=%s"
        % (len(nodes), real, proxy, gate_actors, plan.get("geometry"),
           plan.get("cave"), plan.get("floor"), plan.get("seed"), plan.get("salt"))
    )


def _parse_model_arg(value: str):
    _require("=" in value, f"--model must be node=path, got {value!r}")
    node_id, path = value.split("=", 1)
    node_id = node_id.strip()
    path = path.strip()
    _require(node_id != "" and path != "", f"--model must be node=path, got {value!r}")
    return node_id, path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rooms", required=True, help="lane-44 p2-cave-rooms.json")
    parser.add_argument("--model-root", default=None, help="root the model paths are relative to")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--model", action="append", default=[], metavar="NODE=PATH",
                        help="model path for a choke/leaf/gate node (repeatable)")
    parser.add_argument("--gate-actor", default=DEFAULT_GATE_ACTOR)
    args = parser.parse_args(argv)

    rooms = json.loads(Path(args.rooms).read_text(encoding="utf-8"))
    models = {}
    for entry in args.model:
        node_id, path = _parse_model_arg(entry)
        models[node_id] = path

    plan = build_geometry(rooms, models=models, gate_actor=args.gate_actor,
                          model_root=args.model_root)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "p2-cave-geometry.json"
    text_path = out_dir / "p2-cave-geometry.txt"
    json_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    text_path.write_text(geometry_text(plan), encoding="utf-8", newline="\n")
    print(geometry_marker(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
