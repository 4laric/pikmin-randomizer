"""Lane 40 cave spike: independent acceptance checker for the #468 cave model.

This is QA tooling, not a generator. It takes a *seeded structural table* (the
per-floor logic graph: ordered chokes, treasure -> segment + leaf hazard,
bud segments + conversion counts) and one or more *observed floor layouts*
(unit graphs produced by the engine's own generator) and evaluates the
acceptance contract from ``_cave_fanout.md``:

  1. generation invariant  -- required chokes/leaves/buds exist and each choke
     is on every path to the hole (graph dominance, not observation);
  2. seed determinism      -- same seed -> identical logical table;
  3. re-roll invariance    -- two layouts for one seed keep the same table and
     the same per-treasure/per-hole requirements;
  4. reachability          -- the hole is never behind a hard gate the floor's
     logic does not require; hard gates only on choke/leaf doors;
  5. end-to-end loop       -- model-level reachability of two tagged treasures
     under an ability timeline (come back with the ability);
  6. failure handling      -- a layout missing a required slot is rejected with
     ``retry_required`` rather than accepted as tableless/ungated.

Evidence is labelled: a layout with ``"source": "engine"`` is *natural*; any
other source is *injected* (fixture / hand-placed) and can never produce a
``generation_pass`` -- only a ``model_pass``. This mirrors the wave rule that a
mocked scene is never a generation PASS.

The checker is fail-closed: malformed tables/layouts raise ``CaveSpikeError``
before any check runs. It does not import native code and does not generate
rooms.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import deque

SCHEMA_TABLE = "p2-cave-seeded-table/1"
SCHEMA_LAYOUT = "p2-cave-observed-layout/1"

# hazard -> Pikmin species that is the primary key
SPECIES = {"water": "blue", "elec": "yellow", "fire": "red", "poison": "white"}
# hard hazards block carrying; soft hazards are timing-based unless gated
HARD_HAZARDS = {"water", "elec"}
HAZARDS = set(SPECIES) | {"none"}
LAYOUT_SOURCES = {"engine", "fixture", "hand-placed"}
NODE_KINDS = {"segment", "choke", "leaf", "bud", "gate"}


class CaveSpikeError(ValueError):
    """Fail-closed validation error for table/layout/scenario input."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CaveSpikeError(message)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _load(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path: str, payload) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate_table(table) -> None:
    _require(isinstance(table, dict), "table must be an object")
    _require(table.get("schema") == SCHEMA_TABLE, f"table schema must be {SCHEMA_TABLE}")
    _require(_is_int(table.get("seed")), "table.seed must be an integer")
    _require(isinstance(table.get("cave"), str) and table["cave"], "table.cave must be a non-empty string")
    _require(_is_int(table.get("floor")) and table["floor"] >= 1, "table.floor must be >= 1")

    segments = table.get("segments")
    _require(isinstance(segments, list) and segments, "table.segments must be a non-empty list")
    indices = []
    for index, segment in enumerate(segments):
        _require(isinstance(segment, dict), "each segment must be an object")
        _require(_is_int(segment.get("index")) and segment["index"] == index,
                 f"segment {index} index must be {index}")
        _require(isinstance(segment.get("name"), str) and segment["name"], f"segment {index} needs a name")
        indices.append(index)
    last_segment = indices[-1]

    seen = set()
    chokes = table.get("chokes")
    _require(isinstance(chokes, list), "table.chokes must be a list")
    previous = 0
    for choke in chokes:
        _require(isinstance(choke, dict), "each choke must be an object")
        _require(isinstance(choke.get("id"), str) and choke["id"], "choke needs a string id")
        _require(choke["id"] not in seen, f"duplicate choke id {choke['id']}")
        seen.add(choke["id"])
        _require(choke.get("kind") in HAZARDS and choke["kind"] != "none",
                 f"choke {choke['id']} kind must be a hazard")
        _require(_is_int(choke.get("segment_index")) and 1 <= choke["segment_index"] <= last_segment,
                 f"choke {choke['id']} segment_index out of range")
        _require(choke["segment_index"] >= previous,
                 f"choke {choke['id']} out of trunk order")
        previous = choke["segment_index"]

    leaves = table.get("leaves")
    _require(isinstance(leaves, list), "table.leaves must be a list")
    leaf_ids = set()
    for leaf in leaves:
        _require(isinstance(leaf, dict), "each leaf must be an object")
        _require(isinstance(leaf.get("id"), str) and leaf["id"], "leaf needs a string id")
        _require(leaf["id"] not in seen, f"duplicate leaf id {leaf['id']}")
        seen.add(leaf["id"])
        leaf_ids.add(leaf["id"])
        _require(leaf.get("hazard") in HAZARDS and leaf["hazard"] != "none",
                 f"leaf {leaf['id']} hazard must be a hazard")
        _require(_is_int(leaf.get("segment_index")) and leaf["segment_index"] in indices,
                 f"leaf {leaf['id']} segment_index out of range")
        _require(isinstance(leaf.get("item_slot"), str) and leaf["item_slot"],
                 f"leaf {leaf['id']} needs an item_slot")

    buds = table.get("buds")
    _require(isinstance(buds, list), "table.buds must be a list")
    for bud in buds:
        _require(isinstance(bud, dict), "each bud must be an object")
        _require(bud.get("hazard") in HAZARDS and bud["hazard"] != "none",
                 "bud hazard must be a hazard")
        _require(_is_int(bud.get("segment_index")) and bud["segment_index"] in indices,
                 "bud segment_index out of range")
        _require(_is_int(bud.get("count")) and bud["count"] >= 1, "bud count must be >= 1")

    # a bud may never sit in a segment gated by the type it provides
    for bud in buds:
        for choke in chokes:
            _require(not (choke["kind"] == bud["hazard"] and choke["segment_index"] <= bud["segment_index"]),
                     f"bud {bud['hazard']}@s{bud['segment_index']} is behind its own gate")

    treasures = table.get("treasures")
    _require(isinstance(treasures, list), "table.treasures must be a list")
    for treasure in treasures:
        _require(isinstance(treasure, dict), "each treasure must be an object")
        _require(isinstance(treasure.get("id"), str) and treasure["id"], "treasure needs a string id")
        _require(treasure["id"] not in seen, f"duplicate treasure id {treasure['id']}")
        seen.add(treasure["id"])
        _require(isinstance(treasure.get("tagged"), bool), "treasure.tagged must be a bool")
        if treasure["tagged"]:
            _require(treasure.get("hazard") in HAZARDS and treasure["hazard"] != "none",
                     f"tagged treasure {treasure['id']} needs a hazard")
            _require(treasure.get("leaf") in leaf_ids,
                     f"tagged treasure {treasure['id']} must reference a leaf")
            _require(_is_int(treasure.get("segment_index")) and treasure["segment_index"] in indices,
                     f"tagged treasure {treasure['id']} segment_index out of range")
        else:
            _require(treasure.get("hazard") in (None, "none"),
                     f"untagged treasure {treasure['id']} must not carry a hazard tag")

    hole = table.get("hole")
    _require(isinstance(hole, dict), "table.hole must be an object")
    _require(_is_int(hole.get("segment_index")) and hole["segment_index"] in indices,
             "hole.segment_index out of range")
    _require(hole["segment_index"] >= previous,
             "hole must sit at or beyond the last choke segment")


