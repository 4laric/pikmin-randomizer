import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from experimental import pikmin2_performance_budget as pb
from experimental import pikmin2_qa_matrix as qa


def budgets(status=pb.ACCEPTED, **overrides):
    base = {
        "schema": pb.BUDGET_SCHEMA,
        "status": status,
        "revision": "test-1",
        "target_mean_frame_ms_max": 16.7,
        "slowest_window_mean_ms_max": 20.0,
        "tracked_texture_peak_mib_max": 64,
        "total_pose_bank_bytes_max": 8 * 1024 * 1024,
        "actor_count_max": 14,
    }
    base.update(overrides)
    return base


def manifest(mean=12.0, slowest=15.0, texture=40, bank=4883616, actors=13, **overrides):
    data = {
        "passed": True,
        "budget_assessment": {
            "total_pose_bank_bytes": {"measured": bank, "budget": 8 * 1024 * 1024, "within": True},
            "mean_frame_ms": {"measured": mean, "budget": 16.7, "within": None},
            "slowest_window_mean_ms": {"measured": slowest, "budget": 20.0, "within": None},
            "tracked_texture_peak_mib": {"measured": texture, "budget": 64, "within": True},
            "status": "proposed_not_accepted",
        },
        "frame_time": {"mean_frame_ms": mean, "slowest_window_mean_ms": slowest},
        "texture_memory": {"last": {"peak_mib_rounded_down": texture}},
        "total_pose_bank_bytes": bank,
        "actor_count": actors,
        "capture": {"executable_sha256": "c" * 64, "exit_code": 0, "timed_out": False},
    }
    data.update(overrides)
    return data


def make_exe(tmp, data=b"pinned-binary"):
    path = Path(tmp) / "nectar.exe"
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


class BudgetValidationTests(unittest.TestCase):
    def test_accepts_valid_policy(self):
        normalized = pb.validate_budgets(budgets())
        self.assertEqual(normalized["status"], pb.ACCEPTED)
        self.assertEqual(normalized["target_mean_frame_ms_max"], 16.7)

    def test_rejects_bad_schema_and_status(self):
        with self.assertRaises(pb.AcceptanceError):
            pb.validate_budgets(budgets(schema="nope"))
        with self.assertRaises(pb.AcceptanceError):
            pb.validate_budgets(budgets(status="maybe"))

    def test_rejects_missing_or_nonpositive_metric(self):
        bad = budgets()
        del bad["target_mean_frame_ms_max"]
        with self.assertRaises(pb.AcceptanceError):
            pb.validate_budgets(bad)
        with self.assertRaises(pb.AcceptanceError):
            pb.validate_budgets(budgets(total_pose_bank_bytes_max=0))

    def test_rejects_bad_actor_budget(self):
        with self.assertRaises(pb.AcceptanceError):
            pb.validate_budgets(budgets(actor_count_max=0))


class MeasurementTests(unittest.TestCase):
    def test_reads_all_metrics(self):
        measured = pb.measurements_from_manifest(manifest(mean=11.5, slowest=14.5,
                                                          texture=33, bank=100, actors=7))
        self.assertEqual(measured["mean_frame_ms"], 11.5)
        self.assertEqual(measured["slowest_window_mean_ms"], 14.5)
        self.assertEqual(measured["tracked_texture_peak_mib"], 33)
        self.assertEqual(measured["total_pose_bank_bytes"], 100)
        self.assertEqual(measured["actor_count"], 7)

    def test_falls_back_to_frame_time_and_texture_summary(self):
        data = manifest()
        del data["budget_assessment"]
        data["texture_memory"] = {"maximum_reported_mib": 55}
        measured = pb.measurements_from_manifest(data)
        self.assertEqual(measured["mean_frame_ms"], 12.0)
        self.assertEqual(measured["tracked_texture_peak_mib"], 55)

    def test_actor_count_from_nested_scene(self):
        data = manifest()
        del data["actor_count"]
        data["scene"] = {"actor_count": 9}
        self.assertEqual(pb.measurements_from_manifest(data)["actor_count"], 9)


