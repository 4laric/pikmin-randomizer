import json
import tempfile
import unittest
from pathlib import Path

from experimental import pikmin2_qa_matrix as qa


def record(record_id="r1", stage="natural_fight", scenario="baseline_cohort",
           kind=qa.KIND_NATURAL, status=qa.PASS, **overrides):
    base = {
        "id": record_id,
        "stage": stage,
        "scenario": scenario,
        "kind": kind,
        "status": status,
        "root_commit": "a" * 40,
        "build_sha256": "b" * 64,
        "evidence_paths": ["output/run/verification.json"],
    }
    base.update(overrides)
    return base


class MatrixShapeTests(unittest.TestCase):
    def test_matrix_is_full_cross_product(self):
        self.assertEqual(len(qa.STAGES), 6)
        cells = qa.matrix_cells()
        self.assertEqual(len(cells), len(qa.STAGES) * len(qa.SCENARIOS))
        self.assertEqual(len(set(cells)), len(cells))

    def test_natural_required_stages_and_scenarios(self):
        for stage in ("natural_fight", "reward", "revisit", "restart"):
            self.assertTrue(qa.stage_natural_required(stage))
        for stage in ("generate", "install"):
            self.assertFalse(qa.stage_natural_required(stage))
        self.assertTrue(qa.cell_required("install", "baseline_cohort"))
        self.assertFalse(qa.cell_required("install", "missing_assets"))
        self.assertFalse(qa.cell_required("install", "minimum_cap"))

    def test_fixture_never_satisfies_natural_only_cell(self):
        self.assertTrue(qa.pass_allowed(qa.KIND_NATURAL, natural_required=True))
        self.assertTrue(qa.pass_allowed(qa.KIND_FIXTURE, natural_required=False))
        self.assertFalse(qa.pass_allowed(qa.KIND_FIXTURE, natural_required=True))
        for kind in (qa.KIND_INJECTED, qa.KIND_SYNTHETIC, qa.KIND_MOCKED):
            self.assertFalse(qa.pass_allowed(kind, natural_required=False))


