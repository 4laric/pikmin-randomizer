"""Lane 46: physical item placement bridge for an observed Pikmin 2 cave floor.

This is host-side instantiation glue only. It consumes a lane-40/41/44
``p2-cave-observed-layout/1`` graph and maps every item name carried by a node
to the node that must host the spawned treasure actor. The lane-44 rooms config
already carries the item names per unit, so this module only needs the mapping
``item -> host unit -> hazard/tagged``; the native side resolves the world
coordinates from the live rooms layout, and *no coordinates appear in this
grammar*.

The emitted native text grammar (``P2_CAVE_ITEMS_1``) is strict: a fixed header,
six scalar sections and one whitespace-delimited line per item with exactly
seven tokens. ``parse_items_text`` is a lossless inverse of the encoded fields.

Placement is fail-closed. A tagged treasure token (any name in
``KNOWN_TAGGED_HAZARDS``) must sit in a ``leaf`` whose hazard matches its tag; an
untagged item must sit on a ``segment`` in the entrance segment; an unknown
``treasure_*`` token, or any item on a ``choke``/``gate``/``bud`` host, is
rejected.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from experimental.pikmin2_cave_spike import CaveSpikeError, validate_layout

ITEMS_SCHEMA = "p2-cave-items/1"
ITEMS_TEXT_HEADER = "P2_CAVE_ITEMS_1"
REPORT_SCHEMA = "p2-cave-items-report/1"
PROXY_GEOMETRY = "proxy"

TAGGED_PREFIX = "treasure_"
KNOWN_TAGGED_HAZARDS = {
    "treasure_elec": "elec",
    "treasure_water": "water",
    "treasure_fire": "fire",
    "treasure_poison": "poison",
}
GATED_HOST_KINDS = frozenset({"choke", "gate", "bud"})


class CaveItemsError(ValueError):
    """Fail-closed error for item placement and native text parsing."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CaveItemsError(message)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def items_from_layout(layout) -> dict:
    try:
        validate_layout(layout)
    except CaveSpikeError as exc:
        raise CaveItemsError(str(exc)) from exc

    nodes = {node["id"]: node for node in layout["nodes"]}
    entrance_node = nodes[layout["entrance"]]
    entrance_segment = entrance_node.get("segment_index")

    entries = []
    for node in layout["nodes"]:
        node_id = node["id"]
        kind = node["kind"]
        hazard = node.get("hazard")
        segment_index = node.get("segment_index")
        for index, item in enumerate(node.get("items", [])):
            _require(isinstance(item, str) and item, f"node {node_id} has an empty item name")
            if item.startswith(TAGGED_PREFIX) or item in KNOWN_TAGGED_HAZARDS:
                _require(item in KNOWN_TAGGED_HAZARDS,
                         f"node {node_id} carries unknown tagged treasure token {item!r}")
                _require(kind == "leaf",
                         f"tagged item {item} must sit on a leaf, not {kind} host {node_id}")
                _require(hazard == KNOWN_TAGGED_HAZARDS[item],
                         f"tagged item {item} needs a {KNOWN_TAGGED_HAZARDS[item]} leaf, "
                         f"but host {node_id} is {hazard}")
                tagged = True
            else:
                _require(kind not in GATED_HOST_KINDS,
                         f"item {item} may not sit on {kind} host {node_id}")
                _require(kind == "segment",
                         f"untagged item {item} must sit on a segment, not {kind} host {node_id}")
                _require(segment_index == entrance_segment,
                         f"untagged item {item} must sit in the entrance segment "
                         f"({entrance_segment}), not segment {segment_index}")
                tagged = False
            entries.append({
                "slot_id": f"item:{node_id}:{index}",
                "item": item,
                "host": node_id,
                "kind": kind,
                "hazard": hazard,
                "tagged": tagged,
                "segment_index": segment_index,
            })

    counts = {
        "total": len(entries),
        "tagged": sum(1 for entry in entries if entry["tagged"]),
        "untagged": sum(1 for entry in entries if not entry["tagged"]),
    }
    return {
        "schema": ITEMS_SCHEMA,
        "source": layout["source"],
        "geometry": PROXY_GEOMETRY,
        "cave": layout["cave"],
        "floor": layout["floor"],
        "seed": layout["seed"],
        "entrance": layout["entrance"],
        "hole": layout["hole"],
        "entrance_segment": entrance_segment,
        "items": entries,
        "counts": counts,
    }


def logical_projection(items) -> dict:
    return {
        "cave": items["cave"],
        "floor": items["floor"],
        "seed": items["seed"],
        "entrance": items["entrance"],
        "hole": items["hole"],
        "slots": sorted((entry["slot_id"], entry["item"], entry["host"])
                        for entry in items["items"]),
        "hazards": {entry["slot_id"]: entry["hazard"] for entry in items["items"]},
        "segment_index": {entry["slot_id"]: entry["segment_index"] for entry in items["items"]},
        "tagged": {entry["slot_id"]: entry["tagged"] for entry in items["items"]},
    }


