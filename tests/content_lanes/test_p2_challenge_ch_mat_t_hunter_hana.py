"""P0 import-contract tests for ch_MAT_t_hunter_hana (lane p2-challenge, #547).

Synthetic stage and cave malformed and missing-input tests run anywhere;
the live decode test runs only where the local disc image is present. No
placements, no gameplay, no invented values.
"""
import importlib.util
import unittest
from pathlib import Path

_ADAPTER = (Path(__file__).resolve().parent.parent.parent
            / "experimental" / "content_lanes"
            / "p2-challenge-ch_mat_t_hunter_hana.py")


def _load():
    spec = importlib.util.spec_from_file_location(
        "p2_challenge_ch_mat_t_hunter_hana_lane", _ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_lane = _load()
LANE = _lane.LANE
CAVE_ID = _lane.CAVE_ID
SOURCE = _lane.SOURCE
STAGES_TABLE = _lane.STAGES_TABLE
EXPECTED_SOURCE_SHA256 = _lane.EXPECTED_SOURCE_SHA256
parse_stage_record = _lane.parse_stage_record
find_stage_record = _lane.find_stage_record
read_blob = _lane.read_blob
check_contract = _lane.check_contract
check_closure = _lane.check_closure
decode = _lane.decode

ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
DECOMP = Path("C:/Users/alari/pikmin-randomizer/native/pikmin2-research")

ENEMIES = {"Miulin", "Hanachirashi", "Chappy"}
TREASURES = {"gem_one", "map01", "key"}


def stage_block(cave="mycave.txt", counters=None, tail=None):
    counters = ["0"] * 21 if counters is None else counters
    tail = ["400.0", "0", "0", "1", "0", "14", "145.0"] if tail is None else tail
    return ["{", "4", cave] + counters + tail + ["}"]


def stage_table_text(*blocks):
    return "\n".join(["# stage"] + [" ".join(b) for b in blocks])


def cave_dict(floors=1):
    return {"floor_count": floors,
            "floors": [{"first_floor": n, "last_floor": n,
                        "parameters": {"f008": "pool%d.txt" % n},
                        "enemies": [], "treasures": []}
                       for n in range(1, floors + 1)]}


def stage_dict():
    return {"cave_file": "ch_MAT_t_hunter_hana.txt",
            "pikmin": [[0, 0, 0], [0, 0, 40], [0, 0, 0], [0, 0, 20],
                       [0, 0, 20], [0, 0, 0], [0, 0, 0]],
            "time": 400.0, "bitter_sprays": 0, "spicy_sprays": 0,
            "floor_count": 1, "treasure_count": 0, "ui_index": 14,
            "floor_seconds": [145.0]}


class StageRecordTests(unittest.TestCase):
    def test_full_block_decodes(self):
        counters = ["0"] * 21
        counters[5] = "40"
        counters[11] = "20"
        counters[14] = "20"
        block = (["{", "4", "ch_MAT_t_hunter_hana.txt"]
                 + counters
                 + ["400.0", "0", "0", "1", "0", "14", "145.0"]
                 + ["}"])
        record = parse_stage_record(block)
        self.assertEqual(record["cave_file"], "ch_MAT_t_hunter_hana.txt")
        self.assertEqual(record["pikmin"][1], [0, 0, 40])
        self.assertEqual(record["pikmin"][3], [0, 0, 20])
        self.assertEqual(record["pikmin"][4], [0, 0, 20])
        self.assertEqual(record["time"], 400.0)
        self.assertEqual(record["bitter_sprays"], 0)
        self.assertEqual(record["spicy_sprays"], 0)
        self.assertEqual(record["floor_count"], 1)
        self.assertEqual(record["treasure_count"], 0)
        self.assertEqual(record["ui_index"], 14)
        self.assertEqual(record["floor_seconds"], [145.0])

    def test_malformed_blocks_fail_closed(self):
        good = stage_block()
        self.assertEqual(parse_stage_record(good)["ui_index"], 14)
        bad_version = list(good); bad_version[1] = "3"
        for bad in (good[:-1], good[1:], bad_version,
                    ["{", "4", "mycave.txt"] + ["0"] * 22
                    + ["400.0", "0", "0", "1", "0", "14", "145.0", "}"],
                    ["{", "4", "mycave.txt"] + ["0"] * 21
                    + ["400.0", "0", "0", "1", "0", "14", "145.0", "9.0", "}"],
                    ["{", "4", "mycave.txt"] + ["nan"] * 21
                    + ["400.0", "0", "0", "1", "0", "14", "145.0", "}"]):
            with self.subTest(bad=bad[-3:]), self.assertRaises(ValueError):
                parse_stage_record(bad)

    def test_table_lookup(self):
        text = stage_table_text(stage_block("othercave.txt"),
                                stage_block("ch_MAT_t_hunter_hana.txt"))
        record = find_stage_record(text, "ch_MAT_t_hunter_hana")
        self.assertEqual(record["cave_file"], "ch_MAT_t_hunter_hana.txt")
        with self.assertRaises(FileNotFoundError):
            find_stage_record(text, "missing_cave")
        with self.assertRaises(ValueError):
            find_stage_record(text + "\n" + " ".join(stage_block("othercave.txt")),
                              "othercave")
        with self.assertRaises(ValueError):
            find_stage_record("{ 4 mycave.txt", "mycave")


class ContractTests(unittest.TestCase):
    def test_matching_contract_is_empty(self):
        self.assertEqual(check_contract(cave_dict(), stage_dict()), [])

    def test_coverage_gap_is_reported(self):
        cave = cave_dict(0)
        mismatches = check_contract(cave, stage_dict())
        self.assertTrue(any("coverage" in m for m in mismatches))
        self.assertTrue(any("floor count" in m for m in mismatches))

    def test_stage_drift_is_reported(self):
        stage = stage_dict(); stage["ui_index"] = 15
        mismatches = check_contract(cave_dict(), stage)
        self.assertTrue(any("ui_index" in m for m in mismatches))
        stage = stage_dict(); stage["bitter_sprays"] = 1
        mismatches = check_contract(cave_dict(), stage)
        self.assertTrue(any("bitter_sprays" in m for m in mismatches))


class ClosureTests(unittest.TestCase):
    def test_missing_asset_is_a_blocker(self):
        pools = {"p.txt": [{"name": "room_x"}]}
        self.assertEqual(
            check_closure(pools, set()),
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
        with self.assertRaises(FileNotFoundError):
            read_blob({}, ISO, STAGES_TABLE)

    def test_truncated_cave_definition_fails_closed(self):
        with self.assertRaises(ValueError):
            decode({SOURCE: b"{ {c000} 4 1",
                    STAGES_TABLE: " ".join(stage_block("ch_MAT_t_hunter_hana.txt")).encode("ascii")},
                   ENEMIES, TREASURES)

    def test_unknown_enemy_fails_closed(self):
        text = ("{ {c000} 4 1 {_eof} } 1\n"
                "{ {f000} 4 0 {f001} 4 0 {f008} -1 units.txt {_eof} }\n"
                "{ 1 NosuchEnemy 10 1 }\n{ 0 }\n{ 1 gate 5 1 }\n")
        with self.assertRaises(ValueError):
            decode({SOURCE: text.encode("ascii"),
                    STAGES_TABLE: " ".join(stage_block("ch_MAT_t_hunter_hana.txt")).encode("ascii")},
                   ENEMIES, TREASURES)

    def test_lane_identity(self):
        self.assertEqual(LANE, "p2-challenge-ch_mat_t_hunter_hana")
        self.assertEqual(CAVE_ID, "ch_MAT_t_hunter_hana")
        self.assertEqual(SOURCE, "user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_hana.txt")
        self.assertEqual(STAGES_TABLE, "user/Matoba/challenge/stages.txt")
        self.assertEqual(EXPECTED_SOURCE_SHA256,
                         "3bc86de3c581eeccaa8367ba1acbeb4b824c574e7db0ddc3b392f4af6ff8be9a")


@unittest.skipUnless(ISO.is_file(), "local disc image unavailable")
class LiveDecodeTests(unittest.TestCase):
    def test_live_contract_and_closure(self):
        collect, run = _lane.collect, _lane.run
        import tempfile
        collected = collect(ISO, DECOMP)
        self.assertIn("Miulin", collected["enemy_ids"])
        self.assertIn("Hanachirashi", collected["enemy_ids"])
        with tempfile.TemporaryDirectory() as tmp:
            packet = run(ISO, DECOMP, Path(tmp))
        self.assertEqual(packet["cave_id"], "ch_MAT_t_hunter_hana")
        self.assertEqual(packet["floor_count"], 1)
        self.assertTrue(packet["source_sha256_match"])
        self.assertEqual(packet["contract_mismatches"], [])
        self.assertEqual(packet["missing_unit_assets"], [])
        self.assertFalse(packet["generated"])
        self.assertEqual(len(packet["floors"]), 1)
        self.assertEqual([e["enemy_id"] for e in packet["floors"][0]["enemies"]],
                         ["Miulin", "Hanachirashi", "Hanachirashi", "Hanachirashi"])
        self.assertEqual(packet["stage"]["floor_seconds"], [145.0])
        self.assertEqual(packet["stage"]["bitter_sprays"], 0)
        self.assertEqual(packet["stage"]["spicy_sprays"], 0)


if __name__ == "__main__":
    unittest.main()