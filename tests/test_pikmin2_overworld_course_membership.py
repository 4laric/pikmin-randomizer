'''Fail-closed tests for the overworld-course membership classifier.'''

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import experimental.pikmin2_overworld_course_membership as lane

NL = chr(10)


class ClassifyTests(unittest.TestCase):
    def test_linked(self):
        text = NL.join(['P2_OVERWORLD_COURSE_MEMBERSHIP_LINKED',
                        'P2_OVERWORLD_COURSE_FLAG course=forest index=1',
                        'P2_OVERWORLD_COURSE_REGISTERED course=forest',
                        'PASS P2_OVERWORLD_COURSE_MEMBERSHIP'])
        self.assertEqual(lane.classify_log(text, 0)['verdict'], 'linked')

    def test_boot_pass(self):
        text = NL.join(['P2_OVERWORLD_BOOT_COURSE_FLAG course=forest index=1',
                        'P2_OVERWORLD_BOOT_COURSE_REGISTERED course=forest',
                        'PASS P2_OVERWORLD_BOOT_SMOKE course=forest ticks=30'])
        verdict = lane.classify_log(text, 0)
        self.assertEqual(verdict['verdict'], 'boot-pass')
        self.assertEqual(verdict['flags'], [('forest', 1)])

    def test_blocked(self):
        verdict = lane.classify_log('P2_FIXTURE_CAPTAIN_DOWN tick=9' + NL, 86)
        self.assertEqual(verdict['verdict'], 'blocked')

    def test_unguarded_refused(self):
        verdict = lane.classify_log('unguarded runs refused' + NL, 2)
        self.assertEqual(verdict['verdict'], 'unguarded-refused')

    def test_unattributed(self):
        verdict = lane.classify_log('P2_OVERWORLD_BOOT_SMOKE room=1 challenge=-1' + NL, 1)
        self.assertEqual(verdict['verdict'], 'unattributed')


if __name__ == '__main__':
    unittest.main()
