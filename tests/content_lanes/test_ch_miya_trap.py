"""Focused P1 import tests for the ch_MIYA_trap lane (issue #560).

Lane p2-challenge-ch-miya-trap-p1, generation 2. The P1 module under test is
loaded relative to this file; the sibling P0 adapter is loaded read-only by
the module itself (never edited). Floor blocks below are synthetic harness
inputs (labeled here, never presented as source evidence); the pinned values
they preserve (1 floor, [300.0], squad total 25 at [3][2], sprays 2/2,
ui_index 26) come from the P0 baseline. Hermetic: stdlib only.
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "experimental" / "content_lanes" / "ch_miya_trap.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ch_miya_trap", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_module()


def _manifest(**over):
    roster = [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 25],
              [0, 0, 0], [0, 0, 0], [0, 0, 0]]
    m = {
        "schema": "p2-challenge-ch_miya_trap-p0/1",
        "cave_id": "ch_MIYA_trap",
        "floors": [
            {"unit_pool": "trap_floor1_pool",
             "enemies": [{"source_token": "TrapA"}, {"source_token": "TrapB"}],
             "treasures": [{"treasure_id": "trap_key"}]},
        ],
        "starting_roster": roster,
        "floor_seconds": [300.0],
        "sprays": {"bitter": 2, "spicy": 2},
        "ui_index": 26,
    }
    m.update(over)
    return m


class P1MiyaTrapTests(unittest.TestCase):
    def test_validate_ok(self):
        out = adapter.validate_p1_manifest(_manifest())
        self.assertEqual(out["cave_id"], "ch_MIYA_trap")
        self.assertEqual(out["squad_total"], 25)
        self.assertEqual(len(out["floors"]), 1)
        self.assertEqual(out["floor_seconds"], [300.0])
        self.assertEqual(out["sprays"], {"bitter": 2, "spicy": 2})
        self.assertEqual(out["ui_index"], 26)

    def test_p0_helpers_reused_not_forked(self):
        self.assertEqual(adapter.CAVE_ID, adapter.p0.SOURCE_ID)
        self.assertEqual(adapter.p0.EXPECTED_FLOORS, 1)
        self.assertEqual(adapter.p0.EXPECTED_TOTAL_PIKMIN, 25)

    def test_wrong_cave_rejected(self):
        with self.assertRaises(ValueError):
            adapter.validate_p1_manifest(_manifest(cave_id="ch_OTHER"))

    def test_floor_count_rejected(self):
        m = _manifest()
        m["floors"] = m["floors"] * 2
        with self.assertRaises(ValueError):
            adapter.validate_p1_manifest(m)

    def test_empty_enemies_rejected(self):
        m = _manifest()
        m["floors"][0]["enemies"] = []
        with self.assertRaises(ValueError):
            adapter.validate_p1_manifest(m)

    def test_missing_unit_pool_rejected(self):
        m = _manifest()
        del m["floors"][0]["unit_pool"]
        with self.assertRaises(ValueError):
            adapter.validate_p1_manifest(m)

    def test_wrong_squad_total_rejected(self):
        m = _manifest()
        m["starting_roster"][3][2] = 24
        with self.assertRaises(ValueError):
            adapter.validate_p1_manifest(m)

    def test_missing_pinned_cell_rejected(self):
        m = _manifest()
        m["starting_roster"][3][2] = 0
        m["starting_roster"][0][0] = 25
        with self.assertRaises(ValueError):
            adapter.validate_p1_manifest(m)

    def test_bad_timer_rejected(self):
        with self.assertRaises(ValueError):
            adapter.validate_p1_manifest(_manifest(floor_seconds=[299.0]))

    def test_wrong_sprays_rejected(self):
        with self.assertRaises(ValueError):
            adapter.validate_p1_manifest(_manifest(sprays={"bitter": 0, "spicy": 2}))

    def test_wrong_ui_rejected(self):
        with self.assertRaises(ValueError):
            adapter.validate_p1_manifest(_manifest(ui_index=0))

    def test_stage_run_layout_writes_three_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            result = adapter.stage_run_layout(_manifest(), out)
            self.assertEqual(result["cave_id"], "ch_MIYA_trap")
            self.assertEqual(len(result["files"]), 3)
            for name in ("stage-manifest.json", "p1-input-package.json", "run-plan.json"):
                self.assertIn(name, result["files"])
                self.assertTrue((out / name).is_file())
            package = json.loads((out / "p1-input-package.json").read_text())
            self.assertEqual(package["schema"], "p2-challenge-ch-miya-trap-p1-v1")
            self.assertEqual(package["squad_total"], 25)
            self.assertEqual(package["floor_seconds"], [300.0])

    def test_stage_run_layout_rejects_bad_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                adapter.stage_run_layout({"cave_id": "nope"}, Path(tmp))

    def test_p1_main_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                adapter.p1_main(Path(tmp) / "absent.json", Path(tmp) / "out")

    def test_p1_main_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "manifest.json"
            src.write_text(json.dumps(_manifest()), encoding="utf-8")
            result = adapter.p1_main(src, Path(tmp) / "run")
            self.assertEqual(result["floors"], 1)


if __name__ == "__main__":
    unittest.main()
