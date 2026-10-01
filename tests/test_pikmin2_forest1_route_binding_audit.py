"""Focused tests for the forest1 route/spawn binding audit (issue #796).

Synthetic inputs only: real defect shape, healthy shape, partial spawn set,
malformed/missing input, and disposition gates. The real-evidence audit is
run separately against the pinned collision-obs files.
"""
import importlib.util
import unittest
from pathlib import Path

def _root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "experimental" / "pikmin2_forest1_route_binding_audit.py").is_file():
            return parent
    raise AssertionError("Lane root with the audit module not found")


ROOT = _root()
spec = importlib.util.spec_from_file_location(
    "forest1_route_binding_audit",
    ROOT / "experimental" / "pikmin2_forest1_route_binding_audit.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

GENERATE_DEFECT = "\n".join([
    "P2_CAVE_GENERATE_1",
    "pool 1_units_cent3_tsuchi.txt 7",
    "unit 0 item_cap_tsuchi 1 1 0",
    "rooms 1",
    "room 0 0 0 0 0 0",
    "doors 0",
    "links 0",
    "spawns 2",
    "spawn UjiA 6",
    "spawn UjiB 4",
    "anchor hole",
]) + "\n"

RUNLOG_DEFECT = "\n".join([
    "[PC Route] group 0: id='test' points=64",
    "[PC Route] group 1: id='tkch' points=0",
    "P2_CAVE_READY floor=1 survivors=20 health=1",
    "P2_FOREST1_COLLISION_ENTRY_READY floor=1 observed=2",
    "P2_FOREST1_BIRTH id=2370202546432 tick=2 x=173.6 y=0.0 z=-143.2",
    "P2_FOREST1_CONTACT id=2370202546432 tick=2 y=0.0 ground=0.0",
    "P2_FOREST1_COLLISION_OBSERVE observed=20000 squad=0 births=1 grounded=1 moved=0 live_actors=1",
]) + "\n"

RUNLOG_HEALTHY = RUNLOG_DEFECT.replace(
    "P2_FOREST1_COLLISION_OBSERVE observed=20000 squad=0 births=1 grounded=1 moved=0 live_actors=1",
    "P2_FOREST1_TRAVERSE id=1 tick=900\n"
    "P2_FOREST1_COLLISION_OBSERVE observed=20000 squad=20 births=1 grounded=1 moved=1 live_actors=1")


class ParseTests(unittest.TestCase):
    def test_parse_generate(self):
        parsed = adapter.parse_generate(GENERATE_DEFECT)
        self.assertEqual(parsed["spawns"], [("UjiA", 6), ("UjiB", 4)])
        self.assertEqual(parsed["requested_actors"], 10)
        self.assertEqual(parsed["spawn_lines"], 2)
        self.assertEqual(parsed["anchor"], "hole")
        self.assertFalse(parsed["carries_route_group"])

    def test_parse_runlog(self):
        parsed = adapter.parse_runlog(RUNLOG_DEFECT)
        self.assertEqual(parsed["birth_count"], 1)
        self.assertEqual(parsed["route_points"], 64)
        self.assertEqual(parsed["traverses"], 0)
        self.assertEqual(parsed["final_observe"], (20000, 0, 1, 1, 0, 1))

    def test_malformed_input_fails_closed(self):
        with self.assertRaises(ValueError):
            adapter.parse_generate("")
        with self.assertRaises(ValueError):
            adapter.parse_generate("P2_CAVE_GENERATE_1\nanchor hole\n")
        with self.assertRaises(ValueError):
            adapter.parse_runlog("")


class AdjudicateTests(unittest.TestCase):
    def test_named_defect(self):
        result = adapter.audit(GENERATE_DEFECT, RUNLOG_DEFECT)
        self.assertEqual(result["verdict"]["verdict"], "DEFECT")
        self.assertEqual(result["verdict"]["defect"],
                         "SPAWN_ROUTE_BINDING_MISSING")
        self.assertIn("#129", result["verdict"]["owner"])
        self.assertEqual(result["disposition"]["resume"], False)
        self.assertIn("NO-RESUME", result["disposition"]["reason"])

    def test_healthy_run_not_a_defect(self):
        result = adapter.audit(GENERATE_DEFECT, RUNLOG_HEALTHY)
        self.assertEqual(result["verdict"]["verdict"], "HEALTHY")
        self.assertIsNone(result["verdict"]["defect"])
        self.assertEqual(result["disposition"]["resume"], False)

    def test_undetermined_without_route_group(self):
        log = RUNLOG_DEFECT.replace(
            "[PC Route] group 0: id='test' points=64\n", "")
        result = adapter.audit(GENERATE_DEFECT, log)
        self.assertEqual(result["verdict"]["verdict"], "UNDETERMINED")
        self.assertIn("no-route-group-loaded", result["verdict"]["problems"])

    def test_undetermined_without_birth(self):
        log = RUNLOG_DEFECT.replace(
            "P2_FOREST1_BIRTH id=2370202546432 tick=2 x=173.6 y=0.0 z=-143.2\n", "")
        result = adapter.audit(GENERATE_DEFECT, log)
        self.assertEqual(result["verdict"]["verdict"], "UNDETERMINED")
        self.assertIn("no-actor-birth", result["verdict"]["problems"])

    def test_route_field_in_manifest_undetermined(self):
        bad = GENERATE_DEFECT.replace("spawn UjiA 6", "spawn UjiA 6 route1")
        result = adapter.audit(bad, RUNLOG_DEFECT)
        self.assertEqual(result["verdict"]["verdict"], "UNDETERMINED")
        self.assertIn("manifest-carries-unexpected-route-field",
                      result["verdict"]["problems"])

    def test_contract_identity(self):
        result = adapter.audit(GENERATE_DEFECT, RUNLOG_DEFECT)
        self.assertEqual(result["issue"], 796)
        self.assertEqual(result["downstream_issue"], 154)
        self.assertEqual(result["owning_issues"], [129, 154])
        self.assertFalse(result["generated"])
        self.assertEqual(result["spawn_binding_grammar"],
                         ["spawn <name> <count>", "no route/group field"])


if __name__ == "__main__":
    unittest.main()
