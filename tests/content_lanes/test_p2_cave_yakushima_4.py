"""Focused P0 tests for the yakushima_4 adapter (issue #161).

Positive pins come from the real retail ISO (decoded via the shared
parsers); the source hash is asserted so drift fails loudly. Negative tests
cover malformed/missing input, the missing-source boundary, and the
catalogued-baseline cross-check.
"""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
            "planning-shards/caves-yakushima/prepared/yakushima4-p0-root")
ADAPTER = ROOT / "experimental/content_lanes/p2-cave-yakushima_4.py"
INVENTORY = ROOT / "docs/PIKMIN2_CONTENT_INVENTORY.json"


def load_adapter():
    spec = importlib.util.spec_from_file_location("y4", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_adapter()
INV = json.loads(INVENTORY.read_text(encoding="utf-8"))

PIN_SHA = "3e3fc04e1131673e22063eb2e395e22e7ac3d4252d2db9223400632696272de0"
PIN_BYTES = 5977
EXPECTED_COUNTS = {1: (8, 2, 0, 2), 2: (8, 2, 1, 0), 3: (9, 2, 1, 4),
                   4: (9, 2, 1, 1), 5: (4, 0, 1, 1)}


def synthetic_parsed(floors):
    return {
        "definition_count": len(floors),
        "floor_count": len(floors),
        "source_path": "user/Mukki/mapunits/caveinfo/yakushima_4.txt",
        "source_bytes": 1,
        "source_sha256": "0" * 64,
        "floors": [
            {
                "first_floor": first,
                "last_floor": first,
                "parameters": {"f008": pool},
                "enemies": [{"enemy_id": "X"}] * enemies,
                "treasures": [{"treasure_id": "t"}] * treasures,
                "gates": [{}] * gates,
                "caps": [{}] * caps,
            }
            for first, pool, enemies, treasures, gates, caps in floors
        ],
    }


class RealDecodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        found = adapter.locate_source(None)
        if not found["available"]:
            raise unittest.SkipTest(found["prerequisite"])
        cls.packet = adapter.audit(None, None, INV)

    def test_source_identity(self):
        self.assertEqual(self.packet["source_bytes"], PIN_BYTES)
        self.assertEqual(self.packet["source_sha256"], PIN_SHA)
        self.assertEqual(self.packet["source_path"],
                         "user/Mukki/mapunits/caveinfo/yakushima_4.txt")

    def test_floor_coverage_and_pools(self):
        self.assertEqual(self.packet["floor_count"], 5)
        self.assertEqual(self.packet["definition_count"], 5)
        self.assertEqual(tuple(self.packet["unit_pools"]),
                         adapter.EXPECTED_POOLS)

    def test_per_floor_counts(self):
        for floor in self.packet["floors"]:
            expected = EXPECTED_COUNTS[floor["first"]]
            observed = (floor["enemies"], floor["treasures"],
                        floor["gates"], floor["caps"])
            self.assertEqual(observed, expected, floor["first"])

    def test_catalogued_baseline_agrees(self):
        self.assertEqual(self.packet["findings"], [])
        self.assertEqual(self.packet["baseline_floor_count"], 5)
        self.assertFalse(self.packet["generated"])

    def test_reuses_shared_importers(self):
        joined = " ".join(self.packet["reused_importers"])
        self.assertIn("pikmin2_cave_catalog.parse", joined)
        self.assertIn("pellet_catalog", joined)

    def test_blockers_published(self):
        joined = " ".join(self.packet["blockers"])
        for token in ("#129", "#132", "#128"):
            self.assertIn(token, joined)


class NegativeTests(unittest.TestCase):
    def test_missing_iso_reports_prerequisite(self):
        found = adapter.locate_source(Path("C:/nonexistent/pikmin2.iso"))
        self.assertFalse(found["available"])
        self.assertIn("yakushima_4.txt", found["prerequisite"])

    def test_decode_missing_iso_raises(self):
        with self.assertRaises(ValueError):
            adapter.decode(Path("C:/nonexistent/pikmin2.iso"))

    def test_build_universes_missing_iso_raises(self):
        with self.assertRaises(ValueError):
            adapter.build_universes(Path("C:/nonexistent/pikmin2.iso"))

    def test_universes_reject_missing_research(self):
        with self.assertRaises(ValueError):
            adapter.build_universes(None, Path("C:/nonexistent/research"))

    def test_inventory_missing_entry_raises(self):
        with self.assertRaises(ValueError):
            adapter.audit(None, None, {"story_caves": []})

    def test_inventory_wrong_shape_raises(self):
        with self.assertRaises(ValueError):
            adapter.audit(None, None, {})

    def test_noncontiguous_floors_rejected(self):
        bad = synthetic_parsed([(1, "2_units_gw_l_conc.txt", 1, 0, 0, 0),
                                (3, "3_units_h_k_pypes_conc.txt", 1, 0, 0, 0)])
        with self.assertRaises(ValueError):
            adapter.audit(parsed=bad)

    def test_pool_mismatch_reported_not_raised(self):
        floors = [(i + 1, adapter.EXPECTED_POOLS[i], 1, 0, 0, 0)
                  for i in range(5)]
        floors[2] = (3, "wrong_pool.txt", 1, 0, 0, 0)
        packet = adapter.audit(parsed=synthetic_parsed(floors))
        self.assertIn("unit pool sequence differs from catalogued baseline",
                      packet["findings"])

    def test_baseline_count_mismatch_reported(self):
        floors = [(i + 1, adapter.EXPECTED_POOLS[i], 1, 0, 0, 0)
                  for i in range(5)]
        packet = adapter.audit(parsed=synthetic_parsed(floors), inventory_doc=INV)
        self.assertTrue(any("enemy count differs" in f
                            for f in packet["findings"]))


if __name__ == "__main__":
    unittest.main()
