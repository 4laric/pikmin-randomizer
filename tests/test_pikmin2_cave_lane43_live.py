"""Live-gate tests for the lane-43 native cave-generation path.

These do not run the native engine; they pin the ``P2_CAVE_GEN`` marker
contract, the re-roll-invariant logical projection, and the pass/fail rules of
the live and unset-env checks using small synthetic layouts.
"""
import pytest

from experimental.pikmin2_cave_lane43_live import (
    LAYOUT_SCHEMA,
    LiveGateError,
    check_live_generation,
    check_unset_env,
    compare_live_and_standalone,
    logical_projection,
    parse_marker,
)

MARKER = (
    "P2_CAVE_GEN source=engine cave=forest_1 floor=1 seed=123456789 "
    "segments=2 chokes=1 leaves=1 buds=1 gates=1 entrance=n0 hole=n3 salt=7 attempts=3"
)


def make_layout(source="engine", schema=LAYOUT_SCHEMA, seed=123456789, unit=1, salt=7,
                entrance="n0", hole="n3", nodes=None, edges=None):
    """Build a small synthetic ``p2-cave-observed-layout/1`` layout."""
    if nodes is None:
        nodes = [
            {"id": "n0", "kind": "segment", "hazard": "water", "segment_index": 0,
             "items": ["treasure_a", "treasure_b"]},
            {"id": "n1", "kind": "choke", "hazard": "elec", "segment_index": 1, "items": []},
            {"id": "n2", "kind": "leaf", "hazard": "fire", "segment_index": 2,
             "items": ["treasure_c"]},
            {"id": "n3", "kind": "bud", "hazard": "", "segment_index": 3, "items": []},
        ]
    if edges is None:
        edges = [["n0", "n1"], ["n1", "n2"], ["n2", "n3"]]
    return {
        "schema": schema,
        "source": source,
        "seed": seed,
        "unit": unit,
        "salt": salt,
        "entrance": entrance,
        "hole": hole,
        "nodes": nodes,
        "edges": edges,
    }


def test_matching_projection_passes_with_natural_evidence():
    live = make_layout(unit=1, salt=7, seed=123456789)
    standalone = make_layout(unit=99, salt=42, seed=987654321)

    report = check_live_generation(MARKER, live, standalone)

    assert report["pass"] is True
    assert report["evidence"] == "natural"
    assert report["differences"] == []
    assert report["standalone_matches"] is True
    assert report["layout_source"] == "engine"
    assert report["marker"]["source"] == "engine"
    assert report["marker"]["cave"] == "forest_1"
    assert report["marker"]["seed"] == "123456789"


def test_geometry_is_excluded_from_projection():
    live = make_layout(unit=1, salt=7, seed=1)
    standalone = make_layout(unit=500, salt=9001, seed=2)
    assert logical_projection(live) == logical_projection(standalone)
    assert compare_live_and_standalone(live, standalone) == []


@pytest.mark.parametrize("mutate", [
    pytest.param(lambda layout: layout["nodes"][1].__setitem__("kind", "gate"), id="node-kind"),
    pytest.param(lambda layout: layout["nodes"][2].__setitem__("hazard", "poison"), id="node-hazard"),
    pytest.param(lambda layout: layout["edges"].append(["n0", "n3"]), id="edge-added"),
    pytest.param(lambda layout: layout["edges"].pop(0), id="edge-removed"),
    pytest.param(lambda layout: layout.__setitem__("entrance", "n1"), id="entrance"),
    pytest.param(lambda layout: layout.__setitem__("hole", "n2"), id="hole"),
    pytest.param(lambda layout: (layout["nodes"][0]["items"].remove("treasure_a"),
                                 layout["nodes"][2]["items"].append("treasure_a")), id="item-host"),
])
def test_logical_differences_fail(mutate):
    live = make_layout()
    standalone = make_layout()
    mutate(live)

    differences = compare_live_and_standalone(live, standalone)
    assert differences, "expected a non-empty difference list"

    report = check_live_generation(MARKER, live, standalone)
    assert report["pass"] is False
    assert report["differences"]
    assert report["standalone_matches"] is False


def test_unrelated_nodes_and_missing_items_differ():
    live = make_layout(nodes=[
        {"id": "n0", "kind": "segment", "hazard": "water", "items": ["treasure_a"]},
        {"id": "n1", "kind": "choke", "items": []},
    ], edges=[["n0", "n1"]])
    standalone = make_layout()
    differences = compare_live_and_standalone(live, standalone)
    assert any("n2" in difference or "n3" in difference for difference in differences)


def test_parse_marker_requires_exactly_one_line():
    assert parse_marker(MARKER + "\n")["cave"] == "forest_1"
    with pytest.raises(LiveGateError):
        parse_marker("nothing to see here\n")
    with pytest.raises(LiveGateError):
        parse_marker(MARKER + "\n" + MARKER + "\n")


def test_parse_marker_rejects_failed_line():
    with pytest.raises(LiveGateError):
        parse_marker("P2_CAVE_GEN source=engine FAILED reason=no-solution\n")


def test_parse_marker_returns_none_for_malformed_tokens():
    assert parse_marker("P2_CAVE_GEN source=engine cave=forest_1\n") == {
        "source": "engine", "cave": "forest_1"}
    assert parse_marker("P2_CAVE_GEN source=engine broken tokens\n") is None
    assert parse_marker("P2_CAVE_GEN\n") is None


def test_non_engine_layout_source_fails():
    live = make_layout(source="standalone")
    report = check_live_generation(MARKER, live, make_layout())
    assert report["pass"] is False


def test_wrong_schema_fails():
    live = make_layout(schema="p2-cave-observed-layout/0")
    report = check_live_generation(MARKER, live, make_layout())
    assert report["pass"] is False


def test_non_engine_marker_fails():
    live = make_layout()
    report = check_live_generation(
        "P2_CAVE_GEN source=standalone cave=forest_1 floor=1\n", live, make_layout())
    assert report["pass"] is False


def test_check_unset_env():
    assert check_unset_env("clean control run\nno markers here\n") == {"pass": True, "markers": 0}
    control = "boot\n" + MARKER + "\nshutdown\n"
    assert check_unset_env(control) == {"pass": False, "markers": 1}
