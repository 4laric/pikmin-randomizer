"""Unit tests for the ElecBug28 receipt auditor (#585).

Synthetic logs only; no engine, session or retail assets are touched. Covers
the new=1 / duplicate new=0 contract, natural-carry gating, injection
rejection, missing-receipt failure and the no-carcass static audit.
"""
import importlib.util
import unittest
from pathlib import Path


def _load():
    path = (Path(__file__).resolve().parents[1] / "experimental"
            / "pikmin2_elecbug28_receipt.py")
    spec = importlib.util.spec_from_file_location("elecbug28_receipt", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load()

READY = "P2_ELECBUG28_READY squad=20 elecbug_gen=346002 pair_gen=346010 reg=2 session=1"
BIND = "P2_ELECBUG_DELIVERY_BIND generator=346002 source_id=28"
WINDOW = "Experimental preview window set to 960x540 windowed and centered"
FLIP = "P2_ELECBUG28_FLIPPED tick=500"
DEAD = "P2_ELECBUG28_DIED tick=900 health=0.00"
CORPSE = "P2_ELECBUG28_CORPSE pellet=1 tick=960"
CARRY = "P2_ELECBUG28_CARRY tick=1400 moved=573.55 goal_dist=44.10 state=7"
DELIVERED = "P2_ELECBUG28_DELIVERED_TO_GOAL tick=1800 moved=610.20"
PASS_LINE = "PASS P2_ELECBUG28_RECEIPT_RUN delivered=1"

RETAIL = "C:/Users/alari/pikmin-randomizer/native/pikmin2-research"


def log_with(new):
    return "\n".join([
        READY, BIND, WINDOW, FLIP, DEAD, CORPSE, CARRY, DELIVERED, PASS_LINE,
        "P2_ORDINARY_P2_RECEIPT seed=abc id=onion:p2:28:4 generator=346002 new=%d" % new,
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
        result = self.validate(log_with(1) + "P2_LL_INJECT ElecBug health=0\n", 1)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["no_inject"])

    def test_missing_natural_death_fails(self):
        text = log_with(1).replace(DEAD + "\n", "")
        result = self.validate(text, 1)
        self.assertFalse(result["checks"]["natural_death"])
        self.assertFalse(result["passed"])

    def test_missing_staged_flip_fails(self):
        text = log_with(1).replace(FLIP + "\n", "")
        result = self.validate(text, 1)
        self.assertFalse(result["checks"]["flipped"])
        self.assertFalse(result["passed"])

    def test_wrong_generator_rejected(self):
        text = log_with(1).replace("generator=346002 new=", "generator=999999 new=")
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

    def test_instrument_rejects_double_splice(self):
        base = ("class RoomApp : public PlugPikiApp {\n};\n"
                "int main(int argc,char** argv) { pc_bbft_init(argc,argv); return 0; }\n")
        app = "class Receipt { };\n// P2_ELECBUG28_READY\n"
        once = R.instrument(base, app=app)
        with self.assertRaisesRegex(ValueError, "already carries"):
            R.instrument(once, app=app)

    def test_no_carcass_audit(self):
        ok = R.check_ordinary_corpse_source(RETAIL)
        self.assertTrue(ok["passed"], ok)
        bad = R.check_ordinary_corpse_source("C:/nonexistent-retail-root")
        self.assertFalse(bad["passed"])

    def test_flip_label_is_reported(self):
        result = self.validate(log_with(1), 1)
        self.assertEqual(result["natural_vs_injected"]["flip"], "staged-press")


if __name__ == "__main__":
    unittest.main()