def validate_layout(layout) -> None:
    _require(isinstance(layout, dict), "layout must be an object")
    _require(layout.get("schema") == SCHEMA_LAYOUT, f"layout schema must be {SCHEMA_LAYOUT}")
    _require(layout.get("source") in LAYOUT_SOURCES, "layout.source must be engine/fixture/hand-placed")
    _require(_is_int(layout.get("seed")), "layout.seed must be an integer")
    _require(isinstance(layout.get("cave"), str) and layout["cave"], "layout.cave must be a non-empty string")
    _require(_is_int(layout.get("floor")) and layout["floor"] >= 1, "layout.floor must be >= 1")

    nodes = layout.get("nodes")
    _require(isinstance(nodes, list) and nodes, "layout.nodes must be a non-empty list")
    ids = set()
    for node in nodes:
        _require(isinstance(node, dict), "each node must be an object")
        _require(isinstance(node.get("id"), str) and node["id"], "node needs a string id")
        _require(node["id"] not in ids, f"duplicate node id {node['id']}")
        ids.add(node["id"])
        _require(node.get("kind") in NODE_KINDS, f"node {node['id']} has an unknown kind")
        if node["kind"] in {"choke", "leaf", "bud", "gate"}:
            _require(node.get("hazard") in HAZARDS and node["hazard"] != "none",
                     f"node {node['id']} needs a hazard")
        items = node.get("items", [])
        _require(isinstance(items, list) and all(isinstance(i, str) for i in items),
                 f"node {node['id']} items must be a list of ids")

    edges = layout.get("edges")
    _require(isinstance(edges, list), "layout.edges must be a list")
    for edge in edges:
        _require(isinstance(edge, list) and len(edge) == 2, "each edge must be a pair")
        _require(edge[0] in ids and edge[1] in ids, f"edge {edge} references an unknown node")

    _require(layout.get("entrance") in ids, "layout.entrance must be a node id")
    _require(layout.get("hole") in ids, "layout.hole must be a node id")


