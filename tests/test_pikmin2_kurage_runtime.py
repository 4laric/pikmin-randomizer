"""Tests for the lane-29 Kurage corpse-receipt runtime validator (#243)."""
import os

import pytest

from experimental import pikmin2_kurage_runtime as runtime


def _sample():
    return runtime.default_sample_log().splitlines()


def test_default_sample_log_validates_pass():
    result = runtime.validate_corpse_receipt(_sample())
    assert result["ok"] is True
    assert result["generator"] == 201001
    assert result["missing"] == []


def test_strip_dead_corpse_receipt_flips_fail():
    lines = [line for line in _sample() if not line.startswith("P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS")]
    result = runtime.validate_corpse_receipt(lines)
    assert result["ok"] is False
    assert result["dead_corpse_receipt"] is False
    assert "P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS generator=" in result["missing"]


def test_strip_corpse_receipt_flips_fail():
    lines = [line for line in _sample() if not line.startswith("P2_KURAGE_CORPSE_RECEIPT_PASS")]
    result = runtime.validate_corpse_receipt(lines)
    assert result["ok"] is False
    assert result["corpse_receipt"] is False
    assert "P2_KURAGE_CORPSE_RECEIPT_PASS generator=" in result["missing"]


def test_strip_cleanup_pass_flips_fail():
    lines = [line for line in _sample() if line != "PASS KURAGE_RUNTIME corpse_receipt_cleanup"]
    result = runtime.validate_corpse_receipt(lines)
    assert result["ok"] is False
    assert "PASS KURAGE_RUNTIME corpse_receipt_cleanup" in result["missing"]


def test_parse_generator():
    assert runtime.parse_generator(_sample()) == 201001
    assert runtime.parse_generator([]) is None
    assert runtime.parse_generator(["P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS generator=bad injected=health_zero"]) is None


def test_native_helper_graceful_without_env(monkeypatch):
    monkeypatch.delenv("PIKMIN_NATIVE_ROOT", raising=False)
    assert runtime.native_corpsereceipt_flag_present() in (None, False)


def test_native_helper_graceful_with_fake_dir(monkeypatch, tmp_path):
    (tmp_path / "tools").mkdir(exist_ok=True)
    monkeypatch.setenv("PIKMIN_NATIVE_ROOT", str(tmp_path))
    assert runtime.native_corpsereceipt_flag_present() is False
