"""Focused tests for the receipt-ledger endpoint binding (#749)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experimental.pikmin2_receipt_ledger_binding import (
    PINS, Endpoint, ContractError, validate_log,
)


class BindingTests(unittest.TestCase):
    def test_pins(self):
        self.assertEqual([p[0] for p in PINS],
                         ["SuckReady", "ActOnyon", "ObtainPellet", "LedgerWrite"])
        self.assertEqual([p[2] for p in PINS], [195, 403, 800, 832])

    def test_happy_path(self):
        endpoint = Endpoint("seed-1")
        self.assertEqual(endpoint.stage, "Idle")
        endpoint.suck_ready("onion:p2:38:0")
        endpoint.act_onyon("g1")
        endpoint.obtain_pellet("enc1")
        self.assertEqual(endpoint.ledger_write(), 1)
        self.assertEqual(endpoint.stage, "Idle")

    def test_order_refused(self):
        endpoint = Endpoint("seed-1")
        with self.assertRaisesRegex(ContractError, "order"):
            endpoint.act_onyon("g1")
        with self.assertRaisesRegex(ContractError, "order"):
            endpoint.obtain_pellet("enc1")
        with self.assertRaisesRegex(ContractError, "order"):
            endpoint.ledger_write()
        self.assertEqual(endpoint.stage, "Idle")

    def test_double_ready_refused(self):
        endpoint = Endpoint("seed-1")
        endpoint.suck_ready("onion:p2:38:0")
        with self.assertRaisesRegex(ContractError, "not-idle"):
            endpoint.suck_ready("onion:p2:38:0")

    def test_duplicate_grant(self):
        endpoint = Endpoint("seed-1")
        endpoint.suck_ready("onion:p2:38:0")
        endpoint.act_onyon("g1")
        endpoint.obtain_pellet("enc1")
        self.assertEqual(endpoint.ledger_write(), 1)
        endpoint.suck_ready("onion:p2:38:0")
        endpoint.act_onyon("g1")
        endpoint.obtain_pellet("enc1")
        self.assertEqual(endpoint.ledger_write(), 2)

    def test_malformed_tokens(self):
        endpoint = Endpoint("seed-1")
        with self.assertRaisesRegex(ContractError, "bad identity"):
            endpoint.suck_ready("has space")
        with self.assertRaisesRegex(ContractError, "bad identity"):
            endpoint.suck_ready("")
        endpoint.suck_ready("onion:p2:38:0")
        with self.assertRaisesRegex(ContractError, "bad slot"):
            endpoint.act_onyon("x" * 200)


class LogValidatorTests(unittest.TestCase):
    LOG = "\n".join([
        "P2_RECEIPT_ENDPOINT stage=SuckReady identity=onion:p2:38:0",
        "P2_RECEIPT_ENDPOINT_REFUSED stage=actOnyon reason=order state=Idle",
        "P2_RECEIPT_ENDPOINT stage=LedgerWrite identity=onion:p2:38:0 granted=1",
        "P2_RECEIPT_ENDPOINT stage=LedgerWrite identity=onion:p2:38:0 granted=0 duplicate=1",
        "P2_RECEIPT_LEDGER_SELFTEST_PASS rows=7",
        "PASS RECEIPT_LEDGER contract stages=4 negatives=8",
        "P2_FIXTURE_CAPTAIN_DOWN tick=0 outcome=BLOCKED",
    ])

    def test_validate_log(self):
        report = validate_log(self.LOG)
        self.assertIn("SuckReady", report["stages_observed"])
        self.assertEqual(report["refusals"], [("actOnyon", "order")])
        self.assertEqual(report["grants"], [("onion:p2:38:0", 1), ("onion:p2:38:0", 0)])
        self.assertEqual(report["selftest_rows"], [7])
        self.assertEqual(report["contract_negatives"], [8])
        self.assertTrue(report["captain_down"])

    def test_validate_empty(self):
        report = validate_log("nothing here\n")
        self.assertEqual(report["stages_observed"], [])
        self.assertEqual(report["grants"], [])
        self.assertFalse(report["captain_down"])


if __name__ == "__main__":
    unittest.main()
