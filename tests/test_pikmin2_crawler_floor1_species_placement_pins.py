"""Focused fail-closed tests for the crawler floor-1 pins registry (#778).

Hermetic: validates the registry shape, the ABSENT verdicts with named
owners, and the downstream spec outlines. No engine, no build, no runtime.
"""

import importlib.util
import unittest
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "experimental" / "pikmin2_crawler_floor1_species_placement_pins.py"
spec = importlib.util.spec_from_file_location("p2_crawler_pins", MOD)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class PinsRegistryTests(unittest.TestCase):
    def test_registry_schema(self):
        r = adapter.registry()
        self.assertEqual(r["schema"], adapter.SCHEMA)
        self.assertEqual(r["consumer"]["issue"], 562)
        self.assertEqual(r["stage"], "ch_MAT_crawler")
        self.assertEqual(r["floor"], 1)

    def test_species_absent_with_owners(self):
        for name, rid in (("Wealthy", 10), ("Hana", 84), ("Ooinu_s", 49)):
            v = adapter.species_verdict(name)
            self.assertEqual(v["roster_id"], rid)
            self.assertEqual(v["status"], "ABSENT")
            self.assertTrue(v["owner"])
            self.assertTrue(v["decomp"])

    def test_ooinu_is_flora_not_enemy(self):
        v = adapter.species_verdict("Ooinu_s")
        self.assertIn("flora", v["owner"].lower() + v["note"].lower())

    def test_unknown_species_keyerror(self):
        with self.assertRaises(KeyError):
            adapter.species_verdict("NoSuchBeast")

    def test_gate_absent_with_owner(self):
        g = adapter.gate_verdict()
        self.assertEqual(g["status"], "ABSENT")
        self.assertIn("570", g["owner"])

    def test_collision_absent_with_owner(self):
        c = adapter.collision_routes_verdict()
        self.assertEqual(c["status"], "ABSENT")
        self.assertTrue(c["owner"])
        self.assertTrue(c["nearest_generic"])

    def test_generic_context_not_species_proof(self):
        g = adapter.registry()["generic_spawn_context"]
        self.assertEqual(g["status"], "PRESENT_GENERIC")

    def test_downstream_specs_have_owners(self):
        for s in adapter.downstream_specs():
            self.assertTrue(s["title"])
            self.assertTrue(s["owner"])
            self.assertTrue(s["depends_on"])

    def test_guard_hash_shape(self):
        self.assertEqual(len(adapter.GUARD_SHA256), 64)


if __name__ == "__main__":
    unittest.main()
