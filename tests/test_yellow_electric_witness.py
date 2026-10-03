import unittest

from scripts.pikmin2_yellow_electric_witness import witness


LOG = '''P2_ELECBUG_YELLOW_STAGED piki=0xabc species=2 relocated_debug_member=1 acquisition=0 campaign=0
P2_ELECBUG_THROW frame=100 piki=0xabc phase=held
P2_ELECBUG_THROW frame=110 piki=0xabc phase=released
P2_ELECBUG_THROW frame=111 piki=0xabc phase=rising
P2_ELECBUG_THROW frame=120 piki=0xabc phase=descending
P2_ELECBUG_OFF_CONTACT frame=121 generator=346002 piki=0xabc contact=0
P2_ELECBUG_PRESS_IMMUNE generator=346002 source_id=28 pikmin=yellow species=2 piki=0xabc accepted=0 state_before=14 target_state=14 alive=1
P2_ELECBUG_CONTACT_DISPATCH generator=346002 piki=0xabc species=2 vy=-100 contact=1 enemy_before=discharge enemy_after=reverse
P2_ELECBUG_YELLOW_SURVIVED frame=140 piki=0xabc species=2 alive=1 grounded=1 live=20 state=0
P2_ELECBUG_CONTACT_CANDIDATE frame=140 generator=346002 piki=0xabc observed_reverse=1 mode=yellow-electric species=2
'''


class ElectricWitnessTest(unittest.TestCase):
    def test_complete_chain(self):
        result = witness(LOG)
        self.assertEqual(result['piki'], '0xabc')
        self.assertTrue(result['actual_receiver_rejected'])
        self.assertFalse(result['original_acquisition'])

    def test_required_links(self):
        for tag in ('YELLOW_STAGED', 'PRESS_IMMUNE', 'OFF_CONTACT', 'CONTACT_DISPATCH', 'YELLOW_SURVIVED'):
            with self.subTest(tag=tag):
                self.assertIsNone(witness('\n'.join(line for line in LOG.splitlines() if 'P2_ELECBUG_'+tag not in line)))

    def test_false_receipts(self):
        mutations = (
            ('accepted=0', 'accepted=1'), ('state_before=14', 'state_before=0'),
            ('enemy_before=discharge', 'enemy_before=charge'), ('vy=-100', 'vy=nan'),
            ('grounded=1', 'grounded=0'), ('live=20', 'live=19'),
            ('target_state=14', 'target_state=35'),
            ('source_id=28', 'source_id=21'), ('contact=1', 'contact=0'),
            ('piki=0xabc accepted=0', 'piki=0xdef accepted=0'),
        )
        for before, after in mutations:
            with self.subTest(after=after):
                self.assertIsNone(witness(LOG.replace(before, after)))

    def test_survivor_must_be_recovered(self):
        for state in (6, 7, 12, 14, 24, 35):
            with self.subTest(state=state):
                self.assertIsNone(witness(LOG.replace('live=20 state=0', 'live=20 state='+str(state))))

    def test_interrupted_throw_and_guard(self):
        self.assertIsNone(witness(LOG.replace('P2_ELECBUG_OFF_CONTACT', 'P2_ELECBUG_THROW frame=121 piki=0xabc phase=invalidated\nP2_ELECBUG_OFF_CONTACT')))
        self.assertIsNone(witness('P2_FIXTURE_CAPTAIN_DOWN tick=1\n'+LOG))


if __name__ == '__main__':
    unittest.main()
