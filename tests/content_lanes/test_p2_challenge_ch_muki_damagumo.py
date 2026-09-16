"""Focused boundary tests for the ch_MUKI_damagumo P0 adapter (#538).

Every test uses synthetic or catalogued-baseline inputs only. No retail
bytes, builds, runtime, or lane worktrees are touched; subprocesses are
never spawned. The adapter module has a hyphenated filename, so it is
loaded by path instead of a package import.
"""

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ADAPTER = (Path(__file__).resolve().parents[2]
           / "experimental" / "content_lanes"
           / "p2-challenge-ch_muki_damagumo.py")


def load_adapter():
    spec = importlib.util.spec_from_file_location("damagumo_adapter", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_adapter()

BASELINE = {
    "table_order": 9,
    "cave_id": "ch_MUKI_damagumo",
    "cave_path": "user/Mukki/mapunits/caveinfo/ch_MUKI_damagumo.txt",
    "floors": 1,
    "pikmin_by_native_color_and_maturity": [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 50],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ],
    "legacy_time": 0.0,
    "bitter_sprays": 0,
    "spicy_sprays": 1,
    "treasure_count_field": 0,
    "ui_index": 6,
    "floor_seconds": [150.0],
    "issue": 137,
}


class BaselineContractTests(unittest.TestCase):
    def test_baseline_record_passes(self):
        validated = adapter.validate_stage_record(BASELINE)
        self.assertEqual(validated, BASELINE)
        self.assertIsNot(validated, BASELINE)

    def test_adapter_baseline_matches_inventory_row(self):
        self.assertEqual(adapter.BASELINE_RECORD, BASELINE)

    def test_floor_coverage_is_complete(self):
        self.assertEqual(adapter.floor_coverage(BASELINE), [1])

    def test_resource_closure_totals_without_placements(self):
        closure = adapter.resource_closure(BASELINE)
        self.assertEqual(closure["starting_roster_total"], 50)
        self.assertEqual(closure["starting_roster_by_row"], [0, 0, 50, 0, 0, 0, 0])
        self.assertEqual(closure["starting_roster_by_col"], [0, 0, 50])
        self.assertEqual(closure["floor_seconds"], [150.0])
        self.assertEqual(closure["spicy_sprays"], 1)
        self.assertTrue(closure["definitions_are_not_placements"])
        for key in ("actors", "placements", "slots"):
            self.assertNotIn(key, closure)

    def test_packet_is_json_serializable(self):
        packet = adapter.audit_packet()
        self.assertEqual(json.loads(json.dumps(packet))["source_id"],
                         "ch_MUKI_damagumo")
        self.assertEqual(packet["floor_coverage"], [1])
        self.assertEqual(packet["playability"], "none claimed; P1 runtime and P2 acceptance remain OPEN")


class MalformedInputTests(unittest.TestCase):
    def altered(self):
        return copy.deepcopy(BASELINE)

    def test_non_object_rejected(self):
        for bad in (None, [], "ch_MUKI_damagumo"):
            with self.assertRaises(adapter.StageRecordError):
                adapter.validate_stage_record(bad)

    def test_missing_and_extra_keys_rejected(self):
        record = self.altered()
        del record["ui_index"]
        with self.assertRaises(adapter.StageRecordError):
            adapter.validate_stage_record(record)
        record = self.altered()
        record["english_title"] = "Spider Snare"
        with self.assertRaises(adapter.StageRecordError):
            adapter.validate_stage_record(record)

    def test_identity_mismatch_rejected(self):
        for key, bad in (("cave_id", "ch_MUKI_bigfoot"),
                         ("cave_path", "user/Mukki/mapunits/caveinfo/ch_MUKI_bigfoot.txt"),
                         ("table_order", 14), ("floors", 2),
                         ("ui_index", 7), ("issue", 538)):
            record = self.altered()
            record[key] = bad
            with self.assertRaises(adapter.StageRecordError, msg=key):
                adapter.validate_stage_record(record)

    def test_roster_shape_and_sign_rejected(self):
        record = self.altered()
        record["pikmin_by_native_color_and_maturity"] = [[0, 0, 50]]
        with self.assertRaises(adapter.StageRecordError):
            adapter.validate_stage_record(record)
        record = self.altered()
        record["pikmin_by_native_color_and_maturity"][2][2] = -1
        with self.assertRaises(adapter.StageRecordError):
            adapter.validate_stage_record(record)
        record = self.altered()
        record["pikmin_by_native_color_and_maturity"][2][2] = True
        with self.assertRaises(adapter.StageRecordError):
            adapter.validate_stage_record(record)

    def test_timer_floor_disagreement_rejected(self):
        record = self.altered()
        record["floor_seconds"] = [150.0, 150.0]
        with self.assertRaises(adapter.StageRecordError):
            adapter.validate_stage_record(record)
        record = self.altered()
        record["floor_seconds"] = [float("nan")]
        with self.assertRaises(adapter.StageRecordError):
            adapter.validate_stage_record(record)
        record = self.altered()
        record["floor_seconds"] = [-5.0]
        with self.assertRaises(adapter.StageRecordError):
            adapter.validate_stage_record(record)

    def test_negative_sprays_rejected(self):
        record = self.altered()
        record["spicy_sprays"] = -1
        with self.assertRaises(adapter.StageRecordError):
            adapter.validate_stage_record(record)


class SourceBoundaryTests(unittest.TestCase):
    def test_empty_bytes_rejected(self):
        for bad in (b"", bytearray(), None, "bytes"):
            with self.assertRaises(adapter.StageRecordError):
                adapter.verify_source_bytes(bad)

    def test_foreign_bytes_rejected_against_pinned_hash(self):
        with self.assertRaises(adapter.StageRecordError):
            adapter.verify_source_bytes(b"retail caveinfo placeholder")

    def test_matching_bytes_accepted_with_callers_hash(self):
        payload = b"synthetic boundary probe, not retail source"
        expected = hashlib.sha256(payload).hexdigest()
        self.assertEqual(adapter.verify_source_bytes(payload, expected), expected)

    def test_missing_prerequisites_name_exact_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = adapter.missing_prerequisites([tmp])
        paths = [m["path"] for m in missing]
        self.assertIn("user/Mukki/mapunits/caveinfo/ch_MUKI_damagumo.txt", paths)
        self.assertIn("user/Matoba/challenge/stages.txt", paths)
        entry = next(m for m in missing
                     if m["path"].endswith("ch_MUKI_damagumo.txt"))
        self.assertEqual(entry["sha256"], adapter.SOURCE_SHA256)
        self.assertEqual(entry["status"], "absent")

    def test_present_but_foreign_file_reported_as_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = (Path(tmp) / "user" / "Mukki" / "mapunits" / "caveinfo")
            target.mkdir(parents=True)
            (target / "ch_MUKI_damagumo.txt").write_bytes(b"not the retail file")
            missing = adapter.missing_prerequisites([tmp])
        entry = next(m for m in missing
                     if m["path"].endswith("ch_MUKI_damagumo.txt"))
        self.assertEqual(entry["status"], "hash_mismatch")

    def test_blockers_name_exact_owners(self):
        owners = [b["id"] for b in adapter.blockers()]
        for expected in ("#136", "#137", "#129", "#130/#131",
                         "source-bytes", "display-name"):
            self.assertIn(expected, owners)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
