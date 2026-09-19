"""P0 import-contract tests for forest_2 (lane p2-cave-forest_2, #155).

Synthetic malformed/missing/contract-drift tests run anywhere; the live
decode test runs only where the local disc image is present. No
placements, no gameplay, no invented values.
"""
import importlib.util
import unittest
from pathlib import Path

# The reserved lane filename carries dashes, so it cannot be imported by
# statement; load it by path. Its own imports stay absolute (worktree root
# is on sys.path under `py -m pytest`).
_ADAPTER = (Path(__file__).resolve().parent.parent.parent
            / "experimental" / "content_lanes" / "p2-cave-forest_2.py")


def _load():
    spec = importlib.util.spec_from_file_location("p2_cave_forest_2_lane", _ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_lane = _load()
EXPECTED_FLOORS = _lane.EXPECTED_FLOORS
LANE = _lane.LANE
SOURCE = _lane.SOURCE
check_closure = _lane.check_closure
check_contract = _lane.check_contract
decode = _lane.decode
expected_roster = _lane.expected_roster
read_blob = _lane.read_blob
split_cargo_token = _lane.split_cargo_token

ISO = Path(r"C:\Users\alari\Downloads\PIKMIN2 for GAMECUBE.iso")
DECOMP = Path(r"C:\Users\alari\pikmin-randomizer\native\pikmin2-research")

ENEMIES = {"UjiA", "UjiB", "Tank", "SnakeCrow", "Egg", "KareOoinu_s"}
TREASURES = {"fire_helmet", "radar_b", "gem_one"}


def cave_text(pool="units.txt", enemy="$2SnakeCrow_radar_b 21 1"):
    return ("{ {c000} 4 1 {_eof} } 1\n"
            "{ {f000} 4 0 {f001} 4 0 {f008} -1 " + pool + " {_eof} }\n"
            "{ 1 " + enemy + " }\n{ 0 }\n{ 1 gate 5 1 }\n")


def decoded_floor(first=1, last=1, pool="units.txt", enemies=(), treasures=()):
    return {"first_floor": first, "last_floor": last,
            "parameters": {"f008": pool},
            "enemies": [{"enemy_id": e, "carried_treasure": c} for e, c in enemies],
            "treasures": [{"treasure_id": t} for t in treasures]}


class CargoTokenTests(unittest.TestCase):
    def test_cargo_suffix_splits_only_on_known_treasure(self):
        self.assertEqual(split_cargo_token("SnakeCrow_radar_b", TREASURES),
                         ("SnakeCrow", "radar_b"))
        self.assertEqual(split_cargo_token("KareOoinu_s", TREASURES),
                         ("KareOoinu_s", None))
        self.assertEqual(split_cargo_token("UjiA", TREASURES), ("UjiA", None))

    def test_expected_roster_matches_live_floor5_shape(self):
        entry = [e for e in EXPECTED_FLOORS if e["first"] == 5][0]
        enemies, carried, treasures = expected_roster(entry, TREASURES)
        self.assertEqual(enemies, ["Egg", "KareOoinu_l", "KareOoinu_s", "SnakeCrow", "Zenmai"])
        self.assertEqual(carried, ["radar_b"])
        self.assertEqual(treasures, [])


class ContractTests(unittest.TestCase):
    def test_empty_cave_reports_coverage(self):
        cave = {"floors": [], "floor_count": 0}
        mismatches = check_contract(cave, TREASURES)
        self.assertTrue(any("coverage" in m for m in mismatches))

    def test_pool_drift_is_a_mismatch_not_a_raise(self):
        cave = {"floors": [decoded_floor(pool="other.txt",
                                         enemies=[("UjiB", None), ("UjiA", None),
                                                  ("UjiA", None), ("UjiA", None)],
                                         treasures=["fire_helmet"])],
                "floor_count": 1}
        mismatches = check_contract(cave, TREASURES)
        self.assertEqual(len(mismatches), 6)  # coverage + pool + 4 missing floors
        self.assertTrue(any("pool other.txt" in m for m in mismatches))

    def test_enemy_drift_is_reported(self):
        cave = {"floors": [decoded_floor(pool="2_ABE_nor1_cen2_metal.txt",
                                         enemies=[("UjiB", None)],
                                         treasures=["fire_helmet"])],
                "floor_count": 1}
        mismatches = check_contract(cave, TREASURES)
        self.assertTrue(any("enemies" in m for m in mismatches))


class ClosureTests(unittest.TestCase):
    def test_missing_asset_is_a_blocker(self):
        pools = {"p.txt": [{"name": "room_x"}]}
        self.assertEqual(check_closure(pools, set()),
                         ["user/Mukki/mapunits/arc/room_x/arc.szs (via pool p.txt)",
                          "user/Mukki/mapunits/arc/room_x/texts.szs (via pool p.txt)"])

    def test_complete_closure_is_empty(self):
        pools = {"p.txt": [{"name": "room_x"}]}
        names = {"user/Mukki/mapunits/arc/room_x/arc.szs",
                 "user/Mukki/mapunits/arc/room_x/texts.szs"}
        self.assertEqual(check_closure(pools, names), [])


class InputBoundaryTests(unittest.TestCase):
    def test_missing_catalog_entry_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            read_blob({}, ISO, SOURCE)

    def test_truncated_cave_definition_fails_closed(self):
        with self.assertRaises(ValueError):
            decode({SOURCE: b"{ {c000} 4 1"}, ENEMIES, TREASURES)

    def test_unknown_enemy_fails_closed(self):
        with self.assertRaises(ValueError):
            decode({SOURCE: cave_text().encode("ascii")}, {"UjiA"}, TREASURES)

    def test_lane_identity(self):
        self.assertEqual(LANE, "p2-cave-forest_2")
        self.assertEqual(SOURCE, "user/Mukki/mapunits/caveinfo/forest_2.txt")
        self.assertEqual(len(EXPECTED_FLOORS), 5)


@unittest.skipUnless(ISO.is_file(), "local disc image unavailable")
class LiveDecodeTests(unittest.TestCase):
    def test_live_contract_and_closure(self):
        collect, run = _lane.collect, _lane.run
        import tempfile
        collected = collect(ISO, DECOMP)
        self.assertIn("SnakeCrow", collected["enemy_ids"])
        self.assertIn("radar_b", collected["treasure_ids"])
        with tempfile.TemporaryDirectory() as tmp:
            packet = run(ISO, DECOMP, Path(tmp))
        self.assertEqual(packet["cave_id"], "forest_2")
        self.assertEqual(packet["floor_count"], 5)
        self.assertEqual(packet["contract_mismatches"], [])
        self.assertEqual(packet["missing_unit_assets"], [])
        self.assertFalse(packet["generated"])
        self.assertEqual(len(packet["floors"]), 5)
        self.assertTrue(all(f["unit_names"] for f in packet["floors"]))


if __name__ == "__main__":
    unittest.main()
