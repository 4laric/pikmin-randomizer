"""Focused tests for the P1 challenge campaign contract (#52).

No retail values are claimed beyond file hashes and observed record counts;
decode-path tests use the legal local asset tree read-only, and every
unverifiable gameplay semantic stays an explicit follow-on, never an
assertion.
"""

import unittest

from experimental.pikmin1_challenge_campaign_contract import (
    CheckLedger,
    ContractError,
    attempt_id,
    audit_stage,
    check_id,
    classify_state,
    parse_check_id,
    reward_threshold,
    stage_entry,
    stage_slots,
)

ASSETS = "C:/Users/alari/bbft/dist/cohesion/pikmin/assets"


class StageTableTests(unittest.TestCase):
    def test_five_slots_in_area_order(self):
        self.assertEqual(stage_slots(),
                         ["chal0", "chal1", "chal2", "chal3", "chal4"])

    def test_unknown_slot_rejected(self):
        with self.assertRaises(ContractError):
            stage_entry("chal9")

    def test_area_ids_unique(self):
        ids = [stage_entry(s)["area_id"] for s in stage_slots()]
        self.assertEqual(sorted(ids), [0, 1, 2, 3, 4])


class IdentityTests(unittest.TestCase):
    def test_attempt_id_deterministic(self):
        self.assertEqual(attempt_id("seed1", "chal2", 3), "seed1/chal2#3")
        self.assertEqual(attempt_id("seed1", "chal2", 3),
                         attempt_id("seed1", "chal2", 3))

    def test_attempt_id_rejects_bad_inputs(self):
        for seed, slot, index in [("", "chal0", 0), ("s", "chal9", 0),
                                  ("s", "chal0", -1), ("s", "chal0", "0")]:
            with self.assertRaises(ContractError):
                attempt_id(seed, slot, index)

    def test_check_id_roundtrip(self):
        value = check_id("chal4", "population", "tier-1")
        self.assertEqual(parse_check_id(value), ("chal4", "population", "tier-1"))

    def test_check_id_rejects_bad_slugs_and_slots(self):
        for args in [("chal9", "population", "tier-1"),
                     ("chal0", "Pop", "tier-1"),
                     ("chal0", "population", "tier 1"),
                     ("chal0", "", "tier-1")]:
            with self.assertRaises(ContractError):
                check_id(*args)
        with self.assertRaises(ContractError):
            parse_check_id("chal0:population")
        with self.assertRaises(ContractError):
            parse_check_id("chal9:population:tier-1")


class AuditTests(unittest.TestCase):
    def test_all_five_stages_audit_clean(self):
        for slot in stage_slots():
            with self.subTest(slot=slot):
                facts = audit_stage(ASSETS, slot)
                self.assertTrue(facts["ini_sha256"])
                self.assertGreater(facts["day_multiply"], 0)
                self.assertTrue(facts["map_file"])
                self.assertIn("default.gen", facts["generators"])
                self.assertIn("plants.gen", facts["generators"])

    def test_chal3_plants_variant_pinned_not_skipped(self):
        plants = audit_stage(ASSETS, "chal3")["generators"]["plants.gen"]
        self.assertTrue(plants["present"])
        self.assertFalse(plants["decoded"])
        self.assertIn("undecoded_variant", plants)
        self.assertTrue(plants["sha256"])

    def test_missing_assets_fail_closed(self):
        with self.assertRaises(ContractError):
            audit_stage("C:/nonexistent-assets-dir", "chal0")
        with self.assertRaises(ContractError):
            audit_stage(ASSETS, "chal9")


class StateBoundaryTests(unittest.TestCase):
    def test_classify_partitions(self):
        result = classify_state(["score", "awarded_checks", "timer", "upgrades"])
        self.assertEqual(result["attempt_local"], ["score", "timer"])
        self.assertEqual(result["persistent"], ["awarded_checks", "upgrades"])

    def test_unknown_state_key_rejected(self):
        with self.assertRaises(ContractError):
            classify_state(["score", "mystery_flag"])


class LedgerTests(unittest.TestCase):
    def test_award_is_exactly_once(self):
        ledger = CheckLedger()
        value = check_id("chal1", "population", "tier-1")
        self.assertTrue(ledger.award(value))
        self.assertFalse(ledger.award(value))
        self.assertTrue(ledger.has(value))
        self.assertEqual(ledger.awarded(), [value])

    def test_reconnect_reload_preserves_awards(self):
        value = check_id("chal2", "score", "tier-2")
        first = CheckLedger([value])
        second = CheckLedger(first.awarded())
        self.assertTrue(second.has(value))
        self.assertFalse(second.award(value))

    def test_malformed_check_rejected(self):
        ledger = CheckLedger()
        with self.assertRaises(ContractError):
            ledger.award("not-a-check")
        with self.assertRaises(ContractError):
            CheckLedger(["chal9:population:tier-1"])


class ThresholdTests(unittest.TestCase):
    def test_threshold_is_data_not_claim(self):
        record = reward_threshold("chal0", "population", 100)
        self.assertEqual(record["check"], "chal0:population:threshold")
        self.assertEqual(record["target"], 100)
        self.assertIn("unevaluated", record["achievability"])

    def test_threshold_rejects_bad_target(self):
        with self.assertRaises(ContractError):
            reward_threshold("chal0", "population", -5)


if __name__ == "__main__":
    unittest.main()