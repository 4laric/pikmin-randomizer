"""Ordinary-spawn generator identity -> roster source binding (lane 03, cohort).

These tests exercise the diagnostic ``resolve_layout`` bridge API directly with an
explicit cohort, so they do not depend on the lane-02 admission monkeypatch. The
native side resolves a binding target token to a live generator by the decimal
string of that generator's own ID32 identity (``Generator::_70``); here a large
unsigned integer stands in for a real dwarf generator's ``_70`` value.
"""
import pytest

import experimental.pikmin2_seed_bridge as bridge


def test_snow_binding_round_trip_large_uid_target():
    layout = bridge.resolve_layout("seed-x", "Player1", ["2049888785"], [45])
    assert layout["bindings"] == [
        {"target": "2049888785", "source_id": 45, "enum_name": "YellowKochappy"}
    ]
    line = bridge.build_bootstrap(layout)
    assert line.startswith("ENEMY_P2 1 ")
    assert line.rstrip("\n").endswith(" 2049888785 45")
    parsed = bridge.parse_bootstrap(line)
    assert parsed["bindings"][0]["target"] == "2049888785"
    assert parsed["bindings"][0]["source_id"] == 45
    assert parsed["bindings"][0]["enum_name"] == "YellowKochappy"


def test_dwarf_orange_binding_round_trip():
    layout = bridge.resolve_layout("seed-x", "Player1", ["2049888785"], [44])
    assert layout["bindings"] == [
        {"target": "2049888785", "source_id": 44, "enum_name": "BlueKochappy"}
    ]
    line = bridge.build_bootstrap(layout)
    assert line.startswith("ENEMY_P2 1 ")
    assert line.rstrip("\n").endswith(" 2049888785 44")
    parsed = bridge.parse_bootstrap(line)
    assert parsed["bindings"] == layout["bindings"]


def test_multiple_targets_deterministic_and_cover_cohort():
    targets = ["2049888785", "2049888786"]
    first = bridge.resolve_layout("seed-x", "Player1", targets, [44, 45])
    second = bridge.resolve_layout("seed-x", "Player1", targets, [44, 45])
    assert first == second
    bound_sources = {binding["source_id"] for binding in first["bindings"]}
    assert bound_sources == {44, 45}
    bound_targets = [binding["target"] for binding in first["bindings"]]
    assert len(bound_targets) == len(set(bound_targets))
    assert set(bound_targets) == set(targets)


def test_non_bindable_source_rejected():
    with pytest.raises(ValueError):
        bridge.resolve_layout("seed-x", "Player1", ["2049888785"], [0])


def test_unknown_source_rejected():
    with pytest.raises(ValueError):
        bridge.resolve_layout("seed-x", "Player1", ["2049888785"], [999999])


def test_empty_targets_rejected():
    with pytest.raises(ValueError):
        bridge.resolve_layout("s", "p", [], [45])


def test_legacy_manifest_has_no_p2_line():
    assert bridge.bootstrap_for_manifest({}) == ""