class EvaluateTests(unittest.TestCase):
    def test_empty_matrix_defaults_untested(self):
        report = qa.build_report([])
        self.assertEqual(report["summary"][qa.UNTESTED], len(qa.matrix_cells()))
        self.assertEqual(sum(report["summary"].values()), len(qa.matrix_cells()))

    def test_natural_record_satisfies_natural_cell(self):
        cell = qa.evaluate_cell([record()], "natural_fight", "baseline_cohort")
        self.assertEqual(cell["status"], qa.PASS)
        self.assertEqual(cell["evidence"][0]["id"], "r1")

    def test_fixture_record_cannot_satisfy_natural_cell(self):
        cell = qa.evaluate_cell(
            [record(kind=qa.KIND_FIXTURE)], "natural_fight", "baseline_cohort")
        self.assertEqual(cell["status"], qa.BLOCKED)
        self.assertIn("cannot satisfy", cell["reason"])

    def test_fixture_record_satisfies_tooling_cell(self):
        cell = qa.evaluate_cell(
            [record(stage="install", scenario="missing_assets", kind=qa.KIND_FIXTURE)],
            "install", "missing_assets")
        self.assertEqual(cell["status"], qa.PASS)

    def test_injected_synthetic_and_mocked_never_pass(self):
        for kind in (qa.KIND_INJECTED, qa.KIND_SYNTHETIC, qa.KIND_MOCKED):
            cell = qa.evaluate_cell(
                [record(stage="install", scenario="missing_assets", kind=kind)],
                "install", "missing_assets")
            self.assertEqual(cell["status"], qa.BLOCKED, kind)

    def test_missing_provenance_blocks_even_natural(self):
        incomplete = record(root_commit="", build_sha256="", evidence_paths=[])
        cell = qa.evaluate_cell([incomplete], "natural_fight", "baseline_cohort")
        self.assertEqual(cell["status"], qa.BLOCKED)
        self.assertIn("provenance", cell["reason"])

    def test_fail_beats_pass(self):
        records = [record(record_id="ok"), record(record_id="bad", status=qa.FAIL)]
        cell = qa.evaluate_cell(records, "natural_fight", "baseline_cohort")
        self.assertEqual(cell["status"], qa.FAIL)

    def test_blocked_only_when_no_admissible_pass(self):
        records = [record(record_id="blocked", status=qa.BLOCKED)]
        cell = qa.evaluate_cell(records, "natural_fight", "baseline_cohort")
        self.assertEqual(cell["status"], qa.BLOCKED)
        self.assertEqual(cell["reason"], "all recorded attempts blocked")

    def test_stale_pin_rejects_mismatched_root_commit(self):
        pin = {"root_commit": "c" * 40}
        mismatch = record(stage="install", scenario="missing_assets",
                          kind=qa.KIND_FIXTURE, root_commit="a" * 40)
        cell = qa.evaluate_cell([mismatch], "install", "missing_assets", pin=pin)
        self.assertEqual(cell["status"], qa.BLOCKED)
        self.assertIn("stale-pin", cell["reason"])
        self.assertEqual(cell["evidence"][0]["id"], "r1")

        match = record(stage="install", scenario="missing_assets",
                       kind=qa.KIND_FIXTURE, root_commit="c" * 40)
        cell = qa.evaluate_cell([match], "install", "missing_assets", pin=pin)
        self.assertEqual(cell["status"], qa.PASS)

    def test_stale_pin_rejects_mismatched_native_commit(self):
        pin = {"native_commit": "d" * 40}
        mismatch = record(stage="install", scenario="missing_assets",
                          kind=qa.KIND_FIXTURE, native_commit="b" * 40)
        cell = qa.evaluate_cell([mismatch], "install", "missing_assets", pin=pin)
        self.assertEqual(cell["status"], qa.BLOCKED)
        self.assertIn("stale-pin", cell["reason"])

    def test_empty_record_commit_is_provenance_not_stale_pin(self):
        pin = {"root_commit": "c" * 40}
        incomplete = record(stage="install", scenario="missing_assets",
                            kind=qa.KIND_FIXTURE, root_commit="")
        cell = qa.evaluate_cell([incomplete], "install", "missing_assets", pin=pin)
        self.assertEqual(cell["status"], qa.BLOCKED)
        self.assertIn("provenance", cell["reason"])
        self.assertNotIn("stale-pin", cell["reason"])


class ValidationTests(unittest.TestCase):
    def test_validate_record_reports_every_problem(self):
        problems = qa.validate_record({"id": "", "stage": "nope", "scenario": "nope",
                                       "kind": "magic", "status": "maybe"})
        self.assertGreaterEqual(len(problems), 5)

    def test_check_records_flags_duplicates(self):
        problems = qa.check_records([record(), record(status=qa.FAIL)])
        self.assertTrue(any("duplicate" in problem for problem in problems))

    def test_valid_records_have_no_problems(self):
        self.assertEqual(qa.check_records([record()]), [])


class LoadingTests(unittest.TestCase):
    def test_load_records_accepts_object_list_and_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "single.json").write_text(json.dumps(record("single")), encoding="utf-8")
            (root / "list.json").write_text(json.dumps([record("list")]), encoding="utf-8")
            (root / "wrapped.json").write_text(
                json.dumps({"records": [record("wrapped")]}), encoding="utf-8")
            loaded = qa.load_records(root)
            self.assertEqual({r["id"] for r in loaded}, {"single", "list", "wrapped"})

    def test_load_records_rejects_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                qa.load_records(bad)


