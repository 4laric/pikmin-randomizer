"""Focused tests for experimental.pikmin2_cave_gates (lane 50).

Covers the carry-blocking plan over a synthetic forest_1-like lane-44 rooms
dict, its strict ``P2_CAVE_GATES_1`` text round-trip, the elec/water/no-block
mapping, geometry-class inheritance, determinism, the report counts, fail-closed
validation of malformed rooms/geometry/text, the CLI artifacts and (when
present) a bridge from the lane-41 observed layout through lane-44. No disc, ISO
or network access.
"""

import copy
import json
from pathlib import Path

import pytest

from experimental import pikmin2_cave_gates as gates

OBSERVED_LAYOUT = Path(
    "C:/Users/alari/pikmin-randomizer/output/dsw/l41-out/p2-cave-observed-layout.json"
)


def forest_rooms():
    return {
        "schema": "p2-cave-rooms/1",
        "source": "engine",
        "geometry": "proxy",
        "cave": "forest_1",
        "floor": 1,
        "seed": 468001,
        "salt": 0,
        "cell": 48,
        "origin": [0, 0],
        "entrance": "forest_1:f1:segment:0",
        "hole": "forest_1:f1:segment:1",
        "units": [
            {"id": "forest_1:f1:segment:0", "kind": "segment", "hazard": None,
             "segment_index": 0, "items": ["juji_key_fc"], "gx": 0, "gz": 0,
             "doors": ["choke_water_0", "leaf_elec_0"]},
            {"id": "choke_water_0", "kind": "choke", "hazard": "water",
             "segment_index": 1, "items": [], "gx": 24, "gz": 48,
             "doors": ["forest_1:f1:segment:0", "forest_1:f1:segment:1"]},
            {"id": "leaf_elec_0", "kind": "leaf", "hazard": "elec",
             "segment_index": 0, "items": ["treasure_elec"], "gx": 72, "gz": 48,
             "doors": ["forest_1:f1:segment:0", "gate:leaf_elec_0"]},
            {"id": "forest_1:f1:segment:1", "kind": "segment", "hazard": None,
             "segment_index": 1, "items": [], "gx": 0, "gz": 96,
             "doors": ["choke_water_0", "leaf_water_0"]},
            {"id": "gate:leaf_elec_0", "kind": "gate", "hazard": "elec",
             "segment_index": 0, "items": [], "gx": 48, "gz": 96,
             "doors": ["leaf_elec_0"]},
            {"id": "leaf_water_0", "kind": "leaf", "hazard": "water",
             "segment_index": 1, "items": ["treasure_water"], "gx": 24, "gz": 144,
             "doors": ["forest_1:f1:segment:1"]},
        ],
        "edges": [
            ["forest_1:f1:segment:0", "choke_water_0"],
            ["choke_water_0", "forest_1:f1:segment:1"],
            ["forest_1:f1:segment:0", "leaf_elec_0"],
            ["forest_1:f1:segment:1", "leaf_water_0"],
            ["leaf_elec_0", "gate:leaf_elec_0"],
        ],
    }


def geometry_plan(rooms=None, geometry="real"):
    rooms = rooms or forest_rooms()
    nodes = []
    for unit in rooms["units"]:
        nodes.append({
            "id": unit["id"],
            "kind": unit["kind"],
            "hazard": unit["hazard"],
            "class": "real" if unit["kind"] in ("choke", "leaf", "gate") else "proxy",
            "model": "models/%s.mdl" % unit["id"] if unit["kind"] in ("choke", "leaf", "gate") else "",
            "gate": None,
            "gx": unit["gx"],
            "gz": unit["gz"],
        })
    return {
        "schema": "P2_CAVE_GEOMETRY_1",
        "cave": rooms["cave"],
        "floor": rooms["floor"],
        "seed": rooms["seed"],
        "salt": rooms["salt"],
        "geometry": geometry,
        "nodes": nodes,
        "entrance": rooms["entrance"],
        "hole": rooms["hole"],
    }


def door_by_id(plan, door_id):
    return next(door for door in plan["doors"] if door["id"] == door_id)


