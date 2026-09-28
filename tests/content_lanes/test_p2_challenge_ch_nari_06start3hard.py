"""Focused P0+P1 tests for the ch_NARI_06start3hard adapter (#549).

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


_FLOOR_MANIFEST = ADAPTER.floor_manifest
_CONTENT_SIDECAR = ADAPTER.content_sidecar
_GENERATE_SIDECAR = ADAPTER.generate_sidecar
_PREVIEW_RECORD = ADAPTER.preview_record
_STAGE_RUN_LAYOUT = ADAPTER.stage_run_layout
_STAGE_MANIFEST_RECORD = ADAPTER.stage_manifest_record
_PARSE_RUN_MARKERS = ADAPTER.parse_run_markers
_VERIFY_RECEIPT = ADAPTER.verify_receipt
_P1_WINDOW = ADAPTER.P1_WINDOW
_RUN_LAYOUT_FILES = ADAPTER.RUN_LAYOUT_FILES
_CHECK_LANE_ENTRY = ADAPTER.check_lane_entry


def p1_cave():
    return dict(
        cave_id="ch_NARI_06start3hard", floor_count=3, floors=[
            dict(first_floor=1, last_floor=1,
                 parameters={"f008": "1_units_big2_kusachi.txt", "f007": "0"},
                 enemies=[dict(source_token="RandPom", enemy_id="RandPom"),
                          dict(source_token="Hana_silver_medal", enemy_id="Hana"),
                          dict(source_token="Ooinu_s", enemy_id="Ooinu_s")],
                 treasures=[dict(treasure_id="key", source_weight=10)],
                 gates=[], caps=[]),
            dict(first_floor=2, last_floor=2,
                 parameters={"f008": "1_NARI_4x4b_conc.txt", "f007": "1"},
                 enemies=[dict(source_token="RandPom", enemy_id="RandPom"),
                          dict(source_token="Chappy_be_dama_red_l", enemy_id="Chappy")],
                 treasures=[dict(treasure_id="key", source_weight=10),
                            dict(treasure_id="gold_medal", source_weight=10)],
                 gates=[dict(empty=False)], caps=[]),
            dict(first_floor=3, last_floor=3,
                 parameters={"f008": "3_units_d_f_ujikou_tile.txt", "f007": "0"},
                 enemies=[dict(source_token="Tank_key", enemy_id="Tank"),
                          dict(source_token="Hiba", enemy_id="Hiba")],
                 treasures=[dict(treasure_id="bell_red", source_weight=10)],
                 gates=[], caps=[])])


def p1_stage():
    return dict(cave_file="ch_NARI_06start3hard.txt",
                pikmin=[[0, 0, 0], [0, 0, 4],
                        [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                legacy_time=450.0, bitter_sprays=2, spicy_sprays=3, floors=3,
                treasure_count=0, ui_index=16, floor_seconds=[100.0, 150.0, 180.0])


def p1_closure():
    return [dict(floor=1, unit_pool="1_units_big2_kusachi.txt",
                 units=["item_cap_kusachi", "room_big2_kusachi"]),
            dict(floor=2, unit_pool="1_NARI_4x4b_conc.txt",
                 units=["room_4x4b_4_conc"]),
            dict(floor=3, unit_pool="3_units_d_f_ujikou_tile.txt",
                 units=["room_4x4d_4_tile"])]


LOG_GOOD = "\n".join([
    "[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)",
    "P2_CHALLENGE_CONTENT_SELECTED cave=ch_NARI_06start3hard floor=1",
    "P2_CHALLENGE_CONTENT_SPAWN_COVERED id=RandPom count=1",
    "P2_CHALLENGE_CONTENT_SPAWN_COVERED id=key count=1",
    "P2_CHALLENGE_CONTENT_READY cave=ch_NARI_06start3hard floor=1 squad=4",
    "P2_CHALLENGE_CONTENT_LIVE squad=4 actors=1 tick=2",
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
        self.assertEqual(manifest["unit_pool"], "1_units_big2_kusachi.txt")
        self.assertEqual(manifest["anchor"], "hole")
        self.assertEqual(manifest["spawns"],
                         [{"id": "Hana_silver_medal", "count": 1},
                          {"id": "Ooinu_s", "count": 1},
                          {"id": "RandPom", "count": 1},
                          {"id": "key", "count": 1}])

    def test_anchor_maps_geyser(self):
        self.assertEqual(_FLOOR_MANIFEST(p1_cave(), 1)["anchor"], "geyser")

    def test_content_sidecar_exact(self):
        manifest = _FLOOR_MANIFEST(p1_cave(), 0)
        self.assertEqual(_CONTENT_SIDECAR(manifest),
                         "P2_CHALLENGE_CONTENT_1\n"
                         "stage ch_NARI_06start3hard 1\n"
                         "pool 1_units_big2_kusachi.txt\n"
                         "spawn Hana_silver_medal 1\nspawn Ooinu_s 1\n"
                         "spawn RandPom 1\nspawn key 1\n"
                         "anchor hole\n")
        self.assertEqual(_GENERATE_SIDECAR(manifest),
                         "spawn Hana_silver_medal 1\nspawn Ooinu_s 1\n"
                         "spawn RandPom 1\nspawn key 1\n")

    def test_preview_record_room_choice(self):
        self.assertEqual(_PREVIEW_RECORD(["way3_kusachi", "room_big2_kusachi"])["room"],
                         "room_big2_kusachi")
        self.assertEqual(_PREVIEW_RECORD(["way3_kusachi"])["room"], "way3_kusachi")
        self.assertTrue(_PREVIEW_RECORD(["room_big2_kusachi"])["experimental"])
        with self.assertRaises(ValueError):
            _PREVIEW_RECORD([])

    def test_stage_run_layout_writes_and_hashes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            layout = _STAGE_RUN_LAYOUT(p1_cave(), p1_stage(), "a" * 64, "b" * 64,
                                       p1_closure(), tmp, write=True)
            self.assertEqual(layout["files"], sorted(_RUN_LAYOUT_FILES))
            self.assertEqual(layout["window"], _P1_WINDOW)
            self.assertEqual(layout["boot_floor"]["floor"], 1)
            for name, digest in layout["sha256"].items():
                self.assertEqual(len(digest), 64)
            stored = Path(tmp, "p2-challenge-content.txt").read_text(encoding="utf-8")
            self.assertIn("stage ch_NARI_06start3hard 1", stored)
            record = json.loads(Path(tmp, "stage-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(record["ui_index"], 16)
            self.assertEqual(record["floor_seconds"], [100.0, 150.0, 180.0])
            self.assertEqual(record["legacy_time"], 450.0)
            self.assertEqual(record["starting_pikmin"], 4)
            self.assertEqual(record["preview_window"], "960x540")
            self.assertEqual(record["floors"][0]["unit_pool"],
                             "1_units_big2_kusachi.txt")

    def test_stage_run_layout_fails_closed(self):
        with self.assertRaises(ValueError):
            _STAGE_RUN_LAYOUT(dict(floors=[]), p1_stage(), "a" * 64, "b" * 64, [], None, write=False)
        bad = p1_cave()
        bad["floors"][0]["parameters"].pop("f008")
        with self.assertRaises(ValueError):
            _FLOOR_MANIFEST(bad, 0)
        bad = p1_cave()
        bad["floors"][0]["enemies"] = []
        bad["floors"][0]["treasures"] = []
        with self.assertRaises(ValueError):
            _FLOOR_MANIFEST(bad, 0)
        with self.assertRaises(ValueError):
            _FLOOR_MANIFEST(p1_cave(), 5)

    def test_lane_entry_check_reads_real_document(self):
        lanes = str(ROOT / "docs" / "PIKMIN_CONTENT_IMPORT_LANES.json")
        self.assertTrue(_CHECK_LANE_ENTRY(lanes))
        with self.assertRaises(ValueError):
            ADAPTER.check_lane_entry("C:/nonexistent-lanes.json")


class P1ReceiptTests(unittest.TestCase):
    def test_parse_markers_positive(self):
        markers = _PARSE_RUN_MARKERS(LOG_GOOD)
        self.assertTrue(markers["content_selected"])
        self.assertTrue(markers["ready"])
        self.assertTrue(markers["live"])
        self.assertTrue(markers["pass_run"])
        self.assertTrue(markers["window_960x540"])
        self.assertFalse(markers["captain_down"])
        self.assertEqual(len(markers["spawn_covered"]), 2)
        self.assertEqual(len(markers["collision"]), 1)
        self.assertEqual(len(markers["actors"]), 1)
        self.assertEqual(markers["stage"], "ch_NARI_06start3hard")

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
        with self.assertRaises(ValueError):
            _VERIFY_RECEIPT(_PARSE_RUN_MARKERS(LOG_CAPTAIN))
        with self.assertRaises(ValueError):
            _VERIFY_RECEIPT(_PARSE_RUN_MARKERS(LOG_NO_COLLISION))
        with self.assertRaises(ValueError):
            _VERIFY_RECEIPT(_PARSE_RUN_MARKERS("P2_CHALLENGE_CONTENT_SELECTED only"))
        markers = _PARSE_RUN_MARKERS(LOG_GOOD)
        markers["actors"] = []
        with self.assertRaises(ValueError):
            _VERIFY_RECEIPT(markers)


if __name__ == "__main__":
    unittest.main()