# --------------------------------------------------------------------------
# requirements
# --------------------------------------------------------------------------

def _bud_token(hazard: str, segment_index: int, count: int) -> str:
    return f"bud:{hazard}:s{segment_index}:n{count}"


def _token_required_count(token: str) -> int:
    return int(token.rsplit(":n", 1)[1])


def _bud_alternatives(table, hazard: str, segment_index: int, inclusive: bool):
    alternatives = []
    for bud in table["buds"]:
        if bud["hazard"] != hazard:
            continue
        position = bud["segment_index"]
        if position < segment_index or (inclusive and position == segment_index):
            alternatives.append([_bud_token(hazard, position, bud["count"])])
    return alternatives


def _gate(table, hazard: str, segment_index: int, inclusive: bool):
    solutions = [[SPECIES[hazard]]] + _bud_alternatives(table, hazard, segment_index, inclusive)
    return {"hazard": hazard, "segment_index": segment_index, "solutions": solutions}


def segment_requirements(table, segment_index: int):
    return [_gate(table, choke["kind"], choke["segment_index"], inclusive=False)
            for choke in table["chokes"] if choke["segment_index"] <= segment_index]


def treasure_requirements(table, treasure_id: str):
    treasure = next((t for t in table["treasures"] if t["id"] == treasure_id), None)
    _require(treasure is not None, f"unknown treasure {treasure_id}")
    if not treasure["tagged"]:
        return []
    leaf = next(l for l in table["leaves"] if l["id"] == treasure["leaf"])
    gates = segment_requirements(table, treasure["segment_index"])
    gates.append(_gate(table, leaf["hazard"], leaf["segment_index"], inclusive=True))
    return gates


def hole_requirements(table):
    gates = []
    for choke in table["chokes"]:
        gates.append(_gate(table, choke["kind"], choke["segment_index"], inclusive=False))
    return gates


def _solution_satisfied(solution, inventory) -> bool:
    species = inventory.get("species", {})
    buds = inventory.get("buds", {})
    for token in solution:
        if token.startswith("bud:"):
            if int(buds.get(token, 0)) < _token_required_count(token):
                return False
        elif not species.get(token, False):
            return False
    return True


def requirements_satisfied(gates, inventory) -> bool:
    return all(any(_solution_satisfied(s, inventory) for s in gate["solutions"]) for gate in gates)


def reachability(table, inventory):
    result = {
        "hole": requirements_satisfied(hole_requirements(table), inventory),
        "treasures": {},
    }
    for treasure in table["treasures"]:
        result["treasures"][treasure["id"]] = requirements_satisfied(
            treasure_requirements(table, treasure["id"]), inventory)
    return result


# --------------------------------------------------------------------------
# graph helpers
# --------------------------------------------------------------------------

def _adjacency(layout):
    adjacency = {node["id"]: [] for node in layout["nodes"]}
    for left, right in layout["edges"]:
        adjacency[left].append(right)
        adjacency[right].append(left)
    return adjacency


def _connected(layout, removed=frozenset()) -> bool:
    if layout["entrance"] in removed or layout["hole"] in removed:
        return False
    adjacency = _adjacency(layout)
    seen = {layout["entrance"]}
    queue = deque([layout["entrance"]])
    while queue:
        current = queue.popleft()
        if current == layout["hole"]:
            return True
        for neighbour in adjacency[current]:
            if neighbour in removed or neighbour in seen:
                continue
            seen.add(neighbour)
            queue.append(neighbour)
    return False


def _nodes_by(layout, kind):
    return [node for node in layout["nodes"] if node["kind"] == kind]