def test_build_preserves_order_ids_and_round_trips():
    rooms = forest_rooms()
    plan = gates.build_gates(rooms)

    assert [door["id"] for door in plan["doors"]] == [unit["id"] for unit in rooms["units"]]
    assert plan["schema"] == gates.GATES_SCHEMA
    assert plan["cave"] == rooms["cave"]
    assert plan["entrance"] == rooms["entrance"]
    assert plan["hole"] == rooms["hole"]
    assert plan["generation"] is False
    assert plan["source"] == gates.PLAN_SOURCE

    text = gates.gates_text(plan)
    assert text.splitlines()[0] == gates.GATES_TEXT_HEADER
    parsed = gates.parse_gates_text(text)
    assert parsed == plan
    assert gates.gates_text(parsed) == text


def test_every_node_gets_a_row_in_order():
    rooms = forest_rooms()
    plan = gates.build_gates(rooms)
    lines = gates.gates_text(plan).splitlines()

    assert lines[5] == "doors %d" % len(rooms["units"])
    rows = [line.split()[0] for line in lines[6:6 + len(rooms["units"])]]
    assert rows == [unit["id"] for unit in rooms["units"]]
    assert all(len(line.split()) == 5 for line in lines[6:6 + len(rooms["units"])])


def test_all_hazard_mappings():
    plan = gates.build_gates(forest_rooms())

    elec = door_by_id(plan, "leaf_elec_0")
    assert elec["hazard"] == "elec"
    assert elec["carry_block"] == "elec"
    assert elec["key"] == "yellow"

    water = door_by_id(plan, "choke_water_0")
    assert water["hazard"] == "water"
    assert water["carry_block"] == "water"
    assert water["key"] == "blue"

    segment = door_by_id(plan, "forest_1:f1:segment:0")
    assert segment["hazard"] is None
    assert segment["carry_block"] == "none"
    assert segment["key"] == "-"


def test_other_hazard_does_not_block():
    rooms = forest_rooms()
    rooms["units"].append({
        "id": "leaf_fire_0", "kind": "leaf", "hazard": "fire",
        "segment_index": 0, "items": [], "gx": 0, "gz": 0, "doors": [],
    })
    plan = gates.build_gates(rooms)
    fire = door_by_id(plan, "leaf_fire_0")
    assert fire["carry_block"] == "none"
    assert fire["key"] == "-"


def test_text_grammar_section_order():
    plan = gates.build_gates(forest_rooms())
    lines = gates.gates_text(plan).splitlines()
    assert lines[0] == gates.GATES_TEXT_HEADER
    assert lines[1].startswith("cave ")
    assert lines[2].startswith("floor ")
    assert lines[3].startswith("seed ")
    assert lines[4].startswith("geometry ")
    assert lines[5].startswith("doors ")
    assert lines[-2].startswith("entrance ")
    assert lines[-1].startswith("hole ")


def test_geometry_class_copied_from_plan():
    rooms = forest_rooms()
    assert gates.build_gates(rooms)["geometry"] == "proxy"
    assert gates.build_gates(rooms, geometry_plan(rooms, "real"))["geometry"] == "real"
    assert gates.build_gates(rooms, geometry_plan(rooms, "mixed"))["geometry"] == "mixed"
    assert gates.build_gates(rooms, geometry_plan(rooms, "proxy"))["geometry"] == "proxy"


def test_determinism_same_input_identical_text():
    rooms = forest_rooms()
    geometry = geometry_plan(rooms)
    first = gates.gates_text(gates.build_gates(rooms, geometry))
    second = gates.gates_text(gates.build_gates(rooms, geometry))
    assert first == second


def test_marker_reports_counts():
    plan = gates.build_gates(forest_rooms())
    marker = gates.gates_marker(plan)
    assert marker.startswith("P2_CAVE_GATES_READY ")
    fields = dict(part.split("=", 1) for part in marker.split()[1:])
    assert fields["doors"] == "6"
    assert fields["elec"] == "2"
    assert fields["water"] == "2"
    assert fields["no_block"] == "2"
    assert fields["geometry"] == "proxy"
    assert fields["cave"] == "forest_1"
    assert fields["floor"] == "1"
    assert fields["seed"] == "468001"


