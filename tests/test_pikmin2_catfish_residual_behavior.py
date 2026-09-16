"""Unit tests for the Catfish residual-gap validator (#407/#167)."""
import unittest

from experimental.pikmin2_catfish_residual_behavior import (
    FLICK_KNOCKBACK_FRAME, SLOT_MAX, validate)

GOOD_LOG = '\n'.join([
    'P2_CATFISH_BIND generator=374001 source_id=26 visual_only=0',
    'P2_CATFISH_RESIDUAL generator=374001 slots=2 attack_damage=10.0 '
    'poison_damage=300.0 flick_events=25,47',
    'P2_ENEMY_READY species=Catfish native_family=Namazu generator=374001 x=-108.0 y=30.0 '
    'z=1850.0 health=200.0 max_health=200.0 behavior=native source_FSM=implemented '
    'attack=animation_event water=absent',
    'P2_BATCH3_BIND generator=374001 key=aquatic|Catfish visual_only=0 native_fsm=implemented',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_CATFISH_STATE generator=374001 state=attack',
    'P2_CATFISH_ATTACK_NAVI generator=374001 frame=17 damage=10.0',
    'P2_CATFISH_BITE generator=374001 frame=17.0 pikmin=1 slot=0',
    'P2_CATFISH_BITE generator=374001 frame=17.0 pikmin=1 slot=1',
    'P2_CATFISH_EAT generator=374001 pikmin=1 slot=0',
    'P2_CATFISH_EAT generator=374001 pikmin=1 slot=1',
    'P2_CATFISH_FLICK generator=374001 frame=25 event=knockback hit=1',
    'P2_CATFISH_FLICK generator=374001 frame=47 event=restore',
])


class CatfishResidualTests(unittest.TestCase):
    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['two_slot_capture'])
        self.assertTrue(result['checks']['attack_navi_contract'])
        self.assertTrue(result['checks']['poison_contract'])
        self.assertTrue(result['checks']['flick_banked'])
        self.assertTrue(result['checks']['bite_eat_exactly_once'])
        self.assertEqual(result['watched']['residual_slots'], SLOT_MAX)
        self.assertEqual(result['watched']['bite_slots'], [0, 1])
        self.assertEqual(result['watched']['eat_slots'], [0, 1])
        self.assertEqual(result['watched']['flick_knockback'],
                         [(FLICK_KNOCKBACK_FRAME, 1)])

    def test_three_captures_in_one_frame_fails(self):
        log = GOOD_LOG + '\nP2_CATFISH_BITE generator=374001 frame=17.0 pikmin=1 slot=0'
        result = validate(log, code=0)
        self.assertFalse(result['checks']['two_slot_capture'])
        self.assertFalse(result['passed'])

    def test_slot_reuse_across_cycles_is_allowed(self):
        # Two attack cycles can share an animation frame, so slot 0 may recur;
        # the two-slot capability is asserted by the policy test.
        log = GOOD_LOG.replace('pikmin=1 slot=1', 'pikmin=1 slot=0')
        result = validate(log, code=0)
        self.assertTrue(result['checks']['two_slot_capture'])
        self.assertTrue(result['checks']['bite_eat_exactly_once'])

    def test_wrong_attack_damage_contract_fails(self):
        log = GOOD_LOG.replace('attack_damage=10.0', 'attack_damage=5.0')
        result = validate(log, code=0)
        self.assertFalse(result['checks']['attack_navi_contract'])
        self.assertFalse(result['passed'])

    def test_wrong_poison_damage_contract_fails(self):
        log = GOOD_LOG.replace('poison_damage=300.0', 'poison_damage=1.0')
        result = validate(log, code=0)
        self.assertFalse(result['checks']['poison_contract'])
        self.assertFalse(result['passed'])

    def test_observed_poison_uses_source_damage(self):
        log = GOOD_LOG + '\nP2_CATFISH_POISON generator=374001 source_id=26 pikmin=white ' \
                         'damage=300.0 health=-100.0'
        result = validate(log, code=0)
        self.assertTrue(result['checks']['poison_contract'], result['checks'])
        self.assertEqual(result['watched']['poison'], [(300.0, -100.0)])
        bad = log.replace('damage=300.0 health=-100.0', 'damage=1.0 health=199.0')
        self.assertFalse(validate(bad, code=0)['checks']['poison_contract'])

    def test_synthetic_flick_frame_fails(self):
        log = GOOD_LOG.replace('frame=25 event=knockback', 'frame=14 event=knockback')
        result = validate(log, code=0)
        self.assertFalse(result['checks']['flick_banked'])
        self.assertFalse(result['passed'])

    def test_missing_residual_contract_fails(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines()
                        if 'P2_CATFISH_RESIDUAL' not in line)
        result = validate(log, code=0)
        self.assertFalse(result['checks']['residual_contract'])
        self.assertFalse(result['passed'])

    def test_missing_bite_fails(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines()
                        if 'P2_CATFISH_BITE' not in line)
        result = validate(log, code=0)
        self.assertFalse(result['checks']['two_slot_capture'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
