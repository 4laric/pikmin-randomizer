"""Focused P0 contract tests for the ch_MAT_route_rover adapter (#561).

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

STAGE_SHA256 = "e03eb33a78526adb13eebd08af453555bc9cd219f6a3e624b28a0771ea12cb79"
STAGES_SHA256 = "59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1"


def _load_adapter():
    path = ROOT / "experimental" / "content_lanes" / "p2-challenge-ch_mat_route_rover.py"
    spec = importlib.util.spec_from_file_location("matrouterover_adapter", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ADAPTER = _load_adapter()


def _inputs():
    plan = json.loads((ROOT / "docs" / "PIKMIN_CONTENT_IMPORT_LANES.json")
                      .read_text(encoding="utf-8"))
    plan_entry = next(lane for lane in plan["lanes"]
                      if lane.get("lane") == "p2-challenge-ch_mat_route_rover")
    inventory = json.loads((ROOT / "docs" / "PIKMIN2_CONTENT_INVENTORY.json")
                           .read_text(encoding="utf-8"))
    challenge = inventory["challenge"]
    stage = next(row for row in challenge["stages"]
                 if row.get("cave_id") == "ch_MAT_route_rover")
    return (plan_entry, stage, challenge, inventory["source_sha256"])


class MatRouteRoverContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args = _inputs()

    def test_real_sources_validate(self):
        result = ADAPTER.packet(*self.args)
        self.assertEqual(result["lane"], "p2-challenge-ch_mat_route_rover")
        self.assertEqual(result["phase"], "P0")
        self.assertEqual(result["identity"]["source_id"], "ch_MAT_route_rover")
        self.assertEqual(result["details"]["floors"], 1)
        self.assertEqual(result["details"]["floor_seconds"], [90.0])
        self.assertEqual(result["details"]["ui_index"], 27)
        self.assertEqual(result["details"]["table_order"], 21)
        self.assertEqual(result["generated"], False)
        self.assertEqual(result["placements"], [])
        self.assertEqual(result["collection"]["stages"], 30)

    def test_ledger_conserves_definitions(self):
        result = ADAPTER.packet(*self.args)
        ledger = result["ledger"]
        self.assertEqual(ledger["starting_pikmin_total"], 60)
        self.assertEqual(ledger["starting_populations"],
                         [{"native_color": 0, "maturity": 2, "count": 20},
                          {"native_color": 1, "maturity": 2, "count": 20},
                          {"native_color": 2, "maturity": 2, "count": 20}])
        self.assertEqual(ledger["floor_timer_total"], 90.0)
        self.assertEqual(ledger["legacy_time"], 300.0)
        self.assertEqual((ledger["bitter_sprays"], ledger["spicy_sprays"]), (2, 2))
        self.assertEqual(ledger["treasure_count_field"], 0)

    def test_floor_coverage_complete(self):
        result = ADAPTER.packet(*self.args)
        coverage = result["floor_coverage"]
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["floors"], 1)
        self.assertEqual(coverage["timer_count"], 1)
        self.assertEqual(coverage["timer_total"], 90.0)
        self.assertEqual(coverage["coverage"], "floor 1..1")

    def test_resource_closure_names_owners(self):
        result = ADAPTER.packet(*self.args)
        closure = result["resource_closure"]
        self.assertEqual(closure["stage definition bytes"]["status"], "pinned-not-read")
        self.assertIn(STAGE_SHA256, closure["stage definition bytes"]["detail"])
        self.assertEqual(closure["stage table ordering"]["status"], "pinned-not-read")
        self.assertIn("#136", closure["starting roster, sprays and timers"]["owner"])
        self.assertEqual(closure["TheKey/hole/geyser, scoring, retry, result semantics"]["status"],
                         "unsupported-reference")

    def test_hash_pins_match_plan(self):
        result = ADAPTER.packet(*self.args)
        self.assertEqual(result["collection"]["stage_sha256"], STAGE_SHA256)
        self.assertEqual(result["collection"]["stages_txt_sha256"], STAGES_SHA256)
        self.assertEqual(result["collection"]["challenge_floor_total"], 59)

    def test_roster_decode_stays_open_and_chal0_not_challenge(self):
        result = ADAPTER.packet(*self.args)
        self.assertIn("no roster values invented", result["floor_roster_decode"])
        self.assertTrue(any("chal0" in blocker for blocker in result["blockers"]))
        self.assertTrue(any("UI index 27" in blocker for blocker in result["blockers"]))

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
            self.assertEqual(packet["details"]["floors"], 1)
            self.assertRegex(packet["packet_sha256"], r"[0-9a-f]{64}")

    def test_wrong_lane_and_label_rejected(self):
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["lane"] = "p2-challenge-ch_mat_flier"
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, *self.args[1:])
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["label"] = "P2 Challenge 27: wrong"
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, *self.args[1:])

    def test_timer_and_floor_drift_rejected(self):
        _, stage, challenge, hashes = self.args
        plan_entry = copy.deepcopy(self.args[0])
        plan_entry["details"]["floor_seconds"] = [999.0]
        with self.assertRaises(ValueError):
            ADAPTER.packet(plan_entry, stage, challenge, hashes)
        bad_stage = copy.deepcopy(stage)
        bad_stage["floors"] = 2
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, challenge, hashes)
        bad_stage = copy.deepcopy(stage)
        bad_stage["floor_seconds"] = []
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, challenge, hashes)

    def test_population_and_spray_drift_rejected(self):
        bad_stage = copy.deepcopy(self.args[1])
        bad_stage["pikmin_by_native_color_and_maturity"][0] = [0, 0, 21]
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, *self.args[2:])
        bad_stage = copy.deepcopy(self.args[1])
        bad_stage["bitter_sprays"] = 9
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, *self.args[2:])
        bad_stage = copy.deepcopy(self.args[1])
        bad_stage["legacy_time"] = 301.0
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], bad_stage, *self.args[2:])

    def test_duplicate_row_and_index_collision_rejected(self):
        _, stage, challenge, hashes = self.args
        dup = copy.deepcopy(challenge)
        dup["stages"] = challenge["stages"] + [copy.deepcopy(stage)]
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], stage, dup, hashes)
        collided = copy.deepcopy(challenge)
        collided["stages"][0]["table_order"] = 21
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], stage, collided, hashes)
        gap = copy.deepcopy(challenge)
        gap["stages"] = gap["stages"][:-1]
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], stage, gap, hashes)

    def test_floor_total_drift_rejected(self):
        _, stage, challenge, hashes = self.args
        broken = copy.deepcopy(challenge)
        broken["stages"][0]["floors"] = broken["stages"][0]["floors"] + 1
        with self.assertRaises(ValueError):
            ADAPTER.packet(self.args[0], stage, broken, hashes)

    def test_missing_and_placeholder_hash_rejected(self):
        hashes = dict(self.args[3])
        hashes.pop("user/Mukki/mapunits/caveinfo/ch_MAT_route_rover.txt")
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