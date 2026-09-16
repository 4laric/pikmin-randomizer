"""Tests for experimental/pikmin2_king_natural_flick_runtime (#445).

Pure validator/protocol checks for the natural (un-injected) Flick/trample
gate. No native compile is required here; the C++ policy is covered by
tests/test_pikmin2_king_actor.py.
"""
import unittest

from experimental import pikmin2_king_natural_flick_runtime as nf

PASS_TEXT = (
    'P2_KING_BASELINE red=5 blue=5\n'
    'P2_KING_READY id=230020 enemy=53 variant=default xyz=34.000000,30.000000,1896.000000 yaw=0.000 '
    'health=1300.0 scale=1.00 speed=30.0 floor_offset=0 entry_state=9 gauge_hidden=1\n'
    'P2_KING_NATURAL_ARMED no_injection=1\n'
    'P2_KING_APPEAR_TRIGGER id=230020 nearest=30.000 range=60.0 waited=1\n'
    'P2_KING_CHECK_FLICK id=230020 health=1290.0 max=1300.0 roll=0.778 shout_rate=0.5 next=3\n'
    'P2_KING_TRAMPLE id=230020 pressed_pikmin=7 pressed_captains=0 flick_captains=1 range=45.0 band=30\n'
    'P2_KING_STATE id=230020 from=3 to=0 health=1280.0\n'
    'PASS P2_KING_NATURAL_RUNTIME natural_flick_trample\n'
)


class ValidatorTests(unittest.TestCase):
    def test_natural_pass(self):
        evidence = nf.validate(PASS_TEXT, 0)
        self.assertTrue(evidence['passed'], evidence['failed'])

    def test_missing_pass_line_fails(self):
        evidence = nf.validate(PASS_TEXT.replace('PASS P2_KING_NATURAL_RUNTIME natural_flick_trample\n', ''), 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('completion', evidence['failed'])

    def test_injected_flick_fails(self):
        injected = PASS_TEXT.replace(
            'P2_KING_CHECK_FLICK',
            'P2_KING_INJECT_FLICK id=230020 tick=20 state=Flick fixture=1\nP2_KING_CHECK_FLICK')
        evidence = nf.validate(injected, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('no_injection', evidence['failed'])

    def test_staged_bomb_fails_naturalness(self):
        bombed = PASS_TEXT.replace('P2_KING_NATURAL_ARMED',
                                   'P2_KING_BOMB_READY id=360002 enemy=36 state=BOMB_Wait injection=1\nP2_KING_NATURAL_ARMED')
        evidence = nf.validate(bombed, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('no_injection', evidence['failed'])

    def test_no_press_fails_trample(self):
        evidence = nf.validate(PASS_TEXT.replace('pressed_pikmin=7', 'pressed_pikmin=0'), 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('natural_trample', evidence['failed'])

    def test_war_cry_selection_fails(self):
        evidence = nf.validate(PASS_TEXT.replace('next=3', 'next=4'), 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('natural_check_flick', evidence['failed'])


if __name__ == '__main__':
    unittest.main()
