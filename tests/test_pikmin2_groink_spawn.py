"""Tests for experimental/pikmin2_groink_spawn (lane 21 source_id=78 gate 1).

Guards the root-side gate 1 co-occurrence validator: a ``P2_SEED_RESOLVE
source_id=78`` line and a same-run MiniHoudai bind/ready marker
(``P2_GROINK_TEKI_*`` or ``P2_GROINK_CARCASS_READY``) must share the same
generator. ``P2_PLACEMENT_SLOT`` presence is informational only and never
sufficient for a pass.
"""
import unittest

from experimental import pikmin2_groink_spawn as spawn

RESOLVE_LINE = "P2_SEED_RESOLVE source_id=78 generator=201001 target=0 seed=4242"
BIND_TEKI_LINE = "P2_GROINK_TEKI_BIND generator=201001 type=0"
BIND_READY_LINE = "P2_GROINK_CARCASS_READY generator=201001 type=0 gauge_delay=2.000 recovery=3.000 max_health=1200.000"
PLACEMENT_LINE = "P2_PLACEMENT_SLOT generator=201001 slot=3"


class Gate1CooccurrenceTests(unittest.TestCase):
    def test_valid_shared_generator_cooccurrence(self):
        log = f"{RESOLVE_LINE}\n{BIND_TEKI_LINE}\n"
        evidence = spawn.validate_log(log)
        self.assertTrue(evidence["passed"])
        self.assertTrue(evidence["cooccurs"])
        self.assertEqual(evidence["generator"], 201001)
        self.assertEqual(evidence["resolve_line"], RESOLVE_LINE)
        self.assertEqual(evidence["resolve_line_number"], 1)
        self.assertEqual(evidence["bind_line"], BIND_TEKI_LINE)
        self.assertEqual(evidence["bind_line_number"], 2)

    def test_valid_cooccurrence_with_ready_form(self):
        log = f"{RESOLVE_LINE}\n{BIND_READY_LINE}\n"
        evidence = spawn.validate_log(log)
        self.assertTrue(evidence["passed"])
        self.assertTrue(evidence["cooccurs"])
        self.assertEqual(evidence["generator"], 201001)

    def test_missing_resolve(self):
        evidence = spawn.validate_log(f"{BIND_TEKI_LINE}\n")
        self.assertFalse(evidence["passed"])
        self.assertFalse(evidence["cooccurs"])
        self.assertIsNone(evidence["resolve_line"])
        self.assertIsNone(evidence["resolve_line_number"])
        self.assertIsNone(evidence["generator"])
        self.assertIn(spawn.RESOLVE_MARKER, evidence["missing"])

    def test_missing_bind(self):
        evidence = spawn.validate_log(f"{RESOLVE_LINE}\n")
        self.assertFalse(evidence["passed"])
        self.assertFalse(evidence["cooccurs"])
        self.assertIsNone(evidence["bind_line"])
        self.assertIsNone(evidence["bind_line_number"])
        self.assertIsNone(evidence["generator"])

    def test_generator_mismatch(self):
        log = f"{RESOLVE_LINE}\nP2_GROINK_TEKI_BIND generator=201002 type=0\n"
        evidence = spawn.validate_log(log)
        self.assertFalse(evidence["passed"])
        self.assertFalse(evidence["cooccurs"])
        self.assertIsNone(evidence["generator"])
        self.assertEqual(evidence["resolve_generator"], 201001)
        self.assertEqual(evidence["bind_generator"], 201002)

    def test_placement_slot_presence(self):
        log = f"{RESOLVE_LINE}\n{BIND_TEKI_LINE}\n{PLACEMENT_LINE}\n"
        evidence = spawn.validate_log(log)
        self.assertTrue(evidence["passed"])
        self.assertTrue(evidence["cooccurs"])
        self.assertTrue(evidence["has_placement"])
        self.assertEqual(evidence["placement_line"], PLACEMENT_LINE)
        self.assertEqual(evidence["placement_line_number"], 3)

    def test_fixture_only_bind_without_resolve(self):
        log = f"{BIND_TEKI_LINE}\n{PLACEMENT_LINE}\n"
        evidence = spawn.validate_log(log)
        self.assertTrue(evidence["has_placement"])
        self.assertIsNotNone(evidence["bind_line"])
        self.assertFalse(evidence["passed"])
        self.assertFalse(evidence["cooccurs"])
        self.assertIsNone(evidence["generator"])


if __name__ == "__main__":
    unittest.main()
