"""Focused tests for lane-44 proxy room instantiation (#482).

``pikmin2_cave_rooms`` consumes a lane-40/41 ``p2-cave-observed-layout/1`` graph
and produces a deterministic proxy grid plus the ``P2_CAVE_ROOMS_1`` native text
form. These tests pin the invariants: node ids/edges preserved verbatim, logic
unaffected by the salt while world coordinates re-roll, strict text round-trip,
and fail-closed handling of malformed input.
"""
import copy
import json
from pathlib import Path

import pytest

from experimental import pikmin2_cave_rooms as rooms_mod

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pikmin2_cave_spike"
OBSERVED_LAYOUT = Path("C:/Users/alari/pikmin-randomizer/output/dsw/l41-out/p2-cave-observed-layout.json")
LIVE_EVIDENCE = Path("C:/Users/alari/pikmin-randomizer/output/dsw/l44-out/rooms-live")


def load(name):
    with open(FIXTURES / name, "r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def layout():
    return load("spike_layout_fixture.json")


def test_rooms_preserve_ids_edges_and_entrance(layout):
    rooms = rooms_mod.rooms_from_layout(layout)
    assert {unit["id"] for unit in rooms["units"]} == {node["id"] for node in layout["nodes"]}
    assert len(rooms["units"]) == len(layout["nodes"])
    assert rooms["edges"] == layout["edges"]
    assert rooms["entrance"] == layout["entrance"]
    assert rooms["hole"] == layout["hole"]
    assert rooms["schema"] == rooms_mod.ROOMS_SCHEMA
    assert rooms["geometry"] == rooms_mod.PROXY_GEOMETRY
    assert rooms["source"] == layout["source"]


def test_report_is_proxy_and_ids_preserved(layout):
    rooms = rooms_mod.rooms_from_layout(layout)
    report = rooms_mod.instantiation_report(rooms, layout)
    assert report["schema"] == "p2-cave-rooms-report/1"
    assert report["geometry"] == "proxy"
    assert report["ids_preserved"] is True
    assert report["edges_preserved"] is True
    assert report["units"] == len(layout["nodes"])
    assert report["edges"] == len(layout["edges"])
    assert report["source"] == layout["source"]


def test_salt_does_not_change_logic_but_changes_geometry(layout):
    base = rooms_mod.rooms_from_layout(layout, salt=0)
    reroll = rooms_mod.rooms_from_layout(layout, salt=7)
    assert rooms_mod.logical_projection(base) == rooms_mod.logical_projection(reroll)
    assert {(unit["gx"], unit["gz"]) for unit in base["units"]} != {
        (unit["gx"], unit["gz"]) for unit in reroll["units"]}
    assert base["entrance"] == reroll["entrance"]


def test_same_inputs_are_deterministic(layout):
    first = rooms_mod.rooms_text(rooms_mod.rooms_from_layout(layout, salt=3, cell=32))
    second = rooms_mod.rooms_text(rooms_mod.rooms_from_layout(layout, salt=3, cell=32))
    assert first == second


def test_entrance_placed_at_origin(layout):
    rooms = rooms_mod.rooms_from_layout(layout, salt=11)
    entrance = next(unit for unit in rooms["units"] if unit["id"] == rooms["entrance"])
    assert (entrance["gx"], entrance["gz"]) == (0, 0)


def test_text_round_trips_exactly(layout):
    rooms = rooms_mod.rooms_from_layout(layout, salt=5, cell=32, origin=(3, 4))
    text = rooms_mod.rooms_text(rooms)
    assert text.splitlines()[0] == rooms_mod.ROOMS_TEXT_HEADER
    parsed = rooms_mod.parse_rooms_text(text)
    assert parsed == rooms
    assert rooms_mod.rooms_text(parsed) == text


def test_text_grammar_section_order(layout):
    text = rooms_mod.rooms_text(rooms_mod.rooms_from_layout(layout))
    lines = text.splitlines()
    assert lines[1].startswith("cave ")
    assert lines[2].startswith("floor ")
    assert lines[3].startswith("seed ")
    assert lines[4].startswith("salt ")
    assert lines[5].startswith("cell ")
    assert lines[6].startswith("origin ")
    assert lines[7].startswith("source ")
    assert lines[8].startswith("geometry ")
    assert lines[9].startswith("units ")
    edge_count = len(layout["edges"])
    assert lines[-(edge_count + 3)].startswith("entrance ")
    assert lines[-(edge_count + 2)].startswith("hole ")
    assert lines[-(edge_count + 1)].startswith("edges ")


def test_write_rooms_creates_round_trippable_file(tmp_path, layout):
    rooms = rooms_mod.rooms_from_layout(layout, salt=1)
    target = tmp_path / "nested" / "p2-cave-rooms.txt"
    rooms_mod.write_rooms(rooms, target)
    assert rooms_mod.parse_rooms_text(target.read_text(encoding="utf-8")) == rooms


def test_malformed_layout_fails_closed(layout):
    missing_id = copy.deepcopy(layout)
    missing_id["nodes"][0].pop("id")
    with pytest.raises(rooms_mod.CaveRoomsError):
        rooms_mod.rooms_from_layout(missing_id)

    bad_edge = copy.deepcopy(layout)
    bad_edge["edges"].append(["seg_A", "no_such_node"])
    with pytest.raises(rooms_mod.CaveRoomsError):
        rooms_mod.rooms_from_layout(bad_edge)

    bad_schema = copy.deepcopy(layout)
    bad_schema["schema"] = "not-a-layout"
    with pytest.raises(rooms_mod.CaveRoomsError):
        rooms_mod.rooms_from_layout(bad_schema)


def test_invalid_parameters_fail_closed(layout):
    with pytest.raises(rooms_mod.CaveRoomsError):
        rooms_mod.rooms_from_layout(layout, salt=-1)
    with pytest.raises(rooms_mod.CaveRoomsError):
        rooms_mod.rooms_from_layout(layout, cell=4)


def test_truncated_and_bad_text_fail_closed(layout):
    text = rooms_mod.rooms_text(rooms_mod.rooms_from_layout(layout))
    with pytest.raises(rooms_mod.CaveRoomsError):
        rooms_mod.parse_rooms_text(text[:len(text) // 2])
    with pytest.raises(rooms_mod.CaveRoomsError):
        rooms_mod.parse_rooms_text("WRONG_HEADER\n")
    truncated_edges = "\n".join(text.splitlines()[:-1]) + "\n"
    with pytest.raises(rooms_mod.CaveRoomsError):
        rooms_mod.parse_rooms_text(truncated_edges)
    with pytest.raises(rooms_mod.CaveRoomsError):
        rooms_mod.parse_rooms_text("P2_CAVE_ROOMS_1\n")


def test_cli_writes_all_artifacts(tmp_path, capsys, layout):
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(json.dumps(layout), encoding="utf-8")
    out_dir = tmp_path / "out"
    status = rooms_mod.main(["--layout", str(layout_path), "--out-dir", str(out_dir), "--salt", "2"])
    assert status == 0
    assert (out_dir / "p2-cave-rooms.txt").exists()
    assert (out_dir / "p2-cave-rooms.json").exists()
    assert (out_dir / "p2-cave-rooms-report.json").exists()
    printed = json.loads(capsys.readouterr().out.strip())
    assert printed["units"] == len(layout["nodes"])
    assert printed["geometry"] == "proxy"
    assert printed["salt"] == 2


@pytest.mark.skipif(not OBSERVED_LAYOUT.exists(), reason="lane-41 observed layout not present")
def test_lane41_observed_layout_instantiates():
    observed = json.loads(OBSERVED_LAYOUT.read_text(encoding="utf-8"))
    rooms = rooms_mod.rooms_from_layout(observed)
    assert {unit["id"] for unit in rooms["units"]} == {node["id"] for node in observed["nodes"]}
    assert rooms_mod.instantiation_report(rooms, observed)["geometry"] == "proxy"
    assert rooms_mod.parse_rooms_text(rooms_mod.rooms_text(rooms)) == rooms


def _timeline(log_text):
    rows = {}
    projections = []
    for line in log_text.splitlines():
        if line.startswith("P2_CAVE_ROOMS_TIMELINE "):
            fields = dict(part.split("=", 1) for part in line.split()[1:])
            rows[fields["tag"]] = {key: int(fields[key]) for key in
                                   ("hole", "treasure_elec", "treasure_water", "untagged")}
        elif line.startswith("P2_CAVE_ROOMS_PROJECTION "):
            projections.append(line.split("projection=", 1)[1])
    return rows, projections


@pytest.mark.skipif(not (LIVE_EVIDENCE / "rooms-run-salt0.log").exists(),
                    reason="live GL rooms evidence not present")
def test_live_timeline_matches_lane40_scenarios():
    rows, projections = _timeline((LIVE_EVIDENCE / "rooms-run-salt0.log").read_text(encoding="utf-8"))
    assert rows["fresh_floor_no_abilities"] == {
        "hole": 0, "treasure_elec": 0, "treasure_water": 0, "untagged": 1}
    assert rows["come_back_with_yellow"] == {
        "hole": 0, "treasure_elec": 1, "treasure_water": 0, "untagged": 1}
    assert rows["return_with_yellow_and_blue"] == {
        "hole": 1, "treasure_elec": 1, "treasure_water": 1, "untagged": 1}
    assert len(projections) == 1


@pytest.mark.skipif(not (LIVE_EVIDENCE / "rooms-run-salt7.log").exists(),
                    reason="live GL reroll evidence not present")
def test_live_reroll_keeps_projection_changes_geometry():
    rows0, proj0 = _timeline((LIVE_EVIDENCE / "rooms-run-salt0.log").read_text(encoding="utf-8"))
    rows7, proj7 = _timeline((LIVE_EVIDENCE / "rooms-run-salt7.log").read_text(encoding="utf-8"))
    assert proj0 and proj0 == proj7
    assert rows0 == rows7
    assert (LIVE_EVIDENCE / "p2-cave-rooms-salt0.txt").read_text(encoding="utf-8") != \
        (LIVE_EVIDENCE / "p2-cave-rooms-salt7.txt").read_text(encoding="utf-8")
