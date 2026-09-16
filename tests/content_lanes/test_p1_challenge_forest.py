"""Focused boundary tests for the P1 Challenge Forest P0 adapter.

Covers the valid reference shape plus malformed/missing-input boundaries.
All samples are inline; no disc assets or network required.
"""

import sys
import unittest
from pathlib import Path
import importlib.util

_ADAPTER_PATH = (Path(__file__).resolve().parents[2] / "experimental"
                 / "content_lanes" / "p1-challenge-forest.py")
_spec = importlib.util.spec_from_file_location("p1_challenge_forest_adapter",
                                               _ADAPTER_PATH)
_adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_adapter)

Chal1DecodeError = _adapter.Chal1DecodeError
build_import_contract = _adapter.build_import_contract
decode_chal1_ini = _adapter.decode_chal1_ini
source_sha256_of_bytes = _adapter.source_sha256_of_bytes
validate_resource_closure = _adapter.validate_resource_closure

VALID_INI = """navi_start\t\t0.0\t0.0\r
map_file\t\tcourses/stage1/forest.mod\r
\r
day_multiply\t1.4\r
\r
dayMgr {\r
numsettings 5\r
}\r
\r
new_room {\r
\tindex\t\t0\r
\tradius\t\t4.0\r
\tcentre\t\t0.0\t0.0\r
\t}\r
"""


def _files(**extra):
    base = {"chal1.ini": {"sha256": "a" * 64, "size": 2471},
            "chal1/default.gen": {"sha256": "b" * 64, "size": 16019},
            "chal1/plants.gen": {"sha256": "c" * 64, "size": 4944}}
    base.update(extra)
    return base


class DecodeTest(unittest.TestCase):
    def test_valid_reference_shape(self):
        decoded = decode_chal1_ini(VALID_INI)
        self.assertEqual(decoded["navi_start"], (0.0, 0.0))
        self.assertEqual(decoded["map_file"], "courses/stage1/forest.mod")
        self.assertEqual(decoded["day_multiply"], 1.4)
        self.assertEqual(decoded["day_settings"], 5)
        self.assertEqual(decoded["rooms"],
                         [{"index": 0, "radius": 4.0, "centre": (0.0, 0.0)}])

    def test_empty_input_rejected(self):
        with self.assertRaises(Chal1DecodeError):
            decode_chal1_ini("   \n")

    def test_missing_map_file_rejected(self):
        with self.assertRaises(Chal1DecodeError):
            decode_chal1_ini("navi_start 0.0 0.0\n")

    def test_missing_navi_start_rejected(self):
        with self.assertRaises(Chal1DecodeError):
            decode_chal1_ini("map_file courses/stage1/forest.mod\n")

    def test_malformed_day_multiply_rejected(self):
        with self.assertRaises(Chal1DecodeError):
            decode_chal1_ini("navi_start 0.0 0.0\n"
                             "map_file courses/stage1/forest.mod\n"
                             "day_multiply fast\n")

    def test_malformed_room_rejected(self):
        with self.assertRaises(Chal1DecodeError):
            decode_chal1_ini("navi_start 0.0 0.0\n"
                             "map_file courses/stage1/forest.mod\n"
                             "new_room { index 0 radius wide centre 0.0 0.0 }")

    def test_duplicate_room_index_rejected(self):
        with self.assertRaises(Chal1DecodeError):
            decode_chal1_ini(
                "navi_start 0.0 0.0\nmap_file courses/stage1/forest.mod\n"
                "new_room { index 0 radius 4.0 centre 0.0 0.0 }\n"
                "new_room { index 0 radius 2.0 centre 1.0 1.0 }\n")

    def test_day_multiply_optional(self):
        decoded = decode_chal1_ini(
            "navi_start 0.0 0.0\nmap_file courses/stage1/forest.mod\n")
        self.assertIsNone(decoded["day_multiply"])


class ClosureTest(unittest.TestCase):
    def test_valid_closure_single_floor(self):
        decoded = decode_chal1_ini(VALID_INI)
        closure = validate_resource_closure(decoded, _files(), True)
        self.assertEqual(closure["floors"], 1)
        self.assertEqual(closure["floor_ids"], ["challenge:forest"])
        self.assertEqual(closure["generators"],
                         ["chal1/default.gen", "chal1/plants.gen"])

    def test_missing_default_gen_rejected(self):
        decoded = decode_chal1_ini(VALID_INI)
        files = _files()
        del files["chal1/default.gen"]
        with self.assertRaises(Chal1DecodeError):
            validate_resource_closure(decoded, files, True)

    def test_missing_geometry_rejected(self):
        decoded = decode_chal1_ini(VALID_INI)
        with self.assertRaises(Chal1DecodeError):
            validate_resource_closure(decoded, _files(), False)

    def test_inventory_without_hash_rejected(self):
        decoded = decode_chal1_ini(VALID_INI)
        files = _files()
        files["chal1/default.gen"] = {"size": 16019}
        with self.assertRaises(Chal1DecodeError):
            validate_resource_closure(decoded, files, True)

    def test_closure_records_identity_not_placements(self):
        decoded = decode_chal1_ini(VALID_INI)
        closure = validate_resource_closure(decoded, _files(), True)
        self.assertNotIn("placements", closure)
        self.assertNotIn("actors", closure)


class ContractTest(unittest.TestCase):
    def test_contract_preserves_source_facts(self):
        decoded = decode_chal1_ini(VALID_INI)
        closure = validate_resource_closure(decoded, _files(), True)
        contract = build_import_contract(decoded, closure,
                                         source_sha256="d" * 64)
        self.assertEqual(contract["level_key"], "challenge:forest")
        self.assertEqual(contract["native_area_id"], 1)
        self.assertEqual(contract["stage_info_index"], 17)
        self.assertEqual(contract["source"], "stages/chal1.ini")
        self.assertEqual(contract["navi_start"], [0.0, 0.0])
        self.assertEqual(contract["day_multiply"], 1.4)
        self.assertFalse(contract["playable"])
        self.assertIn(52, contract["runtime_dependencies"])

    def test_contract_rejects_floor_drift(self):
        decoded = decode_chal1_ini(VALID_INI)
        closure = validate_resource_closure(decoded, _files(), True)
        closure["floor_ids"] = ["challenge:navel"]
        with self.assertRaises(Chal1DecodeError):
            build_import_contract(decoded, closure)

    def test_contract_rejects_map_drift(self):
        decoded = decode_chal1_ini(VALID_INI)
        closure = validate_resource_closure(decoded, _files(), True)
        closure["map_file"] = "courses/stage2/navel.mod"
        with self.assertRaises(Chal1DecodeError):
            build_import_contract(decoded, closure)

    def test_source_bytes_hash(self):
        self.assertEqual(len(source_sha256_of_bytes(b"abc")), 64)
        with self.assertRaises(Chal1DecodeError):
            source_sha256_of_bytes(b"")


if __name__ == "__main__":
    unittest.main()
