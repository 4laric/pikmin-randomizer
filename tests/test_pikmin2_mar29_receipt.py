"""Focused tests for the Mar29 corpse receipt provider (#650).

All fixtures are synthetic native-log fragments exercising the adapter-scope
checker: bind-once, corpse resolution, exactly-once ledger grant, natural
haul with Pod deferred, injection rejection and captain-down rejection. No
value here is claimed as retail fact.
"""
import unittest

from experimental import pikmin2_mar29_receipt as mod


def good_log(*subs, **over):
    parts = [
        "P2_MAR29_READY squad=20 mar_gen=375001 health=900.00 reg=1 captain_parked=1",
        "P2_MAR_RECEIPT_BIND generator=375001 source_id=29",
        "P2_MAR29_DRAIN events=41 min=120.00 start=900.00",
        "P2_MAR29_NATURAL_DEATH mar=1 health=0.00 tick=900",
        "P2_MAR29_CORPSE pellet=1 generator=375001 tick=950",
        "P2_MAR_CORPSE_READY generator=375001 source_id=29 receipt=corpse:mar:375001",
        "P2_MAR29_RECEIPT seed=local id=enemy:29 slot=375001 encounter=corpse new=1 dup=0 count=1",
        "P2_MAR29_CARRY tick=1000 moved=12.50 goal_dist=210.30",
        "P2_MAR29_HAUL moved=65.20 goal_dist=150.10 tick=1400",
        "PASS P2_MAR29_RECEIPT_RUN receipt=1 haul=1 pod=deferred",
    ]
    text = "\n".join(parts) + "\n"
    for old, new in subs:
        text = text.replace(old, new)
    for key, value in over.items():
        text = text.replace(key, value)
    return text


class ReceiptTests(unittest.TestCase):
    def test_full_chain_passes(self):
        result = mod.validate(good_log())
        for key in ("bind", "resolution", "exactly_once", "haul",
                    "captain"):
            self.assertTrue(result[key]["passed"], (key, result[key]))

    def test_missing_bind_rejected(self):
        text = good_log(("P2_MAR_RECEIPT_BIND generator=375001 source_id=29\n",
                        ""))
        self.assertFalse(mod.validate(text)["bind"]["passed"])

    def test_double_bind_rejected(self):
        text = good_log() + \
            "P2_MAR_RECEIPT_BIND generator=375001 source_id=29\n"
        self.assertFalse(mod.validate(text)["bind"]["passed"])

    def test_wrong_generator_bind_rejected(self):
        text = good_log(("generator=375001 source_id=29",
                        "generator=375002 source_id=29"))
        self.assertFalse(mod.validate(text)["bind"]["passed"])

    def test_missing_resolution_rejected(self):
        text = good_log(("P2_MAR_CORPSE_READY generator=375001 source_id=29 receipt=corpse:mar:375001\n",
                        ""))
        self.assertFalse(mod.validate(text)["resolution"]["passed"])

    def test_regrant_not_duplicate_rejected(self):
        text = good_log(("new=1 dup=0 count=1", "new=1 dup=1 count=2"))
        self.assertFalse(mod.validate(text)["exactly_once"]["passed"])

    def test_missing_receipt_line_rejected(self):
        text = good_log(("P2_MAR29_RECEIPT seed=local id=enemy:29 slot=375001 encounter=corpse new=1 dup=0 count=1\n",
                        ""))
        self.assertFalse(mod.validate(text)["exactly_once"]["passed"])

    def test_haul_below_threshold_rejected(self):
        text = good_log(("moved=65.20", "moved=5.00"))
        self.assertFalse(mod.validate(text)["haul"]["passed"])

    def test_injection_taint_rejected(self):
        text = good_log() + "P2_LIFECYCLE_INJECT health=999\n"
        self.assertFalse(mod.validate(text)["haul"]["passed"])

    def test_captain_down_rejected(self):
        text = good_log() + \
            "P2_FIXTURE_CAPTAIN_DOWN tick=99 hp=0.500 orima_dead=1 dead_state=0 outcome=BLOCKED\n"
        self.assertFalse(mod.validate(text)["captain"]["passed"])

    def test_empty_log_rejected(self):
        result = mod.validate("")
        for key in ("bind", "resolution", "exactly_once", "haul"):
            self.assertFalse(result[key]["passed"], key)

    def test_splice_helper(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            preview = Path(tmp) / "preview.cpp"
            preview.write_text("int x = 1;\nint main() { return 0; }\n",
                               encoding="utf-8")
            fixture = Path(tmp) / "fix.cpp"
            fixture.write_text("// P2_MAR29_READY\nclass RoomApp {};\n",
                               encoding="utf-8")
            out = mod.splice_fixture(str(preview), str(fixture))
            self.assertIn("P2_MAR29_READY", out)
            self.assertIn("int main()", out)
            preview.write_text(out, encoding="utf-8")
            with self.assertRaises(ValueError):
                mod.splice_fixture(str(preview), str(fixture))
            bare = Path(tmp) / "bare.cpp"
            bare.write_text("int x = 1;\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                mod.splice_fixture(str(bare), str(fixture))


if __name__ == "__main__":
    unittest.main()