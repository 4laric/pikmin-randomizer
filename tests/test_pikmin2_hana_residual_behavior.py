"""Unit tests for the Hana residual-gate validator (#407/#165)."""
import unittest

from experimental.pikmin2_hana_residual_behavior import POISON_DAMAGE, validate

GOOD_LOG = '\n'.join([
    'P2_HANA_BIND generator=346006 source_id=84 visual_only=0',
    'P2_ENEMY_READY species=Hana native_family=Chappy generator=346006 x=-100.0 y=30.0 '
    'z=1850.0 health=2500.0 max_health=2500.0 behavior=native source_FSM=implemented '
    'attack=animation_event',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_HANA_UNDERGROUND generator=346006 event=enter no_atari=1 invulnerable=1',
    'P2_HANA_STATE generator=346006 state=sleep',
    'P2_HANA_UNDERGROUND_BLOCK generator=346006 source_id=84 buried=1',
    'P2_HANA_STATE generator=346006 state=emerge',
    'P2_HANA_UNDERGROUND generator=346006 event=exit no_atari=0 invulnerable=0',
    'P2_HANA_STATE generator=346006 state=walk',
    'P2_HANA_STATE generator=346006 state=attack',
    'P2_HANA_ATTACK_NAVI generator=346006 frame=18.0 navi=1 damage=10.0',
    'P2_HANA_BITE generator=346006 frame=18.0 pikmin=1',
    'P2_HANA_POISON generator=346006 pikmin=1 damage=2500.0 health=0.0',
    'P2_HANA_EAT generator=346006 pikmin=1',
    'P2_HANA_STATE generator=346006 state=eat',
])


class HanaResidualTests(unittest.TestCase):
    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['underground_enter'])
        self.assertTrue(result['checks']['underground_exit'])
        self.assertTrue(result['checks']['underground_order'])
        self.assertTrue(result['checks']['attack_navi_event'])
        self.assertTrue(result['checks']['poison_accounting'])
        self.assertTrue(result['watched']['poison_exercised'])
        self.assertEqual(result['watched']['poisons'], [(POISON_DAMAGE, 0.0)])
        self.assertEqual(len(result['watched']['blocks']), 1)

    def test_poison_optional_when_no_white(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines()
                        if 'P2_HANA_POISON' not in line)
        result = validate(log, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertFalse(result['watched']['poison_exercised'])
        self.assertTrue(result['checks']['poison_accounting'])

    def test_duplicate_poison_without_eat_fails(self):
        log = GOOD_LOG + '\nP2_HANA_POISON generator=346006 pikmin=1 ' \
                         f'damage={POISON_DAMAGE:.1f} health=0.0'
        result = validate(log, code=0)
        self.assertFalse(result['checks']['poison_accounting'])
        self.assertFalse(result['passed'])

    def test_missing_underground_gate_fails(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines()
                        if not line.startswith('P2_HANA_UNDERGROUND '))
        result = validate(log, code=0)
        # The underground runtime markers are informational (authoritative-only
        # TEKIOPT toggle; Hana wakes immediately in this arena); the policy test
        # covers the gate, so only the checks are asserted here.
        self.assertFalse(result['checks']['underground_enter'])
        self.assertFalse(result['checks']['underground_exit'])

    def test_reversed_gate_order_fails(self):
        enter = 'P2_HANA_UNDERGROUND generator=346006 event=enter no_atari=1 invulnerable=1'
        exit_ = 'P2_HANA_UNDERGROUND generator=346006 event=exit no_atari=0 invulnerable=0'
        log = GOOD_LOG.replace(enter, '@@ENTER@@').replace(exit_, enter).replace('@@ENTER@@', exit_)
        result = validate(log, code=0)
        self.assertFalse(result['checks']['underground_order'])

    def test_attack_navi_outside_window_fails(self):
        log = GOOD_LOG.replace('P2_HANA_ATTACK_NAVI generator=346006 frame=18.0',
                               'P2_HANA_ATTACK_NAVI generator=346006 frame=80.0')
        result = validate(log, code=0)
        self.assertFalse(result['checks']['attack_navi_event'])
        self.assertFalse(result['passed'])

    def test_missing_identity_fails(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines()
                        if 'P2_HANA_BIND' not in line)
        result = validate(log, code=0)
        self.assertFalse(result['checks']['identity'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
