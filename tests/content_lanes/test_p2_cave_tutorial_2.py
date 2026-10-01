"""Focused contract tests for the tutorial_2 P0 adapter (issue #152).

Positive pins come from the catalogued baseline (observed values, never
invented): 9 floors covering 1..9, 8 distinct unit pools with floors 4/8
sharing one, 79 enemy tokens (68 exact, 8 $-variants, 2 resolved carriers,
1 unknown-cargo), 13 distinct treasures all present in the pellet catalog.
Negative tests cover malformed/missing inputs and the missing-source
prerequisite boundary.
"""
import importlib.util
import json
import unittest
from pathlib import Path

WORKTREE = Path("C:/Users/alari/pikmin-randomizer/output/content-p0-152")
ADAPTER_PATH = WORKTREE / "experimental/content_lanes/p2-cave-tutorial_2.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("p2_cave_tutorial_2", ADAPTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_adapter()

INVENTORY = json.loads((WORKTREE / "docs/PIKMIN2_CONTENT_INVENTORY.json").read_text(encoding="utf-8"))
LANES = json.loads((WORKTREE / "docs/PIKMIN_CONTENT_IMPORT_LANES.json").read_text(encoding="utf-8"))
ENTRY = next(c for c in INVENTORY["story_caves"] if c["id"] == "tutorial_2")
ENEMIES = adapter.enemy_universe_from_inventory(INVENTORY)
TREASURES = adapter.treasure_universe_from_inventory(INVENTORY)


class LaneEntryTests(unittest.TestCase):
    def test_finds_lane_entry(self):
        entry = adapter.find_lane_entry(LANES)
        self.assertEqual(entry["lane"], "p2-cave-tutorial_2")
        self.assertEqual(entry["issue"], 152)
        self.assertEqual(entry["source"], "user/Mukki/mapunits/caveinfo/tutorial_2.txt")

    def test_missing_lane_entry_fails_closed(self):
        with self.assertRaises(ValueError):
            adapter.find_lane_entry({"lanes": []})
        with self.assertRaises(TypeError):
            adapter.find_lane_entry([])

    def test_missing_cave_entry_fails_closed(self):
        with self.assertRaises(ValueError):
            adapter.find_cave_entry({"story_caves": []})
        with self.assertRaises(TypeError):
            adapter.find_cave_entry(None)


class FloorCoverageTests(unittest.TestCase):
    def test_nine_floor_contiguous_coverage(self):
        floors = adapter.floor_coverage(ENTRY)
        self.assertEqual(len(floors), 9)
        self.assertEqual([f["first"] for f in floors], list(range(1, 10)))

    def test_floor_gap_fails_closed(self):
        bad = {"floors": [dict(f) for f in ENTRY["floors"][:8]]}
        with self.assertRaises(ValueError):
            adapter.floor_coverage(bad)

    def test_overlapping_range_fails_closed(self):
        floors = [dict(f) for f in ENTRY["floors"]]
        floors[1] = dict(floors[1], first=1, last=2)
        with self.assertRaises(ValueError):
            adapter.floor_coverage({"floors": floors})

    def test_empty_pool_fails_closed(self):
        floors = [dict(f) for f in ENTRY["floors"]]
        floors[0] = dict(floors[0], unit_pool="")
        with self.assertRaises(ValueError):
            adapter.floor_coverage({"floors": floors})

    def test_missing_floors_fails_closed(self):
        with self.assertRaises(ValueError):
            adapter.floor_coverage({})
        with self.assertRaises(TypeError):
            adapter.floor_coverage(None)


