"""Focused tests for lane-46 physical item placement (#lane46).

``pikmin2_cave_items`` consumes a lane-40/41/44 ``p2-cave-observed-layout/1``
graph and maps each item name onto its host unit plus the ``P2_CAVE_ITEMS_1``
native text form. These tests pin the invariants: tagged treasures only in a
matching leaf, untagged items only in the entrance segment, deterministic slot
ids and ``segment_index`` preserved verbatim, a lossless text round-trip, and
fail-closed handling of malformed input and unknown tagged tokens.
"""
import copy
import json

import pytest

from experimental import pikmin2_cave_items as items_mod

FROZEN_LAYOUT = {
    "schema": "p2-cave-observed-layout/1", "source": "engine", "seed": 468001,
    "cave": "forest_1", "floor": 1,
    "entrance": "forest_1:f1:segment:0", "hole": "forest_1:f1:segment:1",
    "nodes": [
        {"id": "forest_1:f1:segment:0", "kind": "segment", "segment_index": 0,
         "items": ["juji_key_fc"]},
        {"id": "choke_water_0", "kind": "choke", "hazard": "water", "segment_index": 1,
         "items": []},
        {"id": "forest_1:f1:segment:1", "kind": "segment", "segment_index": 1, "items": []},
        {"id": "leaf_elec_0", "kind": "leaf", "hazard": "elec", "segment_index": 0,
         "items": ["treasure_elec"]},
        {"id": "leaf_water_0", "kind": "leaf", "hazard": "water", "segment_index": 1,
         "items": ["treasure_water"]},
        {"id": "gate:leaf_elec_0", "kind": "gate", "hazard": "elec", "segment_index": 0,
         "items": []},
    ],
    "edges": [
        ["forest_1:f1:segment:0", "choke_water_0"],
        ["choke_water_0", "forest_1:f1:segment:1"],
        ["forest_1:f1:segment:0", "leaf_elec_0"],
        ["forest_1:f1:segment:1", "leaf_water_0"],
        ["leaf_elec_0", "gate:leaf_elec_0"],
    ],
}


@pytest.fixture
def layout():
    return copy.deepcopy(FROZEN_LAYOUT)


def node(layout, node_id):
    return next(entry for entry in layout["nodes"] if entry["id"] == node_id)


def test_frozen_layout_places_three_items_with_hosts(layout):
    payload = items_mod.items_from_layout(layout)
    assert payload["schema"] == items_mod.ITEMS_SCHEMA
    assert payload["geometry"] == items_mod.PROXY_GEOMETRY
    assert payload["cave"] == "forest_1"
    assert payload["floor"] == 1
    assert payload["seed"] == 468001
    assert payload["entrance"] == "forest_1:f1:segment:0"
    assert payload["hole"] == "forest_1:f1:segment:1"
    assert payload["counts"] == {"total": 3, "tagged": 2, "untagged": 1}
    assert [entry["item"] for entry in payload["items"]] == [
        "juji_key_fc", "treasure_elec", "treasure_water"]
    assert [entry["host"] for entry in payload["items"]] == [
        "forest_1:f1:segment:0", "leaf_elec_0", "leaf_water_0"]
    assert [entry["hazard"] for entry in payload["items"]] == [None, "elec", "water"]
    assert [entry["tagged"] for entry in payload["items"]] == [False, True, True]


def test_slot_ids_and_segment_index_preserved_from_layout(layout):
    payload = items_mod.items_from_layout(layout)
    by_host = {entry["host"]: entry for entry in payload["items"]}
    for entry in payload["items"]:
        host_node = node(layout, entry["host"])
        index = host_node["items"].index(entry["item"])
        assert entry["slot_id"] == f"item:{entry['host']}:{index}"
        assert entry["kind"] == host_node["kind"]
        assert entry["segment_index"] == host_node["segment_index"]
    assert by_host["forest_1:f1:segment:0"]["slot_id"] == "item:forest_1:f1:segment:0:0"
    assert by_host["leaf_elec_0"]["slot_id"] == "item:leaf_elec_0:0"
    assert by_host["leaf_water_0"]["slot_id"] == "item:leaf_water_0:0"
    assert by_host["leaf_water_0"]["segment_index"] == 1


def test_tagged_item_in_non_matching_hazard_leaf_raises(layout):
    node(layout, "leaf_elec_0")["items"] = []
    node(layout, "leaf_water_0")["items"] = ["treasure_elec"]
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.items_from_layout(layout)


def test_tagged_item_on_segment_raises(layout):
    node(layout, "leaf_elec_0")["items"] = []
    node(layout, "forest_1:f1:segment:0")["items"] = ["treasure_elec"]
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.items_from_layout(layout)


def test_untagged_item_outside_entrance_segment_raises(layout):
    node(layout, "forest_1:f1:segment:0")["items"] = []
    node(layout, "forest_1:f1:segment:1")["items"] = ["juji_key_fc"]
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.items_from_layout(layout)


def test_untagged_item_on_choke_host_raises(layout):
    node(layout, "choke_water_0")["items"] = ["juji_key_fc"]
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.items_from_layout(layout)


def test_unknown_tagged_token_not_in_map_raises(layout):
    node(layout, "leaf_elec_0")["items"] = ["treasure_bomb"]
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.items_from_layout(layout)


