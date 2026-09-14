"""Lane 16 natural frog-combat validator tests (#167/#201)."""
import unittest

from experimental.pikmin2_frog_combat import validate


class FrogCombatTests(unittest.TestCase):
    def sample(self):
        text = ('P2_FROG_COMBAT_BEGIN generator=201001 health=800.0 pikis=20\n'
                'P2_FROG_COMBAT_TICK health=800.0 pikis=20\n'
                'P2_FROG_PRESS species=Frog attack=1 behavior=P1_proxy\n'
                'P2_FROG_COMBAT_TICK health=650.0 pikis=20\n'
                'P2_FROG_COMBAT_TICK health=650.0 pikis=1\n'
                'P2_FROG_COMBAT_RESULT frog_dead=0 corpse=0 squad=1 controls=1 first=800.0 last=650.0\n'
                'PASS P2_FROG_COMBAT natural_combat=1\n')
        return text

    def test_complete_and_incomplete(self):
        text = self.sample()
        self.assertTrue(validate(text, 0)['passed'])
        self.assertFalse(validate(text, 1)['passed'])
        self.assertFalse(validate(text.replace('health=800.0 pikis=20\n', 'health=800.0 pikis=19\n', 1), 0)['passed'])
        self.assertFalse(validate(text.replace('P2_FROG_COMBAT_TICK health=650.0 pikis=1\n', ''), 0)['passed'])
        self.assertFalse(validate(text.replace('health=650.0', 'health=800.0'), 0)['passed'])
        self.assertFalse(validate(text.replace('P2_FROG_PRESS species=Frog attack=1 behavior=P1_proxy\n', ''), 0)['passed'])
        self.assertFalse(validate(text.replace('controls=1', 'controls=0'), 0)['passed'])

    def test_frog_death_requires_a_corpse(self):
        dead = self.sample().replace('frog_dead=0 corpse=0', 'frog_dead=1 corpse=0')
        self.assertFalse(validate(dead, 0)['passed'])
        with_corpse = self.sample().replace('frog_dead=0 corpse=0', 'frog_dead=1 corpse=1')
        self.assertTrue(validate(with_corpse, 0)['passed'])

    def test_missing_begin_is_rejected(self):
        self.assertFalse(validate(self.sample().replace('P2_FROG_COMBAT_BEGIN generator=201001 health=800.0 pikis=20\n', ''), 0)['passed'])


if __name__ == '__main__':
    unittest.main()
