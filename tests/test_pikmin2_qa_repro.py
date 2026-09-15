"""Lane-33 QA reproduction (slice 2) tests for experimental.pikmin2_qa_repro."""

import json
import tempfile
from pathlib import Path

from experimental import pikmin2_qa_matrix as qa
from experimental import pikmin2_qa_repro as repro

ROOT_COMMIT = "a" * 40
NATIVE_COMMIT = "b" * 40
EXE_SHA = "e" * 64

MARKER_A = "P2_ENEMY_READY species=BlueKochappy source_id=44"
MARKER_B = "P2_DWARF_ORANGE_DRAW corpse=0"

GOOD_LOG = "\n".join([MARKER_A, MARKER_B])


def spec(**overrides):
    base = {
        "id": "repro-1",
        "lane": "33",
        "species": "BlueKochappy",
        "stage": "natural_fight",
        "scenario": "baseline_cohort",
        "natural_markers": [MARKER_A, MARKER_B],
        "exe_sha256": EXE_SHA,
        "root_commit": ROOT_COMMIT,
        "native_commit": NATIVE_COMMIT,
    }
    base.update(overrides)
    return base


def test_reproduce_pass_when_exit_zero_and_all_markers_present():
    record = repro.reproduce(spec(), GOOD_LOG, 0, ["run/evidence.json"])
    assert record["status"] == qa.PASS
    assert record["kind"] == qa.KIND_NATURAL
    assert record["checks"][MARKER_A] is True
    assert record["checks"][MARKER_B] is True
    assert record["missing_markers"] == []


def test_reproduce_fail_when_natural_marker_missing():
    record = repro.reproduce(spec(), MARKER_A, 0, ["run/evidence.json"])
    assert record["status"] == qa.FAIL
    assert MARKER_B in record["notes"]
    assert record["missing_markers"] == [MARKER_B]


def test_reproduce_fail_when_nonzero_exit_code():
    record = repro.reproduce(spec(), GOOD_LOG, 1, ["run/evidence.json"])
    assert record["status"] == qa.FAIL


def test_reproduce_record_validates_with_natural_provenance():
    record = repro.reproduce(spec(), GOOD_LOG, 0, ["run/evidence.json"])
    assert qa.validate_record(record) == []
    assert record["kind"] == qa.KIND_NATURAL
    assert record["build_sha256"] == EXE_SHA
    assert record["root_commit"] == ROOT_COMMIT
    assert record["native_commit"] == NATIVE_COMMIT
    assert record["evidence_paths"] == ["run/evidence.json"]
    cell = qa.evaluate_cell([record], "natural_fight", "baseline_cohort")
    assert cell["status"] == qa.PASS


def test_diverge_reports_missing_markers_for_claimed_pass_observed_fail():
    claimed = {"id": "repro-1", "lane": "33", "status": qa.PASS, "notes": "cited natural run"}
    observed = repro.reproduce(spec(), MARKER_A, 0, ["run/evidence.json"])
    report = repro.diverge(claimed, observed)
    assert report["claimed_status"] == qa.PASS
    assert report["observed_status"] == qa.FAIL
    assert report["divergent"] is True
    assert report["missing_markers"] == [MARKER_B]
    assert report["exit_code"] == 0
    assert report["exe_sha256"] == EXE_SHA


def test_diverge_not_divergent_when_both_agree_pass():
    claimed = {"id": "repro-1", "lane": "33", "status": qa.PASS, "notes": "cited natural run"}
    observed = repro.reproduce(spec(), GOOD_LOG, 0, ["run/evidence.json"])
    report = repro.diverge(claimed, observed)
    assert report["claimed_status"] == qa.PASS
    assert report["observed_status"] == qa.PASS
    assert report["divergent"] is False
    assert report["missing_markers"] == []


def test_report_divergences_keeps_only_divergent_when_claimed_supplied():
    claimed_pass = {"id": "repro-1", "lane": "33", "status": qa.PASS}
    observed_fail = repro.reproduce(spec(), MARKER_A, 0, ["run/evidence.json"])
    observed_pass = repro.reproduce(spec(), GOOD_LOG, 0, ["run/evidence.json"])
    reports = repro.report_divergences([
        (claimed_pass, observed_fail),
        (claimed_pass, observed_pass),
    ])
    assert [r["id"] for r in reports] == ["repro-1"]
    assert len(reports) == 1


def test_cli_emit_record_round_trips():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        spec_file = root / "spec.json"
        log_file = root / "native.log"
        out_file = root / "records" / "repro-1.json"
        spec_file.write_text(json.dumps(spec()), encoding="utf-8")
        log_file.write_text(GOOD_LOG, encoding="utf-8")
        assert repro.main(["emit-record", "--spec", str(spec_file),
                           "--log", str(log_file), "--out", str(out_file)]) == 0
        record = json.loads(out_file.read_text(encoding="utf-8"))
        assert record["id"] == "repro-1"
        assert record["status"] == qa.PASS
        assert record["kind"] == qa.KIND_NATURAL
        assert record["build_sha256"] == EXE_SHA
        assert record["evidence_paths"] == [str(log_file)]
        assert qa.validate_record(record) == []
