"""Tests for the gate-5 evidence comparison (read-only, no runtime)."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "experimental"))

from pikmin2_elecbug28_gate5_evidence import (
    compare_against_standard,
    parse_ledger,
    parse_receipt_line,
    summarize_run_log,
)

CANON = "C:/Users/alari/pikmin-randomizer"
RUN1 = os.path.join(CANON, "output/workflow/autofill/enemy-elecbug28-receipt/runs/run1/17f3886b3ecf4338a3e0fcfc7d115e5b/capture/native.log")
RUN2 = os.path.join(CANON, "output/workflow/autofill/enemy-elecbug28-receipt/runs/run2/b08a14f8532c42e7baabf7c4bb5ff26d/capture/native.log")
LEDGER = os.path.join(CANON, "output/workflow/autofill/enemy-elecbug28-receipt/runs/campaign/p2-delivery-receipts.txt")
HANDOFF585 = os.path.join(CANON, "output/workflow/autofill/enemy-elecbug28-receipt/handoff.json")
HANDOFF578 = os.path.join(CANON, "output/workflow/autofill/enemy-sokkuri79-receipt/handoff.json")


def read(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


class Gate5EvidenceTests(unittest.TestCase):
    def test_receipt_line_parses(self):
        line = "[Pikmin Randomizer] P2_ORDINARY_P2_RECEIPT seed=abc id=onion:p2:28:0 extra new=1"
        self.assertEqual(parse_receipt_line(line), ("abc", "onion:p2:28:0", 1))
        self.assertIsNone(parse_receipt_line("unrelated line"))

    def test_run_logs_show_exactly_once(self):
        run1 = summarize_run_log(read(RUN1))
        run2 = summarize_run_log(read(RUN2))
        got1 = [r for r in run1["receipts"] if r[1].startswith("onion:p2:28")]
        got2 = [r for r in run2["receipts"] if r[1].startswith("onion:p2:28")]
        self.assertEqual(len(got1), 1)
        self.assertEqual(got1[0][2], 1)
        self.assertEqual(len(got2), 1)
        self.assertEqual(got2[0][2], 0)
        self.assertEqual(got1[0][:2], got2[0][:2])

    def test_run_logs_show_natural_death_and_haul(self):
        run1 = summarize_run_log(read(RUN1))
        self.assertEqual(run1["died_health"], 0.0)
        self.assertEqual(run1["corpse_pellets"], 1)
        self.assertGreater(run1["haul_moved"], 500.0)

    def test_ledger_matches_receipt(self):
        rows = parse_ledger(read(LEDGER))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "onion:p2:28:0")

    def test_comparison_upholds_staged_tooling(self):
        result = compare_against_standard(
            summarize_run_log(read(RUN1)),
            summarize_run_log(read(RUN2)),
            parse_ledger(read(LEDGER)),
            json.loads(read(HANDOFF585)),
            json.loads(read(HANDOFF578)))
        self.assertTrue(result["endpoint_real_ordinary"])
        self.assertTrue(result["exactly_once_across_restart"])
        self.assertTrue(result["shared_session_ledger"])
        self.assertTrue(result["natural_death_no_write"])
        self.assertEqual(result["recommendation"], "UPHOLD-STAGED-TOOLING")


if __name__ == "__main__":
    unittest.main()
