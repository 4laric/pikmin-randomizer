"""Focused tests for the yakushima_3 P0 import adapter (#160).

All decoded records here are either pinned catalog metadata from the
worktree docs (clearly labeled, never presented as fresh retail bytes) or
explicitly SYNTHETIC fixtures exercising the importer boundary (key order,
floor coverage, token classes, inventory mapping). No value below is claimed
as a retail fact; actual user/Mukki/mapunits/caveinfo/yakushima_3.txt bytes
remain the recorded missing prerequisite.
"""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "experimental" / "content_lanes" / "p2-cave-yakushima_3.py"
LANES_JSON = ROOT / "docs" / "PIKMIN_CONTENT_IMPORT_LANES.json"
INVENTORY_JSON = ROOT / "docs" / "PIKMIN2_CONTENT_INVENTORY.json"


def load_adapter():
    spec = importlib.util.spec_from_file_location("p2_cave_yakushima_3", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synth_floor(n, pool="unit_%d.txt", enemies=("MaroFrog",), treasures=("otama",)):
    return {"first": n, "last": n, "unit_pool": pool % n if "%d" in pool else pool,
            "enemy_ids": list(enemies), "treasure_ids": list(treasures)}


SYNTHETIC_FLOORS = [synth_floor(n) for n in range(1, 8)]


def pinned_lane_floors():
    lanes = json.loads(LANES_JSON.read_text(encoding="utf-8"))["lanes"]
    entry = next(l for l in lanes if l["lane"] == "p2-cave-yakushima_3")
    return entry["details"]["floors"]


def pinned_inventory_floors():
    caves = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))["story_caves"]
    entry = next(c for c in caves if c["id"] == "yakushima_3")
    return entry["floors"]


