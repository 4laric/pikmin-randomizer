"""Focused locator tests: real pin plus fail-closed negatives (issue #152)."""
import hashlib
from pathlib import Path

import pytest

import experimental.pikmin2_tutorial2_source_locator as loc
from experimental.pikmin2_tutorial2_source_locator import (
    CAVEINFO_PATH,
    CODEC,
    DEFAULT_ISO,
    EXPECTED_OFFSET,
    EXPECTED_SHA256,
    EXPECTED_SIZE,
    HashMismatch,
    SourceBundle,
    SourceMissing,
    decode_tutorial2,
    locate_and_decode,
    locate_source,
    read_tutorial2_bytes,
)


def test_pin_constants():
    assert CAVEINFO_PATH == "user/Mukki/mapunits/caveinfo/tutorial_2.txt"
    assert EXPECTED_OFFSET == 770662632
    assert EXPECTED_SIZE == 10222
    assert EXPECTED_SHA256 == "05a38ab1e37c4ad11b5f48425bec3c2101ff199a4ea0b926fc9f35fde5620049"
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
    assert "CaveInfo" in bundle.text and "FloorInfo" in bundle.text


def test_retail_bytes_are_not_plain_utf8():
    if not DEFAULT_ISO.is_file():
        pytest.skip("local legal disc absent")
    data = read_tutorial2_bytes()
    with pytest.raises(UnicodeDecodeError):
        data.decode("utf-8")
    assert decode_tutorial2(data).encode("utf-8") == data.decode(CODEC).encode("utf-8")


def test_absent_disc_fails_closed(tmp_path):
    missing = tmp_path / "no-disc.iso"
    with pytest.raises(SourceMissing):
        locate_source(missing)
    with pytest.raises(SourceMissing):
        read_tutorial2_bytes(missing)


def test_missing_member_fails_closed(monkeypatch, tmp_path):
    fake = tmp_path / "fake.iso"
    fake.write_bytes(b"GPVE01" + b"\x00" * 100)
    monkeypatch.setattr(loc, "disc_files", lambda iso: {})
    with pytest.raises(SourceMissing):
        loc.read_tutorial2_bytes(fake)


def test_hash_mismatch_fails_closed(monkeypatch, tmp_path):
    fake = tmp_path / "fake.iso"
    fake.write_bytes(b"GPVE01" + b"\x00" * 100)
    monkeypatch.setattr(loc, "disc_files",
                        lambda iso: {CAVEINFO_PATH: (EXPECTED_OFFSET, EXPECTED_SIZE)})
    monkeypatch.setattr(loc, "_read_member", lambda iso, off, ln: b"xxxx")
    with pytest.raises(HashMismatch):
        loc.read_tutorial2_bytes(fake)


def test_cli_reports_pin(tmp_path, capsys):
    if not DEFAULT_ISO.is_file():
        pytest.skip("local legal disc absent")
    assert loc.main([]) == 0
    out = capsys.readouterr().out
    assert EXPECTED_SHA256 in out and str(EXPECTED_SIZE) in out
    assert loc.main(["--iso", str(tmp_path / "no-disc.iso")]) == 2