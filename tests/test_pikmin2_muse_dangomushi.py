"""Focused tests for the DangoMushi94 death/cleanup observer (#376).

Synthetic logs only; no engine, session or retail assets are touched.
Covers the correlated death/corpse/re-entry contract, the optional family
receipt, injection rejection, captain-down blocking, ordering and mismatch
negatives.
"""
import importlib.util
import unittest
from pathlib import Path


def _load():
    path = (Path(__file__).resolve().parents[1] / "experimental"
            / "pikmin2_muse_dangomushi.py")
    spec = importlib.util.spec_from_file_location("muse_dangomushi", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load()

BIND = "P2_DANGOMUSHI_BIND generator=376003 source_id=94 visual_only=0"
DEAD = "P2_DANGOMUSHI_DEAD generator=376003 source_id=94 health=0"
CORPSE = "P2_BATCH3_DRAW corpse=1 key=DangoMushi clip=dead"
REBIND = "P2_DANGOMUSHI_BIND generator=376003 source_id=94 visual_only=0"
RECEIPT = "[Pikipelago] P2_POD_RECEIPT id=corpse:376003 value=15 new=1"


def good_log(with_receipt=False):
    lines = [BIND, DEAD, CORPSE, REBIND]
    if with_receipt:
        lines.insert(3, RECEIPT)
    return "\n".join(lines) + "\n"


class DeathCleanupTests(unittest.TestCase):
    def test_correlated_death_and_reentry_pass(self):
        result = R.parse(good_log())
        self.assertTrue(result["gate_ok"], result)
        self.assertTrue(result["gate_death_corpse"])
        self.assertTrue(result["gate_cleanup_reentry"])
        self.assertTrue(result["rebound"])
        self.assertEqual(result["generator"], 376003)
        self.assertFalse(result["transport_observed"])

    def test_family_receipt_reported_not_required(self):
        result = R.parse(good_log(with_receipt=True))
        self.assertTrue(result["gate_ok"], result)
        self.assertTrue(result["receipt_ok"])
        self.assertTrue(result["transport_observed"])

    def test_missing_corpse_fails(self):
        text = good_log().replace(CORPSE + "\n", "")
        result = R.parse(text)
        self.assertFalse(result["gate_ok"])
        self.assertFalse(result["corpse"])

    def test_missing_rebind_fails_cleanup(self):
        text = good_log().replace(REBIND + "\n", "")
        result = R.parse(text)
        self.assertFalse(result["gate_ok"])
        self.assertFalse(result["gate_cleanup_reentry"])

    def test_wrong_order_death_before_bind_fails(self):
        text = "\n".join([DEAD, BIND, CORPSE, REBIND]) + "\n"
        self.assertFalse(R.parse(text)["gate_ok"])

    def test_wrong_generator_fails(self):
        text = good_log().replace("generator=376003 source_id=94 health=0",
                                  "generator=999999 source_id=94 health=0")
        self.assertFalse(R.parse(text)["gate_ok"])

    def test_wrong_source_id_bind_ignored(self):
        text = good_log().replace("source_id=94 visual_only=0", "source_id=34 visual_only=0")
        self.assertFalse(R.parse(text)["gate_ok"])

    def test_non_dangomushi_corpse_key_ignored(self):
        text = good_log().replace("key=DangoMushi", "key=SnakeCrow")
        self.assertFalse(R.parse(text)["gate_ok"])

    def test_injected_health_rejected(self):
        result = R.parse(good_log() + "P2_DANGOMUSHI_DEATH_INJECT before=1.0\n")
        self.assertFalse(result["gate_ok"])
        self.assertTrue(result["injected"])
        self.assertEqual(result["block_reason"], "injected")

    def test_raw_mhealth_write_rejected(self):
        self.assertFalse(R.parse(good_log() + "fixture mHealth=0 set\n")["gate_ok"])

    def test_captain_down_blocked(self):
        result = R.parse(good_log() + "GAMEEND_PikminExtinction\n")
        self.assertTrue(result["blocked"])
        self.assertEqual(result["block_reason"], "captain-down")
        self.assertFalse(result["gate_ok"])

    def test_empty_log_untested(self):
        result = R.parse("")
        self.assertFalse(result["gate_ok"])
        self.assertFalse(result["bound"])
        self.assertIsNone(result["block_reason"])

    def test_proxy_birth_without_family_legs_fails(self):
        text = "P2_ENEMY_READY species=DangoMushi generator=376003\n" + CORPSE + "\n"
        self.assertFalse(R.parse(text)["gate_ok"])


if __name__ == "__main__":
    unittest.main()