def test_report_counts_and_booleans():
    plan = gates.build_gates(forest_rooms())
    report = gates.gates_report(plan)
    assert report["schema"] == gates.REPORT_SCHEMA
    assert report["generation"] is False
    assert report["doors"] == 6
    assert report["elec"] == 2
    assert report["water"] == 2
    assert report["no_block"] == 2
    assert report["has_doors"] is True
    assert report["has_elec"] is True
    assert report["has_water"] is True
    assert report["has_no_block"] is True


def test_fail_closed_unknown_kind_and_hazard():
    bad_kind = forest_rooms()
    bad_kind["units"][0]["kind"] = "portal"
    with pytest.raises(gates.CaveGatesError):
        gates.build_gates(bad_kind)

    bad_hazard = forest_rooms()
    bad_hazard["units"][1]["hazard"] = "lava"
    with pytest.raises(gates.CaveGatesError):
        gates.build_gates(bad_hazard)


def test_fail_closed_missing_entrance_and_hole():
    no_entrance = forest_rooms()
    no_entrance["entrance"] = "no_such_node"
    with pytest.raises(gates.CaveGatesError):
        gates.build_gates(no_entrance)

    no_hole = forest_rooms()
    no_hole["hole"] = "no_such_node"
    with pytest.raises(gates.CaveGatesError):
        gates.build_gates(no_hole)


def test_fail_closed_duplicate_id():
    rooms = forest_rooms()
    rooms["units"][1]["id"] = rooms["units"][0]["id"]
    with pytest.raises(gates.CaveGatesError):
        gates.build_gates(rooms)


def test_fail_closed_unknown_geometry_class():
    rooms = forest_rooms()
    geometry = geometry_plan(rooms)
    geometry["geometry"] = "bogus"
    with pytest.raises(gates.CaveGatesError):
        gates.build_gates(rooms, geometry)


@pytest.mark.parametrize("field,value", [("cave", "forest_9"), ("floor", 2), ("seed", 999999)])
def test_fail_closed_geometry_disagreement(field, value):
    rooms = forest_rooms()
    geometry = geometry_plan(rooms)
    geometry[field] = value
    with pytest.raises(gates.CaveGatesError):
        gates.build_gates(rooms, geometry)


def test_fail_closed_geometry_node_mismatch():
    rooms = forest_rooms()
    geometry = geometry_plan(rooms)
    geometry["nodes"] = geometry["nodes"][:-1]
    with pytest.raises(gates.CaveGatesError):
        gates.build_gates(rooms, geometry)


def test_validate_rejects_tampered_carry_block():
    plan = gates.build_gates(forest_rooms())
    tampered = copy.deepcopy(plan)
    door_by_id(tampered, "choke_water_0")["carry_block"] = "none"
    with pytest.raises(gates.CaveGatesError):
        gates.validate_gates(tampered)

    lying = copy.deepcopy(plan)
    lying["generation"] = True
    with pytest.raises(gates.CaveGatesError):
        gates.validate_gates(lying)


