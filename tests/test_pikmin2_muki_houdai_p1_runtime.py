"""Focused tests for the ch_MUKI_houdai P1 runtime adapter (#735).

All stage records here are SYNTHETIC fixtures exercising the adapter
boundary (catalog pin, missing-source reporting, run layout, log reader).
No value is claimed as a retail fact; legal source bytes remain the
recorded missing prerequisite.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ADAPTER = Path(__file__).resolve().parents[1] / "experimental" / "pikmin2_muki_houdai_p1_runtime.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("pikmin2_muki_houdai_p1_runtime", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def good_record(mod=None):
    return {
        "stage_id": "ch_MUKI_houdai", "table_order": 24, "ui_index": 8,
        "floor_seconds": [100.0, 150.0], "sprays": {"bitter": 1, "spicy": 1},
        "starting_population": {"colors": 5, "per_color": 10, "maturity": "leaf"},
        "treasure_count": 0, "floors": 2,
    }


class HoudaiP1AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_valid_pin_record_passes(self):
        record = self.mod.validate_stage_record(good_record())
        self.assertEqual(record["stage_id"], "ch_MUKI_houdai")

    def test_pin_mismatches_rejected(self):
        cases = [("table_order", 25), ("ui_index", 9), ("treasure_count", 1),
                 ("floors", 3), ("stage_id", "ch_MUKI_king")]
        for key, value in cases:
            record = good_record(); record[key] = value
            with self.subTest(key=key):
                with self.assertRaises(self.mod.P1Error):
                    self.mod.validate_stage_record(record)
        record = good_record(); record["floor_seconds"] = [100.0, 120.0]
        with self.assertRaises(self.mod.P1Error):
            self.mod.validate_stage_record(record)
        record = good_record(); record["sprays"] = {"bitter": 2, "spicy": 1}
        with self.assertRaises(self.mod.P1Error):
            self.mod.validate_stage_record(record)
        with self.assertRaises(self.mod.P1Error):
            self.mod.validate_stage_record("not a dict")

    def test_default_record_marks_source_absent(self):
        record = self.mod.default_record()
        self.assertIsNone(record["source_bytes"])
        self.assertIn("ch_MUKI_houdai.txt", record["missing_prerequisite"])
        self.assertEqual(self.mod.validate_stage_record(record)["ui_index"], 8)

    def test_run_layout_is_hashed_and_complete(self):
        out = Path(tempfile.mkdtemp()) / "run"
        paths = self.mod.stage_run_layout(good_record(), out)
        self.assertEqual(set(Path(p).name for p in paths), {"stage-manifest.json", "p1-input-package.json", "run-plan.json"})
        for path in paths:
            self.assertTrue(Path(path).is_file())
        manifest = json.loads((out / "stage-manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["source_bytes_present"])
        package = json.loads((out / "p1-input-package.json").read_text(encoding="utf-8"))
        self.assertEqual((package["window"]["width"], package["window"]["height"]), (960, 540))
        self.assertEqual(package["captain_guard"]["sha256"], self.mod.GUARD_SHA256)

    def test_existing_output_refused(self):
        out = Path(tempfile.mkdtemp())
        self.mod.stage_run_layout(good_record(), out / "run")
        with self.assertRaises(FileExistsError):
            self.mod.stage_run_layout(good_record(), out / "run")

    def test_log_reader_boot_down_and_empty(self):
        result = self.mod.read_run_log("P2CHALLENGE_STAGE_ENTRY ... P2_ROOM_READY ...")
        self.assertIn("P2CHALLENGE_STAGE_ENTRY", result["observed"])
        self.assertTrue(result["verdict"].startswith("BOOT observed"))
        self.assertFalse(result["captain_down"])
        result = self.mod.read_run_log("P2_FIXTURE_CAPTAIN_DOWN ...")
        self.assertTrue(result["captain_down"])
        self.assertTrue(result["verdict"].startswith("BLOCKED"))
        result = self.mod.read_run_log("nothing here")
        self.assertEqual(result["observed"], [])
        self.assertTrue(result["verdict"].startswith("UNTESTED"))
        with self.assertRaises(self.mod.P1Error):
            self.mod.read_run_log(None)

    def test_host_mode_pins_present(self):
        self.assertEqual(self.mod.HOST_MODE_COMMIT, "ada6bda4")
        self.assertEqual(len(self.mod.HOST_MODE_FILES), 2)


if __name__ == "__main__":
    unittest.main()


class HoudaiP1GateTests(unittest.TestCase):
    """Gate evaluation against real fixture log bytes (utf-16 wide output)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_utf16_log_file_yields_honest_gates(self):
        body = ("P2_MUKI_HOUDAI_P1_WINDOW width=960 height=540 centered=1\n"
                "P2CHALLENGE_STAGE_ENTRY stage=ch_MUKI_houdai table=0 tick=2\n"
                "P2_ROOM_READY squad=20 tick=4\n"
                "PASS MUKI_HOUDAI_P1_BOOT\n")
        log = Path(tempfile.mkdtemp()) / "native.log"
        log.write_bytes(body.encode("utf-16"))
        text = self.mod.read_run_log_file(str(log))
        self.assertIn("P2_MUKI_HOUDAI_P1_WINDOW", text)
        rows = {r["token"]: r for r in self.mod.evaluate_gates(text, exit_code=0)}
        self.assertEqual(rows["window-960x540-centred"]["status"], "PASS")
        self.assertEqual(rows["captain-guard-silent"]["status"], "PASS")
        self.assertEqual(rows["squad-ready"]["status"], "PASS")
        self.assertEqual(rows["stage-boot"]["status"], "PASS")
        self.assertEqual(rows["challenge-arena"]["status"], "PASS")
        self.assertEqual(rows["exit-status"]["status"], "PASS")
        self.assertIn("P2CHALLENGE_STAGE_ENTRY", rows["stage-boot"]["evidence"])

    def test_gates_never_pass_without_markers(self):
        rows = {r["token"]: r for r in self.mod.evaluate_gates("PASS\nwindow\n")}
        for token, row in rows.items():
            self.assertNotEqual(row["status"], "PASS", token)
        with self.assertRaises(self.mod.P1Error):
            self.mod.evaluate_gates(None)

