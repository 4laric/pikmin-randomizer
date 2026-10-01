"""Focused fail-closed tests for the Catfish26 natural-kill prerequisite decision (#800)."""
import unittest

from experimental.pikmin2_catfish26_natural_kill_prereq import (
    PrereqError, PRODUCER_RECEIVER, PRODUCER_WHITE, adjudicate)

OBSERVED = {
    "poison_implemented": True,
    "white_sidecar_present": False,
    "white_models_present": False,
    "catfish_module_available": True,
    "catfish_module_in_maintained": False,
    "catfish_module_in_cmake": False,
}


class DecisionTests(unittest.TestCase):
    def test_observed_inputs_select_receiver_producer(self):
        r = adjudicate(dict(OBSERVED))
        self.assertEqual(r["decision"], PRODUCER_RECEIVER)
        self.assertEqual(r["producer_lane"], PRODUCER_RECEIVER)
        self.assertIsNotNone(r["blocked_on"])
        self.assertIn("user_asset", r["blocked_on"])
        self.assertTrue(r["callsites"])
        self.assertTrue(r["build_membership"])

    def test_white_assets_present_select_white_staging(self):
        o = dict(OBSERVED, white_sidecar_present=True, white_models_present=True)
        r = adjudicate(o)
        self.assertEqual(r["decision"], PRODUCER_WHITE)
        self.assertIsNone(r["blocked_on"])

    def test_poison_missing_is_refused(self):
        with self.assertRaises(PrereqError):
            adjudicate(dict(OBSERVED, poison_implemented=False))

    def test_no_producer_is_refused(self):
        with self.assertRaises(PrereqError):
            adjudicate(dict(OBSERVED, catfish_module_available=False))

    def test_missing_input_is_refused(self):
        o = dict(OBSERVED)
        del o["white_sidecar_present"]
        with self.assertRaises(PrereqError):
            adjudicate(o)

    def test_wrong_type_is_refused(self):
        with self.assertRaises(PrereqError):
            adjudicate(dict(OBSERVED, white_sidecar_present="yes"))

    def test_non_mapping_is_refused(self):
        with self.assertRaises(PrereqError):
            adjudicate(["not", "a", "mapping"])

    def test_consumer_command_is_remapped_to_783(self):
        r = adjudicate(dict(OBSERVED))
        c = r["downstream_consumer"]
        self.assertEqual(c["issue"], 783)
        self.assertEqual(c["lane"], "shard-enemies-5-catfish26-observer")
        self.assertIn("P2_CATFISH_DEAD", c["expected"])

    def test_packet_schema_and_gates(self):
        r = adjudicate(dict(OBSERVED))
        self.assertEqual(r["schema"], 1)
        self.assertIs(r["admit"], False)
        self.assertEqual(set(r["gates"]), {
            "identity_spawn", "movement_animation", "attacks_receivers",
            "death_corpse", "transport_reward", "cleanup_reentry"})
        self.assertTrue(all(v == "UNTESTED" for v in r["gates"].values()))

    def test_citations_are_file_line(self):
        r = adjudicate(dict(OBSERVED))
        self.assertTrue(any("pc_p2_catfish.cpp:374" in c for c in r["citations"]))
        self.assertTrue(any("pc_p2_white.cpp:59" in c for c in r["citations"]))


if __name__ == "__main__":
    unittest.main()
