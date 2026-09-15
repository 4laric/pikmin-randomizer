"""Correlated-birth observer tests for muse-bombsarai (l59, #499).

The observer layers placement/source correlation on top of the lane-27
teki marker contract. These tests feed canonical synthetic logs plus
candidate placement records and assert the exact failing leg; a generated
Napkid birth without a matching source-58 placement resolve must never
correlate.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experimental.pikmin2_muse_bombsarai import (
    BOMBSARAI_SOURCE_ID,
    parse_placement_record,
    validate_correlated_birth,
)

FULL_LOG = "\n".join([
    "P2_BOMBSARAI_TEKI_READY generator=270001 type=11",
    "P2_BOMBSARAI_TEKI_SUPPLY generator=270001 tick=30",
    "P2_BOMBSARAI_TEKI_JOINT_FOLLOW generator=270001 travel_y=3.662 travel_xz=104.059",
    "P2_BOMBSARAI_TEKI_THROW generator=270001 kind=Release tick=53",
    "P2_BOMBSARAI_TEKI_BLAST generator=270001 token=270001 carrier_valid=1 hits=5 pikmin_hits=5",
])

PLACEMENT = {"source_id": 58, "generator": 270001}
PLACEMENT_TEXT = "P2_GENERATED_PLACEMENT source_id=58 generator=270001 slot=chal0"


def test_source_id_constant():
    assert BOMBSARAI_SOURCE_ID == 58


def test_empty_log_no_ready():
    result = validate_correlated_birth("", placement=PLACEMENT)
    assert result["correlated"] is False
    assert result["reason"] == "no-ready"
    assert result["legs"]["actor_bound"] is False


def test_correlated_dict_placement():
    result = validate_correlated_birth(FULL_LOG, placement=PLACEMENT)
    assert result["correlated"] is True
    assert result["reason"] == "correlated"
    assert all(result["legs"].values())
    assert result["generators"] == {"bound": 270001, "placement": 270001}
    assert result["lane27"]["gates"]["supplied"] is True
    assert result["lane27"]["gates"]["blasted"] is True


def test_correlated_text_placement():
    result = validate_correlated_birth(FULL_LOG, placement=PLACEMENT_TEXT)
    assert result["correlated"] is True
    assert result["reason"] == "correlated"


def test_napkid_birth_without_placement_never_correlates():
    # The key honesty gate: a full lane-27 marker stream with no
    # generated-placement resolve must NOT read as a generated identity.
    result = validate_correlated_birth(FULL_LOG, placement=None)
    assert result["correlated"] is False
    assert result["reason"] == "placement-pending"
    assert result["legs"]["actor_bound"] is True
    assert result["legs"]["supplied"] is True


def test_generator_mismatch():
    placement = {"source_id": 58, "generator": 270002}
    result = validate_correlated_birth(FULL_LOG, placement=placement)
    assert result["correlated"] is False
    assert result["reason"] == "generator-mismatch"
    assert result["legs"]["source_agree"] is True
    assert result["legs"]["placement_agree"] is False


def test_wrong_source_id_rejected():
    placement = {"source_id": 57, "generator": 270001}
    result = validate_correlated_birth(FULL_LOG, placement=placement)
    assert result["correlated"] is False
    assert result["reason"] == "source-mismatch"


def test_ready_without_supply():
    log = "P2_BOMBSARAI_TEKI_READY generator=270001 type=11"
    result = validate_correlated_birth(log, placement=PLACEMENT)
    assert result["correlated"] is False
    assert result["reason"] == "supply-missing"


def test_throw_without_ready_is_no_ready():
    log = "P2_BOMBSARAI_TEKI_THROW generator=270001 kind=Release tick=53"
    result = validate_correlated_birth(log, placement=PLACEMENT)
    assert result["correlated"] is False
    assert result["reason"] == "no-ready"


def test_malformed_placement_record():
    assert parse_placement_record("P2_GENERATED_PLACEMENT slot=chal0") is None
    assert parse_placement_record({"source_id": "x", "generator": 1}) is None
    assert parse_placement_record(12345) is None
    result = validate_correlated_birth(
        FULL_LOG, placement="P2_GENERATED_PLACEMENT slot=chal0")
    assert result["correlated"] is False
    assert result["reason"] == "placement-unparseable"
