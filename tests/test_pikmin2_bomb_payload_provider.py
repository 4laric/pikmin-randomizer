"""Contract tests for the Bomb payload provider (issue #577).

Pins the shared-blast defaults and exercises the consumer-log validator:
canonical lifecycle agreement, double-detonation refusal, missing attach,
unknown trigger, injected markers, and malformed/empty logs. The native
behavioral proof (65 checks) lives in
native/tools/p2_bomb_payload_actor_test.cpp; agreement here alone never
passes acceptance.
"""
import unittest

from experimental.pikmin2_bomb_payload_provider import (
    BLAST_DEFAULTS,
    PROVIDER,
    provider_contract,
    validate_log,
)

GOOD = "\n".join([
    "P2_BOMB_PAYLOAD_BIRTH carrier=41 slot=0 gen=1",
    "P2_BOMB_PAYLOAD_ATTACH carrier=41 joint=otakara",
    "P2_BOMB_PAYLOAD_DETONATE carrier=41 trigger=contact detonated=1",
    "P2_BOMB_PAYLOAD_BLAST carrier=41 receivers=2 hits=2",
])


class ContractTests(unittest.TestCase):
    def test_contract_shape(self):
        contract = provider_contract()
        self.assertEqual(contract["schema"], PROVIDER)
        self.assertEqual(contract["consumer_issue"], 573)
        self.assertTrue(contract["exactly_once"])
        self.assertFalse(contract["runtime_claim"])
        self.assertEqual(sorted(contract["triggers"]),
                         ["contact", "death", "earthquake", "press"])

    def test_blast_defaults_pinned(self):
        self.assertEqual(BLAST_DEFAULTS, {
            "radius": 90.0,
            "half_height": 50.0,
            "teki_damage": 500.0,
            "navi_piki_damage": 10.0,
        })


class ValidateLogTests(unittest.TestCase):
    def test_canonical_lifecycle_agrees(self):
        result = validate_log(GOOD)
        self.assertTrue(result["verdict"], result["problems"])
        self.assertEqual(result["carriers"][41]["detonated"], 1)

    def test_double_detonation_refused(self):
        lines = GOOD + "\nP2_BOMB_PAYLOAD_DETONATE carrier=41 trigger=press detonated=1"
        result = validate_log(lines)
        self.assertFalse(result["verdict"])
        self.assertIn("carrier-41-double-detonation", result["problems"])

    def test_missing_attach_refused(self):
        lines = "\n".join(l for l in GOOD.splitlines() if "ATTACH" not in l)
        result = validate_log(lines)
        self.assertFalse(result["verdict"])
        self.assertIn("carrier-41-no-attach", result["problems"])

    def test_unknown_trigger_refused(self):
        lines = GOOD.replace("trigger=contact", "trigger=magic")
        result = validate_log(lines)
        self.assertFalse(result["verdict"])

    def test_injected_markers_refused(self):
        lines = GOOD + "\nP2_BOMBOTAKARA_INJECT_1 99 41 contact"
        result = validate_log(lines)
        self.assertFalse(result["verdict"])
        self.assertTrue(result["injected"])
        self.assertIn("injected-markers-present", result["problems"])

    def test_empty_log_refused(self):
        result = validate_log("")
        self.assertFalse(result["verdict"])
        self.assertIn("no-carriers", result["problems"])

    def test_suppressed_second_trigger_ok(self):
        lines = GOOD + "\nP2_BOMB_PAYLOAD_DETONATE carrier=41 trigger=press detonated=0"
        result = validate_log(lines)
        self.assertTrue(result["verdict"], result["problems"])
        self.assertEqual(result["carriers"][41]["suppressed"], 1)

    def test_detach_reason_recorded(self):
        lines = GOOD + "\nP2_BOMB_PAYLOAD_DETACH carrier=41 reason=carrier_death"
        result = validate_log(lines)
        self.assertTrue(result["verdict"], result["problems"])
        self.assertEqual(result["carriers"][41]["detach"], ["carrier_death"])


if __name__ == "__main__":
    unittest.main()
