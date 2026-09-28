import unittest
from scripts.test_pikmin2_breadbug_visual_native import validate_log
class BreadbugVisualNativeDriverTests(unittest.TestCase):
    def test_enabled_requires_exact_one_displays_and_draw(self):
        text='PASS P2_BREADBUG_VISUAL_FIXTURE\n'+1*'P2_BREADBUG_VISUAL_READY\n'+1*'P2_BREADBUG_FIXTURE_GROUND\n'+'P2_BREADBUG_VISUAL_DRAW\n'
        validate_log(text,True)
        with self.assertRaises(ValueError):validate_log(text.replace('P2_BREADBUG_VISUAL_DRAW','missing'),True)
        with self.assertRaises(ValueError):validate_log(text,False)
    def test_disabled_must_finish_without_visual(self):
        validate_log('PASS P2_BREADBUG_VISUAL_FIXTURE',False)
        with self.assertRaises(ValueError):validate_log('',False)
