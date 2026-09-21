"""Unit tests for scripts/p2_proxy_record_evidence.py (tmp dirs only)."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import p2_proxy_record_evidence as recorder


@pytest.fixture
def rows_dir(tmp_path, monkeypatch):
    import randomizer.p2_proxy as proxy

    # Stub with the full real roster: load_rows() imports family_install on
    # first use, whose module-level wiring re-reads the real declaration
    # dir, so a narrowed stub would fail there before reaching tmp_path.
    stub = dict(proxy._roster_enums())
    monkeypatch.setattr(proxy, "_roster_enums", lambda: stub)
    rows = tmp_path / "rows"
    rows.mkdir()
    for source_id, enum in ((2, "Chappy"), (17, "Frog")):
        (rows / f"{source_id}_{enum}.json").write_text(json.dumps(
            {"schema": 1, "source_id": source_id, "enum_name": enum,
             "host_teki": 4, "pose_limit": 4,
             "notes": "test"}), encoding="utf-8")
    return rows


def write_probe(tmp_path, name="a6", **fields):
    probe_dir = tmp_path / name
    probe_dir.mkdir(exist_ok=True)
    log = probe_dir / "probe.log"
    log.write_bytes(b"natural gameplay log\n")
    digest = hashlib.sha256(b"natural gameplay log\n").hexdigest()
    payload = {"probe": name, "ok": True, "fatal": None,
               "exe_sha256": "cd" * 32, "table": [{"source": 2}],
               "bound_species": [2, 17],
               "drawn_live": {"2": {"frames": 120}, "17": {"frames": 96}},
               "expected": [2, 17], "skips": [],
               "log": "probe.log", "log_sha256": digest}
    payload.update(fields)
    result = probe_dir / "result.json"
    result.write_text(json.dumps(payload), encoding="utf-8")
    return result


def read_row(rows_dir, source_id, enum):
    return json.loads(
        (rows_dir / f"{source_id}_{enum}.json").read_text(encoding="utf-8"))


def test_records_and_is_idempotent(tmp_path, rows_dir):
    result = write_probe(tmp_path)
    lines, refused = recorder.record(result, rows_dir, "abc1234")
    assert refused == 0
    assert [line for line in lines if line.startswith("RECORDED")] and len(lines) == 2
    for source_id, enum in ((2, "Chappy"), (17, "Frog")):
        document = read_row(rows_dir, source_id, enum)
        assert document["evidence"]["run"] == "a6"
        assert document["evidence"]["log_sha256"] == \
            hashlib.sha256(b"natural gameplay log\n").hexdigest()
        assert document["evidence"]["native_commit"] == "abc1234"
        assert document["evidence"]["markers"] == {
            "table": True, "bind": True, "draw": True}
        # No other field touched.
        assert document["host_teki"] == 4 and document["pose_limit"] == 4
    before = {p.name: p.read_bytes() for p in rows_dir.glob("*.json")}
    lines, refused = recorder.record(result, rows_dir, "abc1234")
    assert refused == 0
    assert all(line.startswith("UNCHANGED") for line in lines)
    assert {p.name: p.read_bytes() for p in rows_dir.glob("*.json")} == before


def test_bound_but_not_drawn_is_not_recorded(tmp_path, rows_dir):
    result = write_probe(tmp_path, drawn_live={"2": {"frames": 5}})
    lines, refused = recorder.record(result, rows_dir, "abc1234")
    assert refused == 1
    assert any("17/Frog" in line and "not drawn" in line for line in lines)
    assert "evidence" in read_row(rows_dir, 2, "Chappy")
    assert "evidence" not in read_row(rows_dir, 17, "Frog")


def test_expected_but_unbound_refused(tmp_path, rows_dir):
    result = write_probe(tmp_path, bound_species=[2])
    lines, refused = recorder.record(result, rows_dir, "abc1234")
    assert refused == 1
    assert any("17/Frog" in line and "not in bound_species" in line
               for line in lines)


def test_fatal_empty_table_and_skips_refuse(tmp_path, rows_dir):
    result = write_probe(tmp_path, fatal="segfault")
    with pytest.raises(ValueError, match="fatal"):
        recorder.record(result, rows_dir, "abc1234")
    result = write_probe(tmp_path, table=[])
    _lines, refused = recorder.record(result, rows_dir, "abc1234")
    assert refused == 2
    result = write_probe(tmp_path, skips=["P2_SETUP_SKIP Chappy clip_file_missing"])
    lines, refused = recorder.record(result, rows_dir, "abc1234")
    assert refused == 1
    assert any("2/Chappy" in line and "skips" in line for line in lines)
    assert "evidence" not in read_row(rows_dir, 2, "Chappy")
    assert "evidence" in read_row(rows_dir, 17, "Frog")


def test_ok_false_and_log_mismatch_refuse_all(tmp_path, rows_dir):
    result = write_probe(tmp_path, ok=False)
    with pytest.raises(ValueError, match="ok is not true"):
        recorder.record(result, rows_dir, "abc1234")
    result = write_probe(tmp_path, log_sha256="00" * 32)
    with pytest.raises(ValueError, match="sha256 mismatch"):
        recorder.record(result, rows_dir, "abc1234")


def test_bad_native_commit_rejected(tmp_path, rows_dir):
    result = write_probe(tmp_path)
    with pytest.raises(ValueError, match="native commit"):
        recorder.record(result, rows_dir, "zzz")


def test_enum_name_refs_and_probe_dir_fallback(tmp_path, rows_dir):
    probe_dir = tmp_path / "b7"
    probe_dir.mkdir()
    (probe_dir / "run.log").write_bytes(b"log\n")
    digest = hashlib.sha256(b"log\n").hexdigest()
    result = probe_dir / "result.json"
    result.write_text(json.dumps({
        "ok": True, "fatal": None, "exe_sha256": "cd" * 32,
        "table": "P2_PROXY_CAMPAIGN_1 1 2 Chappy 4",
        "bound_species": ["Chappy"], "drawn_live": {"Chappy": {"frames": 3}},
        "expected": ["Chappy"], "skips": [],
        "log": "run.log", "log_sha256": digest}), encoding="utf-8")
    lines, refused = recorder.record(result, rows_dir, "abc1234")
    assert refused == 0
    assert read_row(rows_dir, 2, "Chappy")["evidence"]["run"] == "b7"


def test_cli_writes_and_reports(tmp_path, rows_dir, capsys):
    result = write_probe(tmp_path)
    assert recorder.main(["--result", str(result), "--rows-dir", str(rows_dir),
                          "--native-commit", "abc1234"]) == 0
    out = capsys.readouterr().out
    assert "RECORDED 2/Chappy" in out and "RECORDED 17/Frog" in out
    assert recorder.main(["--result", str(result), "--rows-dir", str(rows_dir),
                          "--native-commit", "abc1234"]) == 0
    assert "UNCHANGED 2/Chappy" in capsys.readouterr().out
    bad = write_probe(tmp_path, name="c9", drawn_live={})
    assert recorder.main(["--result", str(bad), "--rows-dir", str(rows_dir),
                          "--native-commit", "abc1234"]) == 1


def test_dict_skip_naming_species_refuses(tmp_path, rows_dir):
    result = write_probe(
        tmp_path,
        skips=[{"reason": "P2_SETUP_SKIP Chappy clip_file_missing"}])
    lines, refused = recorder.record(result, rows_dir, "abc1234")
    assert refused == 1
    assert any("2/Chappy" in line and "skips" in line for line in lines)
    assert "evidence" not in read_row(rows_dir, 2, "Chappy")
    assert "evidence" in read_row(rows_dir, 17, "Frog")


def test_rerecord_on_later_day_is_noop(tmp_path, rows_dir):
    from scripts.p2_proxy_record_evidence import apply, decide
    import json as _json

    result = write_probe(tmp_path)
    payload = _json.loads(result.read_text(encoding="utf-8"))
    payload["__path__"] = str(result)
    decisions, context = decide(payload, rows_dir)
    lines = apply(decisions, context, "abc1234", today="2026-09-20")
    assert any(line.startswith("RECORDED") for line in lines)
    before = {p.name: p.read_bytes() for p in rows_dir.glob("*.json")}
    lines = apply(decisions, context, "abc1234", today="2026-09-21")
    assert all(line.startswith("UNCHANGED") for line in lines)
    assert {p.name: p.read_bytes() for p in rows_dir.glob("*.json")} == before
