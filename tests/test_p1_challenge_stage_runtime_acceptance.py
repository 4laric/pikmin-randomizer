'''Focused fail-closed tests for the chal0 runtime acceptance driver (#565).
Synthetic logs only; no builds, runs, or shared writes.'''

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.p1_challenge_stage_runtime_acceptance as driver


GOOD = chr(10).join([
    'CHALLENGE_LAYOUT_READY id=challenge-0 stage_index=16 file=stages/chal0.ini story=1',
    '[PC Generator] default: initialised 80 recognised generators, spawned 95 creatures',
    '[PC Generator] default: initialised 80 recognised generators, spawned 95 creatures',
    'P2_CHALLENGE_SQUAD pikis=20',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_CHALLENGE_BOOT level=0 slot=chal0',
    'PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive',
    '[PC Port] FPS: 30.0', '[PC Port] FPS: 30.0', '[PC Port] FPS: 30.0', '[PC Port] FPS: 30.0',])



class ObserveTests(unittest.TestCase):
    def test_good_log_passes_identity(self):
        facts = driver.observe_run(GOOD, 0)
        self.assertEqual(facts['layout']['id'], 'challenge-0')
        self.assertEqual(facts['layout']['stage_index'], 16)
        self.assertEqual(facts['squads'], [20])
        self.assertEqual(facts['fps_frames'], 4)
        self.assertFalse(facts['captain_down'])
        gates = driver.gate_verdicts(facts)
        self.assertEqual(gates['identity_spawn'][0], 'PASS')
        for gate in ('movement_animation', 'attacks_receivers', 'death_corpse', 'transport_reward', 'cleanup_reentry'):
            self.assertEqual(gates[gate][0], 'UNTESTED')

    def test_captain_down_blocks_everything(self):
        facts = driver.observe_run(GOOD + 'P2_FIXTURE_CAPTAIN_DOWN tick=9 outcome=BLOCKED' + chr(10), 86)
        self.assertTrue(facts['captain_down'])
        gates = driver.gate_verdicts(facts)
        for gate in driver.GATES:
            self.assertEqual(gates[gate][0], 'BLOCKED')

    def test_crash_is_untested_not_pass(self):
        facts = driver.observe_run('something broke' + chr(10), 1)
        gates = driver.gate_verdicts(facts)
        for gate in driver.GATES:
            self.assertEqual(gates[gate][0], 'UNTESTED')

    def test_missing_markers_untested(self):
        facts = driver.observe_run('[PC Port] FPS: 30.0' + chr(10), 0)
        gates = driver.gate_verdicts(facts)
        self.assertEqual(gates['identity_spawn'][0], 'UNTESTED')

    def test_wrong_stage_fails_identity(self):
        facts = driver.observe_run(GOOD.replace('challenge-0', 'challenge-1'), 0)
        gates = driver.gate_verdicts(facts)
        self.assertEqual(gates['identity_spawn'][0], 'FAIL')

    def test_guard_hash_record(self):
        rec = driver.guard_record()
        self.assertEqual(rec['sha256'], driver.GUARD_SHA256)


if __name__ == '__main__':
    unittest.main()
