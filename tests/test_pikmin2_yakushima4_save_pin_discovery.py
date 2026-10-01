"""Fail-closed tests for the yakushima4 save pin-discovery adapter (#779)."""
import copy
import json
import os
import subprocess
import sys
import tempfile

import pytest

ADAPTER = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "experimental",
    "pikmin2_yakushima4_save_pin_discovery.py"))
PY = sys.executable


def _load():
    import importlib.util
    spec = importlib.util.spec_from_file_location("savepin", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load()


def test_embedded_record_validates():
    assert R.validate_pin_record(R.pin_record()) == []


def test_cli_check_ok():
    proc = subprocess.run([PY, ADAPTER, "--check"],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert "P2_YAKUSHIMA4_SAVEPIN_OK sections=7" in proc.stdout


def test_cli_emit_is_valid_json_record():
    proc = subprocess.run([PY, ADAPTER, "--emit"],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    rec = json.loads(proc.stdout)
    assert R.validate_pin_record(rec) == []
    assert rec["consumer"] == 161


def test_missing_contract_section_fails():
    rec = copy.deepcopy(R.pin_record())
    del rec["contracts"]["dayclock_anchors"]
    errors = R.validate_pin_record(rec)
    assert "missing-contract:dayclock_anchors" in errors


def test_hash_mismatch_fails():
    rec = copy.deepcopy(R.pin_record())
    rec["floor1_evidence"]["validation_sha256"] = "zz-top"
    assert "bad-evidence-hash" in R.validate_pin_record(rec)
    rec2 = copy.deepcopy(R.pin_record())
    rec2["first_slice"]["native_base"] = "short"
    assert "bad-first-slice-pin" in R.validate_pin_record(rec2)


def test_absent_provider_fails():
    rec = copy.deepcopy(R.pin_record())
    rec["owner"] = {"kind": "unknown"}
    errors = R.validate_pin_record(rec)
    assert "absent-provider" in errors


def test_malformed_input_file_refused():
    fd, path = tempfile.mkstemp(prefix="savepin-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    proc = subprocess.run([PY, ADAPTER, "--check", path],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2
    assert "P2_YAKUSHIMA4_SAVEPIN_REFUSED reason=malformed-input" in proc.stdout


def test_missing_input_file_refused():
    proc = subprocess.run(
        [PY, ADAPTER, "--check",
         os.path.join(tempfile.gettempdir(), "no-such-savepin-xyz.json")],
        capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2
    assert "P2_YAKUSHIMA4_SAVEPIN_REFUSED reason=malformed-input" in proc.stdout


def test_usage_refused():
    proc = subprocess.run([PY, ADAPTER],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2
    assert "P2_YAKUSHIMA4_SAVEPIN_REFUSED reason=usage" in proc.stdout
