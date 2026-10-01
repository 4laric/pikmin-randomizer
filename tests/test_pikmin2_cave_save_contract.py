"""Malformed-input unit tests for the cave save-contract surface checker."""
import unittest

from experimental.pikmin2_cave_save_contract import (
    MarkerError,
    check_sequence,
    find_markers,
    parse_transfer_text,
    summarize,
)

GOOD_TRANSFER = ("P2_CAVE_TRANSFER_3\n" + "a" * 32 + "\n2 0.625 2\n0 0\n5 0\n")
GOOD_LOG = ("P2_LANE11_WRITE ok=1\n"
            "P2_CAVE_TRANSFER_3\n" + "a" * 32 + "\n2 0.625 2\n0 0\n5 0\n"
            "P2_CAVE_TRANSFER floor=2 survivors=2 health=0.625 failed=0\n"
            "P2_CAVE_RESTORE species=5 maturity=0\n"
            "P2_LANE11_READ bulbmin=1\n"
            "PASS P2_LANE11_RESTORE\n")


class SaveContractCheckerTests(unittest.TestCase):
    def test_valid_transfer_parses(self):
        schema, token, floor, health, survivors = parse_transfer_text(GOOD_TRANSFER)
        self.assertEqual((schema, floor, health, survivors), (3, 2, 0.625, [(0, 0), (5, 0)]))
        self.assertEqual(token, "a" * 32)

    def test_valid_log_sequence(self):
        markers = find_markers(GOOD_LOG)
        self.assertTrue(check_sequence(markers))
        report = summarize(GOOD_LOG)
        self.assertTrue(report["complete"])

    def test_header_failures_fail_closed(self):
        for bad in ("", "P2_CAVE_TRANSFER_4\n" + "a" * 32 + "\n2 0.5 1\n0 0\n",
                    "P2_CAVE_ENTRY_3\n" + "a" * 32 + "\n2 0.5 1\n0 0\n",
                    "P2_CAVE_TRANSFER_3\n" + "g" * 32 + "\n2 0.5 1\n0 0\n",
                    "P2_CAVE_TRANSFER_3\n" + "a" * 31 + "\n2 0.5 1\n0 0\n",
                    "P2_CAVE_TRANSFER_3\n" + "a" * 32 + "\n3 0.5 1\n0 0\n",
                    "P2_CAVE_TRANSFER_3\n" + "a" * 32 + "\n2 0 1\n0 0\n",
                    "P2_CAVE_TRANSFER_3\n" + "a" * 32 + "\n2 1.5 1\n0 0\n",
                    "P2_CAVE_TRANSFER_3\n" + "a" * 32 + "\n2 0.5 0\n",
                    "P2_CAVE_TRANSFER_3\n" + "a" * 32 + "\n2 0.5 2\n0 0\n"):
            with self.subTest(bad=bad[:28]), self.assertRaises(MarkerError):
                parse_transfer_text(bad)

    def test_survivor_failures_fail_closed(self):
        for bad in ("P2_CAVE_TRANSFER_3\n" + "a" * 32 + "\n2 0.5 1\n9 0\n",
                    "P2_CAVE_TRANSFER_3\n" + "a" * 32 + "\n2 0.5 1\n0 3\n",
                    "P2_CAVE_TRANSFER_3\n" + "a" * 32 + "\n2 0.5 1\nx y\n",
                    "P2_CAVE_TRANSFER_3\n" + "a" * 32 + "\n2 0.5 1\n0 0\n9 9\n",
                    "P2_CAVE_TRANSFER_2\n" + "a" * 32 + "\n2 0.5 1\n5 0\n"):
            with self.subTest(bad=bad[:28]), self.assertRaises(MarkerError):
                parse_transfer_text(bad)

    def test_sequence_failures_fail_closed(self):
        with self.assertRaises(MarkerError):
            check_sequence(find_markers("PASS P2_LANE11_RESTORE\n"))
        with self.assertRaises(MarkerError):
            check_sequence(find_markers("PASS P2_LANE11_RESTORE\nP2_LANE11_WRITE ok=1\n"))
        with self.assertRaises(MarkerError):
            find_markers(None)
        with self.assertRaises(MarkerError):
            parse_transfer_text(None)
        report = summarize("nothing here")
        self.assertFalse(report["complete"])

    def test_old_reader_rejects_bulbmin_explicitly(self):
        with self.assertRaises(MarkerError) as ctx:
            parse_transfer_text("P2_CAVE_TRANSFER_2\n" + "a" * 32 + "\n2 0.5 1\n5 0\n")
        self.assertIn("schema 3", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