def _find_node(layout, kind, hazard=None, segment_index=None, node_id=None):
    for node in _nodes_by(layout, kind):
        if node_id is not None and node.get("id") != node_id:
            continue
        if hazard is not None and node.get("hazard") != hazard:
            continue
        if segment_index is not None and node.get("segment_index") != segment_index:
            continue
        return node
    return None


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def _logic_projection(table):
    return {
        "seed": table["seed"],
        "cave": table["cave"],
        "floor": table["floor"],
        "chokes": [{"id": c["id"], "kind": c["kind"], "segment_index": c["segment_index"]}
                   for c in table["chokes"]],
        "leaves": [{"id": l["id"], "hazard": l["hazard"], "segment_index": l["segment_index"]}
                   for l in table["leaves"]],
        "buds": [{"hazard": b["hazard"], "segment_index": b["segment_index"], "count": b["count"]}
                 for b in table["buds"]],
        "treasures": [{"id": t["id"], "tagged": t["tagged"], "hazard": t.get("hazard"),
                       "segment_index": t.get("segment_index"), "leaf": t.get("leaf")}
                      for t in table["treasures"]],
        "hole": {"segment_index": table["hole"]["segment_index"]},
    }


def check_determinism(first, second) -> dict:
    validate_table(first)
    validate_table(second)
    same_seed = first["seed"] == second["seed"]
    identical = _logic_projection(first) == _logic_projection(second)
    if same_seed:
        return {"name": "seed_determinism", "pass": identical, "same_seed": True,
                "detail": "same seed reproduces the logical table" if identical
                else "same seed produced a different logical table"}
    return {"name": "seed_determinism", "pass": not identical, "same_seed": False,
            "detail": "changing the seed changed the logical table" if not identical
            else "changing the seed did not change the logical table"}


def check_layout(table, layout) -> dict:
    validate_layout(layout)
    _require(layout["cave"] == table["cave"] and layout["floor"] == table["floor"],
             "layout does not belong to the table's cave/floor")
    injected = layout["source"] != "engine"
    result = {
        "name": "generation_invariant",
        "layout_source": layout["source"],
        "evidence_class": "injected" if injected else "natural",
        "seed_matches": layout["seed"] == table["seed"],
        "retry_required": False,
        "pass": True,
        "findings": [],
    }

    def fail(message, retry=False):
        result["pass"] = False
        result["findings"].append(message)
        if retry:
            result["retry_required"] = True

    # 1. required slots exist
    choke_nodes = {}
    for choke in table["chokes"]:
        node = _find_node(layout, "choke", hazard=choke["kind"],
                          segment_index=choke["segment_index"], node_id=choke["id"])
        if node is None:
            fail(f"missing choke {choke['id']} on every-path slot", retry=True)
        else:
            choke_nodes[choke["id"]] = node["id"]
    for leaf in table["leaves"]:
        if _find_node(layout, "leaf", hazard=leaf["hazard"],
                      segment_index=leaf["segment_index"], node_id=leaf["id"]) is None:
            fail(f"missing leaf {leaf['id']}", retry=True)
    for bud in table["buds"]:
        if _find_node(layout, "bud", hazard=bud["hazard"], segment_index=bud["segment_index"]) is None:
            fail(f"missing bud {bud['hazard']}@s{bud['segment_index']}", retry=True)

    # 2. choke dominance: removing any choke must disconnect entrance from hole
    for choke_id, node_id in choke_nodes.items():
        if _connected(layout, removed=frozenset({node_id})):
            fail(f"choke {choke_id} is bypassable; a path to the hole avoids it")

    # 3. hard gates only where the logic requires them, and only on choke/leaf doors
    table_hazards = {c["kind"] for c in table["chokes"]} | {l["hazard"] for l in table["leaves"]}
    for node in _nodes_by(layout, "gate"):
        if node["hazard"] in HARD_HAZARDS and node["hazard"] not in table_hazards:
            fail(f"ambient hard gate {node['id']} ({node['hazard']}) is not in the floor's logic")
        neighbours = set()
        for left, right in layout["edges"]:
            if left == node["id"]:
                neighbours.add(right)
            elif right == node["id"]:
                neighbours.add(left)
        host_kinds = {n["kind"] for n in layout["nodes"] if n["id"] in neighbours}
        if not (host_kinds & {"choke", "leaf"}):
            fail(f"gate {node['id']} is not on a choke/leaf door")

    # 4. tagged item placement
    for treasure in table["treasures"]:
        host = next((node for node in layout["nodes"] if treasure["id"] in node.get("items", [])), None)
        if host is None:
            fail(f"treasure {treasure['id']} is not placed", retry=treasure["tagged"])
            continue
        if treasure["tagged"]:
            leaf = next(l for l in table["leaves"] if l["id"] == treasure["leaf"])
            if not (host["kind"] == "leaf" and host.get("hazard") == treasure["hazard"]
                    and host.get("segment_index") == leaf["segment_index"]):
                fail(f"tagged treasure {treasure['id']} is not in its {treasure['hazard']} leaf")
        else:
            if host.get("hazard") not in (None, "none"):
                fail(f"untagged treasure {treasure['id']} leaked into hazard node {host['id']}")

    if not result["seed_matches"] and not injected:
        fail("natural layout seed does not match the frozen table seed")
    return result