def test_parser_rejects_malformed_text():
    plan = gates.build_gates(forest_rooms())
    text = gates.gates_text(plan)
    lines = text.splitlines()

    with pytest.raises(gates.CaveGatesError):
        gates.parse_gates_text("\n".join(["P2_CAVE_GATES_X"] + lines[1:]) + "\n")

    bad_count = list(lines)
    bad_count[5] = "doors %d" % (len(plan["doors"]) + 1)
    with pytest.raises(gates.CaveGatesError):
        gates.parse_gates_text("\n".join(bad_count) + "\n")

    bad_class = list(lines)
    bad_class[4] = "geometry weird"
    with pytest.raises(gates.CaveGatesError):
        gates.parse_gates_text("\n".join(bad_class) + "\n")

    bad_key = list(lines)
    parts = bad_key[6].split()
    parts[4] = "green"
    bad_key[6] = " ".join(parts)
    with pytest.raises(gates.CaveGatesError):
        gates.parse_gates_text("\n".join(bad_key) + "\n")

    duplicate = list(lines)
    first_id = duplicate[6].split()[0]
    parts = duplicate[7].split()
    parts[0] = first_id
    duplicate[7] = " ".join(parts)
    with pytest.raises(gates.CaveGatesError):
        gates.parse_gates_text("\n".join(duplicate) + "\n")

    with pytest.raises(gates.CaveGatesError):
        gates.parse_gates_text(text[:len(text) // 2])
    with pytest.raises(gates.CaveGatesError):
        gates.parse_gates_text(text + "extra\n")
    with pytest.raises(gates.CaveGatesError):
        gates.parse_gates_text("P2_CAVE_GATES_1\n")


def test_cli_writes_all_three_files(tmp_path, capsys):
    rooms_path = tmp_path / "p2-cave-rooms.json"
    rooms_path.write_text(json.dumps(forest_rooms()), encoding="utf-8")
    geometry_path = tmp_path / "custom-geometry.json"
    geometry_path.write_text(json.dumps(geometry_plan(geometry="real")), encoding="utf-8")
    out_dir = tmp_path / "out"

    status = gates.main(["--rooms", str(rooms_path), "--out-dir", str(out_dir),
                         "--geometry", str(geometry_path)])
    assert status == 0

    text_path = out_dir / "p2-cave-gates.txt"
    json_path = out_dir / "p2-cave-gates.json"
    report_path = out_dir / "p2-cave-gates-report.json"
    assert text_path.exists()
    assert json_path.exists()
    assert report_path.exists()

    plan = json.loads(json_path.read_text(encoding="utf-8"))
    assert gates.parse_gates_text(text_path.read_text(encoding="utf-8")) == plan
    assert plan["geometry"] == "real"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["doors"] == 6
    assert report["elec"] == 2
    assert report["water"] == 2
    assert report["no_block"] == 2
    assert capsys.readouterr().out.startswith("P2_CAVE_GATES_READY ")


def test_cli_autodiscovers_geometry_next_to_rooms(tmp_path, capsys):
    rooms_path = tmp_path / "p2-cave-rooms.json"
    rooms_path.write_text(json.dumps(forest_rooms()), encoding="utf-8")
    (tmp_path / gates.GEOMETRY_FILE).write_text(
        json.dumps(geometry_plan(geometry="mixed")), encoding="utf-8")
    out_dir = tmp_path / "out"

    status = gates.main(["--rooms", str(rooms_path), "--out-dir", str(out_dir)])
    assert status == 0
    plan = json.loads((out_dir / "p2-cave-gates.json").read_text(encoding="utf-8"))
    assert plan["geometry"] == "mixed"
    assert plan["generation"] is False
    assert capsys.readouterr().out.startswith("P2_CAVE_GATES_READY ")


def test_cli_without_geometry_is_proxy(tmp_path):
    rooms_path = tmp_path / "p2-cave-rooms.json"
    rooms_path.write_text(json.dumps(forest_rooms()), encoding="utf-8")
    out_dir = tmp_path / "out"

    assert gates.main(["--rooms", str(rooms_path), "--out-dir", str(out_dir)]) == 0
    plan = json.loads((out_dir / "p2-cave-gates.json").read_text(encoding="utf-8"))
    assert plan["geometry"] == "proxy"
    assert plan["generation"] is False


@pytest.mark.skipif(not OBSERVED_LAYOUT.exists(), reason="lane-41 observed layout not present")
def test_lane41_to_lane44_bridge_blocks_water_and_elec():
    from experimental import pikmin2_cave_rooms as rooms_mod

    observed = json.loads(OBSERVED_LAYOUT.read_text(encoding="utf-8"))
    rooms = rooms_mod.rooms_from_layout(observed)
    plan = gates.build_gates(rooms)

    assert [door["id"] for door in plan["doors"]] == [unit["id"] for unit in rooms["units"]]
    assert plan["geometry"] == "proxy"

    water = {door["id"] for door in plan["doors"] if door["carry_block"] == "water"}
    elec = {door["id"] for door in plan["doors"] if door["carry_block"] == "elec"}
    blocking = water | elec

    assert water == {"choke_water_0", "leaf_water_0"}
    assert elec == {"leaf_elec_0", "gate:leaf_elec_0"}
    assert all(door["key"] == "blue" for door in plan["doors"] if door["id"] in water)
    assert all(door["key"] == "yellow" for door in plan["doors"] if door["id"] in elec)
    assert all(door["carry_block"] == "none"
               for door in plan["doors"] if door["id"] not in blocking)

    assert gates.parse_gates_text(gates.gates_text(plan)) == plan
