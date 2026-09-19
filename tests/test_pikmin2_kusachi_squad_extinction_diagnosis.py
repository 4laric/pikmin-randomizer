"""Fail-closed tests for the kusachi extinction diagnosis adapter (issue #787).

Positive: the real pinned evidence reproduces the engine-manager-removal
verdict. Negatives: missing files, hash drift, truncated log and wrong
fingerprint are all REFUSED (exit 2 / return 2), never a verdict.
No engine edits.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

CANON = Path("C:/Users/alari/pikmin-randomizer")
ADAPTER = Path(__file__).resolve().parents[1] / "experimental" / "pikmin2_kusachi_squad_extinction_diagnosis.py"
LOG = CANON / "output/kusachi-gameplay-obs-run-gen3-v2/native.log"
REP = CANON / "output/workflow/autofill/planning-shards/challenge-3/prepared/kusachi-gameplay-output/gen3-report.json"
PY = sys.executable


def run(*args):
    return subprocess.run([PY, str(ADAPTER), *args], capture_output=True, text=True, cwd=str(CANON))


def load_adapter(tmp_path=None):
    sys.path.insert(0, str(ADAPTER.parent))
    import importlib
    mod = importlib.import_module("pikmin2_kusachi_squad_extinction_diagnosis")
    return importlib.reload(mod)


def test_positive_verdict_on_pinned_evidence():
    r = run(str(LOG), str(REP))
    assert r.returncode == 0, r.stdout + r.stderr
    v = json.loads(r.stdout)
    assert v["cause_class"] == "engine-manager-removal"
    assert v["abrupt_flip_20_to_0"] is True
    assert v["hazards_ruled_out"] is True
    assert v["fixture_ruled_out"] is True
    assert v["navimgr_drop_proven"] is False
    assert v["extinction_cinemas_played"] is True


def test_missing_log_refused(tmp_path):
    r = run(str(tmp_path / "nope.log"), str(REP))
    assert r.returncode == 2 and r.stdout.startswith("REFUSED")


def test_missing_report_refused(tmp_path):
    r = run(str(LOG), str(tmp_path / "nope.json"))
    assert r.returncode == 2 and r.stdout.startswith("REFUSED")


def test_hash_drift_refused(tmp_path):
    bad = tmp_path / "native.log"
    bad.write_bytes(b"P2_KUSACHI_EXTINCTION tick=90 wired=0\n")
    r = run(str(bad), str(REP))
    assert r.returncode == 2 and "drift" in r.stdout


def test_truncated_log_refused(tmp_path):
    mod = load_adapter()
    lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    cut = tmp_path / "cut.log"
    cut.write_text("\n".join(lines[:1200]), encoding="utf-8")
    mod.NATIVE_LOG_SHA = hashlib.sha256(cut.read_bytes()).hexdigest()
    assert "PASS KUSACHI_GAMEPLAY" not in cut.read_text(encoding="utf-8")
    assert mod.main([str(ADAPTER), str(cut), str(REP)]) == 2


def test_wrong_fingerprint_refused(tmp_path):
    mod = load_adapter()
    bad = tmp_path / "rep.json"
    d = json.loads(REP.read_text(encoding="utf-8"))
    d["diagnostic_fingerprint"] = "something-else"
    bad.write_text(json.dumps(d), encoding="utf-8")
    mod.REPORT_SHA = hashlib.sha256(bad.read_bytes()).hexdigest()
    assert mod.main([str(ADAPTER), str(LOG), str(bad)]) == 2