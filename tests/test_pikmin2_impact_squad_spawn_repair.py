'''Fail-closed tests for the squad-spawn stall classifier.'''

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import experimental.pikmin2_impact_squad_spawn_repair as lane

NL = chr(10)

class ClassifyTests(unittest.TestCase):
    def test_spawned(self):
        text = NL.join(['P2_CHALLENGE_PARK_ALIVE pikis=3', 'P2_CHALLENGE_SQUAD pikis=3', 'P2_CHALLENGE_BOOT level=0 slot=chal0', 'PASS P2_CHALLENGE_GUARDED_BOOT x'])
        verdict = lane.classify_log(text, 0)
        self.assertEqual(verdict['verdict'], 'spawned')

    def test_frozen_attributed(self):
        text = NL.join(['P2_CHALLENGE_PARK_ALIVE pikis=1', 'P2_CHALLENGE_GATE_DIAG gate=movie observed=1 alive=1 frames=120 movie=1 pause=0 ui=0 navi=1'])
        verdict = lane.classify_log(text, 1)
        self.assertEqual(verdict['verdict'], 'frozen-attributed')

    def test_frozen_unattributed(self):
        verdict = lane.classify_log('P2_CHALLENGE_PARK nx=1 ny=2 nz=3' + NL, 1)
        self.assertEqual(verdict['verdict'], 'frozen-unattributed')

    def test_blocked(self):
        verdict = lane.classify_log('P2_FIXTURE_CAPTAIN_DOWN tick=9' + NL, 86)
        self.assertEqual(verdict['verdict'], 'blocked')


if __name__ == '__main__':
    unittest.main()
