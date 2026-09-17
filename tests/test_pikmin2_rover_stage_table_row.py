"""Contract tests for the rover stage-table row provider (issue #734).

Pins the ch_MAT_route_rover row values and exercises the fixture-log
validator: canonical agreement, double resolution, wrong cave/ui/floors,
injected markers, and empty logs. The native behavioral proof (26 checks)
lives in native/tools/p2_rover_stage_table_fixture.cpp; agreement here
alone never passes acceptance.
"""
import unittest

from experimental.pikmin2_rover_stage_table_row import (
    PINNED,
    PROVIDER,
    provider_contract,
    validate_log,
)

GOOD = "\n".join([
    "P2_ROVER_STAGE_RESOLVED cave=ch_MAT_route_rover ui=27 floors=1",
    "P2_ROVER_STAGE_REFUSED reason=unknown-key",
])


class ContractTests(unittest.TestCase):
    def test_contract_shape(self):
        contract = provider_contract()
        self.assertEqual(contract["schema"], PROVIDER)
        self.assertEqual(contract["consumer_issue"], 561)
        self.assertTrue(contract["exactly_once"])
        self.assertFalse(contract["runtime_claim"])
        self.assertIn("pc_bbft.cpp", contract["integration"])

    def test_pins(self):
        self.assertEqual(PINNED["cave_id"], "ch_MAT_route_rover")
        self.assertEqual(PINNED["ui_index"], 27)
        self.assertEqual(PINNED["table_order"], 21)
        self.assertEqual(PINNED["floors"], 1)
        self.assertEqual(PINNED["floor_seconds"], [90.0])
        self.assertEqual(PINNED["roster"][0], [0, 0, 20])
        self.assertEqual(PINNED["roster"][3], [0, 0, 0])
        self.assertEqual(PINNED["source_sha256"],
                         "e03eb33a78526adb13eebd08af453555bc9cd219f6a3e624b28a0771ea12cb79")


class ValidateLogTests(unittest.TestCase):
    def test_canonical_log_agrees(self):
        result = validate_log(GOOD)
        self.assertTrue(result["verdict"], result["problems"])
        self.assertEqual(result["resolved"][0]["cave"], "ch_MAT_route_rover")

    def test_double_resolution_refused(self):
        lines = GOOD + "\nP2_ROVER_STAGE_RESOLVED cave=ch_MAT_route_rover ui=27 floors=1"
        result = validate_log(lines)
        self.assertFalse(result["verdict"])
        self.assertIn("resolved-count-2", result["problems"])

    def test_wrong_cave_refused(self):
        result = validate_log("P2_ROVER_STAGE_RESOLVED cave=ch_NARI_01kusachi ui=3 floors=1")
        self.assertFalse(result["verdict"])
        self.assertIn("wrong-cave:ch_NARI_01kusachi", result["problems"])

    def test_wrong_ui_refused(self):
        result = validate_log("P2_ROVER_STAGE_RESOLVED cave=ch_MAT_route_rover ui=28 floors=1")
        self.assertFalse(result["verdict"])
        self.assertIn("wrong-ui:28", result["problems"])

    def test_wrong_floors_refused(self):
        result = validate_log("P2_ROVER_STAGE_RESOLVED cave=ch_MAT_route_rover ui=27 floors=2")
        self.assertFalse(result["verdict"])
        self.assertIn("wrong-floors:2", result["problems"])

    def test_injected_markers_refused(self):
        result = validate_log(GOOD + "\nP2_ROVER_INJECT cave=ch_MAT_route_rover")
        self.assertFalse(result["verdict"])
        self.assertIn("injected-markers-present", result["problems"])

    def test_empty_log_refused(self):
        result = validate_log("")
        self.assertFalse(result["verdict"])
        self.assertIn("resolved-count-0", result["problems"])


if __name__ == "__main__":
    unittest.main()
