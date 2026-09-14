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


if __name__ == "__main__":
    unittest.main()
