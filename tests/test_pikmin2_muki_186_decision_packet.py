"""Focused fail-closed tests for the MUKI #186 decision packet (issue #777).

Covers the pinned packet shape, the exact unified diff content (both MUKI
rows in boot-table field order plus the CMake membership line), malformed
pins, unknown files/drift refusal, and packet self-validation round-trip.
No engine, runtime, manifest or ADMIT surface is touched here.
"""
import json
import unittest

from experimental.pikmin2_muki_186_decision_packet import (
    CONSUMER_ISSUES,
    DECISION_FILES,
    PACKET_SCHEMA,
    PRODUCER_COMMITS,
    build_packet,
    unified_diff,
    validate_packet,
)


class PacketShapeTests(unittest.TestCase):
    def test_schema_and_parties(self):
        packet = build_packet()
        self.assertEqual(packet["schema"], PACKET_SCHEMA)
        self.assertEqual(packet["producer_issue"], 748)
        self.assertEqual(packet["consumer_issues"], [735, 744])
        self.assertEqual(packet["decision_files"], [
            "native/pc_port/pc_bbft.cpp",
            "native/CMakeLists.txt",
        ])
        self.assertFalse(packet["runtime_claim"])
        self.assertEqual(packet["review"]["status"], "requested-not-granted")

    def test_producer_commits_pinned(self):
        packet = build_packet()
        self.assertEqual(packet["producer_commits"], list(PRODUCER_COMMITS))
        self.assertEqual(len(packet["producer_commits"]), 2)


class DiffContentTests(unittest.TestCase):
    def test_both_rows_present_in_order(self):
        diff = unified_diff()
        self.assertIn("+    { \"ch_MUKI_houdai\",", diff)
        self.assertIn("+    { \"ch_MUKI_redblue\",", diff)
        self.assertLess(diff.index("ch_MUKI_houdai"), diff.index("ch_MUKI_redblue"))

    def test_row_fields_exact(self):
        diff = unified_diff()
        self.assertIn("8, 24, 2,", diff)
        self.assertIn("18, 17, 2,", diff)
        self.assertIn("{ 100.0f, 150.0f,", diff)
        self.assertIn("{ 200.0f, 200.0f,", diff)
        self.assertIn("07cdf2cd492024548b9982a6ed63c40ba6c781bd114814339aefc9b8b35232f3", diff)
        self.assertIn("f81653301ec2f1b4f5cd1e51d2e15c81608bfbea0beaaadeb623de58db791434", diff)

    def test_cmake_membership_line(self):
        diff = unified_diff()
        self.assertIn("+pc_port/pc_p2_challenge_muki_stages.cpp", diff)

    def test_headers_name_files(self):
        diff = unified_diff()
        self.assertIn("--- a/native/pc_port/pc_bbft.cpp", diff)
        self.assertIn("+++ b/native/CMakeLists.txt", diff)


class FailClosedTests(unittest.TestCase):
    def test_malformed_producer_commit_refused(self):
        with self.assertRaises(ValueError):
            unified_diff(["zzzz", PRODUCER_COMMITS[1]])

    def test_wrong_commit_count_refused(self):
        with self.assertRaises(ValueError):
            unified_diff([PRODUCER_COMMITS[0]])

    def test_malformed_boot_pin_refused(self):
        with self.assertRaises(ValueError):
            unified_diff(PRODUCER_COMMITS, "not-a-pin!!")

    def test_packet_self_validation_round_trip(self):
        packet = build_packet()
        self.assertTrue(validate_packet(packet))

    def test_tampered_diff_rejected(self):
        packet = build_packet()
        packet["unified_diff"] += "+evil\n"
        self.assertFalse(validate_packet(packet))

    def test_wrong_schema_rejected(self):
        packet = build_packet()
        packet["schema"] = "other/9"
        self.assertFalse(validate_packet(packet))

    def test_unknown_consumer_set_rejected(self):
        packet = build_packet()
        packet["consumer_issues"] = [735]
        self.assertFalse(validate_packet(packet))

    def test_json_serialisable(self):
        json.dumps(build_packet())


if __name__ == "__main__":
    unittest.main()
