"""Focused pytest for the lane-27 BombSarai runtime-log parser/validator.

The fixture is ``engine/tools/p2_bombsarai_runtime.cpp``; this test proves that
``experimental.pikmin2_bombsarai_runtime_log.validate_markers`` parses a
canonical synthetic marker stream (all three pinned scenarios) and degrades
tolerantly on empty/missing/numeric-corrupted inputs.
"""
import pytest

from experimental.pikmin2_bombsarai_runtime_log import validate_markers


def build_canonical_log():
    """Assemble the fixture's expected marker stream for all three scenarios."""
    head = [
        "P2_BOMBSARAI_MAP_PROBES_PASS",
        "P2_BOMBSARAI_FLOOR_PROBE ground=0.000000 center=5.000000 floor=1",
        "P2_BOMBSARAI_WALL_PROBE_PASS",
    ]
    approach = [
        "P2_BOMBSARAI_SCENARIO_BEGIN scenario=approach",
        "P2_BOMBSARAI_FSM_ENTER scenario=approach state=Wait tick=0",
        "P2_BOMBSARAI_FSM_SUPPLY scenario=approach tick=15",
        "P2_BOMBSARAI_FSM_ENTER scenario=approach state=BombMove tick=17",
        "P2_BOMBSARAI_JOINT_FOLLOW scenario=approach travel_y=40.0 min=30.0 max=50.0",
        "P2_BOMBSARAI_FSM_ENTER scenario=approach state=Release tick=88",
        "P2_BOMBSARAI_FSM_THROW scenario=approach kind=Release tick=90",
        "P2_BOMBSARAI_BLAST scenario=approach ticks=120 traces=8 floors=2 walls=1 "
        "hits=3 carrier_dead=0",
        "P2_BOMBSARAI_HIT scenario=approach id=501 kind=0 damage=45.000 self=0 token=9001",
        "P2_BOMBSARAI_HIT scenario=approach id=502 kind=1 damage=30.000 self=0 token=9002",
        "P2_BOMBSARAI_HIT scenario=approach id=503 kind=2 damage=25.000 self=0 token=9003",
        "P2_BOMBSARAI_SCENARIO_PASS scenario=approach",
    ]
    purple = [
        "P2_BOMBSARAI_SCENARIO_BEGIN scenario=purple",
        "P2_BOMBSARAI_FSM_ENTER scenario=purple state=Wait tick=0",
        "P2_BOMBSARAI_FSM_SUPPLY scenario=purple tick=20",
        "P2_BOMBSARAI_JOINT_FOLLOW scenario=purple travel_y=55.0 min=40.0 max=70.0",
        "P2_BOMBSARAI_FSM_THROW scenario=purple kind=Fall tick=75",
        "P2_BOMBSARAI_BLAST scenario=purple ticks=95 traces=7 floors=1 walls=3 "
        "hits=3 carrier_dead=0",
        "P2_BOMBSARAI_HIT scenario=purple id=501 kind=0 damage=45.000 self=0 token=9001",
        "P2_BOMBSARAI_HIT scenario=purple id=502 kind=1 damage=30.000 self=0 token=9002",
        "P2_BOMBSARAI_HIT scenario=purple id=503 kind=2 damage=25.000 self=0 token=9003",
        "P2_BOMBSARAI_SCENARIO_PASS scenario=purple",
    ]
    death = [
        "P2_BOMBSARAI_SCENARIO_BEGIN scenario=death",
        "P2_BOMBSARAI_FSM_ENTER scenario=death state=Wait tick=0",
        "P2_BOMBSARAI_FSM_SUPPLY scenario=death tick=18",
        "P2_BOMBSARAI_JOINT_FOLLOW scenario=death travel_y=30.0 min=20.0 max=40.0",
        "P2_BOMBSARAI_FSM_THROW scenario=death kind=Death tick=60",
        "P2_BOMBSARAI_BLAST scenario=death ticks=80 traces=6 floors=1 walls=1 "
        "hits=3 carrier_dead=1",
        "P2_BOMBSARAI_HIT scenario=death id=501 kind=0 damage=45.000 self=0 token=9001",
        "P2_BOMBSARAI_HIT scenario=death id=502 kind=1 damage=30.000 self=1 token=0",
        "P2_BOMBSARAI_HIT scenario=death id=503 kind=2 damage=25.000 self=1 token=0",
        "P2_BOMBSARAI_SCENARIO_PASS scenario=death",
    ]
    lines = head + approach + purple + death + ["PASS BOMBSARAI_RUNTIME"]
    return "\n".join(lines) + "\n"


