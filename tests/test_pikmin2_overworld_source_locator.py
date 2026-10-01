"""Focused locator tests: real pin plus fail-closed negatives (issue #646)."""
import hashlib
from pathlib import Path

import pytest

import experimental.pikmin2_overworld_source_locator as loc
from experimental.pikmin2_overworld_source_locator import (
    DEFAULT_ISO,
    EXPECTED_SHA256,
    EXPECTED_SIZE,
    STAGES_PATH,
    HashMismatch,
    SourceBundle,
    SourceMissing,
    decode_stages,
    locate_and_decode,
    locate_source,
    read_stages_bytes,
)


def test_pin_constants():
    assert EXPECTED_SHA256 == "4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8"
    assert EXPECTED_SIZE == 3275
    assert STAGES_PATH == "user/Abe/stages.txt"
    assert DEFAULT_ISO.name == "PIKMIN2 for GAMECUBE.iso"


def test_positive_real_disc():
    if not DEFAULT_ISO.is_file():
        pytest.skip("local legal disc absent")
    bundle = locate_and_decode()
    assert isinstance(bundle, SourceBundle)
    assert bundle.size == EXPECTED_SIZE == len(bundle.data)
    assert bundle.sha256 == EXPECTED_SHA256
    assert hashlib.sha256(bundle.data).hexdigest() == EXPECTED_SHA256
    assert "tutorial" in bundle.text


def test_absent_disc_fails_closed(tmp_path):
    missing = tmp_path / "no-disc.iso"
    with pytest.raises(SourceMissing):
        locate_source(missing)
    with pytest.raises(SourceMissing):
        read_stages_bytes(missing)


def test_missing_member_fails_closed(monkeypatch, tmp_path):
    fake = tmp_path / "fake.iso"
    fake.write_bytes(b"GPVE01" + b"\x00" * 100)
    monkeypatch.setattr(loc, "disc_files", lambda iso: {})
    with pytest.raises(SourceMissing):
        loc.read_stages_bytes(fake)


def test_hash_mismatch_fails_closed(monkeypatch, tmp_path):
    fake = tmp_path / "fake.iso"
    fake.write_bytes(b"GPVE01" + b"\x00" * 100)
    monkeypatch.setattr(loc, "disc_files", lambda iso: {STAGES_PATH: (0, 4)})
    monkeypatch.setattr(loc, "_read_member", lambda iso, off, ln: b"xxxx")
    with pytest.raises(HashMismatch):
        loc.read_stages_bytes(fake)


def test_decode_roundtrip():
    if not DEFAULT_ISO.is_file():
        pytest.skip("local legal disc absent")
    data = read_stages_bytes()
    assert decode_stages(data).encode("utf-8") == data


def test_cli_reports_pin(tmp_path, capsys):
    if not DEFAULT_ISO.is_file():
        pytest.skip("local legal disc absent")
    assert loc.main([]) == 0
    out = capsys.readouterr().out
    assert EXPECTED_SHA256 in out and str(EXPECTED_SIZE) in out
    assert loc.main(["--iso", str(tmp_path / "no-disc.iso")]) == 2