class Yakushima3AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_lane_identity_constants(self):
        self.assertEqual((self.mod.CAVE_ID, self.mod.ISSUE), ("yakushima_3", 160))
        self.assertEqual(self.mod.SOURCE_PATH, "user/Mukki/mapunits/caveinfo/yakushima_3.txt")
        self.assertEqual(self.mod.FLOOR_COUNT, 7)
        self.assertEqual(self.mod.RUNTIME_DEPENDENCIES, (129, 128, 131, 132, 140, 144, 145, 146))

    def test_well_formed_synthetic_floors_decode(self):
        record = self.mod.decode_cave_floors([dict(f) for f in SYNTHETIC_FLOORS])
        self.assertEqual(len(record), 7)
        self.assertEqual([(f["first"], f["last"]) for f in record], [(n, n) for n in range(1, 8)])
        self.assertEqual(record[0]["enemy_ids"], ["MaroFrog"])

    def test_pinned_catalog_floors_decode(self):
        record = self.mod.decode_cave_floors(pinned_lane_floors())
        self.assertEqual(len(record), 7)
        coverage = self.mod.floor_coverage(record)
        self.assertTrue(coverage["contiguous"], coverage)

    def test_pinned_lane_matches_pinned_inventory(self):
        report = self.mod.lane_vs_inventory(pinned_lane_floors(), pinned_inventory_floors())
        self.assertTrue(report["equal"], report["mismatches"][:5])

    def test_floor_count_enforced(self):
        with self.assertRaises(self.mod.CaveDecodeError):
            self.mod.decode_cave_floors(SYNTHETIC_FLOORS[:6])
        with self.assertRaises(self.mod.CaveDecodeError):
            self.mod.decode_cave_floors(SYNTHETIC_FLOORS + [synth_floor(8)])

    def test_noncontiguous_and_extra_floors_rejected(self):
        bad = [dict(f) for f in SYNTHETIC_FLOORS]
        bad[3] = synth_floor(4, enemies=())
        bad[3]["first"] = 5
        with self.assertRaises(self.mod.CaveDecodeError):
            self.mod.decode_cave_floors(bad)
        bad = [dict(f) for f in SYNTHETIC_FLOORS]
        bad[0]["last"] = 2
        with self.assertRaises(self.mod.CaveDecodeError):
            self.mod.decode_cave_floors(bad)

    def test_malformed_rows_rejected(self):
        base = [dict(f) for f in SYNTHETIC_FLOORS]
        cases = []
        missing_key = [dict(f) for f in base]
        del missing_key[2]["unit_pool"]
        cases.append(missing_key)
        extra_key = [dict(f) for f in base]
        extra_key[2] = dict(extra_key[2], timer=99)
        cases.append(extra_key)
        bad_pool = [dict(f) for f in base]
        bad_pool[0]["unit_pool"] = ""
        cases.append(bad_pool)
        traversal = [dict(f) for f in base]
        traversal[0]["unit_pool"] = "../escape.txt"
        cases.append(traversal)
        bad_index = [dict(f) for f in base]
        bad_index[0]["first"] = 0
        cases.append(bad_index)
        bad_tokens = [dict(f) for f in base]
        bad_tokens[0]["enemy_ids"] = "MaroFrog"
        cases.append(bad_tokens)
        empty_token = [dict(f) for f in base]
        empty_token[0]["treasure_ids"] = [""]
        cases.append(empty_token)
        not_a_list = "seven floors"
        cases.append(not_a_list)
        for i, bad in enumerate(cases):
            with self.subTest(case=i):
                with self.assertRaises(self.mod.CaveDecodeError):
                    self.mod.decode_cave_floors(bad)

    def test_token_classes(self):
        cases = {
            "$1Tadpole": ("generator_variant", "$1Tadpole", "$1Tadpole"[1:].partition("$")[2] or "Tadpole"),
            "$1Catfish": ("generator_variant", "$1Catfish", "Catfish"),
            "MaroFrog": ("exact", "MaroFrog", None),
            "Rock": ("exact", "Rock", None),
            "OniKurage_compact_make": ("compound", "OniKurage_compact_make", None),
            "UmiMushi_fue_wide": ("compound", "UmiMushi_fue_wide", None),
            "KareOoinu_s": ("compound", "KareOoinu_s", None),
        }
        for token, (cls, _, base) in cases.items():
            with self.subTest(token=token):
                info = self.mod.classify_token(token)
                self.assertEqual(info["class"], cls)
                self.assertEqual(info["token"], token)
                self.assertEqual(info["base"], base)
        with self.assertRaises(self.mod.CaveDecodeError):
            self.mod.classify_token("$Tadpole")
        with self.assertRaises(self.mod.CaveDecodeError):
            self.mod.classify_token("")

    def test_pinned_token_inventory_shape(self):
        inventory = self.mod.token_inventory(pinned_lane_floors())
        enemies, treasures = inventory["enemy_ids"], inventory["treasure_ids"]
        self.assertIn("$1Tadpole", enemies)
        self.assertEqual(enemies["$1Tadpole"]["class"], "generator_variant")
        self.assertEqual(enemies["$1Tadpole"]["base"], "Tadpole")
        self.assertEqual(enemies["MaroFrog"]["class"], "exact")
        self.assertIn("otama", treasures)
        # Floor attribution is preserved, never aggregated into counts.
        self.assertEqual(sorted(enemies["MaroFrog"]["floors"]), [1, 5, 6])
        self.assertEqual(treasures["otama"]["floors"], [1])

    def test_coverage_report_names_gaps(self):
        floors = [dict(f) for f in SYNTHETIC_FLOORS if f["first"] != 4]
        report = self.mod.floor_coverage(floors)
        self.assertFalse(report["contiguous"])
        self.assertEqual(report["missing"], [(4, 4)])

    def test_lane_vs_inventory_mismatch_reported(self):
        other = [dict(f) for f in pinned_lane_floors()]
        other[0] = dict(other[0], unit_pool="other_pool.txt")
        report = self.mod.lane_vs_inventory(other, pinned_inventory_floors())
        self.assertFalse(report["equal"])
        self.assertTrue(any("floor 1" in m and "unit_pool" in m for m in report["mismatches"]))

    def test_missing_source_boundary(self):
        with self.assertRaises(self.mod.CaveDecodeError) as ctx:
            self.mod.load_source_bytes("user/Mukki/mapunits/caveinfo/yakushima_3.txt")
        message = str(ctx.exception)
        self.assertIn("yakushima_3.txt", message)
        self.assertIn("SHA-256", message)

    def test_resource_closure_marks_missing_source(self):
        closure = self.mod.resource_closure(self.mod.decode_cave_floors(pinned_lane_floors()))
        self.assertEqual(set(closure), {"unit layout files", "enemy spawns", "treasure placements",
                                        "floor timing and schedules", "gate/cap/door seams"})
        self.assertEqual(closure["unit layout files"]["floor_1"]["status"], "missing-source")
        self.assertIn("129", closure["unit layout files"]["floor_1"]["owner"])
        self.assertEqual(closure["floor timing and schedules"]["status"], "unsupported-reference")

    def test_resource_closure_with_inventory(self):
        pools = {f["unit_pool"] for f in pinned_lane_floors()}
        closure = self.mod.resource_closure(
            self.mod.decode_cave_floors(pinned_lane_floors()), file_inventory=pools)
        self.assertEqual(closure["unit layout files"]["floor_7"]["status"], "present")
        self.assertEqual(closure["enemy spawns"]["status"], "present")

    def test_missing_prerequisites_exact(self):
        prereqs = self.mod.missing_prerequisites()
        self.assertEqual(len(prereqs), 4)
        self.assertIn("yakushima_3.txt", prereqs[0])
        self.assertIn("1_units_a_tile.txt", prereqs[1])
        self.assertIn("#129", prereqs[2])

    def test_implementation_packet_shape(self):
        packet = self.mod.implementation_packet(test_log_sha256="0" * 64)
        self.assertEqual(packet["lane"], "p2-cave-yakushima_3")
        self.assertEqual(packet["floors"], 7)
        self.assertIsNone(packet["source_sha256"])
        self.assertIn("no claim of playability", packet["playability"])


if __name__ == "__main__":
    unittest.main()
