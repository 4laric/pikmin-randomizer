"""Focused tests for the forest_1 P1 floor-1 staging adapter (#154).

All decoded values here are an explicit SYNTHETIC packet fixture that
exercises the adapter boundary (schema, floor coverage, floor-1 decode,
invariants, sidecar). No value is claimed as a retail fact; the real P0
packet is the pinned input used by the run.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ADAPTER = Path(__file__).resolve().parents[2] / "experimental" / "content_lanes" / "p2-cave-forest_1_p1.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("p2_cave_forest_1_p1", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_packet():
    def floor(n, pool, units, enemies, treasures):
        return {"first": n, "last": n, "unit_pool": pool, "unit_names": units,
                "enemies": enemies, "treasures": treasures, "gates": [], "cap_count": 0}
    return {
        "schema": 1, "lane": "shard-caves-forest-forest1-p0", "cave_id": "forest_1",
        "source": "user/Mukki/mapunits/caveinfo/forest_1.txt",
        "source_sha256": "a" * 64,
        "unit_pool_sha256": {"1_units_cent3_tsuchi.txt": "b" * 64},
        "floor_count": 5,
        "floors": [
            floor(1, "1_units_cent3_tsuchi.txt", ["room_cent3_4_tsuchi", "way3_tsuchi"],
                  [{"enemy_id": "UjiB", "carried_treasure": None, "minimum_count": 4,
                    "selection_weight": 0, "target_count": None},
                   {"enemy_id": "Clover", "carried_treasure": None, "minimum_count": None,
                    "selection_weight": None, "target_count": 4}],
                  ["juji_key_fc"]),
            floor(2, "1_units_cent2_tsuchi.txt", ["room_cent2_4_tsuchi"], [], []),
            floor(3, "2_ABE_norhiba_blkhiba_tsuchi.txt", ["room_north_1_hiba_tsuchi"], [], []),
            floor(4, "2_ABE_mid1_nor3_tsuchi.txt", ["room_mid_tsuchi"], [], []),
            floor(5, "1_units_boss_tsuchi.txt", ["room_boss_tsuchi"], [], []),
        ],
    }


class Forest1P1AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def write(self, packet):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "packet.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        self.addCleanup(directory.cleanup)
        return path

    def test_well_formed_packet_produces_plan(self):
        result = self.mod.write_plan(self.write(synthetic_packet()), Path(tempfile.mkdtemp()))
        plan = result["plan"]
        self.assertEqual(plan["cave_id"], "forest_1")
        self.assertEqual(plan["unit_pool"], "1_units_cent3_tsuchi.txt")
        self.assertEqual(plan["generated"], False)
        self.assertEqual(plan["placements"], [])
        self.assertEqual(plan["problems"] if "problems" in plan else result["problems"], [])
        self.assertIn("juji_key_fc", plan["treasures"])
        self.assertIn("room_cent3_4_tsuchi/arc.szs", plan["unit_assets"])

    def test_sidecar_is_line_oriented_and_terminated(self):
        result = self.mod.write_plan(self.write(synthetic_packet()), Path(tempfile.mkdtemp()))
        sidecar = Path(result["sidecar"]).read_text(encoding="utf-8")
        self.assertTrue(sidecar.startswith("P2_FOREST1_P1_1\n"))
        self.assertTrue(sidecar.rstrip().endswith("end"))
        self.assertIn("floor 1", sidecar)
        self.assertIn("unit room_cent3_4_tsuchi", sidecar)
        self.assertIn("enemy UjiB min=4 weight=0 target=-", sidecar)
        self.assertIn("enemy Clover min=- weight=- target=4", sidecar)

    def test_missing_packet_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            self.mod.load_packet(Path(tempfile.mkdtemp()) / "absent.json")

    def test_bad_schema_and_cave_rejected(self):
        packet = synthetic_packet(); packet["schema"] = 2
        with self.assertRaises(ValueError):
            self.mod.load_packet(self.write(packet))
        packet = synthetic_packet(); packet["cave_id"] = "forest_2"
        with self.assertRaises(ValueError):
            self.mod.load_packet(self.write(packet))

    def test_incomplete_floor_coverage_rejected(self):
        packet = synthetic_packet(); packet["floors"] = packet["floors"][:4]
        with self.assertRaises(ValueError) as ctx:
            self.mod.load_packet(self.write(packet))
        self.assertIn("floor coverage", str(ctx.exception))

    def test_malformed_floor_one_range_rejected(self):
        packet = synthetic_packet(); packet["floors"][0]["last"] = 2
        with self.assertRaises(ValueError):
            self.mod.staging_plan(packet)

    def test_enemy_row_without_count_rejected(self):
        packet = synthetic_packet()
        packet["floors"][0]["enemies"].append({"enemy_id": "Tukushi", "carried_treasure": None,
                                               "minimum_count": None, "selection_weight": None,
                                               "target_count": None})
        plan = self.mod.staging_plan(packet)
        problems = self.mod.validate_plan(plan)
        self.assertTrue(any("neither minimum nor target" in p for p in problems))

    def test_missing_unit_asset_detected_when_inventory_supplied(self):
        plan = self.mod.staging_plan(synthetic_packet())
        problems = self.mod.validate_plan(plan, unit_assets={"room_cent3_4_tsuchi/arc.szs"})
        self.assertTrue(any("missing unit asset" in p for p in problems))
        self.assertFalse(self.mod.validate_plan(plan, unit_assets=set(plan["unit_assets"])))

    def test_no_units_rejected(self):
        packet = synthetic_packet(); packet["floors"][0]["unit_names"] = []
        with self.assertRaises(ValueError):
            self.mod.staging_plan(packet)

    def test_plan_is_deterministic(self):
        first = self.mod.staging_plan(synthetic_packet())
        second = self.mod.staging_plan(synthetic_packet())
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