class ReportTests(unittest.TestCase):
    def test_markdown_contains_stage_tables_and_summary(self):
        report = qa.build_report([record()], pin={"root_commit": "x" * 40})
        markdown = qa.to_markdown(report)
        self.assertIn("natural_fight", markdown)
        self.assertIn("PASS", markdown)
        self.assertIn("Pinned baseline", markdown)
        self.assertIn("| scenario | status | reason | evidence |", markdown)

    def test_build_report_threads_pin(self):
        pin = {"root_commit": "c" * 40, "native_commit": "d" * 40}
        stale = record(stage="install", scenario="missing_assets",
                       kind=qa.KIND_FIXTURE, root_commit="a" * 40,
                       native_commit="b" * 40)
        fresh = record(record_id="fresh", stage="install", scenario="minimum_cap",
                       kind=qa.KIND_FIXTURE, root_commit="c" * 40,
                       native_commit="d" * 40)
        report = qa.build_report([stale, fresh], pin=pin)
        self.assertEqual(report["pin"], pin)
        cells = {(c["stage"], c["scenario"]): c for c in report["cells"]}
        self.assertEqual(cells[("install", "missing_assets")]["status"], qa.BLOCKED)
        self.assertIn("stale-pin", cells[("install", "missing_assets")]["reason"])
        self.assertEqual(cells[("install", "minimum_cap")]["status"], qa.PASS)

    def test_cli_report_and_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = root / "records"
            records.mkdir()
            (records / "run.json").write_text(json.dumps(record()), encoding="utf-8")
            out = root / "report"
            self.assertEqual(qa.main(["report", "--records", str(records),
                                      "--output", str(out),
                                      "--root-commit", "c" * 40]), 0)
            report = json.loads((out / "qa-matrix.json").read_text(encoding="utf-8"))
            self.assertEqual(report["pin"]["root_commit"], "c" * 40)
            self.assertTrue((out / "qa-matrix.md").exists())
            self.assertEqual(qa.main(["validate", "--records", str(records)]), 0)

            (records / "run.json").write_text(json.dumps(record(status="maybe")), encoding="utf-8")
            self.assertEqual(qa.main(["validate", "--records", str(records)]), 1)


class ImportTests(unittest.TestCase):
    def test_manifest_status_mapping(self):
        self.assertEqual(qa.manifest_status({"status": "passed"}), qa.PASS)
        self.assertEqual(qa.manifest_status({"status": "FAILED"}), qa.FAIL)
        self.assertEqual(qa.manifest_status({"status": "error"}), qa.FAIL)
        self.assertEqual(qa.manifest_status({"status": "blocked"}), qa.BLOCKED)
        self.assertEqual(qa.manifest_status({}), qa.BLOCKED)

    def test_record_from_manifest_extracts_fixture_hash(self):
        manifest = {"status": "passed",
                    "fixture": {"executable": {"sha256": "c" * 64}}}
        rec = qa.record_from_manifest(manifest, "output/run/verification.json",
                                      record_id="bt-run", stage="natural_fight",
                                      scenario="baseline_cohort", kind=qa.KIND_FIXTURE,
                                      root_commit="d" * 40)
        self.assertEqual(rec["status"], qa.PASS)
        self.assertEqual(rec["build_sha256"], "c" * 64)
        self.assertEqual(rec["evidence_paths"], ["output/run/verification.json"])
        self.assertEqual(qa.validate_record(rec), [])

    def test_record_from_manifest_rejects_bad_classification(self):
        with self.assertRaises(ValueError):
            qa.record_from_manifest({"status": "passed"}, "m.json", record_id="x",
                                    stage="nope", scenario="nope", kind="magic")

    def test_cli_import_then_report_guardrail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "verification.json"
            manifest.write_text(json.dumps(
                {"status": "passed", "fixture": {"executable": {"sha256": "e" * 64}}}),
                encoding="utf-8")
            boundary = root / "records" / "boundary.json"
            natural = root / "records" / "natural.json"
            common = ["--manifest", str(manifest), "--root-commit", "f" * 40]
            self.assertEqual(qa.main(["import-run", *common, "--id", "b",
                                      "--stage", "install", "--scenario", "missing_assets",
                                      "--kind", "fixture", "--out", str(boundary)]), 0)
            self.assertEqual(qa.main(["import-run", *common, "--id", "n",
                                      "--stage", "natural_fight", "--scenario",
                                      "baseline_cohort", "--kind", "fixture",
                                      "--out", str(natural)]), 0)
            out = root / "report"
            self.assertEqual(qa.main(["report", "--records", str(root / "records"),
                                      "--output", str(out)]), 0)
            report = json.loads((out / "qa-matrix.json").read_text(encoding="utf-8"))
            cells = {(c["stage"], c["scenario"]): c["status"] for c in report["cells"]}
            # A private fixture may satisfy a boundary cell but never a natural one.
            self.assertEqual(cells[("install", "missing_assets")], qa.PASS)
            self.assertEqual(cells[("natural_fight", "baseline_cohort")], qa.BLOCKED)


if __name__ == "__main__":
    unittest.main()
