"""Lane 16 Frog/MaroFrog corpse carry/delivery fixture tests (#167/#201)."""
import unittest
from unittest.mock import patch

from experimental.pikmin2_frog_carry import run, validate


class FrogCarryTests(unittest.TestCase):
    def sample(self):
        return (
            'P2_FROG_CARRY_BIRTH id=201001 type=0 registered=1 x=-538.186 y=30.000 z=1569.469\n'
            'P2_FROG_CARRY_BIRTH id=201002 type=33 registered=1 x=-458.186 y=30.000 z=1569.469\n'
            'P2_FROG_CARRY_BIRTH id=201003 type=0 registered=0 x=-150.000 y=30.000 z=1550.000\n'
            'P2_FROG_CARRY_BIRTH id=201004 type=33 registered=0 x=150.000 y=30.000 z=1550.000\n'
            'P2_FROG_INJECTED_ATTACK id=201001 accepted=1\n'
            'P2_FROG_INJECTED_ATTACK id=201002 accepted=1\n'
            'P2_FROG_CORPSE id=201001 found=1 alive=1 state=0 x=-538.186 y=30.000 z=1569.469\n'
            'P2_FROG_CORPSE id=201002 found=1 alive=1 state=0 x=-458.186 y=30.000 z=1569.469\n'
            'P2_FROG_CORPSE_GROUND id=201001 ground=-0.680 snapped=1 min_carriers=7\n'
            'P2_FROG_CARRY_ASSIST moved=1 around=201001 assigned=18 attempt=1 pikis=18\n'
            'P2_FROG_CARRY id=201001 carried=1 carriers=3 strength=3 state=0\n'
            'P2_FROG_CARRY_TICK id=201001 state=1 alive=1 strength=7 carriers=7 distance=12.000 x=-140.000 y=30.000 z=1840.000\n'
            'P2_FROG_CARRY_TICK id=201001 state=1 alive=1 strength=7 carriers=7 distance=530.000 x=-480.000 y=30.000 z=1470.000\n'
            'P2_FROG_DELIVER id=201001 delivered=1 goal=1 distance=531.000 state=1\n'
            'P2_FROG_CARRY_RESULT reason=complete corpses=2 carry=1 deliver=1 assisted=1\n'
            'PASS P2_FROG_CARRY corpses=2 carry=1 deliver=1 assisted=1\n')

    def test_complete_observation_passes(self):
        result = validate(self.sample(), 0)
        self.assertTrue(result['passed'])
        self.assertEqual(result['carry'], ['201001'])
        self.assertEqual(result['deliver'], ['201001'])
        self.assertFalse(result['unobserved'])
        self.assertTrue(result['assisted'])
        self.assertTrue(result['grounded'])
        self.assertEqual(result['route_distance'], 530.0)

    def test_nonzero_exit_rejected(self):
        self.assertFalse(validate(self.sample(), 1)['passed'])

    def test_missing_carry_rejected(self):
        text = self.sample().replace('P2_FROG_CARRY id=201001 carried=1 carriers=3 strength=3 state=0\n', '')
        result = validate(text, 0)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['carry'])
        self.assertTrue(result['unobserved'])

    def test_missing_delivery_rejected(self):
        text = self.sample().replace('P2_FROG_DELIVER id=201001 delivered=1 goal=1 distance=531.000 state=1\n', '')
        result = validate(text, 0)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['deliver'])
        self.assertTrue(result['unobserved'])

    def test_delivery_without_carry_rejected(self):
        text = self.sample().replace('P2_FROG_CARRY id=201001 carried=1 carriers=3 strength=3 state=0\n', '')
        result = validate(text, 0)
        self.assertFalse(result['passed'])
        self.assertEqual(result['delivered'], [])
        self.assertTrue(result['unobserved'])

    def test_injected_only_without_carry_is_unobserved(self):
        text = (
            'P2_FROG_CARRY_BIRTH id=201001 type=0 registered=1 x=-538.186 y=30.000 z=1569.469\n'
            'P2_FROG_CARRY_BIRTH id=201002 type=33 registered=1 x=-458.186 y=30.000 z=1569.469\n'
            'P2_FROG_CARRY_BIRTH id=201003 type=0 registered=0 x=-150.000 y=30.000 z=1550.000\n'
            'P2_FROG_CARRY_BIRTH id=201004 type=33 registered=0 x=150.000 y=30.000 z=1550.000\n'
            'P2_FROG_INJECTED_ATTACK id=201001 accepted=1\n'
            'P2_FROG_INJECTED_ATTACK id=201002 accepted=1\n'
            'P2_FROG_CORPSE id=201001 found=1 alive=1 state=0 x=-538.186 y=30.000 z=1569.469\n'
            'P2_FROG_CORPSE id=201002 found=1 alive=1 state=0 x=-458.186 y=30.000 z=1569.469\n'
            'P2_FROG_CARRY_RESULT reason=budget corpses=2 carry=0 deliver=0 assisted=0\n'
            'UNOBSERVED P2_FROG_CARRY corpses=2 carry=0 deliver=0 assisted=0\n')
        result = validate(text, 0)
        self.assertFalse(result['passed'])
        self.assertEqual(result['injected'], ['201001', '201002'])
        self.assertEqual(result['corpses'], ['201001', '201002'])
        self.assertTrue(result['unobserved'])

    def test_missing_corpse_rejected(self):
        text = self.sample().replace('P2_FROG_CORPSE id=201002 found=1 alive=1 state=0 x=-458.186 y=30.000 z=1569.469\n', '')
        self.assertFalse(validate(text, 0)['passed'])

    def test_missing_registered_birth_rejected(self):
        text = self.sample().replace('P2_FROG_CARRY_BIRTH id=201002 type=33 registered=1 x=-458.186 y=30.000 z=1569.469\n', '')
        self.assertFalse(validate(text, 0)['passed'])


    def test_run_uses_near_onion_arena(self):
        with patch('experimental.pikmin2_frog_carry._run') as runner:
            run('assets', 'bank', 'output', 'exe')
        runner.assert_called_once_with('assets', 'bank', 'output', 'exe', validator=validate, near_onion=True)


if __name__ == '__main__':
    unittest.main()
