"""Engine-free native IPC acceptance; this does not certify gameplay routes."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun

PROBE = os.environ.get('PIKMIN_CATALOG_PROBE')
OUTPUT = os.environ.get('PIKMIN_TEST_OUTPUT')


@unittest.skipUnless(PROBE, 'Set PIKMIN_CATALOG_PROBE to the paired native probe')
class NativeCatalogTests(unittest.TestCase):
    def run_probe(self, run, *args):
        run.write_state(True)
        return subprocess.run([PROBE, '--randomizer-seed', str(run.bootstrap),
                               '--enemy-checks-probe', *map(str, args)],
                              capture_output=True, text=True, timeout=15)

    def make(self, directory, **options):
        settings = dict(mode='ap', p2_enemies=True, p2_species='playable', p2_checks=True)
        settings.update(options)
        manifest = generate('native-ap-1046', **settings)
        session = Session(manifest, directory)
        return session, NativeRun(session)

    def test_delivery_separates_source_from_host_and_replays_once(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            session, run = self.make(directory)
            p2 = next(r for r in session.manifest['enemy_catalog']['checks'] if r['game'] == 'p2')
            uid = p2['sources'][0]
            stage = next(s['stage'] for s in session.manifest['enemy_catalog']['sources'] if s['uid'] == uid)
            args = ['--deliver-p2', p2['species'], uid, stage]
            result = self.run_probe(run, *args, *args, '--deliver-p1', 3,
                                    '--check-name', 'Bestiary: Deliver Puffstool')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            run.poll()
            self.assertEqual(session.data['checked'], [p2['name'], 'Bestiary: Deliver Dwarf Bulborb'])
            before = (run.directory/'checks.txt').read_bytes()
            next_run = NativeRun(session)
            again = self.run_probe(next_run, *args)
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            next_run.poll()
            self.assertFalse((next_run.directory/'checks.txt').exists())
            self.assertEqual((run.directory/'checks.txt').read_bytes(), before)
            recovered = Session(session.manifest, directory)
            self.assertEqual(recovered.data['checked'], session.data['checked'])

    def test_crash_before_runner_poll_recovers_exact_mapping(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            session, run = self.make(directory)
            row = next(r for r in session.manifest['enemy_catalog']['checks'] if r['game'] == 'p2')
            uid = row['sources'][0]
            stage = next(s['stage'] for s in session.manifest['enemy_catalog']['sources'] if s['uid'] == uid)
            result = self.run_probe(run, '--deliver-p2', row['species'], uid, stage)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            recovered = Session(session.manifest, directory)
            self.assertEqual(recovered.data['checked'], [row['name']])
            run.bootstrap.write_text(run.bootstrap.read_text().replace('ENEMY_CHECKS 1', 'ENEMY_CHECKS 2'))
            with self.assertRaisesRegex(ValueError, 'catalog mismatch'):
                Session(session.manifest, directory)

    def test_foreign_generator_and_stage_cannot_earn_source_check(self):
        for wrong_stage in (False, True):
            with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
                session, run = self.make(directory)
                row = next(r for r in session.manifest['enemy_catalog']['checks'] if r['game'] == 'p2')
                uid = row['sources'][0]
                stage = next(s['stage'] for s in session.manifest['enemy_catalog']['sources'] if s['uid'] == uid)
                result = self.run_probe(run, '--deliver-p2', row['species'], uid if wrong_stage else 1,
                                        (stage+1)%5 if wrong_stage else stage)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('resolved source catalog', result.stdout + result.stderr)
                self.assertFalse((run.directory/'checks.txt').exists())

    def test_missing_native_capability_rejected(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            session, run = self.make(directory)
            result = self.run_probe(run)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            hello = run.directory/'hello.txt'
            hello.write_text(hello.read_text().replace(' resolved-enemy-checks-v1', ''))
            with self.assertRaisesRegex(ValueError, 'handshake mismatch'):
                run.poll()

    def test_proxy_and_purple_bootstrap_suffixes_recover(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            session, _ = self.make(directory, p2_species='full', p2_proxy_tier='proven', permanent_checks=True)
            run = NativeRun(session, purple_campaign=True)
            result = self.run_probe(run, '--deliver-p1', 3)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            recovered = Session(session.manifest, directory)
            self.assertEqual(recovered.data['checked'], ['Bestiary: Deliver Dwarf Bulborb'])


if __name__ == '__main__':
    unittest.main()
