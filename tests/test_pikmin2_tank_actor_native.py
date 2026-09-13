import unittest
from scripts.test_pikmin2_tank_actor_native import validate
class TankActorRuntimeTests(unittest.TestCase):
    def valid(self):return 'P2_TANK_PROXY_READY generator=186151 native_type=15 xyz=-150.000000,30.000000,1850.000000\nP2_TANK_PROXY_DRAW\nP2_TANK_ARENA_MOVE frame=300 displacement=50.5 moving=90\nP2_TANK_CONTROL generator=186152\nP2_WTANK_DISPLAY_READY display=186153\nP2_WTANK_DISPLAY_DRAW noninteractive_static_no_actor_no_collision_no_receiver\nP2_TANK_COUNTER state=1 motion=1 counter=1.0 frames=55\nP2_TANK_COUNTER state=1 motion=1 counter=2.0 frames=55\nPASS P2_TANK_ACTOR_ARENA'
    def test_full_xyz_and_natural_motion(self):
        self.assertEqual(validate(self.valid())['max_displacement'],50.5)
        for text in (self.valid().replace('30.000000','0.000000'),self.valid().replace('moving=90','moving=0'),self.valid().replace('displacement=50.5','displacement=0'),self.valid().replace('P2_TANK_PROXY_DRAW','missing')):
            with self.assertRaises(ValueError):validate(text)
    def test_duplicate_ready_rejected(self):
        with self.assertRaises(ValueError):validate(self.valid()+'\n'+self.valid())

    def test_water_control_and_counter_required(self):
        for text in (self.valid().replace('P2_WTANK_DISPLAY_DRAW','missing'),self.valid().replace('P2_TANK_CONTROL','missing'),self.valid().replace('counter=2.0','counter=1.0')):
            with self.assertRaises(ValueError):validate(text)
