"""Focused contract tests for the ch_MAT_t_hunter_enemy P0 adapter (issue #543).

Positive pins come from the catalogued baseline (observed values, never
invented): 5 floors, table_order 10, ui_index 10, 7x3 pikmin roster with
5-flower rows at index 1 and 4, legacy_time 400.0 against floor timers
summing to 300.0 (reported discrepancy +100.0), bitter 2 / spicy 3 /
treasure_count 0, source pin dc373436... . Negative tests cover malformed
and missing inputs plus the missing-source prerequisite boundary.
"""
import importlib.util
import json
import unittest
from pathlib import Path

WORKTREE = Path("C:/Users/alari/pikmin-randomizer/output/content-p0-543")
ADAPTER_PATH = WORKTREE / "experimental/content_lanes/p2-challenge-ch_mat_t_hunter_enemy.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("ch_mat_t_hunter_enemy", ADAPTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_adapter()

INVENTORY = json.loads((WORKTREE / "docs/PIKMIN2_CONTENT_INVENTORY.json").read_text(encoding="utf-8"))
LANES = json.loads((WORKTREE / "docs/PIKMIN_CONTENT_IMPORT_LANES.json").read_text(encoding="utf-8"))
LANE_ENTRY = adapter.find_lane_entry(LANES)
STAGE = adapter.find_stage_entry(INVENTORY)
PIN = "dc3734362430697c2a4dbce67b447efe876c60934cb282bc10051a3cdb2f5a82"


class LaneEntryTests(unittest.TestCase):
    def test_finds_lane_entry(self):
        self.assertEqual(LANE_ENTRY["lane"], "p2-challenge-ch_mat_t_hunter_enemy")
        self.assertEqual(LANE_ENTRY["issue"], 543)
        self.assertEqual(LANE_ENTRY["source"], "user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_enemy.txt")

    def test_stage_entry_matches_lane_contract(self):
        self.assertEqual(STAGE["cave_id"], "ch_MAT_t_hunter_enemy")
        self.assertEqual(STAGE["floors"], 5)
        self.assertEqual(STAGE["table_order"], 10)
        self.assertEqual(STAGE["ui_index"], 10)

    def test_missing_entries_fail_closed(self):
        with self.assertRaises(ValueError):
            adapter.find_lane_entry({"lanes": []})
        with self.assertRaises(TypeError):
            adapter.find_lane_entry(None)
        with self.assertRaises(ValueError):
            adapter.find_stage_entry({"challenge": {"stages": []}})
        with self.assertRaises(TypeError):
            adapter.find_stage_entry([])


class StageMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = adapter.validate_stage_metadata(STAGE)

    def test_identity_and_floors(self):
        self.assertEqual(self.meta["floors"], 5)
        self.assertEqual(self.meta["table_order"], 10)
        self.assertEqual(self.meta["ui_index"], 10)

    def test_pikmin_roster_preserved(self):
        self.assertEqual(len(self.meta["pikmin_roster"]), 7)
        for row in self.meta["pikmin_roster"]:
            self.assertEqual(len(row), 3)
        self.assertEqual(self.meta["pikmin_nonzero_rows"],
                         [{"row": 1, "counts": [0, 0, 5]}, {"row": 4, "counts": [0, 0, 5]}])
        self.assertEqual(self.meta["pikmin_total"], 10)

    def test_timers_and_sprays(self):
        self.assertEqual(self.meta["floor_seconds"], [50.0, 75.0, 65.0, 40.0, 70.0])
        self.assertEqual(self.meta["floor_seconds_total"], 300.0)
        self.assertEqual(self.meta["legacy_time"], 400.0)
        self.assertEqual(self.meta["timer_finding"]["legacy_minus_floor_total"], 100.0)
        self.assertEqual(self.meta["bitter_sprays"], 2)
        self.assertEqual(self.meta["spicy_sprays"], 3)
        self.assertEqual(self.meta["treasure_count_field"], 0)

    def test_identity_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            adapter.validate_stage_metadata(dict(STAGE, cave_id="other"))
        with self.assertRaises(ValueError):
            adapter.validate_stage_metadata(dict(STAGE, table_order=11))
        with self.assertRaises(ValueError):
            adapter.validate_stage_metadata(dict(STAGE, ui_index=9))

    def test_roster_shape_failures(self):
        bad6 = dict(STAGE, pikmin_by_native_color_and_maturity=[[0, 0, 0]] * 6)
        with self.assertRaises(ValueError):
            adapter.validate_stage_metadata(bad6)
        badcols = dict(STAGE, pikmin_by_native_color_and_maturity=[[0, 0]] * 7)
        with self.assertRaises(ValueError):
            adapter.validate_stage_metadata(badcols)
        badneg = dict(STAGE, pikmin_by_native_color_and_maturity=[[0, 0, -1]] + [[0, 0, 0]] * 6)
        with self.assertRaises(ValueError):
            adapter.validate_stage_metadata(badneg)

    def test_timer_shape_failures(self):
        with self.assertRaises(ValueError):
            adapter.validate_stage_metadata(dict(STAGE, floor_seconds=[50.0] * 4))
        with self.assertRaises(ValueError):
            adapter.validate_stage_metadata(dict(STAGE, floor_seconds=[50.0] * 4 + [-1.0]))
        with self.assertRaises(ValueError):
            adapter.validate_stage_metadata(dict(STAGE, legacy_time="400"))
        with self.assertRaises(TypeError):
            adapter.validate_stage_metadata(None)


