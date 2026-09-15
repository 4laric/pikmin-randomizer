"""Tests for experimental/pikmin2_king_natural_death_runtime (#445).

Pure validator checks for the natural (un-injected) combat->lethal-death gate.
No native compile is required here; the C++ policy is covered by
tests/test_pikmin2_king_actor.py and tests/pikmin2_king_policy.cpp.
"""
import unittest

from experimental import pikmin2_king_natural_death_runtime as knd

PASS_TEXT = (
    'P2_KING_NATDEATH_BASELINE red=32 other=0\n'
    'P2_KING_READY id=230020 enemy=53 variant=default xyz=34.000000,30.000000,1896.000000 yaw=0.000 '
    'health=1300.0 scale=1.00 speed=30.0 floor_offset=0 entry_state=9 gauge_hidden=1\n'
    'P2_KING_NATDEATH_ARMED no_injection=1\n'
    'P2_KING_COMBAT_DAMAGE id=230020 stuck=32 damage=32.0 health=850.0 interval=20\n'
    'P2_KING_COMBAT_DAMAGE id=230020 stuck=31 damage=31.0 health=50.0 interval=20\n'
    'P2_KING_STATE id=230020 from=3 to=2 health=0\n'
    'P2_KING_DEAD_KEY id=230020 frame=185 kill=1\n'
    'PASS P2_KING_NATURAL_DEATH natural_combat_death\n'
)


class ValidatorTests(unittest.TestCase):
    def test_natural_pass(self):
        evidence = knd.validate(PASS_TEXT, 0)
        self.assertTrue(evidence['passed'], evidence['failed'])

    def test_missing_pass_line_fails(self):
        evidence = knd.validate(PASS_TEXT.replace('PASS P2_KING_NATURAL_DEATH natural_combat_death\n', ''), 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('completion', evidence['failed'])

    def test_kill_injection_fails(self):
        injected = PASS_TEXT.replace(
            'P2_KING_COMBAT_DAMAGE',
            'P2_KING_INJECT_KILL id=230020 tick=5 health=0 fixture=1\nP2_KING_COMBAT_DAMAGE')
        evidence = knd.validate(injected, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('no_injection', evidence['failed'])

    def test_staged_bomb_fails_naturalness(self):
        bombed = PASS_TEXT.replace('P2_KING_NATDEATH_ARMED',
                                   'P2_KING_BOMB_READY id=360002 enemy=36 state=BOMB_Wait injection=1\n'
                                   'P2_KING_NATDEATH_ARMED')
        evidence = knd.validate(bombed, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('no_injection', evidence['failed'])

    def test_no_combat_damage_fails(self):
        evidence = knd.validate(PASS_TEXT.replace('P2_KING_COMBAT_DAMAGE ', 'P2_KING_XCOMBAT_DAMAGE '), 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('combat_damage', evidence['failed'])

    def test_no_lethal_transition_fails(self):
        evidence = knd.validate(PASS_TEXT.replace('to=2 health=0', 'to=0 health=0'), 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('lethal_transition', evidence['failed'])

    def test_no_death_key_fails(self):
        evidence = knd.validate(PASS_TEXT.replace('P2_KING_DEAD_KEY id=230020 frame=185 kill=1\n', ''), 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('death_key', evidence['failed'])


if __name__ == '__main__':
    unittest.main()