def test_unknown_item_on_gate_host_raises(layout):
    node(layout, "gate:leaf_elec_0")["items"] = ["mystery_relic"]
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.items_from_layout(layout)


def test_malformed_layout_is_wrapped_as_items_error(layout):
    layout["schema"] = "not-a-layout"
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.items_from_layout(layout)


def test_text_round_trip_is_lossless(layout):
    payload = items_mod.items_from_layout(layout)
    text = items_mod.items_text(payload)
    parsed = items_mod.parse_items_text(text)
    assert parsed["schema"] == items_mod.ITEMS_SCHEMA
    for key in ("source", "geometry", "cave", "floor", "seed", "items", "counts"):
        assert parsed[key] == payload[key]
    assert parsed["items"][0]["hazard"] is None
    assert parsed["items"][1]["tagged"] is True
    assert items_mod.items_text(parsed) == text


def test_text_grammar_has_fixed_sections_and_seven_tokens(layout):
    text = items_mod.items_text(items_mod.items_from_layout(layout))
    lines = text.splitlines()
    assert lines[0] == items_mod.ITEMS_TEXT_HEADER
    assert lines[1] == "cave forest_1"
    assert lines[2] == "floor 1"
    assert lines[3] == "seed 468001"
    assert lines[4] == "source engine"
    assert lines[5] == "geometry proxy"
    assert lines[6] == "items 3"
    assert len(lines) == 10
    for line in lines[7:]:
        assert len(line.split()) == 7


def test_malformed_header_raises(layout):
    text = items_mod.items_text(items_mod.items_from_layout(layout))
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.parse_items_text(text.replace(items_mod.ITEMS_TEXT_HEADER, "WRONG_HEADER", 1))
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.parse_items_text("P2_CAVE_ITEMS_1\n")


def test_wrong_count_raises(layout):
    text = items_mod.items_text(items_mod.items_from_layout(layout))
    too_many = text.replace("items 3", "items 5", 1)
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.parse_items_text(too_many)
    too_few = text.replace("items 3", "items 1", 1)
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.parse_items_text(too_few)


def test_trailing_content_raises(layout):
    text = items_mod.items_text(items_mod.items_from_layout(layout))
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.parse_items_text(text + "extra garbage line\n")


def test_malformed_item_row_raises(layout):
    text = items_mod.items_text(items_mod.items_from_layout(layout))
    lines = text.splitlines()
    lines[7] = " ".join(lines[7].split()[:6])
    with pytest.raises(items_mod.CaveItemsError):
        items_mod.parse_items_text("\n".join(lines) + "\n")


def test_placement_report_booleans_and_hosts(layout):
    payload = items_mod.items_from_layout(layout)
    report = items_mod.placement_report(payload)
    assert report["schema"] == items_mod.REPORT_SCHEMA
    assert report["geometry"] == "proxy"
    assert report["counts"] == {"total": 3, "tagged": 2, "untagged": 1}
    assert report["tagged_in_matching_leaf"] is True
    assert report["untagged_in_entrance"] is True
    assert report["hosts"] == ["forest_1:f1:segment:0", "leaf_elec_0", "leaf_water_0"]
    assert report["tagged_hosts"] == ["leaf_elec_0", "leaf_water_0"]
    assert report["untagged_hosts"] == ["forest_1:f1:segment:0"]


def test_write_items_creates_round_trippable_file(tmp_path, layout):
    payload = items_mod.items_from_layout(layout)
    target = tmp_path / "nested" / "p2-cave-items.txt"
    items_mod.write_items(payload, target)
    text = target.read_text(encoding="utf-8")
    parsed = items_mod.parse_items_text(text)
    assert parsed["items"] == payload["items"]
    assert parsed["counts"] == payload["counts"]
    assert items_mod.items_text(parsed) == text


def test_same_layout_is_deterministic(layout):
    first = items_mod.items_from_layout(layout)
    second = items_mod.items_from_layout(copy.deepcopy(layout))
    assert items_mod.logical_projection(first) == items_mod.logical_projection(second)
    assert items_mod.items_text(first) == items_mod.items_text(second)


def test_main_writes_all_artifacts_and_text_parses(tmp_path, capsys, layout):
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(json.dumps(layout), encoding="utf-8")
    out_dir = tmp_path / "out"
    status = items_mod.main(["--layout", str(layout_path), "--out-dir", str(out_dir)])
    assert status == 0

    text_path = out_dir / "p2-cave-items.txt"
    json_path = out_dir / "p2-cave-items.json"
    report_path = out_dir / "p2-cave-items-report.json"
    assert text_path.exists()
    assert json_path.exists()
    assert report_path.exists()

    parsed = items_mod.parse_items_text(text_path.read_text(encoding="utf-8"))
    assert parsed["counts"] == {"total": 3, "tagged": 2, "untagged": 1}
    written = json.loads(json_path.read_text(encoding="utf-8"))
    assert written["items"] == parsed["items"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema"] == items_mod.REPORT_SCHEMA
    assert report["tagged_in_matching_leaf"] is True
    assert report["untagged_in_entrance"] is True

    summary = json.loads(capsys.readouterr().out.strip())
    assert summary == {
        "items": str(json_path), "count": 3, "tagged": 2, "geometry": "proxy"}