class SourceBoundaryTests(unittest.TestCase):
    def test_pin_format_and_value(self):
        self.assertEqual(adapter.source_pin(LANE_ENTRY), PIN)

    def test_missing_source_reports_exact_prerequisite(self):
        result = adapter.source_prerequisite(LANE_ENTRY, source_root=None)
        self.assertFalse(result["available"])
        self.assertIn("user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_enemy.txt",
                      result["prerequisite"])
        self.assertIn(PIN, result["prerequisite"])
        self.assertIsNone(result["sha256"])

    def test_empty_dir_reports_missing_prerequisite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = adapter.source_prerequisite(LANE_ENTRY, source_root=tmp)
            self.assertFalse(result["available"])

    def test_present_source_hash_checked_against_pin(self):
        import hashlib
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_enemy.txt"
            target.parent.mkdir(parents=True)
            payload = "candidate definition bytes".encode("shift_jis")
            target.write_bytes(payload)
            result = adapter.source_prerequisite(LANE_ENTRY, source_root=tmp)
            self.assertTrue(result["available"])
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertFalse(result["match"])

    def test_present_malformed_source_raises_not_silent(self):
        import tempfile
        enemies = adapter.enemy_universe_from_inventory(INVENTORY)
        treasures = adapter.treasure_universe_from_inventory(INVENTORY)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_enemy.txt"
            target.parent.mkdir(parents=True)
            target.write_bytes("not a cave definition".encode("shift_jis"))
            with self.assertRaises(ValueError):
                adapter.decode_source_text(
                    target.read_bytes().decode("shift_jis"), enemies, treasures)


class AuditPacketTests(unittest.TestCase):
    def test_packet_shape_and_pins(self):
        packet = adapter.audit_stage(STAGE, LANE_ENTRY)
        self.assertEqual(packet["schema"], "p2-challenge-ch_mat_t_hunter_enemy-p0/1")
        self.assertEqual(packet["floors"], 5)
        self.assertEqual(packet["source_sha256_pin"], PIN)
        self.assertFalse(packet["generated"])
        self.assertTrue(packet["limitations"])


class InventoryUniverseTests(unittest.TestCase):
    def test_universes_load(self):
        self.assertGreater(len(adapter.enemy_universe_from_inventory(INVENTORY)), 100)
        self.assertGreater(len(adapter.treasure_universe_from_inventory(INVENTORY)), 100)

    def test_empty_universes_fail_closed(self):
        with self.assertRaises(ValueError):
            adapter.enemy_universe_from_inventory({"enemies": []})
        with self.assertRaises(ValueError):
            adapter.treasure_universe_from_inventory({"catalogs": {}})


if __name__ == "__main__":
    unittest.main()
