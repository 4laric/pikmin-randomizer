"""Focused tests for the Catfish26 receiver review checker (#641).

No retail values are claimed and no gates are passed: every test pins the
checker's fail-closed log-reading behavior, including the missing corpse
registration finding and injected-taint labelling.
"""

import unittest

from experimental.pikmin2_catfish26_receiver_review import review_log

GEN = 221001

BIND = "P2_CATFISH_BIND generator=%d source_id=26 visual_only=0" % GEN
READY = ("P2_ENEMY_READY species=Catfish native_family=Namazu generator=%d "
         "health=1500.0" % GEN)
BITE = "P2_CATFISH_BITE generator=%d" % GEN
EAT = "P2_CATFISH_EAT generator=%d pikmin=1 slot=0" % GEN
FLICK = "P2_CATFISH_FLICK generator=%d" % GEN
ATTACK = ("P2_CATFISH_ATTACK_NAVI generator=%d frame=17 damage=300.0" % GEN)
DEAD = "P2_CATFISH_DEAD generator=%d source_id=26 health=0" % GEN


class ReviewLogTests(unittest.TestCase):
    def test_full_attack_chain_without_corpse_reports_missing(self):
        verdict = review_log("\n".join([BIND, READY, BITE, EAT, FLICK, ATTACK, DEAD]))
        self.assertEqual(verdict["binding_generators"], [str(GEN)])
        self.assertTrue(all(verdict["attack_legs"].values()))
        self.assertEqual(verdict["death_generators"], [str(GEN)])
        self.assertFalse(verdict["corpse_registration"])
        self.assertTrue(any(f.startswith("missing-registration")
                            for f in verdict["findings"]))
        self.assertEqual(verdict["gate_claim"], "none: review only")

    def test_corpse_receipt_marks_registration(self):
        log = "\n".join([BIND, DEAD,
                         "P2_CATFISH_CORPSE_READY generator=%d source_id=26 "
                         "receipt=corpse:catfish:%d" % (GEN, GEN)])
        verdict = review_log(log)
        self.assertTrue(verdict["corpse_registration"])
        self.assertEqual(verdict["corpse_receipt_generators"], [str(GEN)])
        self.assertFalse(any(f.startswith("missing-registration")
                             for f in verdict["findings"]))

    def test_unbound_log_cannot_attribute_legs(self):
        verdict = review_log("\n".join([BITE, EAT]))
        self.assertFalse(verdict["binding_generators"])
        self.assertTrue(any("no actor bound" in f for f in verdict["findings"]))

    def test_bound_without_attack_legs_flagged(self):
        verdict = review_log(BIND)
        self.assertTrue(any("no attack leg" in f for f in verdict["findings"]))

    def test_wrong_source_id_ignored(self):
        verdict = review_log(
            "P2_CATFISH_BIND generator=%d source_id=27" % GEN)
        self.assertFalse(verdict["binding_generators"])

    def test_injected_taint_labelled(self):
        verdict = review_log("\n".join([
            BIND, DEAD,
            "P2_CATFISH_DEAD generator=%d source_id=26 health=0 injected" % GEN]))
        self.assertTrue(verdict["tainted_lines"])
        self.assertTrue(any(f.startswith("injected-taint")
                            for f in verdict["findings"]))

    def test_empty_log_absent(self):
        verdict = review_log("")
        self.assertTrue(any(f.startswith("absent-markers")
                            for f in verdict["findings"]))

    def test_other_family_markers_ignored(self):
        verdict = review_log("\n".join([
            "P2_SARAI_CORPSE_READY generator=385875968 source_id=23 "
            "receipt=corpse:sarai:385875968",
            "P2_KURAGE_CORPSE_READY generator=201001 source_id=57 "
            "receipt=corpse:kurage:201001"]))
        self.assertFalse(verdict["binding_generators"])
        self.assertFalse(verdict["corpse_registration"])
        self.assertFalse(verdict["death_generators"])


if __name__ == "__main__":
    unittest.main()