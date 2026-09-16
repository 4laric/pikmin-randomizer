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
    validate_generated_birth,
)
from experimental.pikmin2_muse_placement import MUSE_ACCEPTED_SLOT

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


# Generation-2: log-derived validation against the real reviewed marker
# contract (P2_SEED_RESOLVE + P2_GENERATED_PLACEMENT bound=1 on the accepted
# slot + teki READY/SUPPLY on the same generator).

ACCEPTED_58 = MUSE_ACCEPTED_SLOT[58]

GEN_LOG = "\n".join([
    "P2_SEED_RESOLVE source_id=58 target={uid} original_type=11 x=76.1 z=-178.4",
    "P2_GENERATED_PLACEMENT source_id=58 target={uid} generator=270001 bound=1",
    "P2_BOMBSARAI_TEKI_READY generator=270001 type=11",
    "P2_BOMBSARAI_TEKI_SUPPLY generator=270001 tick=30",
    "P2_BOMBSARAI_TEKI_JOINT_FOLLOW generator=270001 travel_y=3.662 travel_xz=104.059",
    "P2_BOMBSARAI_TEKI_THROW generator=270001 kind=Release tick=53",
    "P2_BOMBSARAI_TEKI_BLAST generator=270001 token=270001 carrier_valid=1 hits=5 pikmin_hits=5",
]).format(uid=ACCEPTED_58)


def test_accepted_slot_is_58_profile():
    assert ACCEPTED_58 == 1787125272


def test_generated_birth_correlated():
    result = validate_generated_birth(GEN_LOG)
    assert result["correlated"] is True
    assert result["reason"] == "correlated"
    assert all(result["legs"].values())
    assert result["generators"] == {"bound": 270001, "placement": 270001}
    assert result["uids"]["resolved"] == ACCEPTED_58
    assert result["uids"]["bound"] == ACCEPTED_58
    assert result["lane27"]["gates"]["supplied"] is True


def test_teki_only_log_needs_seed_markers():
    # Same honesty gate as generation 1, now against real markers: a full
    # teki stream with no P2_SEED_RESOLVE/P2_GENERATED_PLACEMENT never
    # correlates.
    result = validate_generated_birth(FULL_LOG)
    assert result["correlated"] is False
    assert result["reason"] == "seed-unresolved"
    assert result["legs"]["actor_bound"] is True


def test_wrong_uid_slot_mismatch():
    log = GEN_LOG.replace("target=%d" % ACCEPTED_58, "target=12345")
    result = validate_generated_birth(log)
    assert result["correlated"] is False
    assert result["reason"] == "slot-mismatch"
    assert result["legs"]["seed_resolved"] is True
    assert result["legs"]["slot_accepted"] is False


def test_bound_zero_is_refusal():
    log = GEN_LOG.replace("generator=270001 bound=1",
                          "generator=270001 bound=0 reason=slot-rejected")
    result = validate_generated_birth(log)
    assert result["correlated"] is False
    assert result["reason"] == "placement-refused"
    assert result["placement"]["refusal_reason"] == "slot-rejected"


def test_bind_generator_must_match_vehicle():
    log = GEN_LOG.replace("P2_GENERATED_PLACEMENT source_id=58 target=%d generator=270001 bound=1" % ACCEPTED_58,
                          "P2_GENERATED_PLACEMENT source_id=58 target=%d generator=270002 bound=1" % ACCEPTED_58)
    result = validate_generated_birth(log)
    assert result["correlated"] is False
    assert result["reason"] == "generator-mismatch"
    assert result["legs"]["slot_accepted"] is True
    assert result["legs"]["generator_agree"] is False


def test_ready_without_supply_log_derived():
    lines = [line for line in GEN_LOG.splitlines()
             if "TEKI_SUPPLY" not in line]
    result = validate_generated_birth("\n".join(lines))
    assert result["correlated"] is False
    assert result["reason"] == "supply-missing"


def test_empty_log_is_no_ready():
    result = validate_generated_birth("")
    assert result["correlated"] is False
    assert result["reason"] == "no-ready"
