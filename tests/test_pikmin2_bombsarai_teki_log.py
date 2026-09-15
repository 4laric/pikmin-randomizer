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
    assert result["corpse_probes"] == []
    assert result["corpse_max_carriers"] == 0
    assert result["corpse_moved"] is None
    assert result["corpse_config"] is None
    assert result["transported"] is False


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


def test_corpse_probes_aggregate_and_transport():
    log = "\n".join([
        "P2_BOMBSARAI_TEKI_CORPSE tick=100 x=1.0 z=2.0 moved=5.0 carriers=0",
        "P2_BOMBSARAI_TEKI_CORPSE tick=101 x=1.5 z=2.5 moved=40.0 carriers=3",
        "P2_BOMBSARAI_TEKI_CORPSE tick=102 x=1.5 z=2.5 moved=12.0 carriers=4",
    ])
    result = validate_teki_markers(log)
    assert len(result["corpse_probes"]) == 3
    assert result["corpse_max_carriers"] == 4
    assert result["corpse_moved"] == 40.0
    assert result["transported"] is True
    assert result["corpse_probes"][0] == {"tick": 100, "moved": 5.0, "carriers": 0}
    assert result["corpse_probes"][1]["carriers"] == 3
    assert result["corpse_probes"][2]["carriers"] == 4


def test_corpse_probes_never_carried_not_transported():
    log = "\n".join([
        "P2_BOMBSARAI_TEKI_CORPSE tick=200 x=9.0 z=9.0 moved=7.5 carriers=0",
        "P2_BOMBSARAI_TEKI_CORPSE tick=201 x=9.0 z=9.0 moved=8.0 carriers=0",
    ])
    result = validate_teki_markers(log)
    assert result["transported"] is False
    assert result["corpse_max_carriers"] == 0
    assert result["corpse_moved"] == 8.0


def test_corpse_config_parsed():
    log = "P2_BOMBSARAI_TEKI_CORPSE_CONFIG carry_min=1 carry_max=3"
    result = validate_teki_markers(log)
    assert result["corpse_config"] == {"carry_min": 1, "carry_max": 3}


def test_pod_receipt_transports_without_carriers():
    log = "P2_POD_RECEIPT id=corpse:x:bombsarai:270001 value=10 new=1 pokos=10 seeds=0"
    result = validate_teki_markers(log)
    assert result["corpse_max_carriers"] == 0
    assert result["transported"] is True


def test_corpse_probe_malformed_numerics_degrade_to_none():
    log = "\n".join([
        "P2_BOMBSARAI_TEKI_CORPSE tick=300 x=1.0 z=1.0 moved=NaN carriers=..",
        "P2_BOMBSARAI_TEKI_CORPSE tick=301 x=2.0 z=2.0 moved=3.5",
    ])
    result = validate_teki_markers(log)
    assert len(result["corpse_probes"]) == 2
    assert result["corpse_probes"][0]["carriers"] is None
    assert result["corpse_probes"][0]["moved"] is None
    assert result["corpse_probes"][1]["carriers"] is None
    assert result["corpse_probes"][1]["moved"] == 3.5
    assert result["corpse_max_carriers"] == 0
    assert result["corpse_moved"] == 3.5
    assert result["transported"] is False


def test_full_log_with_corpse_probes():
    log = "\n".join(FULL_LOG.splitlines() + [
        "P2_BOMBSARAI_TEKI_CORPSE_CONFIG carry_min=1 carry_max=3",
        "P2_BOMBSARAI_TEKI_CORPSE tick=110 x=3.0 z=4.0 moved=6.0 carriers=0",
        "P2_BOMBSARAI_TEKI_CORPSE tick=111 x=3.5 z=4.5 moved=30.0 carriers=2",
    ])
    result = validate_teki_markers(log)
    assert result["gates"] == {
        "ready": True, "supplied": True, "joint_follow": True, "thrown": True,
        "blasted": True, "dead": True, "corpse": True,
    }
    assert result["throw_kind"] == "Release"
    assert result["blasts"] == 1 and result["pikmin_hits"] == 2
    assert result["engaged"] is True
    assert result["corpse_config"] == {"carry_min": 1, "carry_max": 3}
    assert result["corpse_max_carriers"] == 2
    assert result["corpse_moved"] == 30.0
    assert result["transported"] is True
