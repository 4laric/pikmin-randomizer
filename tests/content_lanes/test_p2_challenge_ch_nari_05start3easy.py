"""Focused P0 tests for the ch_NARI_05start3easy import adapter (issue #548).

Synthetic inputs only (no disc image): malformed stage blocks, contract
divergences, missing pools and unreadable sources must fail closed with
ContractMismatch, never with invented values.
"""
import importlib.util as _importlib_util
import json
import unittest
from pathlib import Path

# Reserved filename contains dashes; load the exact reserved path under alias.
_ADAPTER_PATH = (Path(__file__).resolve().parents[2] / "experimental" / "content_lanes"
                 / "p2-challenge-ch_nari_05start3easy.py")
_SPEC = _importlib_util.spec_from_file_location("p2_challenge_ch_nari_05start3easy", _ADAPTER_PATH)
_adapter = _importlib_util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_adapter)

ContractMismatch = _adapter.ContractMismatch
decode_stage = _adapter.decode_stage
lane_contract = _adapter.lane_contract
parse_stage_block = _adapter.parse_stage_block
read_iso_file = _adapter.read_iso_file
split_stage_blocks = _adapter.split_stage_blocks
verify_cave_contract = _adapter.verify_cave_contract
verify_closure = _adapter.verify_closure
verify_stage = _adapter.verify_stage

LANES = "C:/Users/alari/pikmin-randomizer/docs/PIKMIN_CONTENT_IMPORT_LANES.json"

BLOCK = """{
\t4 \t# version
\tch_NARI_05start3easy.txt
\t# PikiCounter
\t1 \t# col0 happa0
\t0 \t# col0 happa1
\t0 \t# col0 happa2
\t1 \t# col1 happa0
\t0 \t# col1 happa1
\t0 \t# col1 happa2
\t1 \t# col2 happa0
\t0 \t# col2 happa1
\t0 \t# col2 happa2
\t0 \t# col3 happa0
\t0 \t# col3 happa1
\t0 \t# col3 happa2
\t0 \t# col4 happa0
\t0 \t# col4 happa1
\t0 \t# col4 happa2
\t0 \t# col5 happa0
\t0 \t# col5 happa1
\t0 \t# col5 happa2
\t0 \t# col6 happa0
\t0 \t# col6 happa1
\t0 \t# col6 happa2
\t400.000000 \t# time
\t1 \t# dope black
\t2 \t# dope red
\t2 \t# floor num
\t0 \t# otakara num
\t15 \t# 2d index
\t120.000000 \t# 1""" + "\u968e\u306e\u79d2\u6570" + """
\t80.000000 \t# 2""" + "\u968e\u306e\u79d2\u6570" + """
}"""