class EvaluateTests(unittest.TestCase):
    def test_within_accepted_budgets_passes(self):
        report = pb.evaluate(manifest(), budgets())
        self.assertEqual(report["status"], qa.PASS)
        self.assertEqual(report["cells"]["frame_budget"]["status"], qa.PASS)
        self.assertEqual(report["cells"]["memory_budget"]["status"], qa.PASS)

    def test_exceeded_frame_budget_fails_frame_cell(self):
        report = pb.evaluate(manifest(mean=25.0), budgets())
        self.assertEqual(report["status"], qa.FAIL)
        self.assertEqual(report["cells"]["frame_budget"]["status"], qa.FAIL)
        self.assertEqual(report["cells"]["memory_budget"]["status"], qa.PASS)

    def test_exceeded_actor_budget_fails_memory_cell(self):
        report = pb.evaluate(manifest(actors=99), budgets())
        self.assertEqual(report["cells"]["memory_budget"]["status"], qa.FAIL)

    def test_missing_measurement_blocks_cell(self):
        data = manifest()
        data["budget_assessment"]["mean_frame_ms"] = {"measured": None, "budget": 16.7, "within": None}
        del data["frame_time"]["mean_frame_ms"]
        report = pb.evaluate(data, budgets())
        self.assertEqual(report["cells"]["frame_budget"]["status"], qa.BLOCKED)
        self.assertEqual(report["cells"]["memory_budget"]["status"], qa.PASS)

    def test_proposed_policy_never_passes(self):
        report = pb.evaluate(manifest(), budgets(status=pb.PROPOSED))
        self.assertEqual(report["status"], qa.BLOCKED)
        for cell in report["cells"].values():
            self.assertEqual(cell["status"], qa.BLOCKED)
        self.assertIn("proposed", report["metrics"]["mean_frame_ms"]["reason"])

    def test_invalid_capture_fails(self):
        data = manifest()
        data["capture"]["exit_code"] = 1
        report = pb.evaluate(data, budgets())
        self.assertEqual(report["status"], qa.FAIL)

    def test_missing_actor_budget_blocks_memory_cell(self):
        policy = budgets()
        del policy["actor_count_max"]
        report = pb.evaluate(manifest(), policy)
        self.assertEqual(report["cells"]["memory_budget"]["status"], qa.BLOCKED)


class RecordTests(unittest.TestCase):
    def _report(self, status=pb.ACCEPTED):
        return pb.evaluate(manifest(), budgets(status=status))

    def test_fixture_records_are_valid(self):
        records = pb.records_from_evaluation(self._report(), pb.Pin(), kind=qa.KIND_FIXTURE,
                                             evidence_paths=["e.json"])
        self.assertEqual([r["scenario"] for r in records], ["frame_budget", "memory_budget"])
        for record in records:
            self.assertEqual(qa.validate_record(record), [])

    def test_natural_requires_a_verified_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe, sha = make_exe(tmp)
            bad = pb.Pin(root_commit="a" * 40, native_commit="b" * 40,
                         executable=str(exe), executable_sha256="0" * 64)
            with self.assertRaises(pb.PinMismatch):
                pb.records_from_evaluation(self._report(), bad, kind=qa.KIND_NATURAL,
                                           evidence_paths=["e.json"])
            good = pb.Pin(root_commit="a" * 40, native_commit="b" * 40,
                          executable=str(exe), executable_sha256=sha)
            records = pb.records_from_evaluation(self._report(), good, kind=qa.KIND_NATURAL,
                                                 evidence_paths=["e.json"])
            self.assertEqual(len(records), 2)

    def test_proposed_policy_records_are_blocked(self):
        records = pb.records_from_evaluation(self._report(status=pb.PROPOSED), pb.Pin(),
                                             kind=qa.KIND_FIXTURE, evidence_paths=["e.json"])
        self.assertTrue(all(record["status"] == qa.BLOCKED for record in records))

    def test_rejects_unknown_kind_and_empty_evidence(self):
        with self.assertRaises(pb.AcceptanceError):
            pb.records_from_evaluation(self._report(), pb.Pin(), kind="magic",
                                       evidence_paths=["e.json"])
        with self.assertRaises(pb.AcceptanceError):
            pb.records_from_evaluation(self._report(), pb.Pin(), kind=qa.KIND_FIXTURE,
                                       evidence_paths=[])


class CliTests(unittest.TestCase):
    def _write(self, tmp, name, data):
        path = Path(tmp) / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_evaluate_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = [(manifest(), 0), (manifest(mean=99.0), 1),
                     (manifest(), 2)]
            policies = [budgets(), budgets(), budgets(status=pb.PROPOSED)]
            for index, ((data, expected), policy) in enumerate(zip(cases, policies)):
                mpath = self._write(tmp, f"m{index}.json", data)
                bpath = self._write(tmp, f"b{index}.json", policy)
                out = Path(tmp) / f"out{index}.json"
                self.assertEqual(pb.main(["evaluate", "--manifest", str(mpath),
                                          "--budgets", str(bpath), "--output", str(out)]),
                                 expected)


if __name__ == "__main__":
    unittest.main()


class IntegrationBudgetGuards(unittest.TestCase):
    def test_missing_exit_cannot_pass(self):
        self.assertEqual(pb.evaluate(manifest(capture={}), budgets())["status"], qa.FAIL)

    def test_invalid_measurements_cannot_pass(self):
        for value in (float("nan"), float("inf"), -1, True, "12"):
            with self.subTest(value=value):
                self.assertEqual(pb.evaluate(manifest(mean=value), budgets())["status"], qa.FAIL)

    def test_nonfinite_budgets_rejected(self):
        for value in (float("nan"), float("inf")):
            with self.assertRaises(pb.AcceptanceError):
                pb.validate_budgets(budgets(target_mean_frame_ms_max=value))
