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
    "P2_BOMBSARAI_TEKI_PROBE generator=270001 tick=88 y=25.0 nearest=120.0 squad=0",
    "P2_BOMBSARAI_TEKI_PROBE generator=270001 tick=89 y=18.0 nearest=35.0 squad=6",
    "P2_BOMBSARAI_TEKI_DEAD generator=270001",
    "[Pikipelago] P2_POD_RECEIPT id=corpse:test:bombsarai:270001 value=10 new=1 pokos=10 seeds=0",
])


def test_empty_log_all_false():
    result = validate_teki_markers("")
    assert result["blasts"] == 0 and result["throw_kind"] is None
    assert set(result["gates"].values()) == {False}
    assert result["probes"] == []
    assert result["min_y"] is None and result["max_nearest"] is None
    assert result["engaged"] is False


def test_probe_in_reach_engages():
    log = "P2_BOMBSARAI_TEKI_PROBE generator=270001 tick=90 y=18.0 nearest=35.0 squad=6"
    result = validate_teki_markers(log)
    assert result["engaged"] is True
    assert result["min_y"] == 18.0
    assert result["max_nearest"] == 35.0
    assert len(result["probes"]) == 1
    probe = result["probes"][0]
    assert probe["tick"] == 90 and probe["y"] == 18.0
    assert probe["nearest"] == 35.0 and probe["squad"] == 6


def test_probe_out_of_reach_does_not_engage():
    log = "P2_BOMBSARAI_TEKI_PROBE generator=270001 tick=90 y=18.0 nearest=150.0 squad=6"
    result = validate_teki_markers(log)
    assert result["engaged"] is False
    assert result["min_y"] == 18.0
    assert result["max_nearest"] == 150.0


def test_probe_zero_squad_does_not_engage():
    log = "P2_BOMBSARAI_TEKI_PROBE generator=270001 tick=90 y=18.0 nearest=35.0 squad=0"
    result = validate_teki_markers(log)
    assert result["engaged"] is False


def test_probe_malformed_numerics_degrade_to_none():
    log = "\n".join([
        "P2_BOMBSARAI_TEKI_PROBE generator=270001 tick=90 y=NaN nearest=.. squad=6",
        "P2_BOMBSARAI_TEKI_PROBE generator=270001 tick=91 nearest=35.0 squad=6",
        "P2_BOMBSARAI_TEKI_PROBE generator=270001 tick=92 y=20.0 nearest=40.0 squad=7",
    ])
    result = validate_teki_markers(log)
    assert len(result["probes"]) == 3
    assert result["probes"][0]["y"] is None
    assert result["probes"][0]["nearest"] is None
    assert result["probes"][1]["y"] is None
    assert result["probes"][1]["nearest"] == 35.0
    assert result["probes"][2]["y"] == 20.0 and result["probes"][2]["squad"] == 7
    assert result["min_y"] == 20.0
    assert result["max_nearest"] == 40.0
    assert result["engaged"] is True


def test_full_log_flips_all_gates():
    result = validate_teki_markers(FULL_LOG)
    assert result["gates"] == {
        "ready": True, "supplied": True, "joint_follow": True, "thrown": True,
        "blasted": True, "dead": True, "corpse": True,
    }
    assert result["throw_kind"] == "Release"
    assert result["blasts"] == 1
    assert result["pikmin_hits"] == 2
    assert len(result["probes"]) == 2
    assert result["min_y"] == 18.0
    assert result["max_nearest"] == 120.0
    assert result["engaged"] is True


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
