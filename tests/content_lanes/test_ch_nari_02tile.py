"""Focused tests for the ch_NARI_02tile P1 runtime import (#537).

Unit matrix uses synthetic contracts; one integration test drives the real P0
adapter and source file when present (skipped otherwise). All fail-closed
behaviour is asserted; no runtime boot is performed here.
"""
import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from experimental.content_lanes import ch_nari_02tile as p1

SOURCE = Path(os.environ.get("P1_NARI02TILE_SOURCE", str(REPO / "output/workflow/content-expansion/p2-challenge-ch_nari_02tile/ch_NARI_02tile.txt")))


def good_contract():
    return {
        "schema": 1,
        "cave_id": "ch_NARI_02tile",
        "source": "user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt",
        "source_sha256": "d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6",
        "ui_index": 4,
        "floor_coverage": [0, 1],
        "floor_manifest": [
            {"floor": 0, "unit_pool": "a", "enemy_rows": 1, "treasure_rows": 0,
             "gate_rows": 0, "cap_rows": 0},
            {"floor": 1, "unit_pool": "b", "enemy_rows": 2, "treasure_rows": 1,
             "gate_rows": 0, "cap_rows": 0},
        ],
        "timer_roster_spray_baseline": {
            "floor_seconds": [200.0, 150.0],
            "bitter_sprays": 0,
            "spicy_sprays": 5,
            "ui_index": 4,
        },
    }


class ManifestValidationTests(unittest.TestCase):
    def test_valid_manifest_accepted(self):
        valid = p1.validate_manifest(good_contract())
        self.assertEqual(valid["cave_id"], "ch_NARI_02tile")
        self.assertEqual(valid["ui_index"], 4)
        self.assertEqual(len(valid["floors"]), 2)
        self.assertEqual(valid["timer_roster_spray_baseline"]["floor_seconds"], [200.0, 150.0])

    def test_wrong_cave_rejected(self):
        bad = good_contract(); bad["cave_id"] = "ch_NARI_01kusachi"
        with self.assertRaises(p1.P1Error):
            p1.validate_manifest(bad)

    def test_floor_count_rejected(self):
        bad = good_contract(); bad["floor_coverage"] = [0]
        bad["floor_manifest"] = bad["floor_manifest"][:1]
        with self.assertRaises(p1.P1Error):
            p1.validate_manifest(bad)

    def test_ui_index_rejected(self):
        bad = good_contract(); bad["ui_index"] = 7
        with self.assertRaises(p1.P1Error):
            p1.validate_manifest(bad)

    def test_timer_baseline_rejected(self):
        bad = good_contract()
        bad["timer_roster_spray_baseline"] = dict(bad["timer_roster_spray_baseline"])
        bad["timer_roster_spray_baseline"]["floor_seconds"] = [100.0, 100.0]
        with self.assertRaises(p1.P1Error):
            p1.validate_manifest(bad)

    def test_spray_baseline_rejected(self):
        bad = good_contract()
        bad["timer_roster_spray_baseline"] = dict(bad["timer_roster_spray_baseline"])
        bad["timer_roster_spray_baseline"]["spicy_sprays"] = 9
        with self.assertRaises(p1.P1Error):
            p1.validate_manifest(bad)

    def test_missing_source_rejected(self):
        with self.assertRaises(Exception):
            p1.run_import(str(REPO), str(REPO / "no-such-file.txt"), str(REPO / "output/x"))


class LayoutTests(unittest.TestCase):
    def test_layout_files_and_hashes_deterministic(self):
        import tempfile
        valid = p1.validate_manifest(good_contract())
        with tempfile.TemporaryDirectory() as tmp:
            first = p1.stage_run_layout(valid, tmp)
            self.assertEqual(sorted(first), ["p1-input-package.json", "run-plan.json", "stage-manifest.json"])
            second = p1.stage_run_layout(valid, tmp)
            self.assertEqual(first, second)
            manifest = json.loads((Path(tmp) / "stage-manifest.json").read_text())
            self.assertEqual(manifest["ui_index"], 4)
            plan = json.loads((Path(tmp) / "run-plan.json").read_text())
            self.assertIn("blocker", plan)
            self.assertIn("P2CHALLENGE_STAGE_ENTRY", plan["expected_markers"])
            package = json.loads((Path(tmp) / "p1-input-package.json").read_text())
            self.assertIn("pc_port/pc_p2_challenge_mode.cpp", package["host_mode"]["files"])

    def test_host_mode_pins_shape(self):
        pins = p1.host_mode_pins()
        self.assertEqual(pins["commit"], "ada6bda4")
        self.assertEqual(set(pins["files"]), {"pc_port/pc_p2_challenge_mode.h", "pc_port/pc_p2_challenge_mode.cpp"})
        self.assertTrue(all(len(v) == 64 for v in pins["files"].values()))
        self.assertTrue(any("ui_index" in a for a in pins["api"]))


class RealSourceIntegrationTest(unittest.TestCase):
    def test_real_p0_decode_and_layout_or_skip(self):
        if not SOURCE.is_file():
            self.skipTest("P0 source file not present")
        adapter = p1.load_p0_adapter(str(REPO))
        self.assertEqual(adapter.CAVE_ID, "ch_NARI_02tile")
        scan, contract = p1.decode_stage(adapter, str(SOURCE))
        valid = p1.validate_manifest(contract)
        self.assertEqual(valid["ui_index"], 4)
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            hashes = p1.stage_run_layout(valid, tmp)
            self.assertEqual(len(hashes), 3)


if __name__ == "__main__":
    unittest.main()