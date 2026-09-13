import unittest
from scripts.test_pikmin2_breadbug_actor_native import validate
class BreadbugActorRuntimeTests(unittest.TestCase):
    def valid(self):return 'P2_BREADBUG_ACTOR_READY generator=186081 native_type=8 xyz=-150.000000,30.000000,1850.000000\nP2_BREADBUG_ACTOR_DRAW\nP2_BREADBUG_ARENA_MOVE frame=300 displacement=50.5 moving=90\nPASS P2_BREADBUG_ACTOR_ARENA'
    def test_full_xyz_and_natural_motion(self):
        self.assertEqual(validate(self.valid())['max_displacement'],50.5)
        for text in (self.valid().replace('30.000000','0.000000'),self.valid().replace('moving=90','moving=0'),self.valid().replace('displacement=50.5','displacement=0'),self.valid().replace('P2_BREADBUG_ACTOR_DRAW','missing')):
            with self.assertRaises(ValueError):validate(text)
    def test_duplicate_ready_rejected(self):
        with self.assertRaises(ValueError):validate(self.valid()+'\n'+self.valid())
