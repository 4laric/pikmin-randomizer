"""Unit tests for the muse-ground Sokkuri79 delivery observer (#495).

No runtime, no injection: synthetic log strings only. Proves the validator
refuses natural transport PASS without carry proof, uncited claims, or
injected markers, and accepts the interface-level exactly-once shape.
"""

import unittest

from experimental.pikmin2_muse_ground import (
    gate_summary,
    parse_receipts,
    validate,
)

NATURAL_DEATH_LOG = """\
P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0
P2_SOKKURI_DELIVERY_BIND generator=346005 source_id=79
Experimental preview window set to 960x540 windowed and centered
P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=105.0
P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=15.0
P2_SOKKURI_DEAD generator=346005 source_id=79 health=0 prior_health=15.0
P2_SOKKURI_NATURAL_CORPSE pellet=1
PASS P2_SOKKURI_NATURAL_RUNTIME death=natural corpse=1 cleanup=1 reentry=1 injected=0
"""

RECEIPT_ONLY_LOG = NATURAL_DEATH_LOG + """\
[Pikmin Randomizer] P2_ORDINARY_P2_RECEIPT seed=abc123 id=onion:p2:79:1 generator=346005 new=1
"""

CARRY_LOG = RECEIPT_ONLY_LOG + """\
P2_SOKKURI_CARRY_GRASP generator=346005 carriers=3
P2_SOKKURI_CARRY_HAUL generator=346005 dist=12.0 onion=1
"""

INJECTED_LOG = NATURAL_DEATH_LOG + """\
P2_LIFECYCLE_INJECT species=Sokkuri,Armor injected_health=0 source=fixture not_natural_combat=1
[Pikmin Randomizer] P2_ORDINARY_P2_RECEIPT seed=abc123 id=onion:p2:79:1 generator=346005 new=1
"""


class MuseGroundValidatorTests(unittest.TestCase):
    def test_natural_death_chain_without_receipt_is_untransported(self):
        r = validate(NATURAL_DEATH_LOG)
        self.assertTrue(r["checks"]["identity"])
        self.assertTrue(r["checks"]["natural_damage"])
        self.assertTrue(r["checks"]["natural_death"])
        self.assertTrue(r["checks"]["small_prior_health"])
        self.assertTrue(r["checks"]["no_inject"])
        self.assertTrue(r["checks"]["corpse"])
        self.assertFalse(r["checks"]["ordinary_receipt"])
        self.assertEqual(r["transport_gate"], "untested")

    def test_receipt_without_carry_stays_interface_only(self):
        r = validate(RECEIPT_ONLY_LOG)
        self.assertTrue(r["checks"]["ordinary_receipt"])
        self.assertTrue(r["checks"]["interface_exactly_once"])
        self.assertFalse(r["checks"]["natural_carry"])
        self.assertEqual(r["transport_gate"], "untested")
        self.assertIn("interface-only", r["transport_reason"])

    def test_receipt_plus_carry_closes_transport(self):
        r = validate(CARRY_LOG)
        self.assertTrue(r["checks"]["natural_carry"])
        self.assertEqual(r["transport_gate"], "pass")

    def test_injected_log_never_passes_transport(self):
        r = validate(INJECTED_LOG)
        self.assertFalse(r["checks"]["no_inject"])
        self.assertEqual(r["transport_gate"], "untested")

    def test_large_prior_health_fails_small_prior(self):
        log = NATURAL_DEATH_LOG.replace("prior_health=15.0", "prior_health=120.0")
        r = validate(log)
        self.assertFalse(r["checks"]["small_prior_health"])

    def test_duplicate_grant_breaks_exactly_once(self):
        log = RECEIPT_ONLY_LOG + (
            "[Pikmin Randomizer] P2_ORDINARY_P2_RECEIPT seed=abc123 "
            "id=onion:p2:79:1 generator=346005 new=1\n"
        )
        r = validate(log)
        self.assertFalse(r["checks"]["interface_exactly_once"])
        self.assertEqual(len(parse_receipts(log)), 2)

    def test_duplicate_new_zero_keeps_exactly_once(self):
        log = RECEIPT_ONLY_LOG + (
            "[Pikmin Randomizer] P2_ORDINARY_P2_RECEIPT seed=abc123 "
            "id=onion:p2:79:1 generator=346005 new=0\n"
        )
        r = validate(log)
        self.assertTrue(r["checks"]["interface_exactly_once"])

    def test_missing_delivery_bind_fails_identity(self):
        log = NATURAL_DEATH_LOG.replace(
            "P2_SOKKURI_DELIVERY_BIND generator=346005 source_id=79\n", ""
        )
        r = validate(log)
        self.assertFalse(r["checks"]["identity"])

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate(None)

    def test_gate_summary_mentions_transport(self):
        self.assertIn("transport=untested", gate_summary(validate(RECEIPT_ONLY_LOG)))
        self.assertIn("transport=pass", gate_summary(validate(CARRY_LOG)))


if __name__ == "__main__":
    unittest.main()
