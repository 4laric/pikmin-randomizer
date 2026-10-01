"""Focused P0 tests for the ch_MUKI_metal import-contract adapter (#535).

No legal copy of the retail caveinfo exists on this host, so no test claims
retail values: decode-path tests use explicitly synthetic format fragments
(structural parser behavior only), and every source-dependent test asserts
the exact missing-prerequisite / hash-mismatch boundary.
"""

import hashlib
import importlib.util
import unittest
from pathlib import Path

RESERVED = (Path(__file__).resolve().parents[2] / "experimental" / "content_lanes"
            / "p2-challenge-ch_muki_metal.py")


def load_lane():
    # Reserved filename contains dashes, so import by path, not dotted name.
    spec = importlib.util.spec_from_file_location("p2_challenge_ch_muki_metal_lane",
                                                  RESERVED)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lane = load_lane()


MINIMAL_TWO_FLOOR = """\
{ {c000} 4 2 {_eof} } 2
{ {f000} 4 0 {f001} 4 0 {f008} -1 synthetic_a.txt {_eof} }
{ 2 enemy_a 10 0 enemy_b 5 1 }
{ 1 item_a 3 }
{ 0 }
{ 0 }
{ {f000} 4 1 {f001} 4 1 {f008} -1 synthetic_b.txt {_eof} }
{ 1 enemy_a 7 0 }
{ 0 }
{ 0 }
{ 0 }
"""


class LocateTests(unittest.TestCase):
    def test_missing_everywhere_reports_exact_prerequisite(self):
        with self.assertRaises(lane.SourceUnavailable) as ctx:
            lane.locate_source(exists=lambda candidate: False)
        self.assertIn("user/Mukki/mapunits/caveinfo/ch_MUKI_metal.txt",
                      str(ctx.exception))

    def test_first_available_candidate_wins(self):
        seen = []
        found = lane.locate_source(
            candidates=["a", "b"],
            exists=lambda candidate: seen.append(candidate) or candidate == "b")
        self.assertEqual(found, "b")
        self.assertEqual(seen, ["a", "b"])

    def test_missing_prerequisite_record(self):
        record = lane.missing_prerequisite(checked=["x"])
        self.assertEqual(record["source_id"], "ch_MUKI_metal")
        self.assertEqual(record["expected_sha256"], lane.EXPECTED_SHA256)
        self.assertIn("GPVE01", record["prerequisite"])
        self.assertIn(lane.EXPECTED_SHA256, record["prerequisite"])

    def test_host_search_finds_nothing(self):
        # Actual host boundary today: no legal source on this machine.
        with self.assertRaises(lane.SourceUnavailable):
            lane.locate_source()


class HashTests(unittest.TestCase):
    def test_synthetic_bytes_mismatch(self):
        with self.assertRaises(lane.SourceHashMismatch):
            lane.verify_bytes(b"not the retail caveinfo")

    def test_empty_bytes_rejected(self):
        with self.assertRaises(lane.SourceHashMismatch):
            lane.verify_bytes(b"")

    def test_expected_digest_is_inventory_pin(self):
        self.assertEqual(lane.EXPECTED_SHA256,
                         "903b43195c5f2d53683a462af4fe1383bfe0604551f2935cb78fc3f55d0de1f1")


class DetailsTests(unittest.TestCase):
    def test_authoritative_details_validate(self):
        record = lane.validate_details()
        self.assertEqual(record["floors"], 2)
        self.assertEqual(record["floor_seconds"], [130.0, 100.0])
        self.assertEqual(record["bitter_sprays"], 1)
        self.assertEqual(record["spicy_sprays"], 1)
        self.assertEqual(record["pikmin_by_native_color_and_maturity"][0], [0, 0, 50])
        self.assertEqual(len(record["pikmin_by_native_color_and_maturity"]), 7)

    def test_timer_count_mismatch_rejected(self):
        bad = dict(lane.DETAILS, floor_seconds=[130.0])
        with self.assertRaises(ValueError):
            lane.validate_details(bad)

    def test_negative_spray_rejected(self):
        bad = dict(lane.DETAILS, bitter_sprays=-1)
        with self.assertRaises(ValueError):
            lane.validate_details(bad)

    def test_roster_shape_rejected(self):
        bad = dict(lane.DETAILS, pikmin_by_native_color_and_maturity=[[0, 0, 50]])
        with self.assertRaises(ValueError):
            lane.validate_details(bad)

    def test_foreign_source_record_rejected(self):
        bad = dict(lane.DETAILS, cave_id="ch_MUKI_king")
        with self.assertRaises(ValueError):
            lane.validate_details(bad)


class DecodeTests(unittest.TestCase):
    def test_synthetic_two_floor_format_decodes(self):
        # Synthetic format fragment only: proves the shared-parser path and
        # floor-coverage logic, claims no retail values.
        floors = lane.decode_definitions(MINIMAL_TWO_FLOOR)
        self.assertEqual(len(floors), 2)
        coverage = lane.floor_coverage(floors, expected=2)
        self.assertTrue(coverage["complete"])

    def test_empty_text_rejected(self):
        with self.assertRaises(ValueError):
            lane.decode_definitions("   \n")

    def test_unclosed_block_rejected(self):
        with self.assertRaises(ValueError):
            lane.decode_definitions("{ c000 4 2")

    def test_floor_gap_detected(self):
        coverage = lane.floor_coverage([{"number": 1}, {"number": 3}], expected=2)
        self.assertFalse(coverage["complete"])

    def test_duplicate_floor_detected(self):
        coverage = lane.floor_coverage([{"number": 1}, {"number": 1}], expected=2)
        self.assertFalse(coverage["complete"])


class AuditTests(unittest.TestCase):
    def test_audit_without_source_is_exact_prerequisite(self):
        report = lane.audit(exists=lambda candidate: False)
        self.assertFalse(report["source"]["available"])
        prereq = report["source"]["missing_prerequisite"]
        self.assertEqual(prereq["expected_sha256"], lane.EXPECTED_SHA256)
        self.assertFalse(report["floor_coverage"]["complete"])
        self.assertEqual(report["playability"], "no claim: metadata audit only")
        self.assertIn("136", report["framework_blockers"])
        self.assertIn("137", report["framework_blockers"])

    def test_audit_preserves_roster_and_timers(self):
        report = lane.audit(exists=lambda candidate: False)
        self.assertEqual(report["details"]["floor_seconds"], [130.0, 100.0])
        self.assertEqual(report["details"]["bitter_sprays"], 1)
        self.assertEqual(report["details"]["spicy_sprays"], 1)

    def test_audit_with_wrong_bytes_is_mismatch_not_values(self):
        with self.assertRaises(lane.SourceHashMismatch):
            lane.audit(source_bytes=b"synthetic, not retail")


if __name__ == "__main__":
    unittest.main()
