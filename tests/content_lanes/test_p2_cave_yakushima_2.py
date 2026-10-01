"""Focused P0 contract tests for the yakushima_2 import adapter (issue #159).

The adapter module is loaded from its file path (no package init is owned by
this lane) and exercised against the real pinned sources: the lane-plan
entry, the inventory cave entry and the decoded catalog entry with its hash
map and unit-pool closure. Positive tests pin actual floor coverage, hashes
and the explicit cap/ambush ledger; negative tests prove fail-closed
boundaries for drifted, truncated, corrupted or missing inputs. Nothing here
generates placements or claims playability.
"""

import copy
import importlib.util
import json
import unittest
from pathlib import Path


def _root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "docs" / "PIKMIN_CONTENT_IMPORT_LANES.json").is_file():
            return parent
    raise AssertionError("Repository root with content plan not found")


ROOT = _root()
CATALOG = Path(r"C:\Users\alari\pikmin-randomizer\output\dsw\l35-out"
               r"\catalog\catalog.json")


def _load_adapter():
    path = ROOT / "experimental" / "content_lanes" / "p2-cave-yakushima_2.py"
    spec = importlib.util.spec_from_file_location("yakushima_2_adapter", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ADAPTER = _load_adapter()


def _inputs():
    plan = json.loads((ROOT / "docs" / "PIKMIN_CONTENT_IMPORT_LANES.json")
                      .read_text(encoding="utf-8"))
    plan_entry = next(lane for lane in plan["lanes"]
                      if lane.get("lane") == "p2-cave-yakushima_2")
    inventory = json.loads((ROOT / "docs" / "PIKMIN2_CONTENT_INVENTORY.json")
                           .read_text(encoding="utf-8"))
    inventory_cave = next(cave for cave in inventory["story_caves"]
                          if cave.get("id") == "yakushima_2")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    catalog_cave = next(cave for cave in catalog["caves"]
                        if cave.get("cave_id") == "yakushima_2")
    return (plan_entry, inventory_cave, catalog_cave,
            catalog["source_sha256"], catalog["unit_pools"],
            catalog["enemy_catalog_sha256"])


class Yakushima2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args = _inputs()

    def test_real_sources_validate(self):
        result = ADAPTER.packet(*self.args)
        self.assertEqual(result["floor_count"], 6)
        self.assertEqual([f["floor"] for f in result["floors"]], [1, 2, 3, 4, 5, 6])
        self.assertEqual(result["generated"], False)
        self.assertEqual(result["placements"], [])
        self.assertEqual(len(result["hashes"]["unit_pools"]), 6)

    def test_cap_and_cargo_ledger_is_explicit(self):
        result = ADAPTER.packet(*self.args)
        ledger = result["ledger"]
        self.assertEqual(ledger["cap_only_tokens"],
                         ["$1Egg", "$1ElecBug", "$1RandPom", "YellowPom"])
        self.assertEqual(ledger["cargo_tokens"],
                         ["KumaChappy_g_futa_sikoku", "OoPanModoki_fue_b"])
        drop = dict(ledger["drop_tokens"])
        self.assertIn("$1ElecBug", drop)
        self.assertIn("$1RandPom", drop)
        self.assertIn("Egg", [t for t in ledger["enemies"]
                              if ledger["enemies"][t]["cap_floors"]])
        self.assertTrue(any("P1 waits" in blocker for blocker in result["blockers"]))

    def test_parameters_preserved_verbatim(self):
        result = ADAPTER.packet(*self.args)
        first = result["floors"][0]
        self.assertEqual(first["parameters"]["f008"],
                         "1_units_hit6x6_yakushima_toy.txt")
        self.assertEqual(first["parameters"]["f009"], "yakushima_2_light.ini")
        self.assertIn("f006", first["parameters"])
        self.assertIn("f016", first["parameters"])

    def test_cli_writes_packet(self):
        import tempfile
        plan_entry, inventory_cave, catalog_cave, hashes, pools, enemy_hash = self.args
        catalog = {"source_sha256": hashes, "unit_pools": pools,
                   "enemy_catalog_sha256": enemy_hash}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {}
            for name, value in (("plan.json", plan_entry),
                                ("inventory.json", inventory_cave),
                                ("cave.json", catalog_cave),
                                ("catalog.json", catalog)):
                path = root / name
                path.write_text(json.dumps(value), encoding="utf-8")
                files[name] = str(path)
            out = root / "packet.json"
            ADAPTER.main(["--plan-entry", files["plan.json"],
                          "--inventory-cave", files["inventory.json"],
                          "--catalog-cave", files["cave.json"],
                          "--catalog", files["catalog.json"],
                          "--output", str(out)])
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(packet["floor_count"], 6)
            self.assertRegex(packet["packet_sha256"], r"[0-9a-f]{64}")

    def test_wrong_lane_rejected(self):
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["lane"] = "p2-cave-yakushima_3"
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, *self.args[1:])

    def test_source_drift_rejected(self):
        _, inventory_cave, catalog_cave, hashes, pools, enemy_hash = self.args
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["source"] = "user/Mukki/mapunits/caveinfo/fake.txt"
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, inventory_cave, catalog_cave,
                            hashes, pools, enemy_hash)
        bad_inventory = copy.deepcopy(inventory_cave)
        bad_inventory["floors"][0]["unit_pool"] = "other.txt"
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_inventory, catalog_cave,
                            hashes, pools, enemy_hash)

    def test_dropped_floor_rejected(self):
        catalog_cave = copy.deepcopy(self.args[2])
        catalog_cave["floors"].pop()
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], self.args[1], catalog_cave,
                            *self.args[3:])

    def test_roster_and_treasure_drift_rejected(self):
        catalog_cave = copy.deepcopy(self.args[2])
        catalog_cave["floors"][0]["enemies"][0]["source_token"] = "KumaChappy"
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], self.args[1], catalog_cave,
                            *self.args[3:])
        catalog_cave = copy.deepcopy(self.args[2])
        catalog_cave["floors"][5]["treasures"].append(
            {"treasure_id": "extra", "source_weight": 10,
             "minimum_count": 1, "selection_weight": 0})
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], self.args[1], catalog_cave,
                            *self.args[3:])

    def test_missing_and_placeholder_hash_rejected(self):
        hashes = dict(self.args[3])
        hashes.pop("user/Mukki/mapunits/caveinfo/yakushima_2.txt")
        with self.assertRaises(ValueError):
            ADAPTER.packet(*self.args[:3], hashes, *self.args[4:])
        hashes = dict(self.args[3])
        hashes["user/Mukki/mapunits/units/1_units_opan_toy.txt"] = "0" * 64
        with self.assertRaises(ValueError):
            ADAPTER.packet(*self.args[:3], hashes, *self.args[4:])

    def test_missing_pool_closure_rejected(self):
        pools = copy.deepcopy(self.args[4])
        pools.pop("2_units_sara_sara2_toy.txt")
        with self.assertRaises(ValueError):
            ADAPTER.packet(*self.args[:3], self.args[3], pools, self.args[5])
        pools = copy.deepcopy(self.args[4])
        pools["2_units_sara_sara2_toy.txt"]["units"] = []
        with self.assertRaises(ValueError):
            ADAPTER.packet(*self.args[:3], self.args[3], pools, self.args[5])

    def test_corrupt_and_missing_files_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "absent.json"
            with self.assertRaises(ValueError):
                ADAPTER.load_json(missing)
            corrupt = Path(directory) / "corrupt.json"
            corrupt.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                ADAPTER.load_json(corrupt)


if __name__ == "__main__":
    unittest.main()
