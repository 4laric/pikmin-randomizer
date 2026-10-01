"""Contract tests for the generic held-object provider (issue #614).

Pins the provider contract and receipt-key mapping, and exercises the
consumer-log validator: canonical lifecycle agreement, double-release and
double-reward refusal, missing follow/detach, bad reason, injected
markers, and malformed/empty logs. The native behavioral proof (67 checks)
lives in native/tools/p2_held_object_test.cpp; agreement here alone never
passes acceptance.
"""
import unittest

from experimental.pikmin2_held_object_provider import (
    PROVIDER,
    provider_contract,
    receipt_keys,
    validate_log,
)

GOOD = "\n".join([
    "P2_HELD_OBJECT_ATTACH carrier=41 item=7 slot=0 gen=1",
    "P2_HELD_OBJECT_FOLLOW carrier=41",
    "P2_HELD_OBJECT_DETACH carrier=41 reason=dropped",
    "P2_HELD_OBJECT_RELEASE carrier=41 item=7 delivered=1",
    "P2_HELD_OBJECT_REWARD carrier=41 granted=1",
])


class ContractTests(unittest.TestCase):
    def test_contract_shape(self):
        contract = provider_contract()
        self.assertEqual(contract["schema"], PROVIDER)
        self.assertEqual(contract["consumer_issues"], [574])
        self.assertEqual(contract["exactly_once"], ["release", "confirmReward"])
        self.assertFalse(contract["runtime_claim"])
        self.assertEqual(contract["reward_routing"]["grant_api"],
                         "pc_p2_receipt_host_grant")
        self.assertEqual(contract["reward_routing"]["encounter"], "held-release")

    def test_receipt_keys_shape(self):
        keys = receipt_keys(41, 7, "seed9")
        self.assertEqual(keys, {"seed": "seed9", "reward": "treasure:7",
                                "slot": "41", "encounter": "held-release"})

    def test_receipt_keys_reject_bad_inputs(self):
        with self.assertRaises(ValueError):
            receipt_keys(0, 7, "seed9")
        with self.assertRaises(ValueError):
            receipt_keys(41, 0, "seed9")
        with self.assertRaises(ValueError):
            receipt_keys(41, 7, "")


class ValidateLogTests(unittest.TestCase):
    def test_canonical_lifecycle_agrees(self):
        result = validate_log(GOOD)
        self.assertTrue(result["verdict"], result["problems"])
        self.assertEqual(result["carriers"][41]["delivered"], 1)

    def test_double_release_refused(self):
        lines = GOOD + "\nP2_HELD_OBJECT_RELEASE carrier=41 item=7 delivered=1"
        result = validate_log(lines)
        self.assertFalse(result["verdict"])
        self.assertIn("carrier-41-double-release", result["problems"])
        self.assertIn("carrier-41-double-delivery", result["problems"])

    def test_double_reward_refused(self):
        lines = GOOD + "\nP2_HELD_OBJECT_REWARD carrier=41 granted=0"
        result = validate_log(lines)
        self.assertFalse(result["verdict"])
        self.assertIn("carrier-41-double-reward", result["problems"])

    def test_missing_follow_refused(self):
        lines = "\n".join(l for l in GOOD.splitlines() if "FOLLOW" not in l)
        result = validate_log(lines)
        self.assertFalse(result["verdict"])
        self.assertIn("carrier-41-no-follow", result["problems"])

    def test_missing_detach_refused(self):
        lines = "\n".join(l for l in GOOD.splitlines() if "DETACH" not in l)
        result = validate_log(lines)
        self.assertFalse(result["verdict"])
        self.assertIn("carrier-41-no-detach", result["problems"])

    def test_bad_reason_recorded(self):
        lines = GOOD.replace("reason=dropped", "reason=vaporized")
        result = validate_log(lines)
        self.assertFalse(result["verdict"])
        self.assertIn("carrier-41-bad-reason:vaporized", result["problems"])

    def test_injected_markers_refused(self):
        result = validate_log(GOOD + "\nP2_HELD_OBJECT_INJECT carrier=41")
        self.assertFalse(result["verdict"])
        self.assertIn("injected-markers-present", result["problems"])

    def test_empty_log_refused(self):
        result = validate_log("")
        self.assertFalse(result["verdict"])
        self.assertIn("no-carriers", result["problems"])


if __name__ == "__main__":
    unittest.main()
