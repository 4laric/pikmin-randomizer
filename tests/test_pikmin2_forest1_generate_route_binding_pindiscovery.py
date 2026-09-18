"""Fail-closed tests for the forest1 route-binding pin-discovery (#801).

Read-only pin-discovery: these tests pin the callsite table, the grammar
extension, the manifest adjudicator (BOUND / SPAWN_ROUTE_BINDING_MISSING /
MALFORMED) and the downstream resume gate. They never build or edit engine
files and claim no acceptance.
"""
import unittest

from experimental.pikmin2_forest1_generate_route_binding_pindiscovery import (
    CALLSITES,
    DEFECT,
    DOWNSTREAM_ISSUE,
    FIRST_SLICE,
    OWNER_LINE,
    PACKET,
    adjudicate,
    packet,
    parse_spawns,
    resume_disposition,
)

# Real defect shape: no route field on any spawn line.
UNBOUND = "\n".join([
    "P2_CAVE_GENERATE_1",
    "pool units 2",
    "spawns 2",
    "spawn UjiA 6",
    "spawn UjiB 4",
    "anchor hole",
])

# Extended grammar: every spawn carries a route group.
BOUND = "\n".join([
    "P2_CAVE_GENERATE_1",
    "spawns 2",
    "spawn UjiA 6 test",
    "spawn UjiB 4 test",
    "anchor hole",
])

SAME_LINE = "\n".join([
    "P2_CAVE_GENERATE_1",
    "spawns 1",
    "spawn UjiA 6 test",
    "anchor hole",
])


class ParseTests(unittest.TestCase):
    def test_unbound_parses(self):
        spawns = parse_spawns(UNBOUND)
        self.assertEqual([s["id"] for s in spawns], ["UjiA", "UjiB"])
        self.assertEqual([s["route"] for s in spawns], [None, None])

    def test_bound_parses(self):
        spawns = parse_spawns(BOUND)
        self.assertEqual([s["route"] for s in spawns], ["test", "test"])

    def test_same_line_count(self):
        self.assertEqual(len(parse_spawns(SAME_LINE)), 1)

    def test_missing_header_refused(self):
        with self.assertRaises(ValueError):
            parse_spawns("spawns 1\nspawn A 1 test\nanchor hole\n")

    def test_missing_spawns_block_refused(self):
        with self.assertRaises(ValueError):
            parse_spawns("P2_CAVE_GENERATE_1\nanchor hole\n")

    def test_malformed_spawn_refused(self):
        with self.assertRaises(ValueError):
            parse_spawns("P2_CAVE_GENERATE_1\nspawns 1\nspawn A x test\nanchor hole\n")

    def test_count_mismatch_refused(self):
        with self.assertRaises(ValueError):
            parse_spawns("P2_CAVE_GENERATE_1\nspawns 3\nspawn A 1 test\nanchor hole\n")


class AdjudicateTests(unittest.TestCase):
    def test_defect_shape(self):
        r = adjudicate(UNBOUND)
        self.assertEqual(r["verdict"], DEFECT)
        self.assertEqual(r["unbound"], ["UjiA", "UjiB"])

    def test_bound_shape(self):
        self.assertEqual(adjudicate(BOUND)["verdict"], "BOUND")

    def test_malformed_shape(self):
        self.assertEqual(adjudicate("nonsense")["verdict"], "MALFORMED")

    def test_resume_gate(self):
        self.assertFalse(resume_disposition(DEFECT)["resume"])
        self.assertTrue(resume_disposition("BOUND")["resume"])
        self.assertFalse(resume_disposition("MALFORMED")["resume"])


class PacketTests(unittest.TestCase):
    def test_identity(self):
        p = packet()
        self.assertEqual(p["schema"], PACKET)
        self.assertEqual(p["consumer_issue"], 773)
        self.assertEqual(p["downstream_issue"], DOWNSTREAM_ISSUE)
        self.assertEqual(p["defect"], DEFECT)
        self.assertFalse(p["runtime_claim"])

    def test_callsites_named(self):
        symbols = [c["symbol"] for c in CALLSITES]
        self.assertTrue(any("readManifest" in s for s in symbols))
        self.assertTrue(any("struct Spawn" in s for s in symbols))
        self.assertTrue(all("file" in c and "status" in c for c in CALLSITES))

    def test_first_slice_reserves(self):
        self.assertIn("native/pc_port/pc_p2_cave_generate.h",
                      FIRST_SLICE["reserve"])
        self.assertEqual(FIRST_SLICE["provider_shard"], "provider-cave-generation")
        self.assertIn("#129", OWNER_LINE)


if __name__ == "__main__":
    unittest.main()