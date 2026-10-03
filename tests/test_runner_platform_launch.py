"""Exercise ordinary launch/bootstrap; these controls do not accept gameplay."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from randomizer import runner
from randomizer.seed import generate, fingerprint


class OrdinaryPlatformLaunch(unittest.TestCase):
    def test_linux_launches_real_child_with_private_bootstrap(self):
        if sys.platform != "linux":
            self.skipTest("actual Linux subprocess and symlink test")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            assets = base / "retail"
            (assets / "dataDir/stages").mkdir(parents=True)
            exe = base / "native-standin"
            exe.write_text("#!/bin/sh\nprintf '%s\\n' \"$1\" \"$2\" > child-argv.txt\n")
            exe.chmod(0o700)
            manifest = generate(1153)
            observed = {}

            async def serve(session, run, process, *args):
                self.assertEqual(process.wait(timeout=5), 0)
                self.assertEqual(session.manifest, manifest)
                self.assertTrue((run.directory / 'assets').is_symlink())
                self.assertEqual((run.directory / 'assets').resolve(), assets.resolve())
                self.assertEqual((run.directory / 'child-argv.txt').read_text().splitlines(),
                                 ['--randomizer-seed', str(run.bootstrap.resolve())])
                self.assertEqual(json.loads((run.directory / 'overlay-manifest.json').read_text()), manifest)
                observed['ran'] = True

            with patch.object(runner, 'serve', serve), patch.dict(os.environ, {
                    'PIKMIN_SETTINGS_PATH': str(base / 'settings.conf')}):
                runner.launch(manifest, base / 'session', exe=exe, assets=assets)
            self.assertTrue(observed['ran'])

    def test_mixed_launch_preserves_manifest_and_platform_options(self):
        manifest = generate(1153, campaign_enemies=True, p2_enemies=True, p2_density='sampled-v1')
        for platform in ('linux', 'win32'):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                assets = base / 'retail'
                (assets / 'dataDir/stages').mkdir(parents=True)
                exe = base / 'nectar'
                exe.touch()
                calls = []

                def install(run, layout, content, **kwargs):
                    self.assertEqual(layout, manifest['p2_layout'])
                    self.assertEqual(set(kwargs['actor_bindings']), {b['target'] for b in layout['bindings']})
                    (run / 'assets').mkdir()
                    return {'bindings': layout['bindings']}

                def popen(argv, **kwargs):
                    calls.append((argv, kwargs))
                    return SimpleNamespace(pid=1234, returncode=0, poll=lambda: 0)

                async def serve(session, run, process, *args):
                    self.assertEqual(fingerprint(session.manifest), fingerprint(manifest))
                    self.assertIn('ENEMY_P2', run.bootstrap.read_text())

                with patch.object(runner.sys, 'platform', platform), \
                     patch.object(runner, 'serve', serve), \
                     patch.object(runner, 'verify_source_assets'), \
                     patch('experimental.pikmin2_family_install.install_layout', install), \
                     patch('randomizer.p2_units.stage_units', return_value=[]), \
                     patch.object(subprocess, 'Popen', popen), \
                     patch.object(subprocess, 'STARTUPINFO', lambda: SimpleNamespace(dwFlags=0), create=True), \
                     patch.object(subprocess, 'STARTF_USESHOWWINDOW', 1, create=True), \
                     patch.object(subprocess, 'CREATE_NO_WINDOW', 0x8000000, create=True), \
                     patch.dict(os.environ, {'PIKMIN_SETTINGS_PATH': str(base / 'settings.conf')}):
                    runner.launch(manifest, base / 'session', exe=exe, assets=assets, p2_content=base / 'content')
                self.assertEqual(len(calls), 2 if platform == 'win32' else 1)
                self.assertEqual('startupinfo' in calls[0][1], platform == 'win32')
                if platform == 'win32':
                    self.assertEqual(calls[0][1]['startupinfo'].wShowWindow, 1)
                    self.assertEqual(calls[1][1]['creationflags'], 0x8000000)


if __name__ == '__main__':
    unittest.main()
