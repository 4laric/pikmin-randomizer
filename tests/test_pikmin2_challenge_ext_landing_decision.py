"""Tests for the ext-landing decision packet (#730/#755, recovery 8c2b7615).

Synthetic shape/malformed checks plus live read-only pin re-verification
against the native repo (no writes, no builds, no merges).
"""
import unittest

from experimental.pikmin2_challenge_ext_landing_decision import (
    EXT_BRANCH,
    EXT_COMMIT,
    EXT_FILES,
    FOLLOWON_ISSUE,
    DecisionError,
    ancestry,
    blob_prefix,
    conflict_matrix,
    decision_packet,
    record_producer_pins,
)

NATIVE_REPO = r"C:\Users\alari\pikmin-randomizer\native"


class ShapeTests(unittest.TestCase):
    def test_pins_have_expected_shape(self):
        self.assertEqual(len(EXT_COMMIT), 40)
        self.assertTrue(all(len(v) == 12 for v in EXT_FILES.values()))
        self.assertEqual(len(EXT_FILES), 3)
        self.assertEqual(FOLLOWON_ISSUE, 755)

    def test_malformed_inputs_fail_closed(self):
        with self.assertRaises(DecisionError):
            blob_prefix(r"C:\nonexistent-repo-xyz", EXT_COMMIT, "x.cpp")
        with self.assertRaises(DecisionError):
            record_producer_pins(r"C:\nonexistent-repo-xyz")


class LivePinTests(unittest.TestCase):
    def test_producer_pins_match_recorded(self):
        pins = record_producer_pins(NATIVE_REPO)
        self.assertEqual(pins["commit"], EXT_COMMIT)
        self.assertEqual(pins["branch"], EXT_BRANCH)
        self.assertEqual(set(pins["files"]), set(EXT_FILES))

    def test_destination_matrix_marks_clean_adds(self):
        rows = conflict_matrix(NATIVE_REPO, "HEAD", [])
        adds = [r for r in rows if r["path"] in EXT_FILES]
        self.assertEqual(len(adds), 3)
        for row in adds:
            self.assertIn(row["landing"], ("clean-add", "skip-present"))
        follow = [r for r in rows if "pc_bbft" in r["path"]][0]
        self.assertEqual(follow["landing"][:13], "owner-blocked")

    def test_packet_names_downstream(self):
        packet = decision_packet(NATIVE_REPO, "HEAD", [])
        self.assertEqual(packet["downstream"], ["#537", "recovery 8c2b7615", "#575/#576"])
        self.assertTrue(packet["ordered_steps"])
        self.assertIn("schema", packet)


if __name__ == "__main__":
    unittest.main()
