"""Tests for the damagumo P1 observer reader (#740)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental import pikmin2_muki_damagumo_p1_runtime as muse  # noqa: E402

BASE = "\n".join([
    "Experimental preview window set to 960x540 windowed and centered",
    "P2_MUSE_DAMAGUMO_READY squad=20 stage=ch_MUKI_damagumo",
    "P2_DAMAGUMO_BIND generator=375001 source_id=ch_MUKI_damagumo",
    "P2_CHALLENGE_BOOT stage=ch_MUKI_damagumo",
    "P2_CHALLENGE_RECEIPT stage=ch_MUKI_damagumo",
    "P2_CHALLENGE_EXIT stage=ch_MUKI_damagumo",
    "P2_MUSE_DAMAGUMO_SESSION navi=1 pikis=20",
    "PASS P2_MUSE_DAMAGUMO boot=1 receipt=1 exit=1 injected=0",
]) + "\n"


def test_valid_run_passes():
    r = muse.validate(BASE, 0)
    assert r["passed"] is True
    assert r["gates"] == {"playable_boot": "pass", "combat_receipt": "pass", "exit_cleanup": "pass"}


def test_unresolved_stage_fails_boot():
    text = BASE.replace("P2_CHALLENGE_BOOT stage=ch_MUKI_damagumo",
                        "SelectionError: unknown P2 challenge stage")
    r = muse.validate(text, 0)
    assert r["checks"]["stage_resolved"] is False
    assert r["gates"]["playable_boot"] == "fail"
    assert r["passed"] is False


def test_injected_run_rejected():
    text = BASE.replace("PASS P2_MUSE_DAMAGUMO",
                        "P2_MUSE_DAMAGUMO_INJECT mhealth=0\nPASS P2_MUSE_DAMAGUMO")
    r = muse.validate(text, 0)
    assert r["checks"]["no_inject"] is False
    assert r["passed"] is False


def test_wrong_stage_rejected():
    text = BASE.replace("ch_MUKI_damagumo", "ch_NARI_02tile")
    r = muse.validate(text, 0)
    assert r["checks"]["binds"] is False
    assert r["passed"] is False


def test_captain_down_rejected():
    text = BASE.replace("PASS P2_MUSE_DAMAGUMO",
                        "P2_FIXTURE_CAPTAIN_DOWN tick=5 hp=0.000 orima_dead=0 dead_state=0 outcome=BLOCKED\nPASS P2_MUSE_DAMAGUMO")
    r = muse.validate(text, 86)
    assert r["checks"]["captain_safe"] is False
    assert r["passed"] is False


def test_missing_receipt_fails():
    text = re.sub(r"P2_CHALLENGE_RECEIPT[^\n]*\n", "", BASE)
    r = muse.validate(text, 0)
    assert r["gates"]["combat_receipt"] == "fail"


def test_nonzero_exit_fails():
    assert muse.validate(BASE, 1)["passed"] is False


def test_reader_is_dependency_free():
    src = (ROOT / "experimental" / "pikmin2_muki_damagumo_p1_runtime.py").read_text()
    assert "import numpy" not in src and "import requests" not in src