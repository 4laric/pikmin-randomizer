"""Focused tests for the forest_1 materialization diagnosis adapter (#790).

All log snippets here are SYNTHETIC fixtures exercising the adapter
boundary (counts, attribution, fail-closed refusals). No snippet is
claimed as engine output; the only real log is the pinned gen-13
evidence, consumed read-only by the lane (not by these tests).
"""
import importlib.util
import unittest
from pathlib import Path

ADAPTER = (Path(__file__).resolve().parents[1] / "experimental" /
           "pikmin2_forest1_arena_materialization_diagnosis.py")

SYNTHETIC_LOG = (
    "P2_CAVE_READY floor=1 survivors=20 health=1\n"
    "P2_CAVE_RESTORE species=0 maturity=0\n"
    "P2_CAVE_RESTORE species=1 maturity=0\n"
    "[PC Generator] default: initialised 24 recognised generators, spawned 24 creatures\n"
    "P2_FOREST1_COLLISION_OBSERVE observed=600 squad=0 births=1 grounded=1 moved=0 live_actors=1\n"
    "P2_FOREST1_COLLISION_OBSERVE observed=1200 squad=0 births=0 grounded=0 moved=0 live_actors=0\n"
    '[PC Port] DVDOpen("dataDir/stages/chal0/1.gen") -> FAILED to open assets\n'
)


def load_adapter():
    spec = importlib.util.spec_from_file_location("pikmin2_forest1_arena_materialization_diagnosis", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MaterializationDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_counts_and_series(self):
        counts = self.mod.count_markers(SYNTHETIC_LOG)
        self.assertEqual(counts["P2_CAVE_READY"], 1)
        self.assertEqual(counts["P2_CAVE_RESTORE"], 2)
        self.assertEqual(counts["P2_CAVE_GENERATE_PASS"], 0)
        self.assertEqual(len(counts["observe_series"]), 2)
        self.assertEqual(counts["observe_series"][0], (0, 1, 1, 0, 1))

    def test_attributed_verdicts_name_pins_and_owners(self):
        verdicts = self.mod.attribute(self.mod.count_markers(SYNTHETIC_LOG))
        self.assertEqual([v["gap"] for v in verdicts],
                         ["A1-staged-package-never-parsed", "A2-missing-stage-files",
                          "A3-spawned-vs-addressable", "B-restore-without-squad"])
        for verdict in verdicts:
            self.assertTrue(verdict["pins"])
            for path, symbol in verdict["pins"]:
                self.assertTrue(path.startswith("native/"))
                self.assertTrue(symbol)
            self.assertIn("#773", verdict["owner"])

    def test_unattributable_refused(self):
        with self.assertRaises(self.mod.UnattributableError):
            self.mod.attribute(self.mod.count_markers("P2_CAVE_READY floor=1 survivors=20\n"))
        with self.assertRaises(self.mod.UnattributableError):
            self.mod.attribute(self.mod.count_markers(
                "P2_FOREST1_COLLISION_OBSERVE observed=600 squad=2 births=1 grounded=1 moved=1 live_actors=3\n"
                "P2_CAVE_READY floor=1 survivors=20 health=1\n"))

    def test_malformed_and_missing_refused(self):
        with self.assertRaises(self.mod.DiagnosisError):
            self.mod.count_markers("")
        with self.assertRaises(self.mod.DiagnosisError):
            self.mod.count_markers(None)
        with self.assertRaises(self.mod.DiagnosisError):
            self.mod.attribute({})
        with self.assertRaises(FileNotFoundError):
            self.mod.load_evidence(path="does/not/exist.log", sha256="x")


if __name__ == "__main__":
    unittest.main()
