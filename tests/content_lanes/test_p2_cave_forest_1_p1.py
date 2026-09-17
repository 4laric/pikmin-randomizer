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


CONFORMING_SIDECAR = """P2_CAVE_GENERATE_1
pool 1_units_cent3_tsuchi.txt 2
unit 0 room_cent3_4_tsuchi 100.0 100.0 0
unit 1 way3_tsuchi 50.0 50.0 0
rooms 1
room 0 0 0 0.0 0.0 0.0
doors 0
links 0
spawns 2
spawn UjiB 4
spawn Clover 4
anchor hole
"""


class GenerateConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def packet(self):
        path = Path(tempfile.mkdtemp()) / "packet.json"
        path.write_text(json.dumps(synthetic_packet()), encoding="utf-8")
        return path

    def test_conforming_sidecar_passes_with_staged_notes(self):
        packet = self.mod.load_packet(self.packet())
        problems, notes = self.mod.check_generate_against_floor_one(packet, CONFORMING_SIDECAR)
        self.assertEqual(problems, [])
        self.assertTrue(any("STAGED room topology" in n for n in notes))
        self.assertTrue(any("STAGED anchor kind: hole" in n for n in notes))
        self.assertTrue(any("STAGED unit dimensions" in n for n in notes))

    def test_unknown_unit_and_spawn_fail_closed(self):
        bad = CONFORMING_SIDECAR.replace("way3_tsuchi", "invented_unit")
        packet = self.mod.load_packet(self.packet())
        problems, _ = self.mod.check_generate_against_floor_one(packet, bad)
        self.assertTrue(any("STAGED-EXTRA unit" in p for p in problems))
        bad2 = CONFORMING_SIDECAR.replace("spawn Clover 4", "spawn Invented 4")
        problems, _ = self.mod.check_generate_against_floor_one(packet, bad2)
        self.assertTrue(any("not in floor-1 roster" in p for p in problems))

    def test_below_minimum_and_pool_mismatch_fail(self):
        bad = CONFORMING_SIDECAR.replace("spawn UjiB 4", "spawn UjiB 1")
        packet = self.mod.load_packet(self.packet())
        problems, _ = self.mod.check_generate_against_floor_one(packet, bad)
        self.assertTrue(any("below roster minimum" in p for p in problems))
        bad2 = CONFORMING_SIDECAR.replace("1_units_cent3_tsuchi.txt 2", "1_units_cent2_tsuchi.txt 2")
        problems, _ = self.mod.check_generate_against_floor_one(packet, bad2)
        self.assertTrue(any("pool mismatch" in p for p in problems))

    def test_malformed_sidecar_and_bad_anchor_rejected(self):
        packet = self.mod.load_packet(self.packet())
        problems, _ = self.mod.check_generate_against_floor_one(packet, "P2_CAVE_GENERATE_1\npool")
        self.assertTrue(any("malformed sidecar" in p for p in problems))
        bad = CONFORMING_SIDECAR.replace("anchor hole", "anchor volcano")
        problems, _ = self.mod.check_generate_against_floor_one(packet, bad)
        self.assertTrue(any("malformed sidecar" in p for p in problems))
        with self.assertRaises(ValueError):
            self.mod.parse_generate_sidecar(None)


SYNTHETIC_UNIT_DEFS = [
    {"name": "room_cent3_4_tsuchi", "cells": [100, 100], "kind": 1,
     "doors": [{"id": 0, "direction": 0, "links": [{"door": 0, "distance": 10.5}]}]},
    {"name": "way3_tsuchi", "cells": [50, 50], "kind": 0, "doors": []},
]


class GenerateSidecarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def packet(self):
        path = Path(tempfile.mkdtemp()) / "packet.json"
        path.write_text(json.dumps(synthetic_packet()), encoding="utf-8")
        return path

    def test_generated_sidecar_round_trips_through_conformance(self):
        packet = self.mod.load_packet(self.packet())
        text = self.mod.generate_sidecar(packet, SYNTHETIC_UNIT_DEFS, anchor="hole")
        parsed = self.mod.parse_generate_sidecar(text)
        self.assertEqual(parsed["pool"], "1_units_cent3_tsuchi.txt")
        self.assertEqual(len(parsed["units"]), 2)
        self.assertEqual(parsed["anchor"], "hole")
        self.assertEqual([s["id"] for s in parsed["spawns"]], ["UjiB"])
        problems, notes = self.mod.check_generate_against_floor_one(packet, text)
        self.assertEqual(problems, [])
        self.assertTrue(any("STAGED room topology" in n for n in notes))

    def test_missing_unit_defs_and_unknown_unit_rejected(self):
        packet = self.mod.load_packet(self.packet())
        with self.assertRaises(ValueError):
            self.mod.generate_sidecar(packet, [])
        with self.assertRaises(ValueError):
            self.mod.generate_sidecar(packet, [{"name": "invented", "cells": [10, 10], "doors": []}])

    def test_bad_cells_and_anchor_rejected(self):
        packet = self.mod.load_packet(self.packet())
        with self.assertRaises(ValueError):
            self.mod.generate_sidecar(packet, [{"name": "room_cent3_4_tsuchi", "cells": [0, 10], "doors": []}])
        with self.assertRaises(ValueError):
            self.mod.generate_sidecar(packet, SYNTHETIC_UNIT_DEFS, anchor="volcano")

    def test_write_sidecar_emits_file_and_hash(self):
        out = Path(tempfile.mkdtemp())
        result = self.mod.write_generate_sidecar(self.packet(), SYNTHETIC_UNIT_DEFS, out)
        self.assertTrue(Path(result["path"]).is_file())
        self.assertEqual(len(result["sha256"]), 64)
        self.assertEqual(result["spawns"], 1)
        self.assertTrue(any("target deviation: Clover" in n for n in result["notes"]))
