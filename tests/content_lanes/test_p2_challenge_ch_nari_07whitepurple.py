"""Focused P0 tests for the ch_NARI_07whitepurple import adapter (#553).

The adapter is loaded from its reserved file location so this lane creates
no package-marker files outside its three reserved paths; standardizing
``content_lanes`` package markers across stage lanes is left to the
integrator.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ADAPTER_PATH = (
    Path(__file__).resolve().parents[2] / "experimental" / "content_lanes"
    / "p2-challenge-ch_nari_07whitepurple.py"
)
_spec = importlib.util.spec_from_file_location("ch_nari_07whitepurple_adapter", ADAPTER_PATH)
_adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_adapter)

BASELINE = _adapter.BASELINE
CAVE_ID = _adapter.CAVE_ID
CAVE_PATH = _adapter.CAVE_PATH
EXPECTED_FLOORS = _adapter.EXPECTED_FLOORS
SOURCE_SHA256 = _adapter.SOURCE_SHA256
HashMismatch = _adapter.HashMismatch
SourceMissing = _adapter.SourceMissing
UnsupportedDefinition = _adapter.UnsupportedDefinition
validate_p1_manifest = _adapter.validate_p1_manifest
stage_run_layout = _adapter.stage_run_layout
p1_main = _adapter.p1_main
asset_closure = _adapter.asset_closure
decode_full = _adapter.decode_full
decode_text = _adapter.decode_text
import_contract = _adapter.import_contract
source_bytes = _adapter.source_bytes
structural_scan = _adapter.structural_scan
verify_source = _adapter.verify_source

SOURCE_FILE = Path(
    "C:/Users/alari/pikmin-randomizer/output/workflow/autofill"
    "/p2-challenge-ch_nari_07whitepurple/ch_NARI_07whitepurple.txt"
)
HAS_SOURCE = SOURCE_FILE.is_file()

EXPECTED_ENEMIES_F1 = ["Wealthy_gold_medal", "Fart_silver_medal",
                       "Kogane_wadou_kaichin", "BlackPom", "Egg", "GasHiba",
                       "Magaret", "Clover", "Ooinu_s", "KareOoinu_s"]
EXPECTED_TREASURES_F1 = ["key", "apple", "leaf_normal", "leaf_kare",
                         "dia_a_red", "ichigo_l"]
EXPECTED_ENEMIES_F2 = ["Mar_key", "Wealthy_gold_medal", "Fart_silver_medal",
                       "Kogane_wadou_kaichin", "TamagoMushi", "GasHiba",
                       "Magaret", "Clover", "Ooinu_s", "KareOoinu_s"]
EXPECTED_TREASURES_F2 = ["leaf_yellow", "momiji_kare", "dia_a_green",
                         "donutswhite_s", "bane_yellow"]
EXPECTED_POOLS = ["2_units_cent_north_tsuchi.txt",
                  "2_units_mid2_north_tsuchi.txt"]


def real_text():
    return decode_text(source_bytes(str(SOURCE_FILE)))


def mini_source(version=1):
    return ("{ {c000} 4 1 {_eof} } 1\n"
            "{ {f000} 4 0 {f001} 4 0 {f008} -1 units.txt {f015} 4 "
            + str(version) + " {_eof} }\n"
            "{ 1 Chappy 21 1 }\n{ 1 gem_one 12 }\n{ 0 }\n"
            + ("{ 1 0 Chappy 10 1 }" if version else "{ 0 }"))


class SourceIdentityTests(unittest.TestCase):
    @unittest.skipUnless(HAS_SOURCE, "retail source prerequisite absent")
    def test_hash_pins_recorded_identity(self):
        self.assertEqual(verify_source(source_bytes(str(SOURCE_FILE))), SOURCE_SHA256)

    def test_missing_source_fails_closed(self):
        with self.assertRaises(SourceMissing):
            source_bytes(str(SOURCE_FILE) + ".absent")

    @unittest.skipUnless(HAS_SOURCE, "retail source prerequisite absent")
    def test_tampered_bytes_rejected(self):
        data = bytearray(source_bytes(str(SOURCE_FILE)))
        data[100] ^= 1
        with self.assertRaises(HashMismatch):
            verify_source(bytes(data))


class StructuralScanTests(unittest.TestCase):
    @unittest.skipUnless(HAS_SOURCE, "retail source prerequisite absent")
    def test_floor_coverage_and_pools(self):
        scan = structural_scan(real_text())
        self.assertFalse(scan["generated"])
        self.assertEqual(scan["cave_id"], CAVE_ID)
        self.assertEqual(scan["source"], CAVE_PATH)
        self.assertEqual(scan["floor_count"], EXPECTED_FLOORS)
        self.assertEqual([(f["first_floor"], f["last_floor"]) for f in scan["floors"]],
                         [(1, 1), (2, 2)])
        self.assertEqual([f["unit_pool"] for f in scan["floors"]], EXPECTED_POOLS)
        self.assertTrue(all(f["light"] == "normal_light_cha.ini" for f in scan["floors"]))
        self.assertTrue(all(f["vrbox"] == "none" for f in scan["floors"]))

    @unittest.skipUnless(HAS_SOURCE, "retail source prerequisite absent")
    def test_observed_rosters_match_source(self):
        scan = structural_scan(real_text())
        first, second = scan["floors"]
        self.assertEqual([e["token"] for e in first["enemies"]], EXPECTED_ENEMIES_F1)
        self.assertEqual([t["token"] for t in first["treasures"]], EXPECTED_TREASURES_F1)
        self.assertEqual([e["token"] for e in second["enemies"]], EXPECTED_ENEMIES_F2)
        self.assertEqual([t["token"] for t in second["treasures"]], EXPECTED_TREASURES_F2)
        self.assertEqual(first["gates"], [])
        self.assertEqual(second["gates"], [])
        self.assertEqual(first["caps"], [])
        self.assertEqual([(c["token"], c["source_weight"], c["placement_type"])
                          for c in second["caps"]], [("TamagoMushi", 10, 1)])
        self.assertEqual(first["enemies"][5]["source_weight"], 50)
        self.assertEqual(first["enemies"][5]["placement_type"], 5)
        self.assertEqual(first["enemies"][6]["placement_type"], 6)

    @unittest.skipUnless(HAS_SOURCE, "retail source prerequisite absent")
    def test_authored_maxima_are_recorded_not_spawned(self):
        scan = structural_scan(real_text())
        first, second = scan["floors"]
        params = [first["parameters"], second["parameters"]]
        self.assertEqual([p["f002"] for p in params], ["13", "10"])
        self.assertEqual([p["f003"] for p in params], ["6", "5"])
        self.assertEqual([p["f014"] for p in params], ["100", "100"])
        for floor in (first, second):
            self.assertNotIn("spawns", floor)
            self.assertNotIn("coordinates", floor)

    def test_malformed_definitions_fail_closed(self):
        good = mini_source()
        mutations = [
            good.replace("{c000} 4 1", "{c000} 4 2"),
            good.replace("{f001} 4 0", "{f001} 4 -1"),
            good.replace("{f008} -1 units.txt", "{f008} 4 units.txt"),
            good.replace("units.txt", "../units.txt"),
            good.replace("{ 1 Chappy", "{ 2 Chappy"),
            good + " trailing",
            good[:good.rfind("}")],
            good.replace("{f015} 4 1", "{f099} 4 1"),
            "",
            "{ unbalanced",
        ]
        for text in mutations:
            with self.subTest(text=text[:40]), self.assertRaises((ValueError, UnsupportedDefinition)):
                structural_scan(text)

    @unittest.skipUnless(HAS_SOURCE, "retail source prerequisite absent")
    def test_real_source_mutations_fail_closed(self):
        good = real_text()
        for text in (good + " trailing", good[:good.rfind("}")],
                     good.replace("{f008} -1 2_units_cent_north_tsuchi.txt",
                                  "{f008} -1 ../evil.txt")):
            with self.subTest(text=text[-40:]), self.assertRaises((ValueError, UnsupportedDefinition)):
                structural_scan(text)


class SharedDecodeWiringTests(unittest.TestCase):
    def test_synthetic_source_through_shared_parser(self):
        result = decode_full(mini_source(), {"Chappy"}, {"gem_one"})
        self.assertFalse(result["generated"])
        self.assertEqual(result["floor_count"], 1)
        floor = result["floors"][0]
        self.assertEqual(floor["enemies"][0]["enemy_id"], "Chappy")
        self.assertEqual(floor["caps"][0]["enemy"]["enemy_id"], "Chappy")

    def test_unknown_reference_rejected(self):
        with self.assertRaises(UnsupportedDefinition):
            decode_full(mini_source(), {"Other"}, {"gem_one"})


class ClosureContractTests(unittest.TestCase):
    def setUp(self):
        self.scan = structural_scan(mini_source().replace("units.txt", "pool.txt"))

    def test_none_catalog_leaves_assets_unverified(self):
        for asset in asset_closure(self.scan, None):
            self.assertEqual(asset["status"], "unverified")

    def test_explicit_catalog_resolves_presence(self):
        catalog = {"user/Mukki/mapunits/units/pool.txt": True}
        assets = asset_closure(self.scan, catalog)
        self.assertEqual([a["status"] for a in assets], ["present"])
        missing = asset_closure(self.scan, {})
        self.assertTrue(all(a["status"] == "missing" for a in missing))

    def test_contract_emits_no_placements(self):
        contract = import_contract(self.scan, asset_closure(self.scan, None))
        self.assertEqual(contract["cave_id"], CAVE_ID)
        self.assertEqual(contract["source_sha256"], SOURCE_SHA256)
        self.assertEqual(contract["semantic_resolution"], "open")
        self.assertFalse(contract["generated"])
        for banned in ("coordinates", "placements", "spawns"):
            self.assertNotIn(banned, contract)
            for floor in contract["floor_manifest"]:
                self.assertNotIn(banned, floor)
        self.assertIn("not final spawn instances", repr(contract["limitations"]))
        self.assertEqual(contract["timer_roster_spray_baseline"], BASELINE)

class P1ImportTests(unittest.TestCase):
    """P1 import path for ch_NARI_07whitepurple (lane p2-challenge-ch-nari-07whitepurple-p1).

    Synthetic harness manifests (labeled here, never source evidence) that
    preserve the pinned contract: 2 floors, timers [170.0, 170.0], squad
    total 30 purples at [4][0], sprays 0/3, ui_index 20.
    """

    def manifest(self, **over):
        m = {
            "schema": "p2-challenge-ch_nari_07whitepurple-p0/1",
            "cave_id": "ch_NARI_07whitepurple",
            "floors": [
                {"unit_pool": "whitepurple-floor1-pool",
                 "enemies": [{"source_token": "PurpleA"}],
                 "treasures": [{"treasure_id": "purple_key"}]},
                {"unit_pool": "whitepurple-floor2-pool",
                 "enemies": [{"source_token": "PurpleB"}],
                 "treasures": []},
            ],
            "starting_roster": [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
                                [30, 0, 0], [0, 0, 0], [0, 0, 0]],
            "floor_seconds": [170.0, 170.0],
            "sprays": {"bitter": 0, "spicy": 3},
            "ui_index": 20,
        }
        m.update(over)
        return m

    def test_validate_ok(self):
        out = validate_p1_manifest(self.manifest())
        self.assertEqual(out["cave_id"], "ch_NARI_07whitepurple")
        self.assertEqual(out["squad_total"], 30)
        self.assertEqual(len(out["floors"]), 2)
        self.assertEqual(out["floor_seconds"], [170.0, 170.0])

    def test_wrong_cave_rejected(self):
        with self.assertRaises(UnsupportedDefinition):
            validate_p1_manifest(self.manifest(cave_id="ch_OTHER"))

    def test_floor_count_rejected(self):
        m = self.manifest()
        m["floors"] = m["floors"][:1]
        with self.assertRaises(UnsupportedDefinition):
            validate_p1_manifest(m)

    def test_empty_enemies_rejected(self):
        m = self.manifest()
        m["floors"][0]["enemies"] = []
        with self.assertRaises(UnsupportedDefinition):
            validate_p1_manifest(m)

    def test_missing_unit_pool_rejected(self):
        m = self.manifest()
        del m["floors"][1]["unit_pool"]
        with self.assertRaises(UnsupportedDefinition):
            validate_p1_manifest(m)

    def test_wrong_squad_total_rejected(self):
        m = self.manifest()
        m["starting_roster"][4][0] = 29
        with self.assertRaises(UnsupportedDefinition):
            validate_p1_manifest(m)

    def test_missing_pinned_cell_rejected(self):
        m = self.manifest()
        m["starting_roster"][4][0] = 0
        m["starting_roster"][0][0] = 30
        with self.assertRaises(UnsupportedDefinition):
            validate_p1_manifest(m)

    def test_bad_timer_rejected(self):
        with self.assertRaises(UnsupportedDefinition):
            validate_p1_manifest(self.manifest(floor_seconds=[170.0, 169.0]))

    def test_wrong_sprays_rejected(self):
        with self.assertRaises(UnsupportedDefinition):
            validate_p1_manifest(self.manifest(sprays={"bitter": 0, "spicy": 0}))

    def test_wrong_ui_rejected(self):
        with self.assertRaises(UnsupportedDefinition):
            validate_p1_manifest(self.manifest(ui_index=0))

    def test_stage_run_layout_writes_three_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            result = stage_run_layout(self.manifest(), out)
            self.assertEqual(result["cave_id"], "ch_NARI_07whitepurple")
            self.assertEqual(len(result["files"]), 3)
            for name in ("stage-manifest.json", "p1-input-package.json", "run-plan.json"):
                self.assertIn(name, result["files"])
                self.assertTrue((out / name).is_file())
            package = json.loads((out / "p1-input-package.json").read_text())
            self.assertEqual(package["schema"], "p2-challenge-ch-nari-07whitepurple-p1-v1")
            self.assertEqual(package["squad_total"], 30)

    def test_stage_run_layout_rejects_bad_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(UnsupportedDefinition):
                stage_run_layout({"cave_id": "nope"}, Path(tmp))

    def test_p1_main_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(UnsupportedDefinition):
                p1_main(Path(tmp) / "absent.json", Path(tmp) / "out")

    def test_p1_main_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "manifest.json"
            src.write_text(json.dumps(self.manifest()), encoding="utf-8")
            result = p1_main(src, Path(tmp) / "run")
            self.assertEqual(result["floors"], 2)
if __name__ == '__main__':
    unittest.main()