def stage():
    return dict(cave_file="ch_NARI_05start3easy.txt",
                pikmin=[[1, 0, 0], [1, 0, 0], [1, 0, 0],
                        [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                legacy_time=400.0, bitter_sprays=1, spicy_sprays=2, floors=2,
                treasure_count=0, ui_index=15, floor_seconds=[120.0, 80.0])


def contract():
    return dict(lane="p2-challenge-ch_nari_05start3easy", source_id="ch_NARI_05start3easy",
                cave_path="user/Mukki/mapunits/caveinfo/ch_NARI_05start3easy.txt",
                floors=2, pikmin=[[1, 0, 0], [1, 0, 0], [1, 0, 0],
                                  [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                legacy_time=400.0, bitter_sprays=1, spicy_sprays=2,
                treasure_count=0, ui_index=15, floor_seconds=[120.0, 80.0])


def cave():
    return dict(
        cave_id="ch_NARI_05start3easy",
        source="user/Mukki/mapunits/caveinfo/ch_NARI_05start3easy.txt",
        floor_count=2, definition_count=2, floors=[
            dict(first_floor=1, last_floor=1,
                 parameters={"f008": "2_MAT_cent_north_tsuchi.txt"},
                 enemies=[dict(source_token="RandPom", enemy_id="RandPom",
                               carried_treasure=None, source_weight=20, placement_type=1)],
                 treasures=[dict(treasure_id="key", source_weight=10)],
                 gates=[], caps=[dict(empty=True)]),
            dict(first_floor=2, last_floor=2,
                 parameters={"f008": "2_MAT_cent_north_tsuchi.txt"},
                 enemies=[dict(source_token="Wtank_key", enemy_id="Wtank",
                               carried_treasure="key", source_weight=10, placement_type=1)],
                 treasures=[dict(treasure_id="dia_a_green", source_weight=10)],
                 gates=[], caps=[])])


def catalog():
    return {"unit_pools": {
        "2_MAT_cent_north_tsuchi.txt": {"source": "user/Mukki/mapunits/units/2_MAT_cent_north_tsuchi.txt",
                                       "units": [{"name": "room_cent"}, {"name": "way3_tsuchi"}]}}}


class Start3EasyContractTests(unittest.TestCase):
    def test_stage_block_parses(self):
        parsed = parse_stage_block(BLOCK)
        self.assertEqual(parsed["cave_file"], "ch_NARI_05start3easy.txt")
        self.assertEqual(parsed["pikmin"][:3], [[1, 0, 0]] * 3)
        self.assertEqual(parsed["floor_seconds"], [120.0, 80.0])
        self.assertEqual(parsed["bitter_sprays"], 1)
        self.assertEqual(parsed["spicy_sprays"], 2)
        report = verify_stage(parsed, contract())
        self.assertEqual(report["starting_pikmin"], 3)

    def test_matching_cave_verifies(self):
        coverage = verify_cave_contract(cave(), contract())
        self.assertEqual([row["unit_pool"] for row in coverage],
                         ["2_MAT_cent_north_tsuchi.txt"] * 2)
        closure, pool_hashes = verify_closure(cave(), catalog())
        self.assertEqual(closure[1]["units"], ["room_cent", "way3_tsuchi"])
        self.assertEqual(pool_hashes, {})
        self.assertTrue(all(row.get("provenance") == "baseline" for row in closure))

    def test_real_lanes_document_loads(self):
        loaded = lane_contract(LANES)
        self.assertEqual(loaded["floors"], 2)
        self.assertEqual(loaded["floor_seconds"], [120.0, 80.0])
        self.assertEqual(loaded["ui_index"], 15)
        self.assertEqual(loaded["legacy_time"], 400.0)

    def test_stage_block_problems_fail_closed(self):
        with self.assertRaises(ContractMismatch):
            split_stage_blocks("no blocks here")
        with self.assertRaises(ContractMismatch):
            parse_stage_block(BLOCK + "trailing")
        with self.assertRaises(ContractMismatch):
            parse_stage_block(BLOCK.replace("{", "", 1))
        with self.assertRaises(ContractMismatch):
            verify_stage(stage() | {"ui_index": 16}, contract())
        with self.assertRaises(ContractMismatch):
            verify_stage(stage() | {"floor_seconds": [120.0, 90.0]}, contract())
        with self.assertRaises(ContractMismatch):
            verify_stage(stage() | {"spicy_sprays": 0}, contract())

    def test_cave_contract_problems_fail_closed(self):
        mutated = cave()
        mutated["floors"][1]["last_floor"] = 3
        with self.assertRaises(ContractMismatch):
            verify_cave_contract(mutated, contract())
        mutated = cave()
        mutated["cave_id"] = "ch_MUKI_king"
        with self.assertRaises(ContractMismatch):
            verify_cave_contract(mutated, contract())
        with self.assertRaises(ContractMismatch):
            verify_closure(cave(), {"unit_pools": {}})

    def test_contract_document_problems_fail_closed(self):
        with self.assertRaises(ContractMismatch):
            lane_contract("C:/nonexistent-lanes.json")
        with self.assertRaises(ContractMismatch):
            lane_contract(LANES, lane="p2-challenge-no-such-lane")

    def test_unreadable_sources_fail_closed(self):
        with self.assertRaises(ContractMismatch):
            read_iso_file("C:/nonexistent.iso", "user/Mukki/mapunits/caveinfo/ch_NARI_05start3easy.txt")
        with self.assertRaises(ContractMismatch):
            decode_stage("C:/nonexistent.iso")


_FLOOR_MANIFEST = _adapter.floor_manifest
_CONTENT_SIDECAR = _adapter.content_sidecar
_GENERATE_SIDECAR = _adapter.generate_sidecar
_PREVIEW_RECORD = _adapter.preview_record
_STAGE_RUN_LAYOUT = _adapter.stage_run_layout
_STAGE_MANIFEST_RECORD = _adapter.stage_manifest_record
_PARSE_RUN_MARKERS = _adapter.parse_run_markers
_VERIFY_RECEIPT = _adapter.verify_receipt
_P1_WINDOW = _adapter.P1_WINDOW
_RUN_LAYOUT_FILES = _adapter.RUN_LAYOUT_FILES


def p1_cave():
    return dict(
        cave_id="ch_NARI_05start3easy", floor_count=2, floors=[
            dict(first_floor=1, last_floor=1,
                 parameters={"f008": "2_MAT_cent_north_tsuchi.txt", "f007": "0"},
                 enemies=[dict(source_token="RandPom", enemy_id="RandPom"),
                          dict(source_token="RandPom", enemy_id="RandPom"),
                          dict(source_token="Egg", enemy_id="Egg")],
                 treasures=[dict(treasure_id="key", source_weight=10)],
                 gates=[], caps=[]),
            dict(first_floor=2, last_floor=2,
                 parameters={"f008": "2_MAT_cent_north_tsuchi.txt", "f007": "1"},
                 enemies=[dict(source_token="Wtank_key", enemy_id="Wtank")],
                 treasures=[dict(treasure_id="dia_a_green", source_weight=10)],
                 gates=[], caps=[])])


def p1_closure():
    return [dict(floor=1, unit_pool="2_MAT_cent_north_tsuchi.txt",
                 units=["room_cent_4_tsuchi", "way3_tsuchi"]),
            dict(floor=2, unit_pool="2_MAT_cent_north_tsuchi.txt",
                 units=["room_cent_4_tsuchi", "way3_tsuchi"])]


LOG_GOOD = "\n".join([
    "[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)",
    "P2_CHALLENGE_CONTENT_SELECTED cave=ch_NARI_05start3easy floor=1",
    "P2_CHALLENGE_CONTENT_SPAWN_COVERED id=RandPom count=2",
    "P2_CHALLENGE_CONTENT_READY cave=ch_NARI_05start3easy floor=1 squad=3",
    "P2_CHALLENGE_CONTENT_LIVE squad=3 actors=1 tick=2",
    "P2_ROOM_GROUND x=-85.0 z=0.0 y=0.000",
    "P2_PLACEMENT_PROBE actors=1 evidence_slots=1",
    "PASS P2_CHALLENGE_CONTENT_RUN content=1",
])
LOG_CAPTAIN = LOG_GOOD + "\nP2_FIXTURE_CAPTAIN_DOWN tick=4 hp=0.500 outcome=BLOCKED"
LOG_NO_COLLISION = "\n".join(line for line in LOG_GOOD.splitlines()
                             if "P2_ROOM_GROUND" not in line)


class P1StagingTests(unittest.TestCase):
    def test_floor_manifest_aggregates_and_sorts(self):
        manifest = _FLOOR_MANIFEST(p1_cave(), 0)
        self.assertEqual(manifest["unit_pool"], "2_MAT_cent_north_tsuchi.txt")
        self.assertEqual(manifest["anchor"], "hole")
        self.assertEqual(manifest["spawns"],
                         [{"id": "Egg", "count": 1}, {"id": "RandPom", "count": 2},
                          {"id": "key", "count": 1}])

    def test_anchor_maps_geyser(self):
        self.assertEqual(_FLOOR_MANIFEST(p1_cave(), 1)["anchor"], "geyser")

    def test_content_sidecar_exact(self):
        manifest = _FLOOR_MANIFEST(p1_cave(), 0)
        self.assertEqual(_CONTENT_SIDECAR(manifest),
                         "P2_CHALLENGE_CONTENT_1\n"
                         "stage ch_NARI_05start3easy 1\n"
                         "pool 2_MAT_cent_north_tsuchi.txt\n"
                         "spawn Egg 1\nspawn RandPom 2\nspawn key 1\n"
                         "anchor hole\n")
        self.assertEqual(_GENERATE_SIDECAR(manifest),
                         "spawn Egg 1\nspawn RandPom 2\nspawn key 1\n")

    def test_preview_record_room_choice(self):
        self.assertEqual(_PREVIEW_RECORD(["way3_tsuchi", "room_cent_4_tsuchi"])["room"],
                         "room_cent_4_tsuchi")
        self.assertEqual(_PREVIEW_RECORD(["way3_tsuchi"])["room"], "way3_tsuchi")
        self.assertTrue(_PREVIEW_RECORD(["room_cent_4_tsuchi"])["experimental"])
        with self.assertRaises(ContractMismatch):
            _PREVIEW_RECORD([])

    def test_stage_run_layout_writes_and_hashes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            layout = _STAGE_RUN_LAYOUT(p1_cave(), stage(), "a" * 64, "b" * 64,
                                       p1_closure(), tmp, write=True)
            self.assertEqual(layout["files"], sorted(_RUN_LAYOUT_FILES))
            self.assertEqual(layout["window"], _P1_WINDOW)
            self.assertEqual(layout["boot_floor"]["floor"], 1)
            for name, digest in layout["sha256"].items():
                self.assertEqual(len(digest), 64)
            stored = Path(tmp, "p2-challenge-content.txt").read_text(encoding="utf-8")
            self.assertIn("stage ch_NARI_05start3easy 1", stored)
            record = json.loads(Path(tmp, "stage-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(record["ui_index"], 15)
            self.assertEqual(record["floor_seconds"], [120.0, 80.0])
            self.assertEqual(record["legacy_time"], 400.0)
            self.assertEqual(record["starting_pikmin"], 3)
            self.assertEqual(record["preview_window"], "960x540")
            self.assertEqual(record["floors"][0]["unit_pool"],
                             "2_MAT_cent_north_tsuchi.txt")

    def test_stage_run_layout_fails_closed(self):
        with self.assertRaises(ContractMismatch):
            _STAGE_RUN_LAYOUT(dict(floors=[]), stage(), "a" * 64, "b" * 64, [], None, write=False)
        bad = p1_cave()
        bad["floors"][0]["parameters"].pop("f008")
        with self.assertRaises(ContractMismatch):
            _FLOOR_MANIFEST(bad, 0)
        bad = p1_cave()
        bad["floors"][0]["enemies"] = []
        bad["floors"][0]["treasures"] = []
        with self.assertRaises(ContractMismatch):
            _FLOOR_MANIFEST(bad, 0)
        with self.assertRaises(ContractMismatch):
            _FLOOR_MANIFEST(p1_cave(), 5)


class P1ReceiptTests(unittest.TestCase):
    def test_parse_markers_positive(self):
        markers = _PARSE_RUN_MARKERS(LOG_GOOD)
        self.assertTrue(markers["content_selected"])
        self.assertTrue(markers["ready"])
        self.assertTrue(markers["live"])
        self.assertTrue(markers["pass_run"])
        self.assertTrue(markers["window_960x540"])
        self.assertFalse(markers["captain_down"])
        self.assertEqual(len(markers["spawn_covered"]), 1)
        self.assertEqual(len(markers["collision"]), 1)
        self.assertEqual(len(markers["actors"]), 1)
        self.assertEqual(markers["stage"], "ch_NARI_05start3easy")

    def test_parse_markers_negative(self):
        markers = _PARSE_RUN_MARKERS(LOG_NO_COLLISION)
        self.assertFalse(markers["collision"])
        markers = _PARSE_RUN_MARKERS(LOG_CAPTAIN)
        self.assertTrue(markers["captain_down"])
        empty = _PARSE_RUN_MARKERS("")
        self.assertFalse(empty["content_selected"])

    def test_verify_receipt_positive(self):
        report = _VERIFY_RECEIPT(_PARSE_RUN_MARKERS(LOG_GOOD))
        self.assertTrue(report["ok"])
        self.assertEqual(report["collision_probes"], 1)
        self.assertEqual(report["actor_probes"], 1)

    def test_verify_receipt_fails_closed(self):
        with self.assertRaises(ContractMismatch):
            _VERIFY_RECEIPT(_PARSE_RUN_MARKERS(LOG_CAPTAIN))
        with self.assertRaises(ContractMismatch):
            _VERIFY_RECEIPT(_PARSE_RUN_MARKERS(LOG_NO_COLLISION))
        with self.assertRaises(ContractMismatch):
            _VERIFY_RECEIPT(_PARSE_RUN_MARKERS("P2_CHALLENGE_CONTENT_SELECTED only"))
        markers = _PARSE_RUN_MARKERS(LOG_GOOD)
        markers["actors"] = []
        with self.assertRaises(ContractMismatch):
            _VERIFY_RECEIPT(markers)

if __name__ == "__main__":
    unittest.main()