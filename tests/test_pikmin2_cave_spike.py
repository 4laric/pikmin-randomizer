"""Focused tests for the lane-40 cave spike / acceptance checker (#479).

The checker evaluates the #468 acceptance contract against a seeded structural
table and observed floor layouts. Fixtures in
``tests/fixtures/pikmin2_cave_spike`` are synthetic slot assignments over real
``forest_1`` floor-1 content; every fixture layout is labelled ``fixture`` so it
can never be reported as a natural generation PASS.
"""
import copy
import json
from pathlib import Path

import pytest

from experimental import pikmin2_cave_spike as spike

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pikmin2_cave_spike"


def load(name):
    with open(FIXTURES / name, "r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def table():
    return load("spike_table.json")


def test_table_and_layout_fixtures_validate(table):
    spike.validate_table(table)
    spike.validate_layout(load("spike_layout_fixture.json"))


def test_spike_layout_passes_generation_invariant(table):
    result = spike.check_layout(table, load("spike_layout_fixture.json"))
    assert result["pass"], result["findings"]
    assert result["retry_required"] is False
    assert result["evidence_class"] == "injected"
    assert result["seed_matches"] is True


def test_reroll_layout_changes_geometry_but_keeps_slots(table):
    result = spike.check_layout(table, load("spike_layout_reroll.json"))
    assert result["pass"], result["findings"]


def test_bypassable_choke_is_rejected(table):
    result = spike.check_layout(table, load("spike_layout_bypass.json"))
    assert not result["pass"]
    assert any("bypassable" in finding for finding in result["findings"])


def test_off_slot_gate_is_rejected(table):
    result = spike.check_layout(table, load("spike_layout_gate_offslot.json"))
    assert not result["pass"]
    assert any("choke/leaf door" in finding for finding in result["findings"])


def test_missing_required_leaf_requests_retry(table):
    result = spike.check_layout(table, load("spike_layout_missing_leaf.json"))
    assert not result["pass"]
    assert result["retry_required"] is True
    assert any("missing leaf" in finding for finding in result["findings"])


def test_ambient_hard_gate_outside_logic_is_rejected(table):
    # Table whose only hard hazard is water; an electric gate is not in logic.
    watery = copy.deepcopy(table)
    watery["leaves"] = [leaf for leaf in watery["leaves"] if leaf["hazard"] != "elec"]
    watery["treasures"] = [t for t in watery["treasures"] if t["id"] != "treasure_elec"]
    layout = load("spike_layout_fixture.json")
    layout["nodes"].append({"id": "gate_elec_ambient", "kind": "gate", "hazard": "elec"})
    layout["edges"].append(["seg_B", "gate_elec_ambient"])
    result = spike.check_layout(watery, layout)
    assert not result["pass"]
    assert any("not in the floor's logic" in finding for finding in result["findings"])


def test_same_seed_is_deterministic(table):
    result = spike.check_determinism(table, copy.deepcopy(table))
    assert result["pass"], result["detail"]


def test_changed_seed_changes_table(table):
    result = spike.check_determinism(table, load("spike_table_alt_seed.json"))
    assert result["pass"], result["detail"]


def test_same_seed_with_changed_table_fails(table):
    mutated = copy.deepcopy(table)
    mutated["chokes"][0]["kind"] = "elec"
    result = spike.check_determinism(table, mutated)
    assert not result["pass"]


def test_bud_alternative_key_satisfies_choke():
    seeded = load("spike_table_alt_seed.json")
    # elec choke at segment 1 can be opened by the segment-0 elec bud with 5 Pikmin
    gates = spike.segment_requirements(seeded, 1)
    assert spike.requirements_satisfied(gates, {"species": {"yellow": True}, "buds": {}})
    without_species = {"species": {}, "buds": {"bud:elec:s0:n5": 5}}
    assert spike.requirements_satisfied(gates, without_species)
    short = {"species": {}, "buds": {"bud:elec:s0:n5": 4}}
    assert not spike.requirements_satisfied(gates, short)


def test_bud_behind_its_own_gate_is_rejected(table):
    broken = copy.deepcopy(table)
    broken["buds"] = [{"segment_index": 1, "hazard": "water", "count": 5}]
    with pytest.raises(spike.CaveSpikeError):
        spike.validate_table(broken)


def test_malformed_table_and_layout_fail_closed(table):
    with pytest.raises(spike.CaveSpikeError):
        spike.validate_table({"schema": "wrong"})
    bad_layout = load("spike_layout_fixture.json")
    bad_layout["edges"].append(["seg_A", "no_such_node"])
    with pytest.raises(spike.CaveSpikeError):
        spike.validate_layout(bad_layout)


def test_injected_fixture_is_model_pass_not_generation_pass(table):
    report = spike.check_spike(table, [load("spike_layout_fixture.json")])
    assert report["pass"]
    assert report["generation_invariant"]["model_pass"] is True
    assert report["generation_invariant"]["generation_pass"] is False
    assert report["generation_invariant"]["evidence"] == "injected"


def test_natural_engine_layout_can_be_generation_pass(table):
    layout = load("spike_layout_fixture.json")
    layout["source"] = "engine"
    report = spike.check_spike(table, [layout])
    assert report["generation_invariant"]["generation_pass"] is True


def test_reroll_invariance_holds_across_layouts(table):
    result = spike.check_reroll_invariance(
        table, [load("spike_layout_fixture.json"), load("spike_layout_reroll.json")])
    assert result["pass"], result
    assert result["requirements_stable"] is True


def test_end_to_end_loop_come_back_with_yellow(table):
    scenarios = load("spike_scenarios.json")["scenarios"]
    result = spike.check_scenarios(table, scenarios)
    assert result["pass"], [s for s in result["scenarios"] if not s["pass"]]


def test_full_spike_report(table):
    report = spike.check_spike(
        table,
        [load("spike_layout_fixture.json"), load("spike_layout_reroll.json")],
        load("spike_scenarios.json")["scenarios"])
    assert report["pass"]
    assert report["end_to_end_loop"]["pass"]
    assert report["reroll_invariance"]["pass"]
