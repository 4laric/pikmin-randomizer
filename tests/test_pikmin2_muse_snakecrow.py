"""Negative/contract tests for the muse SnakeCrow gate-4/5/6 observer (#376).

The observer must stay fail-closed until a real run correlates the same
generator file id across the family bind, the family death marker and the
Pod corpse receipt, in that order. Only a fully correlated triple with a
live captain may yield gate_ok True.
"""
import unittest

from experimental.pikmin2_muse_snakecrow import parse

GEN = 340001
BIND = ("P2_SNAKEJOINT_BIND generator=%d species=SnakeCrow source_id=34 "
        "visual_only=0" % GEN)
DEATH = ("P2_SNAKEJOINT_DEAD generator=%d source_id=34 health=0" % GEN)
RECEIPT = ("[Pikipelago] P2_POD_RECEIPT id=corpse:%d value=2 new=1 pokos=2 "
           "seeds=0" % GEN)


class MuseSnakecrowObserverTests(unittest.TestCase):
    def test_correlated_triple_passes_without_rebind(self):
        verdict = parse("\n".join([BIND, DEATH, RECEIPT]))
        self.assertTrue(verdict["gate_ok"])
        self.assertTrue(verdict["bound"])
        self.assertTrue(verdict["dead"])
        self.assertTrue(verdict["receipt_ok"])
        self.assertFalse(verdict["rebound"])
        self.assertEqual(verdict["generator"], GEN)
        self.assertFalse(verdict["blocked"])

    def test_rebind_recorded(self):
        rebind = ("P2_SNAKEJOINT_BIND generator=%d species=SnakeCrow "
                  "source_id=34 visual_only=0" % GEN)
        verdict = parse("\n".join([BIND, DEATH, RECEIPT, rebind]))
        self.assertTrue(verdict["gate_ok"])
        self.assertTrue(verdict["rebound"])

    def test_receipt_generator_mismatch_fails(self):
        other = RECEIPT.replace("id=corpse:%d" % GEN, "id=corpse:340002")
        verdict = parse("\n".join([BIND, DEATH, other]))
        self.assertFalse(verdict["gate_ok"])
        self.assertFalse(verdict["receipt_ok"])

    def test_death_generator_mismatch_fails(self):
        other = DEATH.replace("generator=%d" % GEN, "generator=340002")
        verdict = parse("\n".join([BIND, other, RECEIPT]))
        self.assertFalse(verdict["gate_ok"])

    def test_receipt_before_death_fails(self):
        verdict = parse("\n".join([BIND, RECEIPT, DEATH]))
        self.assertFalse(verdict["gate_ok"])

    def test_missing_bind_fails(self):
        verdict = parse("\n".join([DEATH, RECEIPT]))
        self.assertFalse(verdict["gate_ok"])
        self.assertTrue(verdict["dead"])

    def test_missing_death_fails(self):
        verdict = parse("\n".join([BIND, RECEIPT]))
        self.assertFalse(verdict["gate_ok"])

    def test_missing_receipt_fails(self):
        verdict = parse("\n".join([BIND, DEATH]))
        self.assertFalse(verdict["gate_ok"])
        self.assertTrue(verdict["bound"])
        self.assertTrue(verdict["dead"])

    def test_wrong_source_id_fails(self):
        other = DEATH.replace("source_id=34", "source_id=70")
        verdict = parse("\n".join([BIND, other, RECEIPT]))
        self.assertFalse(verdict["gate_ok"])

    def test_non_snakecrow_bind_ignored(self):
        other = BIND.replace("species=SnakeCrow", "species=SnakeWhole")
        verdict = parse("\n".join([other, DEATH, RECEIPT]))
        self.assertFalse(verdict["gate_ok"])

    def test_captain_down_blocks(self):
        text = "\n".join([BIND, DEATH, RECEIPT,
                          "P2_FIXTURE_CAPTAIN_DOWN tick=99 outcome=BLOCKED"])
        verdict = parse(text)
        self.assertFalse(verdict["gate_ok"])
        self.assertTrue(verdict["blocked"])
        self.assertEqual(verdict["block_reason"], "captain-down")

    def test_extinction_blocks(self):
        text = "\n".join([BIND, "GAMEEND_PikminExtinction"])
        verdict = parse(text)
        self.assertFalse(verdict["gate_ok"])
        self.assertTrue(verdict["blocked"])

    def test_empty_log_fails(self):
        verdict = parse("")
        self.assertFalse(verdict["gate_ok"])
        self.assertEqual(verdict["generator"], -1)
        self.assertFalse(verdict["blocked"])


if __name__ == "__main__":
    unittest.main()
