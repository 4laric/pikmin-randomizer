"""Lane 16 natural frog-combat validator tests (#167/#201)."""
import unittest

from experimental.pikmin2_frog_combat import validate


class FrogCombatTests(unittest.TestCase):
    def sample(self):
        return ('P2_FROG_COMBAT_BEGIN generator=201001 health=800.0 pikis=20\n'
                'P2_FROG_COMBAT_TICK health=800.0 pikis=20\n'
                'P2_FROG_PRESS species=Frog attack=1 behavior=P1_proxy\n'
                'P2_FROG_COMBAT_TICK health=650.0 pikis=20\n'
                'P2_FROG_COMBAT_TICK health=650.0 pikis=1\n'
                'P2_FROG_COMBAT_RESULT reason=window frog_dead=0 corpse=0 squad=1 controls=1 first=800.0 last=650.0\n'
                'PASS P2_FROG_COMBAT natural_combat=1\n')

    def test_complete_and_incomplete(self):
        text = self.sample()
        self.assertTrue(validate(text, 0)['passed'])
        self.assertFalse(validate(text, 1)['passed'])
        self.assertFalse(validate(text.replace('health=800.0 pikis=20\n', 'health=800.0 pikis=19\n', 1), 0)['passed'])
        self.assertFalse(validate(text.replace('P2_FROG_COMBAT_TICK health=650.0 pikis=1\n', ''), 0)['passed'])
        self.assertFalse(validate(text.replace('health=650.0', 'health=800.0'), 0)['passed'])
        self.assertFalse(validate(text.replace('controls=1', 'controls=0'), 0)['passed'])

    def test_frog_death_requires_a_corpse(self):
        dead = self.sample().replace('frog_dead=0 corpse=0', 'frog_dead=1 corpse=0')
        self.assertFalse(validate(dead, 0)['passed'])
        with_corpse = self.sample().replace('frog_dead=0 corpse=0', 'frog_dead=1 corpse=1')
        self.assertTrue(validate(with_corpse, 0)['passed'])

    def test_missing_begin_is_rejected(self):
        self.assertFalse(validate(self.sample().replace('P2_FROG_COMBAT_BEGIN generator=201001 health=800.0 pikis=20\n', ''), 0)['passed'])

    def test_press_markers_are_reported(self):
        self.assertEqual(validate(self.sample(), 0)['press_markers'], {'Frog': 1, 'MaroFrog': 0})
        self.assertEqual(validate(self.sample(), 0)['land_markers'], {'Frog': 0, 'MaroFrog': 0})
        self.assertEqual(validate(self.sample(), 0)['land_attribution'], [])

    def test_land_markers_are_reported_without_becoming_a_hard_pass(self):
        row = 'P2_FROG_LAND species=Frog radius=23.0 bittered=0 pikmin=2 navi=1 behavior=P1_proxy\n'
        report = validate(self.sample() + row, 0)
        self.assertTrue(report['passed'])
        self.assertEqual(report['land_markers'], {'Frog': 1, 'MaroFrog': 0})
        self.assertEqual(report['land_attribution'],
                         [{'species': 'Frog', 'radius': 23.0, 'bittered': False,
                           'pikmin': 2, 'navi': 1}])
        self.assertFalse(validate(self.sample().replace('controls=1', 'controls=0') + row, 0)['passed'])


if __name__ == '__main__':
    unittest.main()
