"""Lane-27 BombSarai teki-carrier marker flip tests (#244).

The teki binding emits a per-marker stream; each marker flips exactly one
acceptance flag. These tests feed canonical synthetic logs and assert which
flags flip, plus the segmentation between "carried/threw/blasted" and the
natural "killed by ordinary Pikmin + corpse receipt" tail.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experimental.pikmin2_bombsarai_teki_log import validate_teki_markers


FULL_LOG = "\n".join([
    "P2_BOMBSARAI_TEKI_READY generator=270001 type=11",
    "P2_BOMBSARAI_TEKI_SUPPLY generator=270001 tick=30",
    "P2_BOMBSARAI_TEKI_JOINT_FOLLOW generator=270001 travel_y=12.342 travel_xz=3.141",
    "P2_BOMBSARAI_TEKI_THROW generator=270001 kind=Release tick=46",
    "P2_BOMBSARAI_TEKI_BLAST generator=270001 token=270001 carrier_valid=1 hits=2 pikmin_hits=2",
    "P2_BOMBSARAI_TEKI_DEAD generator=270001",
    "[Pikipelago] P2_POD_RECEIPT id=corpse:test:bombsarai:270001 value=10 new=1 pokos=10 seeds=0",
])


def test_empty_log_all_false():
    result = validate_teki_markers("")
    assert result["blasts"] == 0 and result["throw_kind"] is None
    assert set(result["gates"].values()) == {False}


def test_full_log_flips_all_gates():
    result = validate_teki_markers(FULL_LOG)
    assert result["gates"] == {
        "ready": True, "supplied": True, "joint_follow": True, "thrown": True,
        "blasted": True, "dead": True, "corpse": True,
    }
    assert result["throw_kind"] == "Release"
    assert result["blasts"] == 1
    assert result["pikmin_hits"] == 2


def test_caught_before_throw_flags_only_acquisition():
    partial = "\n".join(FULL_LOG.splitlines()[:2])
    result = validate_teki_markers(partial)
    assert result["gates"]["ready"] and result["gates"]["supplied"]
    assert not result["gates"]["thrown"] and not result["gates"]["blasted"]


def test_kill_requires_dead_and_corpse():
    result = validate_teki_markers(FULL_LOG)
    assert result["gates"]["dead"] and result["gates"]["corpse"]
    without_dead = "\n".join(
        l for l in FULL_LOG.splitlines() if not l.startswith("P2_BOMBSARAI_TEKI_DEAD"))
    assert not validate_teki_markers(without_dead)["gates"]["dead"]


def test_corpse_receipt_requires_bombsarai_keyword():
    lines = FULL_LOG.splitlines()
    lines[-1] = "[Pikipelago] P2_POD_RECEIPT id=corpse:test:uji:9 value=10 new=1 pokos=10 seeds=0"
    result = validate_teki_markers("\n".join(lines))
    assert not result["gates"]["corpse"]


def test_multiple_blasts_accumulate():
    lines = FULL_LOG.splitlines()
    lines.insert(5, "P2_BOMBSARAI_TEKI_BLAST generator=270001 token=270001 carrier_valid=1 hits=1 pikmin_hits=1")
    result = validate_teki_markers("\n".join(lines))
    assert result["blasts"] == 2 and result["pikmin_hits"] == 3
