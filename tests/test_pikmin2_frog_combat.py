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
        self.assertEqual(validate(self.sample(), 0)['bitter_markers'], [])

    def test_land_markers_are_reported_without_becoming_a_hard_pass(self):
        row = ('P2_FROG_LAND species=Frog radius=23.0 bittered=0 pikmin=2 navi=1 '
               'behavior=P1_proxy pressed=1 origin=none host_frozen=0\n')
        report = validate(self.sample() + row, 0)
        self.assertTrue(report['passed'])
        self.assertEqual(report['land_markers'], {'Frog': 1, 'MaroFrog': 0})
        self.assertEqual(report['land_attribution'],
                         [{'species': 'Frog', 'radius': 23.0, 'bittered': False,
                           'pikmin': 2, 'navi': 1, 'pressed': 1, 'origin': 'none',
                           'host_frozen': 0}])
        self.assertFalse(validate(self.sample().replace('controls=1', 'controls=0') + row, 0)['passed'])

    def test_bittered_land_row_is_reported_and_not_a_hard_pass(self):
        row = ('P2_FROG_LAND species=Frog radius=23.0 bittered=1 pikmin=2 navi=1 '
               'behavior=P1_proxy pressed=0 origin=override host_frozen=0\n')
        report = validate(self.sample() + row, 0)
        self.assertTrue(report['passed'])
        self.assertEqual(report['land_attribution'],
                         [{'species': 'Frog', 'radius': 23.0, 'bittered': True,
                           'pikmin': 2, 'navi': 1, 'pressed': 0, 'origin': 'override',
                           'host_frozen': 0}])

    def test_legacy_land_row_without_branch_fields_still_parses(self):
        row = 'P2_FROG_LAND species=MaroFrog radius=21.0 bittered=0 pikmin=1 navi=0 behavior=P1_proxy\n'
        report = validate(self.sample() + row, 0)
        self.assertTrue(report['passed'])
        self.assertEqual(report['land_attribution'],
                         [{'species': 'MaroFrog', 'radius': 21.0, 'bittered': False,
                           'pikmin': 1, 'navi': 0, 'pressed': 1, 'origin': 'unknown',
                           'host_frozen': 0}])

    def test_land_row_with_source_behavior_parses(self):
        row = ('P2_FROG_LAND species=Frog radius=23.0 bittered=0 pikmin=2 navi=1 '
               'behavior=source pressed=1 origin=source host_frozen=0\n')
        report = validate(self.sample() + row, 0)
        self.assertTrue(report['passed'])
        self.assertEqual(report['land_markers'], {'Frog': 1, 'MaroFrog': 0})
        self.assertEqual(report['land_attribution'],
                         [{'species': 'Frog', 'radius': 23.0, 'bittered': False,
                           'pikmin': 2, 'navi': 1, 'pressed': 1, 'origin': 'source',
                           'host_frozen': 0}])

    def test_land_row_with_source_behavior_without_branch_fields_parses(self):
        row = 'P2_FROG_LAND species=Frog radius=23.0 bittered=0 pikmin=2 navi=1 behavior=source\n'
        report = validate(self.sample() + row, 0)
        self.assertTrue(report['passed'])
        self.assertEqual(report['land_attribution'],
                         [{'species': 'Frog', 'radius': 23.0, 'bittered': False,
                           'pikmin': 2, 'navi': 1, 'pressed': 1, 'origin': 'unknown',
                           'host_frozen': 0}])

    def test_land_row_with_unrelated_behavior_is_not_attributed(self):
        row = ('P2_FROG_LAND species=Frog radius=23.0 bittered=0 pikmin=2 navi=1 '
               'behavior=other pressed=1 origin=none host_frozen=0\n')
        self.assertEqual(validate(self.sample() + row, 0)['land_attribution'], [])

    def test_bitter_toggle_markers_are_reported(self):
        toggles = ('P2_FROG_BITTER species=Frog override=1 host_frozen=0 effective=1 origin=override\n'
                   'P2_FROG_BITTER species=Frog override=0 host_frozen=0 effective=0 origin=none\n')
        report = validate(self.sample() + toggles, 0)
        self.assertTrue(report['passed'])
        self.assertEqual(report['bitter_markers'],
                         [{'species': 'Frog', 'override': True, 'host_frozen': 0,
                           'effective': True, 'origin': 'override'},
                          {'species': 'Frog', 'override': False, 'host_frozen': 0,
                           'effective': False, 'origin': 'none'}])


if __name__ == '__main__':
    unittest.main()
