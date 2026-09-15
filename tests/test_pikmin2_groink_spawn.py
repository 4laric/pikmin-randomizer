"""Tests for experimental/pikmin2_groink_spawn (lane 21 source_id=78 gate 1).

The tests use the exact native evidence shapes for ordinary seed resolution and
accepted placement evidence, plus the explicit generated-claim and Groink bind
markers required by the future gate-1 acceptance contract. None of the latter
markers is currently emitted natively.
"""
import unittest

from experimental import pikmin2_groink_spawn as spawn

RESOLVE_LINE = "P2_SEED_RESOLVE source_id=78 target=402 original_type=0 x=1.0 z=2.0"
CLAIM_LINE = "P2_GENERATED_PLACEMENT source_id=78 target=402 bound=1"
PLACEMENT_LINE = ("P2_PLACEMENT_SLOT generator=201001 slot=402 actor=0 xyz=1 "
                  "terrain=ground route=1 route_distance=0.0 x=1.000 y=0.000 "
                  "z=2.000 water_depth=0.00")
BIND_LINE = "P2_GROINK_TEKI_BIND source_id=78 seed_target=402 generator=201001 bound=1"
CARCASS_READY_LINE = ("P2_GROINK_CARCASS_READY generator=201001 type=0 "
                      "gauge_delay=2.000 recovery=3.000 max_health=1200.000")


class Gate1NaturalSpawnContractTests(unittest.TestCase):
    def test_connected_generated_spawn_chain_passes(self):
        log = "\n".join((RESOLVE_LINE, CLAIM_LINE, PLACEMENT_LINE, BIND_LINE)) + "\n"
        evidence = spawn.validate_log(log)
        self.assertTrue(evidence["passed"])
        self.assertTrue(evidence["connected"])
        self.assertEqual(evidence["source_id"], 78)
        self.assertEqual(evidence["resolve_target"], "402")
        self.assertEqual(evidence["bind_target"], "402")
        self.assertEqual(evidence["bind_generator"], "201001")
        self.assertEqual(evidence["placement_slot"], "402")
        self.assertEqual(evidence["placement_generator"], "201001")
        self.assertEqual(evidence["resolve_line_number"], 1)
        self.assertEqual(evidence["bind_line_number"], 4)

    def test_placement_only_is_insufficient(self):
        evidence = spawn.validate_log(f"{PLACEMENT_LINE}\n")
        self.assertFalse(evidence["passed"])
        self.assertIsNone(evidence["resolve_line"])
        self.assertIsNone(evidence["bind_line"])
        self.assertIsNotNone(evidence["placement_line"])
        self.assertIn("P2_SEED_RESOLVE source_id=78", evidence["missing"])
        self.assertIn("P2_GROINK_TEKI_BIND source_id=78", evidence["missing"])

    def test_missing_generated_claim_fails(self):
        log = "\n".join((RESOLVE_LINE, PLACEMENT_LINE, BIND_LINE)) + "\n"
        evidence = spawn.validate_log(log)
        self.assertFalse(evidence["passed"])
        self.assertEqual(evidence["resolve_target"], "402")
        self.assertEqual(evidence["bind_target"], "402")
        self.assertIn("P2_GENERATED_PLACEMENT source_id=78", evidence["missing"])

    def test_missing_family_bind_fails(self):
        log = "\n".join((RESOLVE_LINE, CLAIM_LINE, PLACEMENT_LINE)) + "\n"
        evidence = spawn.validate_log(log)
        self.assertFalse(evidence["passed"])
        self.assertIsNone(evidence["bind_line"])
        self.assertEqual(evidence["resolve_target"], "402")
        self.assertIn("P2_GROINK_TEKI_BIND source_id=78", evidence["missing"])

    def test_seed_slot_and_physical_generator_must_join(self):
        bad_placement = PLACEMENT_LINE.replace("slot=402", "slot=403")
        log = "\n".join((RESOLVE_LINE, CLAIM_LINE, bad_placement, BIND_LINE)) + "\n"
        evidence = spawn.validate_log(log)
        self.assertFalse(evidence["passed"])
        self.assertEqual(evidence["resolve_target"], "402")
        self.assertEqual(evidence["placement_slot"], "403")
        self.assertEqual(evidence["bind_target"], "402")

    def test_seed_target_mismatch_fails(self):
        bad_bind = BIND_LINE.replace("seed_target=402", "seed_target=403")
        log = "\n".join((RESOLVE_LINE, CLAIM_LINE, PLACEMENT_LINE, bad_bind)) + "\n"
        evidence = spawn.validate_log(log)
        self.assertFalse(evidence["passed"])
        self.assertEqual(evidence["resolve_target"], "402")
        self.assertEqual(evidence["bind_target"], "403")

    def test_physical_generator_mismatch_fails(self):
        bad_bind = BIND_LINE.replace("generator=201001", "generator=201002")
        log = "\n".join((RESOLVE_LINE, CLAIM_LINE, PLACEMENT_LINE, bad_bind)) + "\n"
        evidence = spawn.validate_log(log)
        self.assertFalse(evidence["passed"])
        self.assertEqual(evidence["placement_generator"], "201001")
        self.assertEqual(evidence["bind_generator"], "201002")

    def test_fixture_carcass_ready_is_not_identity_bind(self):
        log = "\n".join((RESOLVE_LINE, PLACEMENT_LINE, CARCASS_READY_LINE)) + "\n"
        evidence = spawn.validate_log(log)
        self.assertFalse(evidence["passed"])
        self.assertIsNone(evidence["bind_line"])
        self.assertIn("P2_GROINK_TEKI_BIND source_id=78", evidence["missing"])

    def test_wrong_source_id_fails(self):
        log = "\n".join((
            RESOLVE_LINE.replace("source_id=78", "source_id=79"),
            CLAIM_LINE.replace("source_id=78", "source_id=79"),
            PLACEMENT_LINE,
            BIND_LINE.replace("source_id=78", "source_id=79"),
        )) + "\n"
        evidence = spawn.validate_log(log)
        self.assertFalse(evidence["passed"])
        self.assertIsNone(evidence["resolve_line"])
        self.assertIsNone(evidence["claim_line"])
        self.assertIsNone(evidence["bind_line"])
        self.assertIsNotNone(evidence["placement_line"])


if __name__ == "__main__":
    unittest.main()
