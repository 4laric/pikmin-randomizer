'''Focused fail-closed tests for the chal3 runtime acceptance driver (#566).
Synthetic logs only; no builds, runs, or shared writes.'''

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.p1_challenge_spring_runtime_acceptance as driver


GOOD = chr(10).join([
    'CHALLENGE_LAYOUT_READY id=challenge-3 stage_index=19 file=stages/chal3.ini story=1',
    '[Pikipelago] CHALLENGE_LAYOUT_READY id=challenge-3',
    '[PC Generator] default: initialised 87 recognised generators, spawned 111 creatures',
    '[PC Generator] plant: initialised 38 recognised generators, spawned 38 creatures',
    'P2_CHALLENGE_PARK nx=564.550 ny=0.000 nz=6.246',
    'P2_CHALLENGE_SQUAD pikis=20',
    'SDL2 Window & OpenGL Context initialized successfully (960x540)',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_CHALLENGE_BOOT level=3 slot=chal3',
    'PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive',
    '[PC Port] FPS: 30.0', '[PC Port] FPS: 30.0', '[PC Port] FPS: 30.0', '[PC Port] FPS: 30.0',])


class ObserveTests(unittest.TestCase):
    def test_good_log_passes_identity(self):
        facts = driver.parse_run_log(GOOD)
        self.assertEqual(facts['layout_id'], 'challenge-3')
        self.assertEqual(facts['boot_level'], 3)
        self.assertEqual(facts['boot_slot'], 'chal3')
        self.assertEqual(facts['squad_pikis'], 20)
        self.assertEqual(facts['spawned_total'], 111 + 38)
        self.assertTrue(facts['window_960x540'])
        self.assertTrue(facts['window_centered'])
        self.assertTrue(facts['fixture_pass_marker'])
        self.assertFalse(facts['captain_down'])
        record = driver.accept_facts(facts, driver.GUARD_SHA256)
        self.assertEqual(record['gates']['identity_spawn']['status'], 'PASS')
        self.assertEqual(record['gates']['identity_spawn']['method'], 'natural')
        for gate in ('movement_animation', 'attacks_receivers', 'death_corpse',
                     'transport_reward', 'cleanup_reentry'):
            self.assertEqual(record['gates'][gate]['status'], 'UNTESTED')

    def test_captain_down_blocks_identity(self):
        facts = driver.parse_run_log(GOOD + chr(10) + 'P2_FIXTURE_CAPTAIN_DOWN tick=9' + chr(10))
        self.assertTrue(facts['captain_down'])
        record = driver.accept_facts(facts, driver.GUARD_SHA256)
        self.assertEqual(record['gates']['identity_spawn']['status'], 'UNTESTED')

    def test_crash_is_untested_not_pass(self):
        facts = driver.parse_run_log('something broke' + chr(10))
        record = driver.accept_facts(facts, driver.GUARD_SHA256)
        for gate in record['gates'].values():
            self.assertEqual(gate['status'], 'UNTESTED')

    def test_missing_markers_untested(self):
        facts = driver.parse_run_log('[PC Port] FPS: 30.0' + chr(10))
        record = driver.accept_facts(facts, driver.GUARD_SHA256)
        self.assertEqual(record['gates']['identity_spawn']['status'], 'UNTESTED')

    def test_wrong_stage_fails_identity(self):
        facts = driver.parse_run_log(GOOD.replace('challenge-3', 'challenge-2'))
        record = driver.accept_facts(facts, driver.GUARD_SHA256)
        self.assertEqual(record['gates']['identity_spawn']['status'], 'UNTESTED')

    def test_empty_squad_fails_identity(self):
        facts = driver.parse_run_log(GOOD.replace('pikis=20', 'pikis=0'))
        record = driver.accept_facts(facts, driver.GUARD_SHA256)
        self.assertEqual(record['gates']['identity_spawn']['status'], 'UNTESTED')

    def test_package_stage_checks(self):
        import json
        import tempfile
        good = {"schema": 1, "stages": [
            {"slot": "chal3", "challenge_level": 3,
             "argv": ["exe", "--experimental-challenge-level", "3"]}]}
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / 'p.json'
            pkg.write_text(json.dumps(good), encoding='utf-8')
            stage, problem = driver.check_stage_package(str(pkg))
            self.assertIsNone(problem)
            self.assertEqual(stage['slot'], 'chal3')
            bad = {"schema": 1, "stages": [
                {"slot": "chal3", "challenge_level": 2,
                 "argv": ["exe", "--experimental-challenge-level", "2"]}]}
            pkg.write_text(json.dumps(bad), encoding='utf-8')
            _, problem = driver.check_stage_package(str(pkg))
            self.assertIsNotNone(problem)

    def test_wave_pins_present(self):
        self.assertEqual(driver.WAVE_ROOT_TIP, '347526301a4a91df673a631c7d7ab0579e5823a9')
        self.assertEqual(driver.WAVE_NATIVE_TIP, '58df488eb1d9582b0ef625d46874f3427c18628d')
        self.assertEqual(driver.C531_TIP, '3eb8806997ec3d9cdf72a9fb3f93b0461045a956')
        self.assertEqual(driver.GUARD_SHA256, 'd2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474')
        self.assertEqual(driver.LEVEL, 3)


    def test_harness_import_resolves_wave(self):
        import scripts.p1_challenge_spring_runtime_acceptance as d2
        wave_root = ('C:/Users/alari/pikmin-randomizer/output/workflow/autofill/'
                     'planning-shards/p1-challenge/prepared/'
                     'p1-challenge-spring-runtime-acceptance-output/wave-root')
        harness, inputs_pkg = d2.import_harness(wave_root)
        self.assertTrue(hasattr(harness, 'build'))
        self.assertEqual(inputs_pkg.CONTRACT_PIN,
                         '9aa6faad2c76b3182b5ad3de3f564d5e5431ba90')


if __name__ == '__main__':
    unittest.main()
