"""Contract tests for the leafchappy stage-table row provider (issue #774).

Pins the ch_ABEM_LeafChappy row values and exercises the fixture-log
validator: canonical agreement, double resolution, wrong cave/ui/floors,
injected markers, and empty logs. The native behavioral proof (row
resolution by the real lookup plus guard self-test/negative) lives in
native/tools/p2_leafchappy_stage_table_fixture.cpp; agreement here
alone never passes acceptance.
"""
import unittest

from experimental.pikmin2_leafchappy_stage_table_row import (
    PINNED,
    PROVIDER,
    provider_contract,
    validate_log,
)

GOOD = "\n".join([
    "P2_LEAFCHAPPY_STAGE_RESOLVED cave=ch_ABEM_LeafChappy ui=17 floors=2",
    "P2_LEAFCHAPPY_STAGE_REFUSED reason=unknown-key",
])


class ContractTests(unittest.TestCase):
    def test_contract_shape(self):
        contract = provider_contract()
        self.assertEqual(contract["schema"], PROVIDER)
        self.assertEqual(contract["consumer_issue"], 550)
        self.assertTrue(contract["exactly_once"])
        self.assertFalse(contract["runtime_claim"])
        self.assertIn("pc_bbft.cpp", contract["integration"])

    def test_pins(self):
        self.assertEqual(PINNED["cave_id"], "ch_ABEM_LeafChappy")
        self.assertEqual(PINNED["ui_index"], 17)
        self.assertEqual(PINNED["table_order"], 4)
        self.assertEqual(PINNED["floors"], 2)
        self.assertEqual(PINNED["floor_seconds"], [85.0, 100.0])
        self.assertEqual(PINNED["roster"][0], [10, 0, 0])
        self.assertEqual(PINNED["roster"][2], [10, 0, 0])
        self.assertEqual(PINNED["roster"][3], [0, 0, 0])
        self.assertEqual((PINNED["bitter_sprays"], PINNED["spicy_sprays"]), (1, 1))
        self.assertEqual(PINNED["legacy_time"], 400.0)
        self.assertEqual(PINNED["treasure_count_field"], 11)
        self.assertEqual(PINNED["source_sha256"],
                         "49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf")


class ValidateLogTests(unittest.TestCase):
    def test_canonical_log_agrees(self):
        result = validate_log(GOOD)
        self.assertTrue(result["verdict"], result["problems"])
        self.assertEqual(result["resolved"][0]["cave"], "ch_ABEM_LeafChappy")

    def test_double_resolution_refused(self):
        lines = GOOD + "\nP2_LEAFCHAPPY_STAGE_RESOLVED cave=ch_ABEM_LeafChappy ui=17 floors=2"
        result = validate_log(lines)
        self.assertFalse(result["verdict"])
        self.assertIn("resolved-count-2", result["problems"])

    def test_wrong_cave_refused(self):
        result = validate_log("P2_LEAFCHAPPY_STAGE_RESOLVED cave=ch_NARI_01kusachi ui=3 floors=1")
        self.assertFalse(result["verdict"])
        self.assertIn("wrong-cave:ch_NARI_01kusachi", result["problems"])

    def test_wrong_ui_refused(self):
        result = validate_log("P2_LEAFCHAPPY_STAGE_RESOLVED cave=ch_ABEM_LeafChappy ui=18 floors=2")
        self.assertFalse(result["verdict"])
        self.assertIn("wrong-ui:18", result["problems"])

    def test_wrong_floors_refused(self):
        result = validate_log("P2_LEAFCHAPPY_STAGE_RESOLVED cave=ch_ABEM_LeafChappy ui=17 floors=1")
        self.assertFalse(result["verdict"])
        self.assertIn("wrong-floors:1", result["problems"])

    def test_injected_markers_refused(self):
        result = validate_log(GOOD + "\nP2_LEAFCHAPPY_INJECT cave=ch_ABEM_LeafChappy")
        self.assertFalse(result["verdict"])
        self.assertIn("injected-markers-present", result["problems"])

    def test_empty_log_refused(self):
        result = validate_log("")
        self.assertFalse(result["verdict"])
        self.assertIn("resolved-count-0", result["problems"])


if __name__ == "__main__":
    unittest.main()