EXPECTED = {
    "approach": ("Release", 3, False, 40.0),
    "purple": ("Fall", 3, False, 55.0),
    "death": ("Death", 3, True, 30.0),
}

ALL_FALSE = {
    "joint_follow": False,
    "travel_y": None,
    "throw_kind": None,
    "blast_fired": False,
    "hit_count": None,
    "carrier_dead": False,
    "scenario_pass": False,
    "carriers": {},
}


def test_happy_path_parses_all_scenarios():
    result = validate_markers(build_canonical_log())
    assert result["passed"] is True
    assert set(result["scenarios"]) == set(EXPECTED)
    for name, (kind, hits, dead, travel_y) in EXPECTED.items():
        entry = result["scenarios"][name]
        assert entry["joint_follow"] is True
        assert entry["travel_y"] == travel_y
        assert entry["travel_y"] > 0
        assert entry["throw_kind"] == kind
        assert entry["blast_fired"] is True
        assert entry["hit_count"] == hits
        assert entry["carrier_dead"] is dead
        assert entry["scenario_pass"] is True


def test_empty_log_returns_all_false_structure():
    result = validate_markers("")
    assert result["passed"] is False
    assert set(result["scenarios"]) == set(EXPECTED)
    for entry in result["scenarios"].values():
        assert entry == ALL_FALSE


def test_missing_pass_line_still_populates_scenarios():
    log = build_canonical_log().replace("PASS BOMBSARAI_RUNTIME", "")
    result = validate_markers(log)
    assert result["passed"] is False
    approach = result["scenarios"]["approach"]
    assert approach["joint_follow"] is True
    assert approach["throw_kind"] == "Release"
    assert approach["scenario_pass"] is True


def test_death_scenario_reports_carrier_dead_and_death_kind():
    result = validate_markers(build_canonical_log())
    death = result["scenarios"]["death"]
    assert death["carrier_dead"] is True
    assert death["throw_kind"] == "Death"


def test_malformed_numeric_field_is_tolerated():
    log = build_canonical_log()
    log = log.replace("hits=3 carrier_dead=0", "hits=three carrier_dead=0", 1)
    log = log.replace("scenario=approach travel_y=40.0",
                      "scenario=approach travel_y=NOPE", 1)
    result = validate_markers(log)
    approach = result["scenarios"]["approach"]
    assert approach["hit_count"] is None
    assert approach["travel_y"] is None
    assert approach["blast_fired"] is True
    assert approach["joint_follow"] is True


def test_malformed_line_raises_value_error():
    log = "P2_BOMBSARAI_BLAST ticks=10 hits=3 carrier_dead=0\n"
    with pytest.raises(ValueError):
        validate_markers(log)


def build_multi_carrier_log():
    """Two carriers, each with its own supply/follow/throw/blast marker."""
    return "\n".join([
        "P2_BOMBSARAI_SCENARIO_BEGIN scenario=multi",
        "P2_BOMBSARAI_FSM_SUPPLY scenario=multi carrier=0 tick=10",
        "P2_BOMBSARAI_JOINT_FOLLOW scenario=multi carrier=0 travel_y=40.0 "
        "travel_xz=12.5 min=30.0 max=50.0",
        "P2_BOMBSARAI_FSM_THROW scenario=multi carrier=0 kind=Release tick=20",
        "P2_BOMBSARAI_FSM_SUPPLY scenario=multi carrier=1 tick=15",
        "P2_BOMBSARAI_JOINT_FOLLOW scenario=multi carrier=1 travel_y=45.0 "
        "travel_xz=18.0 min=30.0 max=50.0",
        "P2_BOMBSARAI_FSM_THROW scenario=multi carrier=1 kind=Release tick=25",
        "P2_BOMBSARAI_BLAST scenario=multi carrier=0 token=9001 carrier_valid=1 "
        "ticks=100 traces=8 floors=2 walls=1 hits=3 carrier_dead=0",
        "P2_BOMBSARAI_BLAST scenario=multi carrier=1 token=9002 carrier_valid=1 "
        "ticks=110 traces=7 floors=1 walls=3 hits=3 carrier_dead=0",
        "P2_BOMBSARAI_HIT scenario=multi id=501 kind=0 damage=45.000 self=0 token=9001",
        "P2_BOMBSARAI_HIT scenario=multi id=502 kind=1 damage=30.000 self=0 token=9002",
        "P2_BOMBSARAI_SCENARIO_PASS scenario=multi",
        "PASS BOMBSARAI_RUNTIME",
    ]) + "\n"


