"""Focused tests for the overworld course boot-flag adapter (#767).

All course records here are SYNTHETIC fixtures exercising the adapter
boundary (course pin, log reader, gate evaluation). No value is claimed
as engine behavior; the pc_bbft argv wiring is an explicit follow-on.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1] / "experimental" / "pikmin2_overworld_course_boot_flag.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("pikmin2_overworld_course_boot_flag", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BootFlagAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_valid_course_records_pass(self):
        for index, course in enumerate(("tutorial", "forest", "yakushima", "last")):
            record = self.mod.validate_course_record({"course_id": course, "index": index})
            self.assertEqual(record["course_id"], course)

    def test_course_mismatches_rejected(self):
        with self.assertRaises(self.mod.BootFlagError):
            self.mod.validate_course_record({"course_id": "nowhere", "index": 0})
        with self.assertRaises(self.mod.BootFlagError):
            self.mod.validate_course_record({"course_id": "last", "index": 0})
        with self.assertRaises(self.mod.BootFlagError):
            self.mod.validate_course_record("not a dict")
        with self.assertRaises(self.mod.BootFlagError):
            self.mod.default_record("nowhere")

    def test_default_record_matches_pin(self):
        record = self.mod.default_record("forest")
        self.assertEqual((record["course_id"], record["index"]), ("forest", 1))
        self.assertEqual(self.mod.validate_course_record(record)["index"], 1)

    def test_guard_pin_present(self):
        self.assertEqual(self.mod.GUARD_SHA256, "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474")

    def test_utf16_log_file_yields_honest_gates(self):
        body = ("P2_OVERWORLD_BOOT_FLAG_WINDOW width=960 height=540 centred=1\n"
                "P2_OVERWORLD_COURSE_FLAG course=last index=3\n"
                "P2_OVERWORLD_COURSE_REGISTERED course=last\n"
                "P2_OVERWORLD_COURSE_OBSERVED course=last index=3 tick=4\n"
                "PASS OVERWORLD_BOOT_FLAG course=last ticks=30\n")
        log = Path(tempfile.mkdtemp()) / "native.log"
        log.write_bytes(body.encode("utf-16"))
        text = self.mod.read_run_log_file(str(log))
        self.assertIn("P2_OVERWORLD_COURSE_FLAG", text)
        rows = {r["token"]: r for r in self.mod.evaluate_gates(text, exit_code=0)}
        self.assertEqual(rows["window-960x540-centred"]["status"], "PASS")
        self.assertEqual(rows["captain-guard-silent"]["status"], "PASS")
        self.assertEqual(rows["course-flag"]["status"], "PASS")
        self.assertEqual(rows["course-registered"]["status"], "PASS")
        self.assertEqual(rows["guarded-observation"]["status"], "PASS")
        self.assertEqual(rows["exit-status"]["status"], "PASS")

    def test_captain_down_blocks(self):
        text = ("P2_OVERWORLD_BOOT_FLAG_WINDOW width=960 height=540 centred=1\n"
                "P2_FIXTURE_CAPTAIN_DOWN tick=9 hp=0.500 orima_dead=0 dead_state=1 outcome=BLOCKED\n")
        rows = {r["token"]: r for r in self.mod.evaluate_gates(text, exit_code=86)}
        self.assertEqual(rows["captain-guard-silent"]["status"], "BLOCKED")
        self.assertEqual(rows["exit-status"]["status"], "BLOCKED")
        self.assertEqual(rows["course-flag"]["status"], "UNTESTED")

    def test_gates_never_pass_without_markers(self):
        rows = {r["token"]: r for r in self.mod.evaluate_gates("PASS\nwindow\ncourse\n")}
        for token, row in rows.items():
            self.assertNotEqual(row["status"], "PASS", token)
        with self.assertRaises(self.mod.BootFlagError):
            self.mod.evaluate_gates(None)


if __name__ == "__main__":
    unittest.main()
