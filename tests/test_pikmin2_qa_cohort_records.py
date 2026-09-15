"""Lane-33 cohort-mixed QA slice: matrix resolution and manifest-import tests."""

import experimental.pikmin2_qa_matrix as qa
import experimental.pikmin2_cohort_mixed_runtime as mixed


ROOT_COMMIT = "c" * 40
BUILD = "b" * 64
EVIDENCE = ["output/run/evidence.json"]


def _record(record_id, stage, scenario, kind, status, *, build_sha256=BUILD,
            root_commit=ROOT_COMMIT, evidence_paths=EVIDENCE):
    return {
        "id": record_id,
        "stage": stage,
        "scenario": scenario,
        "kind": kind,
        "status": status,
        "root_commit": root_commit,
        "build_sha256": build_sha256,
        "evidence_paths": list(evidence_paths),
    }


def test_cohort_slice_build_report_summary():
    records = [
        _record("mix-fixture", "generate", "frame_budget", qa.KIND_FIXTURE, qa.PASS),
        _record("mix-natural", "natural_fight", "baseline_cohort", qa.KIND_NATURAL, qa.PASS),
    ]
    report = qa.build_report(records)
    cells = {(c["stage"], c["scenario"]): c["status"] for c in report["cells"]}
    assert cells[("generate", "frame_budget")] == qa.PASS
    assert cells[("natural_fight", "baseline_cohort")] == qa.PASS
    assert report["summary"][qa.PASS] == 2
    assert report["summary"][qa.UNTESTED] == len(qa.matrix_cells()) - 2


GOOD_LOG = "\n".join([
    "Experimental preview window set to 960x540 windowed and centered",
    "P2_ENEMY_READY species=BlueKochappy source_id=44",
    "P2_ENEMY_READY species=YellowKochappy",
    "P2_QURIONE_BIND generator=203001",
    "P2_ENEMY_READY species=Qurione",
    "P2_SHIJIMI_BIND generator=204001",
    "P2_ENEMY_READY species=ShijimiChou",
    "P2_DWARF_ORANGE_DRAW corpse=0",
    "P2_SNOW_DRAW corpse=0",
    "P2_QURIONE_DRAW corpse=0",
    "P2_SHIJIMI_DRAW corpse=0",
])


def _manifest_from_evidence(evidence):
    manifest = dict(evidence)
    manifest["status"] = "passed" if evidence["passed"] else "failed"
    return manifest


def test_record_from_manifest_with_cohort_evidence():
    evidence = mixed.evidence(GOOD_LOG, 0)
    assert evidence["passed"] is True

    manifest = _manifest_from_evidence(evidence)
    manifest["fixture"] = {"executable": {"sha256": "f" * 64}}

    rec = qa.record_from_manifest(
        manifest, "output/run/evidence.json",
        record_id="lane33-mixed", stage="generate", scenario="frame_budget",
        kind=qa.KIND_FIXTURE, root_commit=ROOT_COMMIT, build_sha256="d" * 64)
    assert rec["status"] == qa.PASS
    assert rec["build_sha256"] == "d" * 64
    assert rec["evidence_paths"] == ["output/run/evidence.json"]
    assert qa.validate_record(rec) == []

    fallback = qa.record_from_manifest(
        manifest, "output/run/evidence.json",
        record_id="lane33-mixed-fallback", stage="generate", scenario="frame_budget",
        kind=qa.KIND_FIXTURE, root_commit=ROOT_COMMIT)
    assert fallback["build_sha256"] == "f" * 64

    failed = mixed.evidence(GOOD_LOG + "\nExtinction\n", 0)
    assert failed["passed"] is False
    failed_rec = qa.record_from_manifest(
        _manifest_from_evidence(failed), "output/run/evidence.json",
        record_id="lane33-mixed-fail", stage="generate", scenario="frame_budget",
        kind=qa.KIND_FIXTURE, root_commit=ROOT_COMMIT, build_sha256="d" * 64)
    assert failed_rec["status"] == qa.FAIL