def items_text(payload) -> str:
    lines = [ITEMS_TEXT_HEADER]
    lines.append(f"cave {payload['cave']}")
    lines.append(f"floor {payload['floor']}")
    lines.append(f"seed {payload['seed']}")
    lines.append(f"source {payload['source']}")
    lines.append(f"geometry {payload['geometry']}")
    lines.append(f"items {len(payload['items'])}")
    for entry in payload["items"]:
        hazard = entry["hazard"] if entry["hazard"] is not None else "none"
        tagged = 1 if entry["tagged"] else 0
        lines.append(
            f"{entry['slot_id']} {entry['item']} {entry['host']} {entry['kind']} "
            f"{hazard} {tagged} {entry['segment_index']}"
        )
    return "\n".join(lines) + "\n"


def parse_items_text(text) -> dict:
    _require(isinstance(text, str), "items text must be a string")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    _require(bool(lines) and lines[0] == ITEMS_TEXT_HEADER, "bad items text header")
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
    except ValueError as exc:
        raise CaveItemsError(f"malformed numeric section: {exc}") from exc

    source = take("source ").strip()
    geometry = take("geometry ").strip()
    _require(geometry == PROXY_GEOMETRY, f"geometry must be {PROXY_GEOMETRY}")

    try:
        item_count = int(take("items "))
        _require(item_count >= 0, "items count must be >= 0")
    except ValueError as exc:
        raise CaveItemsError(f"malformed items count: {exc}") from exc

    entries = []
    for _ in range(item_count):
        _require(index < len(lines), "truncated items section")
        parts = lines[index].split()
        index += 1
        _require(len(parts) == 7, f"malformed item line: {parts!r}")
        slot_id, item, host, kind, hazard, tagged, segment = parts
        try:
            tagged_value = int(tagged)
            segment_index = int(segment)
        except ValueError as exc:
            raise CaveItemsError(f"malformed item numbers: {exc}") from exc
        _require(tagged_value in (0, 1), f"tagged flag must be 0 or 1, got {tagged!r}")
        entries.append({
            "slot_id": slot_id,
            "item": item,
            "host": host,
            "kind": kind,
            "hazard": None if hazard == "none" else hazard,
            "tagged": bool(tagged_value),
            "segment_index": segment_index,
        })

    _require(index == len(lines), "trailing content after the items section")
    counts = {
        "total": len(entries),
        "tagged": sum(1 for entry in entries if entry["tagged"]),
        "untagged": sum(1 for entry in entries if not entry["tagged"]),
    }
    return {
        "schema": ITEMS_SCHEMA,
        "source": source,
        "geometry": geometry,
        "cave": cave,
        "floor": floor,
        "seed": seed,
        "items": entries,
        "counts": counts,
    }


def placement_report(payload) -> dict:
    entries = payload["items"]
    tagged = [entry for entry in entries if entry["tagged"]]
    untagged = [entry for entry in entries if not entry["tagged"]]
    entrance_segment = payload.get("entrance_segment")
    return {
        "schema": REPORT_SCHEMA,
        "geometry": payload["geometry"],
        "source": payload["source"],
        "cave": payload["cave"],
        "floor": payload["floor"],
        "seed": payload["seed"],
        "counts": dict(payload["counts"]),
        "tagged_in_matching_leaf": all(
            entry["kind"] == "leaf"
            and KNOWN_TAGGED_HAZARDS.get(entry["item"]) == entry["hazard"]
            for entry in tagged
        ),
        "untagged_in_entrance": all(
            entry["kind"] == "segment" and entry["segment_index"] == entrance_segment
            for entry in untagged
        ),
        "hosts": sorted({entry["host"] for entry in entries}),
        "tagged_hosts": sorted({entry["host"] for entry in tagged}),
        "untagged_hosts": sorted({entry["host"] for entry in untagged}),
    }


def write_items(payload, path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(items_text(payload), encoding="utf-8", newline="\n")


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", required=True, help="p2-cave-observed-layout/1 JSON")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    payload = items_from_layout(layout)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    text_path = out_dir / "p2-cave-items.txt"
    json_path = out_dir / "p2-cave-items.json"
    report_path = out_dir / "p2-cave-items-report.json"
    write_items(payload, text_path)
    _write_json(json_path, payload)
    _write_json(report_path, placement_report(payload))

    print(json.dumps({
        "items": str(json_path),
        "count": payload["counts"]["total"],
        "tagged": payload["counts"]["tagged"],
        "geometry": PROXY_GEOMETRY,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
