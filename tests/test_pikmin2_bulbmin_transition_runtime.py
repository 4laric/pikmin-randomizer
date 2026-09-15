"""Unit tests for the lane-11 Bulbmin transition/restart validator."""
import unittest

from experimental.pikmin2_bulbmin_transition_runtime import validate

TOKEN = 'e844a2c8be554b7299fd6cc9856bc2d2'
WRITE = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_CAVE_READY floor=1 survivors=18 health=0.625',
    'P2_BULBMIN_TX_WILD made=1 phase=0',
    'P2_BULBMIN_TX_RECRUIT made=1 phase=1',
    'P2_CAVE_BULBMIN_TRANSITION move=descend removed=1',
    'P2_BULBMIN_TX_CHECKPOINT ok=1',
])
READ = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_CAVE_RESTORE species=1 maturity=0',
    'P2_CAVE_RESTORE species=5 maturity=0',
    'P2_CAVE_READY floor=2 survivors=17 health=0.625',
    'P2_BULBMIN_TX_READ bulbmin=1 observed=60',
    'PASS P2_BULBMIN_TRANSITION_RESTORE',
])
TRANSFER = '\n'.join([f'P2_CAVE_TRANSFER_3', TOKEN, '1 0.625 17',
                      *(['1 0'] * 16), '5 0', ''])


class BulbminTransitionRuntimeTests(unittest.TestCase):
    def test_validate_passes_on_source_logs(self):
        result = validate(WRITE, READ, TRANSFER)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['transfer'][0], 'P2_CAVE_TRANSFER_3')

    def test_engine_must_drop_the_wild_dependent(self):
        bad = WRITE.replace('P2_CAVE_BULBMIN_TRANSITION move=descend removed=1',
                            'P2_CAVE_BULBMIN_TRANSITION move=descend removed=0')
        result = validate(bad, READ, TRANSFER)
        self.assertFalse(result['checks']['transition_dropped_wild'])
        self.assertFalse(result['passed'])

    def test_recruit_birth_whistle_must_succeed(self):
        bad = WRITE.replace('P2_BULBMIN_TX_RECRUIT made=1 phase=1',
                            'P2_BULBMIN_TX_RECRUIT made=0 phase=-1')
        result = validate(WRITE, READ, TRANSFER)
        self.assertTrue(result['checks']['recruit_made'])
        result = validate(bad, READ, TRANSFER)
        self.assertFalse(result['checks']['recruit_made'])
        self.assertFalse(result['passed'])

    def test_transfer_must_carry_exactly_one_bulbmin(self):
        two = '\n'.join([f'P2_CAVE_TRANSFER_3', TOKEN, '1 0.625 17',
                         *(['1 0'] * 15), '5 0', '5 0', ''])
        result = validate(WRITE, READ, two)
        self.assertFalse(result['checks']['transfer_one_bulbmin'])
        self.assertFalse(result['passed'])

    def test_restore_requires_a_live_bulbmin(self):
        bad = READ.replace('P2_BULBMIN_TX_READ bulbmin=1', 'P2_BULBMIN_TX_READ bulbmin=0')
        result = validate(WRITE, bad, TRANSFER)
        self.assertFalse(result['checks']['read_bulbmin'])
        self.assertFalse(result['passed'])

    def test_abort_fails(self):
        result = validate(WRITE, READ + '\nInvalid P2 cave entry: Pikmin', TRANSFER)
        self.assertFalse(result['checks']['no_abort'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text', READ, TRANSFER)


if __name__ == '__main__':
    unittest.main()
