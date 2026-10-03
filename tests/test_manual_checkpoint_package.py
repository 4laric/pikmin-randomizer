import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_pikmin2_manual_checkpoint import prepare


class ManualCheckpointPackageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        for name in ('bin', 'randomizer', 'experimental', 'docs', 'sidecars', 'starting-session'):
            (self.source / name).mkdir()
        assets = self.root / 'assets' / 'dataDir'
        assets.mkdir(parents=True)
        for name in ('consFont.bti', 'bigFont.bti'):
            (assets / name).write_bytes(b'legal test stand-in')
        self.exe = self.source / 'bin' / 'nectar.exe'
        self.exe.write_bytes(b'frozen executable stand-in')
        self.card = self.source / 'starting-session' / 'card.sav'
        self.card.write_bytes(b'genuine checkpoint stand-in')
        (self.source / 'docs' / 'roster.json').write_text('{}')
        (self.source / 'manifest.json').write_text('{}')
        self.host = ('if args.smoke_seconds and time.monotonic()-started>=args.smoke_seconds:break\n'
                     'return 0 if args.smoke_seconds else process.returncode\n')
        (self.source / 'play.py').write_text(self.host)
        (self.source / 'README.md').write_text('Instructions')
        (self.source / 'Start.cmd').write_text('launcher')
        (self.source / 'package.json').write_text(json.dumps(dict(
            assets=str(assets.parent), native_source='test-pin',
            host_files_sha256={'docs/roster.json': hashlib.sha256((self.source/'docs/roster.json').read_bytes()).hexdigest()},
            launcher_sha256={'play.py': hashlib.sha256((self.source/'play.py').read_bytes()).hexdigest()},
            binaries={'nectar.exe': hashlib.sha256(self.exe.read_bytes()).hexdigest()},
            starting_session_sha256={'card.sav': hashlib.sha256(self.card.read_bytes()).hexdigest()})))

    def test_copy_preserves_checkpoint_source_and_roster(self):
        target = self.root / 'private'
        receipt = prepare(self.source, target, 60)
        self.assertEqual((target / 'human-session' / 'card.sav').read_bytes(), self.card.read_bytes())
        self.assertTrue((target / 'docs' / 'roster.json').is_file())
        self.assertEqual((self.source / 'play.py').read_text(), self.host)
        self.assertIn('wall-clock-bound', (target / 'play.py').read_text())
        self.assertFalse(receipt['gameplay_accepted'])
        with self.assertRaisesRegex(ValueError, 'existing saves'):
            prepare(self.source, target, 60)

    def test_changed_binary_refuses_before_staging(self):
        self.exe.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'binary differs'):
            prepare(self.source, self.root / 'private', 60)
        self.assertFalse((self.root / 'private').exists())

    def test_changed_checkpoint_refuses_before_staging(self):
        self.card.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checkpoint differs'):
            prepare(self.source, self.root / 'private', 60)
        self.assertFalse((self.root / 'private').exists())

    def test_changed_host_refuses_before_staging(self):
        (self.source / 'docs/roster.json').write_text('{"modified":true}')
        with self.assertRaisesRegex(ValueError, 'host differs'):
            prepare(self.source, self.root / 'private', 60)
        self.assertFalse((self.root / 'private').exists())

    def test_revised_host_preserves_smoke_verdict_and_card(self):
        revised = ('def main():\n'
                   '    if True:\n'
                   '        if True:\n'
                   '            if True:\n'
                   '                while True:\n'
                   '                    if args.smoke_seconds and time.monotonic() - started >= args.smoke_seconds:\n'
                   '                        break\n'
                   '        if args.smoke_seconds:\n'
                   '            return 0 if run.handshaken else 1\n'
                   '        return process.returncode\n')
        (self.source / 'play.py').write_text(revised)
        metadata_path = self.source / 'package.json'
        metadata = json.loads(metadata_path.read_text())
        metadata['launcher_sha256']['play.py'] = hashlib.sha256((self.source / 'play.py').read_bytes()).hexdigest()
        metadata_path.write_text(json.dumps(metadata))
        target = self.root / 'private'
        prepare(self.source, target, 600)
        bounded = (target / 'play.py').read_text()
        compile(bounded, 'bounded-host', 'exec')
        self.assertIn('return 0 if run.handshaken else 1', bounded)
        self.assertEqual((target / 'human-session' / 'card.sav').read_bytes(), self.card.read_bytes())
        self.assertEqual((self.source / 'play.py').read_text(), revised)


if __name__ == '__main__':
    unittest.main()
