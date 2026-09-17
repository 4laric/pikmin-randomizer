"""Focused tests for the kusachi persistence driver (#758)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental import pikmin2_kusachi_persistence_driver as drv  # noqa: E402

WIRING = {"stage": "ch_NARI_01kusachi", "content_wired": True,
          "boot_marker": "content_wired=20 blue-bound boot"}


def test_sequences_generated_with_hashed_evidence(tmp_path):
    packet = drv.drive("ch_NARI_01kusachi", WIRING, tmp_path)
    assert set(packet["gates"]) == {"save", "reload", "retry", "re-entry"}
    assert all(len(g["sha256"]) == 64 for g in packet["gates"].values())
    assert packet["downstream_consumer"] == 533
    assert Path(packet["packet_path"]).is_file()


def test_unwired_stage_refused(tmp_path):
    with pytest.raises(drv.DriverRejected):
        drv.drive("ch_NARI_02tile", WIRING, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_empty_stage_refused(tmp_path):
    with pytest.raises(drv.DriverRejected):
        drv.drive("", WIRING, tmp_path)


def test_missing_wiring_refused(tmp_path):
    bad = dict(WIRING); del bad["content_wired"]
    with pytest.raises(drv.DriverRejected):
        drv.drive("ch_NARI_01kusachi", bad, tmp_path)


def test_wrong_wiring_stage_refused(tmp_path):
    bad = dict(WIRING, stage="ch_NARI_02tile")
    with pytest.raises(drv.DriverRejected):
        drv.drive("ch_NARI_01kusachi", bad, tmp_path)


def test_nonmapping_wiring_refused(tmp_path):
    with pytest.raises(drv.DriverRejected):
        drv.drive("ch_NARI_01kusachi", [], tmp_path)


def test_no_overwrite(tmp_path):
    drv.drive("ch_NARI_01kusachi", WIRING, tmp_path)
    with pytest.raises(drv.DriverRejected):
        drv.drive("ch_NARI_01kusachi", WIRING, tmp_path)


def test_keys_bound_to_kusachi():
    keys = drv.stage_keys("ch_NARI_01kusachi")
    assert all("ch_nari_01kusachi" in v for v in keys.values())
    assert set(keys) == {"save", "load", "clear", "highscore", "unlock"}


def test_gates_untested():
    packet = drv.drive("ch_NARI_01kusachi", WIRING)
    assert "UNTESTED" in packet["gates_claim"]


def test_module_is_stdlib_only():
    src = (ROOT / "experimental" / "pikmin2_kusachi_persistence_driver.py").read_text()
    assert "import numpy" not in src and "import requests" not in src