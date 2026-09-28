"""Focused fail-closed tests for the ch_NARI_03toy P1 runtime slice (#746)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental import pikmin2_nari_03toy_p1_runtime as p1


BLOCKED_LOG = chr(10).join([
    "P2_NARI_03TOY_P1_WINDOW width=960 height=540 centered=1",
    "BLOCKED NARI_03TOY_P1_BOOT engine-table-row-pending stage=ch_NARI_03toy",
]) + chr(10)

GOOD_LOG = chr(10).join([
    "P2_NARI_03TOY_P1_WINDOW width=960 height=540 centered=1",
    "P2CHALLENGE_STAGE_ENTRY stage=ch_NARI_03toy table=0 tick=12",
    "P2_ROOM_READY squad=100 tick=40",
    "PASS NARI_03TOY_P1_BOOT",
]) + chr(10)


class Nari03ToyP1Tests(unittest.TestCase):
    def test_resolve_stage_gap(self):
        record = p1.resolve_stage()
        self.assertEqual(record["cave_id"], "ch_NARI_03toy")
        self.assertEqual(record["floors"], 2)
        self.assertEqual(record["ui_index"], 5)

    def test_validate_good_record(self):
        record = p1.resolve_stage()
        self.assertEqual(p1.validate_stage_record(record)["cave_id"], "ch_NARI_03toy")

    def test_validate_rejects_wrong_stage(self):
        record = p1.resolve_stage()
        record["cave_id"] = "ch_NARI_02tile"
        with self.assertRaises(p1.P1Error):
            p1.validate_stage_record(record)

    def test_validate_rejects_pin_drift(self):
        record = p1.resolve_stage()
        record["floors"] = 3
        with self.assertRaises(p1.P1Error):
            p1.validate_stage_record(record)

    def test_unknown_stage_refused(self):
        module = p1.load_gap_select()
        with self.assertRaises(Exception):
            module.select_stage_extended("ch_NARI_99nope")

    def test_stage_layout_files_and_hashes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            files, digest = p1.stage_run_layout(tmp)
            self.assertEqual(set(files), {"stage-manifest.json", "p1-input-package.json", "run-plan.json"})
            package = json.loads((Path(tmp) / "p1-input-package.json").read_text(encoding="utf-8"))
            ids = [g["id"] for g in package["generators"]]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertTrue(all(len(g["position"]) == 3 for g in package["generators"]))
            self.assertFalse(package["observed"])
            manifest = json.loads((Path(tmp) / "stage-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["control"]["cave_id"], "ch_NARI_01kusachi")
            self.assertIn("pending", manifest["native_engine_row"])

    def test_blocked_log_gates(self):
        gates = p1.evaluate_gates(p1.parse_run_log(BLOCKED_LOG))
        self.assertTrue(all(status == "BLOCKED" for status, _ in gates.values()))

    def test_good_log_identity(self):
        gates = p1.evaluate_gates(p1.parse_run_log(GOOD_LOG))
        self.assertEqual(gates["identity_spawn"][0], "PASS")
        self.assertEqual(gates["movement_animation"][0], "UNTESTED")

    def test_captain_down_blocks(self):
        gates = p1.evaluate_gates(p1.parse_run_log(GOOD_LOG + "P2_FIXTURE_CAPTAIN_DOWN tick=1" + chr(10)))
        self.assertTrue(all(status == "BLOCKED" for status, _ in gates.values()))

    def test_injected_blocks(self):
        gates = p1.evaluate_gates(p1.parse_run_log(GOOD_LOG + "mHealth=0" + chr(10)))
        self.assertTrue(all(status == "BLOCKED" for status, _ in gates.values()))


if __name__ == "__main__":
    unittest.main()
