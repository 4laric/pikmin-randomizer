"""Tests for the kusachi natural-gameplay observation adapter (#780).

The adapter classifies a guarded run log into the six arena gates. These tests
use synthetic receipts (no runtime) and verify fail-closed behaviour: a gate is
never PASS without its marker, and a captain-down run cannot substantiate any
gate. Module names contain hyphens, so it is loaded by path.
"""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[2] / 'experimental' / 'content_lanes' / \
    'p2-challenge-ch_nari_01kusachi_gameplay.py'
spec = importlib.util.spec_from_file_location('kusachi_gameplay', MODULE)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

IDENTITY = 'P2_KUSACHI_IDENTITY tick=1 total=20 blue=20 wired=20 pass=1\n'
MOVEMENT = 'P2_KUSACHI_MOVEMENT tick=80 samples=20 peak=1626.970 pass=1\n'
ENEMIES = 'P2_KUSACHI_ENEMIES tick=60 teki=1 teki_max=1\n'
WINDOW = 'P2_KUSACHI_GAMEPLAY_WINDOW size=960x540 pos=1,1 display=1920x1080 centered=1\n'
STAGE = 'P2_KUSACHI_GAMEPLAY_STAGE cave=ch_NARI_01kusachi ui_index=3 floors=1 seconds=180\n'
PASS = 'PASS KUSACHI_GAMEPLAY identity=1 movement=1 total=20 extinction=1\n'
ATTACK = 'P2_KUSACHI_ATTACK status=PASS\n'
TRANSPORT = 'P2_KUSACHI_TRANSPORT status=PASS\n'
DEATH = 'P2_KUSACHI_DEATH status=PASS\n'
CLEANUP = 'P2_KUSACHI_CLEANUP status=PASS\n'
CAPTAIN_DOWN = 'P2_FIXTURE_CAPTAIN_DOWN tick=0 hp=0.000 orima_dead=1 dead_state=0 outcome=BLOCKED\n'


class AdapterTests(unittest.TestCase):
    def test_pinned_stage_identity(self):
        identity = adapter.stage_identity()
        self.assertEqual(identity['cave_id'], 'ch_NARI_01kusachi')
        self.assertEqual(identity['ui_index'], 3)
        self.assertEqual(identity['floors'], 1)
        self.assertEqual(identity['floor_seconds'], [180.0])
        self.assertEqual(identity['expected_squad'], 20)
        self.assertEqual(len(identity['roster']), 7)
        self.assertEqual(identity['roster'][0], [0, 0, 50])

    def test_identity_and_movement_pass_others_untested(self):
        gates = adapter.classify_gates(STAGE + WINDOW + IDENTITY + ENEMIES + MOVEMENT + PASS)
        self.assertEqual(gates['identity_spawn']['status'], 'PASS')
        self.assertEqual(gates['movement_animation']['status'], 'PASS')
        for name in ('attacks_receivers', 'death_corpse', 'transport_reward', 'cleanup_reentry'):
            self.assertEqual(gates[name]['status'], 'UNTESTED')
            self.assertEqual(gates[name]['method'], 'unobserved')

    def test_no_identity_is_fail_closed(self):
        gates = adapter.classify_gates(STAGE + WINDOW + MOVEMENT + PASS)
        self.assertNotEqual(gates['identity_spawn']['status'], 'PASS')
        self.assertNotEqual(gates['movement_animation']['status'], 'PASS')

    def test_captain_down_cannot_substantiate_any_gate(self):
        gates = adapter.classify_gates(STAGE + WINDOW + IDENTITY + MOVEMENT + CAPTAIN_DOWN)
        for name, gate in gates.items():
            self.assertNotEqual(gate['status'], 'PASS', name)

    def test_full_events_upgrade_gates(self):
        log = STAGE + WINDOW + IDENTITY + MOVEMENT + ATTACK + DEATH + TRANSPORT + CLEANUP + PASS
        gates = adapter.classify_gates(log)
        for name in ('identity_spawn', 'movement_animation', 'attacks_receivers',
                     'death_corpse', 'transport_reward', 'cleanup_reentry'):
            self.assertEqual(gates[name]['status'], 'PASS', name)

    def test_run_summary_reports_receipts(self):
        summary = adapter.run_summary(STAGE + WINDOW + IDENTITY + ENEMIES + MOVEMENT
                                      + 'P2_KUSACHI_EXTINCTION tick=90 wired=0\n' + PASS)
        self.assertEqual(summary['cave'], 'ch_NARI_01kusachi')
        self.assertEqual(summary['ui_index'], 3)
        self.assertTrue(summary['window_960'])
        self.assertEqual(summary['squad']['total'], 20)
        self.assertEqual(summary['teki_first'], 1)
        self.assertEqual(summary['extinction_tick'], 90)
        self.assertTrue(summary['fixture_pass'])


if __name__ == '__main__':
    unittest.main()
