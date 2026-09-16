"""Focused P0 contract tests for the ch_NARI_06start3hard adapter (#549).

The adapter module is loaded from its file path (no package init is owned by
this lane) and exercised against the real pinned sources: the lane-plan
entry, the inventory stage row and the 30-stage challenge collection with
its hash pins. Positive tests pin actual stage metadata, timers, populations
and collection integrity; negative tests prove fail-closed boundaries for
drifted, duplicated, corrupted or missing inputs. Nothing here generates
placements, scores or completion claims.
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


def _load_adapter():
    path = ROOT / "experimental" / "content_lanes" / "p2-challenge-ch_nari_06start3hard.py"
    spec = importlib.util.spec_from_file_location("nari06_adapter", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ADAPTER = _load_adapter()


def _inputs():
    plan = json.loads((ROOT / "docs" / "PIKMIN_CONTENT_IMPORT_LANES.json")
                      .read_text(encoding="utf-8"))
    plan_entry = next(lane for lane in plan["lanes"]
                      if lane.get("lane") == "p2-challenge-ch_nari_06start3hard")
    inventory = json.loads((ROOT / "docs" / "PIKMIN2_CONTENT_INVENTORY.json")
                           .read_text(encoding="utf-8"))
    challenge = inventory["challenge"]
    stage = next(row for row in challenge["stages"]
                 if row.get("cave_id") == "ch_NARI_06start3hard")
    return (plan_entry, stage, challenge, inventory["source_sha256"])


class Nari06ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args = _inputs()

    def test_real_sources_validate(self):
        result = ADAPTER.packet(*self.args)
        self.assertEqual(result["details"]["floors"], 3)
        self.assertEqual(result["details"]["floor_seconds"], [100.0, 150.0, 180.0])
        self.assertEqual(result["details"]["ui_index"], 16)
        self.assertEqual(result["details"]["table_order"], 25)
        self.assertEqual(result["generated"], False)
        self.assertEqual(result["placements"], [])
        self.assertEqual(result["collection"]["stages"], 30)

    def test_ledger_conserves_definitions(self):
        result = ADAPTER.packet(*self.args)
        ledger = result["ledger"]
        self.assertEqual(ledger["starting_pikmin_total"], 4)
        self.assertEqual(ledger["starting_populations"],
                         [{"native_color": 1, "maturity": 2, "count": 4}])
        self.assertEqual(ledger["floor_timer_total"], 430.0)
        self.assertEqual((ledger["bitter_sprays"], ledger["spicy_sprays"]), (2, 3))
        self.assertIn("no roster values invented", result["floor_roster_decode"])
        self.assertTrue(any("chal0" in blocker for blocker in result["blockers"]))

    def test_hash_pins_match_plan(self):
        result = ADAPTER.packet(*self.args)
        self.assertEqual(result["collection"]["stage_sha256"],
                         "f64c2a43fa7b70fc7aa500cbd1c95d46e33a14546ac5e56d049b824d53b45d1b")
        self.assertEqual(result["collection"]["stages_txt_sha256"],
                         "59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1")

    def test_cli_writes_packet(self):
        import tempfile
        plan_entry, stage, challenge, hashes = self.args
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {}
            for name, value in (("plan.json", plan_entry),
                                ("stage.json", stage),
                                ("collection.json", {"stages": challenge["stages"],
                                                     "source_sha256": hashes})):
                path = root / name
                path.write_text(json.dumps(value), encoding="utf-8")
                files[name] = str(path)
            out = root / "packet.json"
            ADAPTER.main(["--plan-entry", files["plan.json"],
                          "--inventory-stage", files["stage.json"],
                          "--inventory-collection", files["collection.json"],
                          "--output", str(out)])
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(packet["details"]["floors"], 3)
            self.assertRegex(packet["packet_sha256"], r"[0-9a-f]{64}")

    def test_wrong_lane_rejected(self):
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["lane"] = "p2-challenge-ch_nari_05start3easy"
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, *self.args[1:])

    def test_timer_and_floor_drift_rejected(self):
        _, stage, challenge, hashes = self.args
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["details"]["floor_seconds"] = [100.0, 150.0, 999.0]
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, stage, challenge, hashes)
        bad_stage = copy.deepcopy(stage)
        bad_stage["floors"] = 2
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, challenge, hashes)

    def test_population_and_spray_drift_rejected(self):
        bad_stage = copy.deepcopy(self.args[1])
        bad_stage["pikmin_by_native_color_and_maturity"][1] = [0, 0, 5]
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, *self.args[2:])
        bad_stage = copy.deepcopy(self.args[1])
        bad_stage["spicy_sprays"] = 9
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, *self.args[2:])

    def test_duplicate_row_and_index_collision_rejected(self):
        _, stage, challenge, hashes = self.args
        dup = copy.deepcopy(challenge)
        dup["stages"] = challenge["stages"] + [copy.deepcopy(stage)]
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], stage, dup, hashes)
        collided = copy.deepcopy(challenge)
        collided["stages"][0]["table_order"] = 25
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], stage, collided, hashes)

    def test_missing_and_placeholder_hash_rejected(self):
        hashes = dict(self.args[3])
        hashes.pop("user/Mukki/mapunits/caveinfo/ch_NARI_06start3hard.txt")
        with self.assertRaises(ValueError):
            ADAPTER.packet(*self.args[:3], hashes)
        hashes = dict(self.args[3])
        hashes["user/Matoba/challenge/stages.txt"] = "0" * 64
        with self.assertRaises(ValueError):
            ADAPTER.packet(*self.args[:3], hashes)

    def test_plan_pin_mismatch_rejected(self):
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["source_sha256"] = "a" * 64
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, *self.args[1:])

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