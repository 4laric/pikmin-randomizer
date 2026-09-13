import unittest
from experimental.pikmin2_tank_start_diagnostic import movie_probe,analyze_start
class TankStartTests(unittest.TestCase):
    def test_production_queue_and_skip_guard_remain(self):
        s=movie_probe('if (pc_bbft_take_skip() && mIsActive) requestSkip();')
        self.assertIn('pc_bbft_take_skip() && mIsActive',s);self.assertEqual(s.count('requestSkip();'),1)
    def test_exactly_one_edge_required(self):
        s='TANK_START_SCHEDULE movie=demo56\nTANK_START_EDGE delivered=1\nTANK_START_CONSUMED allowed=1'
        self.assertTrue(analyze_start(s,True)['allowed'])
        for text in ('',s+'\nTANK_START_EDGE delivered=1'):
            with self.assertRaises(ValueError):analyze_start(text,True)
    def test_denied_edge_not_claimed_allowed(self):
        s='TANK_START_SCHEDULE movie=demo56\nTANK_START_EDGE delivered=1\nTANK_START_CONSUMED allowed=0'
        self.assertFalse(analyze_start(s,True)['allowed'])
    def test_control_rejects_any_injection(self):
        self.assertEqual(analyze_start('',False)['consumed'],0)
        with self.assertRaises(ValueError):analyze_start('TANK_START_SCHEDULE movie=demo56',False)
