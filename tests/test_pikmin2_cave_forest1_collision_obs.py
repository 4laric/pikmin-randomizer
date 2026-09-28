"""Focused tests for the forest_1 criterion-3 log reader (#773). Hermetic;
synthetic logs only, no engine, no assets."""
import importlib.util
import os
import unittest


def _load():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "experimental", "pikmin2_cave_forest1_collision_obs.py")
    spec = importlib.util.spec_from_file_location("collision_obs", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = _load()

GOOD = "\n".join([
    "P2_FOREST1_COLLISION_WINDOW size=960x540 pos=1,2 display=3x4 centered=1",
    "P2_FOREST1_COLLISION_ENTRY_READY floor=1 observed=10",
    "P2_FOREST1_BIRTH id=1 tick=11 x=0.0 y=0.0 z=0.0",
    "P2_FOREST1_CONTACT id=1 tick=12 y=0.0 ground=0.0",
    "P2_FOREST1_TRAVERSE id=1 tick=13 dx=150.0 dz=20.0",
    "P2_FOREST1_COLLISION_PASS floor=1 squad=20 births=1 grounded=1 moved=1 observed=14",
    "PASS FOREST1_COLLISION_OBS",
])


class ParseTests(unittest.TestCase):
    def test_markers_found_in_order(self):
        kinds = M.parse_markers(GOOD)
        self.assertIn("P2_FOREST1_BIRTH", kinds)
        self.assertIn("P2_FOREST1_CONTACT", kinds)
        self.assertIn("P2_FOREST1_TRAVERSE", kinds)
        self.assertIn("PASS FOREST1_COLLISION_OBS", kinds)

    def test_malformed_rejected(self):
        with self.assertRaises(M.LogError):
            M.parse_markers("")
        with self.assertRaises(M.LogError):
            M.parse_markers(None)
        with self.assertRaises(M.LogError):
            M.parse_markers(123)

    def test_non_marker_lines_ignored(self):
        kinds = M.parse_markers("[PC Port] hello\n" + GOOD + "\n[PC Port] bye")
        self.assertNotIn("[PC Port] hello", kinds)
        self.assertIn("PASS FOREST1_COLLISION_OBS", kinds)


class ChainTests(unittest.TestCase):
    def test_pass(self):
        result = M.evaluate_run_log(GOOD, 0)
        self.assertTrue(result["passed"], result["detail"])
        self.assertEqual(result["births"], 1)
        self.assertEqual(result["contacts"], 1)
        self.assertEqual(result["traverses"], 1)

    def test_captain_down_fails(self):
        bad = GOOD + "\nP2_FIXTURE_CAPTAIN_DOWN tick=5 hp=0.000 outcome=BLOCKED"
        result = M.evaluate_run_log(bad, 86)
        self.assertFalse(result["passed"])
        self.assertIn("captain", result["detail"].lower())

    def test_missing_markers_fail(self):
        for drop in ("P2_FOREST1_BIRTH", "P2_FOREST1_CONTACT",
                     "P2_FOREST1_TRAVERSE", "PASS FOREST1_COLLISION_OBS"):
            lines = [l for l in GOOD.splitlines() if not l.startswith(drop)]
            result = M.evaluate_run_log("\n".join(lines), 0)
            self.assertFalse(result["passed"], drop)
            self.assertIn("missing", result["detail"])

    def test_bad_exit_fails(self):
        result = M.evaluate_run_log(GOOD, 2)
        self.assertFalse(result["passed"])
        result = M.evaluate_run_log(GOOD, 86)
        self.assertFalse(result["passed"])

    def test_empty_log_fails_closed(self):
        with self.assertRaises(M.LogError):
            M.evaluate_run_log("", 0)


if __name__ == "__main__":
    unittest.main()