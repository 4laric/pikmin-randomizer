import unittest
from scripts.pikmin2_corpse_evidence import validate_corpse


TRACE = '''P2_LIFECYCLE_ENEMY frame=3 phase=0 enemy=00ab generator=00cd
P2_CORPSE_CAPTAIN_APPROACH frame=700 distance=118 controller_only=1
P2_LIFECYCLE_DEATH frame=900 phase=4 enemy=00ab health=0
P2_LIFECYCLE_BIRTH frame=1000 phase=5 enemy=00ab pellet=00ef
P2_LIFECYCLE_STATE frame=1000 phase=5 pellet=00ef state=0 distance=0 goal=0000
P2_LIFECYCLE_STATE frame=1500 phase=6 pellet=00ef state=1 distance=350 goal=00ff
P2_LIFECYCLE_REMOVED frame=1560 phase=6 pellet=00ef last_state=1 distance=360
'''


class CorpseEvidenceTests(unittest.TestCase):
    def test_complete_and_distant_control(self):
        self.assertEqual(validate_corpse(TRACE)['distance'], 360)
        distant = '\n'.join(line for line in TRACE.splitlines() if 'APPROACH' not in line)
        self.assertFalse(validate_corpse(distant, False)['controller_approach'])

    def test_rejects_missing_birth_goal_removal_or_approach(self):
        for event in ('BIRTH', 'REMOVED', 'APPROACH', 'state=1'):
            with self.subTest(event=event), self.assertRaises(ValueError):
                validate_corpse('\n'.join(line for line in TRACE.splitlines() if event not in line))

    def test_rejects_wrong_identity_order_duplicate_or_short_route(self):
        for old, new in [('enemy=00ab health', 'enemy=00ac health'),
                         ('pellet=00ef last_state', 'pellet=00ee last_state'),
                         ('goal=00ff', 'goal=0000'), ('health=0', 'health=10'),
                         ('distance=350', 'distance=50'), ('distance=360', 'distance=nan'),
                         ('frame=1560', 'frame=800'), ('last_state=1', 'last_state=0'),
                         ('distance=118', 'distance=180'), ('generator=00cd', 'generator=0000')]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                validate_corpse(TRACE.replace(old, new))
        with self.assertRaises(ValueError):
            validate_corpse(TRACE+TRACE.splitlines()[-1]+'\n')
        with self.assertRaises(ValueError):
            validate_corpse(TRACE, False)


if __name__ == '__main__':
    unittest.main()
