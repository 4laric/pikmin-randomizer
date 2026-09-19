"""Focused fail-closed tests for the impact squad-spawn landing validator (#733)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental import pikmin2_impact_squad_spawn_landing as L

R698 = ('C:/Users/alari/pikmin-randomizer/output/workflow/autofill/'
        'prerequisites/impact-squad-spawn-diagnosis-root')
N649 = ('C:/Users/alari/pikmin-randomizer/output/workflow/autofill/'
        'planning-shards/p1-challenge/prepared/p1-challenge-guarded-runtime-native')
RUNS = ('C:/Users/alari/pikmin-randomizer/output/workflow/autofill/'
        'planning-shards/p1-challenge/prepared/p1-challenge-impact-runtime-output/'
        'acceptance/runs')


class LandingValidatorTests(unittest.TestCase):
    def test_commit_present(self):
        found = L.verify_commit(
            R698, 'b286da1286284e915d3a0bf98a57d6584fc33c0d',
            'post-PARK stall classifier')
        self.assertEqual(found['sha'], 'b286da1286284e915d3a0bf98a57d6584fc33c0d')

    def test_commit_subject_drift_refused(self):
        with self.assertRaises(L.LandingError):
            L.verify_commit(R698, 'b286da1286284e915d3a0bf98a57d6584fc33c0d',
                            'definitely not the subject')

    def test_diagnosis_files(self):
        found = L.verify_diagnosis_files(R698)
        self.assertEqual(len(found), 3)

    def test_fix_location(self):
        result = L.verify_fix_location(N649)
        self.assertEqual(len(result['gate_lines']), 5)
        self.assertTrue(all(v is not None for v in result['gate_lines'].values()))

    def test_consumer_runs_shape(self):
        result = L.verify_consumer_runs(RUNS)
        self.assertEqual(len(result['shaped']), 7)
        self.assertEqual(len(result['empty']), 1)

    def test_missing_dir_refused(self):
        with self.assertRaises(L.LandingError):
            L.verify_consumer_runs('/nonexistent/runs/dir')

    def test_missing_file_refused(self):
        with self.assertRaises(L.LandingError):
            L.sha256_file('/nonexistent/path/file.bin')

    def test_captain_down_refused(self):
        with self.assertRaises(L.LandingError):
            L.verify_markers_absent_of_interruption('P2_FIXTURE_CAPTAIN_DOWN tick=1')

    def test_injected_refused(self):
        with self.assertRaises(L.LandingError):
            L.verify_markers_absent_of_interruption('P2_LL_INJECT')

    def test_sequencing(self):
        self.assertIn('#565', L.sequencing())
        self.assertIn('#649', L.sequencing())


if __name__ == '__main__':
    unittest.main()
