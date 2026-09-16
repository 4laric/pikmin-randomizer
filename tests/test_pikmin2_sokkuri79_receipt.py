"""Unit tests for the Sokkuri79 receipt auditor (#578).

Synthetic logs only; no engine, session or retail assets are touched. Covers
the new=1 / duplicate new=0 contract, natural-carry gating, injection
rejection, missing-receipt failure and the no-carcass static audit.
"""
import importlib.util
import unittest
from pathlib import Path


def _load():
    path = (Path(__file__).resolve().parents[1] / "experimental"
            / "pikmin2_sokkuri79_receipt.py")
    spec = importlib.util.spec_from_file_location("sokkuri79_receipt", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load()

READY = "P2_SOKKURI79_READY squad=20 sokkuri_gen=346005 reg=1 session=1"
BIND = "P2_SOKKURI_DELIVERY_BIND generator=346005 source_id=79"
WINDOW = "Experimental preview window set to 960x540 windowed and centered"
CARRY = "P2_SOKKURI79_CARRY tick=900 moved=573.55 goal_dist=44.10 state=7"
DELIVERED = "P2_SOKKURI79_DELIVERED_TO_GOAL tick=1000 moved=610.20"
PASS_LINE = "PASS P2_SOKKURI79_RECEIPT_RUN delivered=1"
CARCASS = "startCarcassMotion present"

RETAIL = "C:/Users/alari/pikmin-randomizer/native/pikmin2-research"


def log_with(new):
    return "\n".join([
        READY, BIND, WINDOW, CARRY, DELIVERED, PASS_LINE, CARCASS,
        "P2_ORDINARY_P2_RECEIPT seed=abc id=onion:p2:79:4 generator=346005 new=%d" % new,
    ]) + "\n"


class ReceiptTests(unittest.TestCase):
    def validate(self, text, expect_new):
        return R.validate(text, expect_new, retail_root=RETAIL, code=0)

    def test_first_delivery_passes(self):
        result = self.validate(log_with(1), 1)
        self.assertTrue(result["passed"], result)

    def test_duplicate_passes_when_expected(self):
        result = self.validate(log_with(0), 0)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["receipt"]["receipts"][0]["new"], 0)

    def test_wrong_new_flag_fails(self):
        self.assertFalse(self.validate(log_with(0), 1)["passed"])
        self.assertFalse(self.validate(log_with(1), 0)["passed"])

    def test_missing_receipt_fails(self):
        result = self.validate("\n".join([READY, BIND, WINDOW]) + "\n", 1)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["receipt"])

    def test_receipt_without_carry_fails(self):
        text = log_with(1).replace(CARRY + "\n", "")
        result = self.validate(text, 1)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["natural_carry"])

    def test_short_haul_fails(self):
        text = log_with(1).replace("moved=573.55", "moved=12.00")
        text = text.replace("moved=610.20", "moved=12.00")
        result = self.validate(text, 1)
        self.assertFalse(result["passed"])

    def test_injected_log_rejected(self):
        result = self.validate(log_with(1) + "P2_LL_INJECT Sokkuri health=0\n", 1)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["no_inject"])

    def test_wrong_generator_rejected(self):
        text = log_with(1).replace("generator=346005 new=", "generator=999999 new=")
        text = text.replace(BIND, "P2_SOKKURI_DELIVERY_BIND generator=999999 source_id=79")
        result = self.validate(text, 1)
        self.assertFalse(result["checks"]["receipt"])

    def test_instrument_enables_session_from_main(self):
        base = ("class RoomApp : public PlugPikiApp {\n"
                "};\n"
                "int main(int argc,char** argv) {\n"
                "  pc_bbft_init(argc,argv);\n"
                "  gsys->run(new RoomApp());return 0;\n"
                "}\n")
        out = R.instrument(base, app="class Receipt { };\n")
        self.assertIn("if(!pc_randomizer_enabled())pc_randomizer_init(argc,argv);", out)

    def test_instrument_rejects_missing_session_anchor(self):
        base = ("class RoomApp : public PlugPikiApp {\n"
                "};\n"
                "int main(int argc,char** argv) { return 0; }\n")
        with self.assertRaisesRegex(ValueError, "pc_bbft_init"):
            R.instrument(base, app="class Receipt { };\n")

    def test_no_carcass_audit(self):
        ok = R.check_ordinary_corpse_source(RETAIL)
        self.assertTrue(ok["passed"], ok)
        bad = R.check_ordinary_corpse_source("C:/nonexistent-retail-root")
        self.assertFalse(bad["passed"])


if __name__ == "__main__":
    unittest.main()