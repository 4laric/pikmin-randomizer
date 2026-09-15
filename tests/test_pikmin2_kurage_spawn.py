"""Tests for the Kurage identity_spawn (source ID 57) log validator.

All samples are inline text only; no logs are read from disk and no absolute
paths are used.
"""

from experimental import pikmin2_kurage_spawn as spawn


def _passing_text():
    return (
        "P2_SEED_RESOLVE source_id=57 target=201001\n"
        "P2_KURAGE_TEKI_READY generator=201001 type=0 binding=private_adapter\n"
        "P2_PLACEMENT_SLOT generator=201001 slot=3 route=generated\n"
    )


def test_passing_sample_same_generator_with_placement():
    lines = _passing_text().splitlines()
    facts = spawn.parse_markers(lines)
    assert facts["seed_target"] == "201001"
    assert facts["generator"] == 201001
    assert facts["placement_marker"] is True
    result = spawn.validate_natural_spawn(lines)
    assert result["ok"] is True
    assert result["source_id"] == 57
    assert result["generator"] == 201001
    assert result["seed_marker"] is True
    assert result["bind_marker"] is True
    assert result["same_generator"] is True
    assert result["missing"] == []


def test_failure_when_seed_marker_stripped():
    lines = [
        line
        for line in _passing_text().splitlines()
        if "P2_SEED_RESOLVE" not in line
    ]
    result = spawn.validate_natural_spawn(lines)
    assert result["ok"] is False
    assert result["seed_marker"] is False
    assert result["bind_marker"] is True
    assert result["same_generator"] is False
    assert "P2_SEED_RESOLVE source_id=57" in result["missing"]


def test_failure_when_generator_and_seed_target_mismatch():
    lines = [
        "P2_SEED_RESOLVE source_id=57 target=201001",
        "P2_KURAGE_TEKI_READY generator=201002 type=0 binding=private_adapter",
        "P2_PLACEMENT_SLOT generator=201002 slot=3 route=generated",
    ]
    result = spawn.validate_natural_spawn(lines)
    assert result["ok"] is False
    assert result["seed_marker"] is True
    assert result["bind_marker"] is True
    assert result["same_generator"] is False
    assert any("mismatch" in entry for entry in result["missing"])


def test_failure_when_only_bind_marker_present():
    lines = [
        "P2_KURAGE_TEKI_READY generator=201001 type=0 binding=private_adapter",
    ]
    result = spawn.validate_natural_spawn(lines)
    assert result["ok"] is False
    assert result["seed_marker"] is False
    assert result["bind_marker"] is True
    assert result["generator"] == 201001
    assert result["same_generator"] is False
    assert "P2_SEED_RESOLVE source_id=57" in result["missing"]


def test_mapping_case_for_non_generator_target():
    lines = [
        "P2_SEED_RESOLVE source_id=57 target=kurage_nest_alpha",
        "P2_KURAGE_TEKI_READY generator=201001 type=0 binding=private_adapter",
    ]
    without_mapping = spawn.validate_natural_spawn(lines)
    assert without_mapping["ok"] is False
    assert without_mapping["same_generator"] is False
    with_mapping = spawn.validate_natural_spawn(
        lines, target_to_generator={"kurage_nest_alpha": 201001}
    )
    assert with_mapping["ok"] is True
    assert with_mapping["same_generator"] is True
    assert with_mapping["missing"] == []