def test_multi_carrier_separates_tokens():
    result = validate_markers(build_multi_carrier_log(), scenarios=("multi",))
    assert result["passed"] is True
    carriers = result["scenarios"]["multi"]["carriers"]
    assert set(carriers) == {0, 1}
    c0 = carriers[0]
    c1 = carriers[1]
    assert c0["blast_token"] == 9001
    assert c1["blast_token"] == 9002
    assert c0["blast_token"] != c1["blast_token"]
    for carrier in (c0, c1):
        assert carrier["joint_follow"] is True
        assert carrier["travel_y"] > 0
        assert carrier["travel_xz"] > 0
        assert carrier["throw_kind"] == "Release"
        assert carrier["blast_fired"] is True
        assert carrier["blast_carrier_valid"] is True
        assert carrier["hit_count"] == 3
        assert carrier["carrier_dead"] is False


def build_dead_carrier_log():
    """Dead carrier whose in-flight bomb still blasts (carrier_valid=0)."""
    return "\n".join([
        "P2_BOMBSARAI_SCENARIO_BEGIN scenario=dead",
        "P2_BOMBSARAI_FSM_SUPPLY scenario=dead carrier=0 tick=18",
        "P2_BOMBSARAI_JOINT_FOLLOW scenario=dead carrier=0 travel_y=30.0 "
        "travel_xz=5.0 min=20.0 max=40.0",
        "P2_BOMBSARAI_FSM_THROW scenario=dead carrier=0 kind=Release tick=60",
        "P2_BOMBSARAI_BLAST scenario=dead carrier=0 token=9001 carrier_valid=0 "
        "ticks=80 traces=6 floors=1 walls=1 hits=3 carrier_dead=1",
        "P2_BOMBSARAI_HIT scenario=dead id=501 kind=0 damage=45.000 self=1 token=0",
        "P2_BOMBSARAI_HIT scenario=dead id=502 kind=1 damage=30.000 self=1 token=0",
        "P2_BOMBSARAI_SCENARIO_PASS scenario=dead",
        "PASS BOMBSARAI_RUNTIME",
    ]) + "\n"


def test_dead_carrier_records_token_and_invalid_carrier():
    result = validate_markers(build_dead_carrier_log(), scenarios=("dead",))
    carriers = result["scenarios"]["dead"]["carriers"]
    assert set(carriers) == {0}
    c0 = carriers[0]
    assert c0["blast_token"] == 9001
    assert c0["blast_carrier_valid"] is False
    assert c0["carrier_dead"] is True


def test_multi_stripping_joint_follow_flips_passed():
    log = "\n".join(
        line for line in build_multi_carrier_log().splitlines()
        if "JOINT_FOLLOW scenario=multi" not in line
    ) + "\n"
    result = validate_markers(log, scenarios=("multi",))
    assert result["passed"] is False


def test_multi_stripping_scenario_pass_flips_passed():
    log = build_multi_carrier_log().replace(
        "P2_BOMBSARAI_SCENARIO_PASS scenario=multi\n", "")
    result = validate_markers(log, scenarios=("multi",))
    assert result["passed"] is False


def test_multi_single_token_flips_passed():
    log = build_multi_carrier_log().replace(
        "carrier=1 token=9002", "carrier=1 token=9001")
    result = validate_markers(log, scenarios=("multi",))
    assert result["passed"] is False
