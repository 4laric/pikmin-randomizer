"""Focused locator tests: real pin plus fail-closed negatives (issue #153)."""
import hashlib
from pathlib import Path

import pytest

import experimental.pikmin2_tutorial3_source_locator as loc
from experimental.pikmin2_tutorial3_source_locator import (
    CAVEINFO_PATH,
    CODEC,
    DEFAULT_ISO,
    EXPECTED_OFFSET,
    EXPECTED_SHA256,
    EXPECTED_SIZE,
    FloorUnit,
    HashMismatch,
    SourceBundle,
    SourceMissing,
    decode_tutorial3,
    floor_units,
    locate_and_decode,
    locate_source,
    read_tutorial3_bytes,
)


def test_pin_constants():
    assert CAVEINFO_PATH == "user/Mukki/mapunits/caveinfo/tutorial_3.txt"
    assert EXPECTED_OFFSET == 770672856
    assert EXPECTED_SIZE == 9701
    assert EXPECTED_SHA256 == "adcc816653957fbf00919c313291142cb110b5479c7790d997399e380c9b1abb"
    assert CODEC == "shift_jis"
    assert DEFAULT_ISO.name == "PIKMIN2 for GAMECUBE.iso"


def test_positive_real_disc():
    if not DEFAULT_ISO.is_file():
        pytest.skip("local legal disc absent")
    bundle = locate_and_decode()
    assert isinstance(bundle, SourceBundle)
    assert bundle.offset == EXPECTED_OFFSET
    assert bundle.size == EXPECTED_SIZE == len(bundle.data)
    assert bundle.sha256 == EXPECTED_SHA256
    assert hashlib.sha256(bundle.data).hexdigest() == EXPECTED_SHA256
    assert "# CaveInfo" in bundle.text and "# FloorInfo" in bundle.text


def test_floor_unit_structure():
    if not DEFAULT_ISO.is_file():
        pytest.skip("local legal disc absent")
    bundle = locate_and_decode()
    units = floor_units(bundle.text)
    assert len(units) == 8
    assert all(isinstance(u, FloorUnit) for u in units)
    assert [u.floor for u in units] == list(range(8))
    assert units[1].unit == "3_MAT_ike3_mid2_sak1_snow.txt"
    assert units[1].light == "tutorial_1_light.ini"
    assert units[1].rooms == 3
    assert all(u.unit for u in units)


def test_retail_bytes_are_not_plain_utf8():
    if not DEFAULT_ISO.is_file():
        pytest.skip("local legal disc absent")
    data = read_tutorial3_bytes()
    with pytest.raises(UnicodeDecodeError):
        data.decode("utf-8")
    assert decode_tutorial3(data).encode("utf-8") == data.decode(CODEC).encode("utf-8")


def test_absent_disc_fails_closed(tmp_path):
    missing = tmp_path / "no-disc.iso"
    with pytest.raises(SourceMissing):
        locate_source(missing)
    with pytest.raises(SourceMissing):
        read_tutorial3_bytes(missing)


def test_missing_member_fails_closed(monkeypatch, tmp_path):
    fake = tmp_path / "fake.iso"
    fake.write_bytes(b"GPVE01" + b"\x00" * 100)
    monkeypatch.setattr(loc, "disc_files", lambda iso: {})
    with pytest.raises(SourceMissing):
        loc.read_tutorial3_bytes(fake)


def test_hash_mismatch_fails_closed(monkeypatch, tmp_path):
    fake = tmp_path / "fake.iso"
    fake.write_bytes(b"GPVE01" + b"\x00" * 100)
    monkeypatch.setattr(loc, "disc_files",
                        lambda iso: {CAVEINFO_PATH: (EXPECTED_OFFSET, EXPECTED_SIZE)})
    monkeypatch.setattr(loc, "_read_member", lambda iso, off, ln: b"xxxx")
    with pytest.raises(HashMismatch):
        loc.read_tutorial3_bytes(fake)


def test_layout_drift_fails_closed(monkeypatch, tmp_path):
    fake = tmp_path / "fake.iso"
    fake.write_bytes(b"GPVE01" + b"\x00" * 100)
    monkeypatch.setattr(loc, "disc_files",
                        lambda iso: {CAVEINFO_PATH: (EXPECTED_OFFSET, EXPECTED_SIZE + 1)})
    with pytest.raises(HashMismatch):
        loc.read_tutorial3_bytes(fake)


def test_cli_reports_pin(tmp_path, capsys):
    if not DEFAULT_ISO.is_file():
        pytest.skip("local legal disc absent")
    assert loc.main([]) == 0
    out = capsys.readouterr().out
    assert EXPECTED_SHA256 in out and str(EXPECTED_SIZE) in out
    assert "floors=8" in out
    assert loc.main(["--iso", str(tmp_path / "no-disc.iso")]) == 2


def test_cli_writes_decoded_text(tmp_path):
    if not DEFAULT_ISO.is_file():
        pytest.skip("local legal disc absent")
    out = tmp_path / "tutorial_3.txt"
    assert loc.main(["--out", str(out)]) == 0
    assert "# CaveInfo" in out.read_text(encoding="utf-8")