class TokenClassificationTests(unittest.TestCase):
    def test_exact_token(self):
        result = adapter.classify_token("YellowChappy", ENEMIES, TREASURES)
        self.assertEqual(result["kind"], "exact")
        self.assertEqual(result["base"], "YellowChappy")
        self.assertEqual(result["drop"], 0)

    def test_generator_variants(self):
        for token, drop in (("$Bomb", 1), ("$BombOtakara", 1)):
            result = adapter.classify_token(token, ENEMIES, TREASURES)
            self.assertEqual(result["kind"], "generator_variant", token)
            self.assertEqual(result["drop"], drop, token)

    def test_resolved_carriers(self):
        for token, base, carried in (("Fkabuto_bolt", "Fkabuto", "bolt"),
                                     ("FminiHoudai_sinkukan_b", "FminiHoudai", "sinkukan_b")):
            result = adapter.classify_token(token, ENEMIES, TREASURES)
            self.assertEqual(result["kind"], "carrier", token)
            self.assertEqual(result["base"], base, token)
            self.assertEqual(result["carried"], carried, token)

    def test_unknown_cargo_flagged_not_raised(self):
        result = adapter.classify_token("Houdai_light_a", ENEMIES, TREASURES)
        self.assertEqual(result["kind"], "unknown_cargo")
        self.assertEqual(result["base"], "Houdai")

    def test_unknown_enemy_flagged_not_raised(self):
        result = adapter.classify_token("NotAnEnemy", ENEMIES, TREASURES)
        self.assertEqual(result["kind"], "unknown_enemy")

    def test_malformed_tokens(self):
        for token in ("", None, 42, "has space", "$", "_bolt"):
            result = adapter.classify_token(token, ENEMIES, TREASURES)
            self.assertEqual(result["kind"], "malformed", repr(token))


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = adapter.audit_entry(ENTRY, ENEMIES, TREASURES)

    def test_floor_count_and_pools(self):
        self.assertEqual(self.report["floor_count"], 9)
        self.assertEqual(len(self.report["unit_pools_ordered"]), 9)
        self.assertEqual(len(self.report["unit_pools_distinct"]), 8)
        self.assertEqual(self.report["unit_pools_duplicated"], ["1_units_hit224_metal.txt"])
        self.assertFalse(self.report["generated"])

    def test_token_kind_totals(self):
        kinds = self.report["token_kinds"]
        self.assertEqual(sum(kinds.values()), 79)
        self.assertEqual(kinds.get("exact"), 68)
        self.assertEqual(kinds.get("generator_variant"), 8)
        self.assertEqual(kinds.get("carrier"), 2)
        self.assertEqual(kinds.get("unknown_cargo"), 1)

    def test_treasure_closure(self):
        self.assertEqual(len(self.report["distinct_treasure_tokens"]), 13)
        floors_missing = [f for f in self.report["floors"] if f["missing_treasure"]]
        self.assertEqual(floors_missing, [])

    def test_unresolved_lists_only_unknown_cargo(self):
        self.assertEqual(len(self.report["unresolved"]), 1)
        only = self.report["unresolved"][0]
        self.assertEqual((only["floor"], only["token"], only["kind"]),
                         (9, "Houdai_light_a", "unknown_cargo"))

    def test_distinct_enemy_tokens(self):
        self.assertEqual(len(self.report["distinct_enemy_tokens"]), 25)


class SourceBoundaryTests(unittest.TestCase):
    def test_missing_source_reports_exact_prerequisite(self):
        result = adapter.source_prerequisite(source_root=None)
        self.assertFalse(result["available"])
        self.assertIn("user/Mukki/mapunits/caveinfo/tutorial_2.txt", result["prerequisite"])
        self.assertIn("pikmin2_cave_catalog", result["prerequisite"])

    def test_empty_dir_reports_missing_prerequisite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = adapter.source_prerequisite(source_root=tmp)
            self.assertFalse(result["available"])
            self.assertIsNone(result["sha256"])

    def test_present_malformed_source_raises_not_silent(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "user/Mukki/mapunits/caveinfo/tutorial_2.txt"
            target.parent.mkdir(parents=True)
            target.write_bytes("not a cave definition".encode("shift_jis"))
            available = adapter.source_prerequisite(source_root=tmp)
            self.assertTrue(available["available"])
            self.assertEqual(len(available["sha256"]), 64)
            with self.assertRaises(ValueError):
                adapter.decode_source_text(
                    target.read_bytes().decode("shift_jis"), ENEMIES, TREASURES)


class InventoryUniverseTests(unittest.TestCase):
    def test_enemy_universe_nonempty(self):
        self.assertGreater(len(ENEMIES), 100)

    def test_treasure_universe_covers_floor_treasures(self):
        self.assertGreater(len(TREASURES), 100)

    def test_empty_universes_fail_closed(self):
        with self.assertRaises(ValueError):
            adapter.enemy_universe_from_inventory({"enemies": []})
        with self.assertRaises(ValueError):
            adapter.treasure_universe_from_inventory({"catalogs": {}})

    def test_inventory_hash_report_shape(self):
        result = adapter.inventory_hashes(
            WORKTREE / "docs/PIKMIN2_CONTENT_INVENTORY.json", LANES)
        self.assertEqual(len(result["observed"]), 64)
        self.assertIsInstance(result["match"], bool)

    def test_inventory_hash_matches_pin(self):
        result = adapter.inventory_hashes(
            WORKTREE / "docs/PIKMIN2_CONTENT_INVENTORY.json", LANES)
        self.assertTrue(result["match"], result)
        self.assertEqual(result["pinned"], result["observed"])


if __name__ == "__main__":
    unittest.main()
