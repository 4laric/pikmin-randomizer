import unittest
from scripts.test_pikmin2_tank_gx_native import analyze
class TankGXDiagnosisTests(unittest.TestCase):
    def test_requires_native_attack(self):
        with self.assertRaises(ValueError):analyze('[PC GX] DESYNC #1')
    def test_post_movie_attribution(self):
        r=analyze('P2_TANK_COUNTER state=7 motion=8 counter=20\nMoviePlayer: clearing top heap!\ndataDir/cinemas/demo56.cin\n[PC GX] DESYNC #1')
        self.assertEqual(r['warnings_before_demo56'],0);self.assertEqual(r['first_warning_line'],4)
    def test_attack_warning_not_mislabeled_post_movie(self):
        r=analyze('P2_TANK_COUNTER state=7 motion=8 counter=20\n[PC GX] DESYNC #1\ndataDir/cinemas/demo56.cin')
        self.assertEqual(r['warnings_before_demo56'],1)
    def test_clean_absent_bank(self):
        r=analyze('P2_TANK_COUNTER state=7 motion=8 counter=20')
        self.assertEqual(r['warning_lines'],[]);self.assertFalse(r['imported_draw'])
