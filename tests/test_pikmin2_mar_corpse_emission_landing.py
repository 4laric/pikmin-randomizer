"""Focused fail-closed tests for the Mar corpse-emission landing validator (#720)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental import pikmin2_mar_corpse_emission_landing as L

NATIVE_716 = ('C:/Users/alari/pikmin-randomizer/output/workflow/autofill/'
              'prerequisites/mar-corpse-emission-native-native')
OUT_716 = ('C:/Users/alari/pikmin-randomizer/output/workflow/autofill/'
           'prerequisites/mar-corpse-emission-native/out')
PROD_EXE = ('C:/Users/alari/pikmin-randomizer/output/'
            'mar-corpse-emission-native-build/bin/nectar.exe')


class LandingValidatorTests(unittest.TestCase):
    def test_commits_present(self):
        native = L.verify_commit(
            NATIVE_716, '0306b0d0f7abf76841f6b36bbd9f1592ae411462', 'corpse pellet')
        self.assertEqual(native['sha'], '0306b0d0f7abf76841f6b36bbd9f1592ae411462')

    def test_commit_subject_drift_refused(self):
        with self.assertRaises(L.LandingError):
            L.verify_commit(NATIVE_716, '0306b0d0f7abf76841f6b36bbd9f1592ae411462',
                            'definitely not the subject')

    def test_native_files_contract(self):
        found = L.verify_native_files(NATIVE_716)
        self.assertEqual(set(found), {'pc_port/pc_p2_mar.h',
                                      'pc_port/pc_p2_mar.cpp',
                                      'tools/p2_mar_corpse_emission_fixture.cpp'})

    def test_arm_compat(self):
        result = L.verify_arm_compat(NATIVE_716)
        self.assertEqual(len(result['checks']), 7)

    def test_compiled_evidence(self):
        result = L.verify_compiled_evidence(
            OUT_716 + '/fixture-out/provenance.json',
            OUT_716 + '/fixture-out/fixture.exe', PROD_EXE)
        self.assertEqual(result['provenance_status'], 'built')
        self.assertEqual(result['fixture_exe_sha256'],
                         'eb371ba5a770bc16883aac8672b1df81ad8a0e26ad93986779a5d1e60be5584e')
        self.assertEqual(result['production_exe_sha256'],
                         '93b83d7d1e4783f768a04f7e69ef216f2c1d0bad45563010c50450001cb2267c')

    def test_provenance_not_built_refused(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'provenance.json'
            bad.write_text(json.dumps({'status': 'checking'}), encoding='utf-8')
            with self.assertRaises(L.LandingError):
                L.verify_compiled_evidence(str(bad), str(bad), str(bad))

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
        self.assertIn('#375', L.sequencing())
        self.assertIn('#716', L.sequencing())


if __name__ == '__main__':
    unittest.main()