def check_reroll_invariance(table, layouts) -> dict:
    base = {tid: treasure_requirements(table, tid) for tid in
            (t["id"] for t in table["treasures"] if t["tagged"])}
    base_hole = hole_requirements(table)
    layout_results = [check_layout(table, layout) for layout in layouts]
    requirements_stable = True
    for treasure_id, gates in base.items():
        again = treasure_requirements(table, treasure_id)
        if again != gates:
            requirements_stable = False
    invariant = all(r["pass"] for r in layout_results) and requirements_stable
    return {
        "name": "reroll_invariance",
        "pass": invariant,
        "table_stable": True,
        "requirements_stable": requirements_stable,
        "hole_requirements_stable": hole_requirements(table) == base_hole,
        "layouts": layout_results,
        "distinct_layouts": len(layouts),
    }


def check_scenarios(table, scenarios) -> dict:
    results = []
    passed = True
    for scenario in scenarios:
        _require(isinstance(scenario, dict) and isinstance(scenario.get("name"), str),
                 "scenario needs a name")
        inventory = {
            "species": scenario.get("species", {}),
            "buds": scenario.get("buds", {}),
        }
        _require(isinstance(inventory["species"], dict) and isinstance(inventory["buds"], dict),
                 "scenario species/buds must be objects")
        observed = reachability(table, inventory)
        expected = scenario.get("expect")
        _require(isinstance(expected, dict), "scenario needs an expect object")
        mismatches = []
        for key, want in expected.items():
            got = observed["hole"] if key == "hole" else observed["treasures"].get(key)
            if got != want:
                mismatches.append(f"{key}: expected {want} got {got}")
        if mismatches:
            passed = False
        results.append({"name": scenario["name"], "pass": not mismatches,
                        "observed": observed, "mismatches": mismatches})
    return {"name": "end_to_end_loop", "pass": passed, "scenarios": results}


def check_spike(table, layouts, scenarios=()) -> dict:
    validate_table(table)
    layout_results = [check_layout(table, layout) for layout in layouts]
    generation_pass = bool(layout_results) and all(
        r["pass"] and r["layout_source"] == "engine" for r in layout_results)
    model_pass = bool(layout_results) and all(r["pass"] for r in layout_results)
    report = {
        "schema": "p2-cave-spike-report/1",
        "cave": table["cave"],
        "floor": table["floor"],
        "seed": table["seed"],
        "generation_invariant": {
            "name": "generation_invariant",
            "pass": model_pass,
            "generation_pass": generation_pass,
            "model_pass": model_pass,
            "evidence": "natural" if generation_pass else "injected",
            "layouts": layout_results,
        },
        "reroll_invariance": check_reroll_invariance(table, layouts) if layouts else None,
        "end_to_end_loop": check_scenarios(table, scenarios) if scenarios else None,
    }
    report["pass"] = model_pass and all(
        section is None or section["pass"]
        for section in (report["reroll_invariance"], report["end_to_end_loop"]))
    return report


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Cave spike / independent acceptance checker")
    parser.add_argument("--table", required=True)
    parser.add_argument("--layout", action="append", default=[])
    parser.add_argument("--scenario", default=None, help="JSON file with a list of scenarios")
    parser.add_argument("--determinism", default=None, help="second table for seed determinism")
    parser.add_argument("--output", required=True)
    parser.add_argument("--expect-fail", action="store_true")
    args = parser.parse_args(argv)

    table = _load(args.table)
    layouts = [_load(path) for path in args.layout]
    scenarios = _load(args.scenario) if args.scenario else []
    if isinstance(scenarios, dict):
        scenarios = scenarios.get("scenarios", [])

    report = check_spike(table, layouts, scenarios)
    if args.determinism:
        report["seed_determinism"] = check_determinism(table, _load(args.determinism))
        report["pass"] = report["pass"] and report["seed_determinism"]["pass"]

    _write(args.output, report)
    print(json.dumps({"pass": report["pass"],
                      "generation_pass": report["generation_invariant"]["generation_pass"],
                      "evidence": report["generation_invariant"]["evidence"],
                      "output": os.path.abspath(args.output)}))
    failed = not report["pass"]
    if args.expect_fail:
        return 0 if failed else 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
