import json
from pathlib import Path
import sys
import tempfile
import unittest
from scripts.prepare_pikmin2_manual_qa import check, inventory, source_inventory, prepare
from scripts.bundle_pikmin2_fixture import sha256
from scripts.compare_pikmin2_extractions import manifest


class ManualQATests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.source = self.root/'source'; self.source.mkdir()
        for name in ('scripts','experimental','randomizer'):
            (self.source/name).mkdir()
            (self.source/name/'sample.py').write_text('# source')
        self.asset = self.root/'asset'; self.asset.write_bytes(b'asset')
        self.path = self.root/'qa-launch.json'
        runtime = {}
        command = [sys.executable,'-m','scripts.play_pikmin2_surface','--treasure',str(self.asset)]
        for role in ('surface','cave'):
            directory=self.root/role; directory.mkdir()
            (directory/'game.exe').write_bytes(b'executable')
            (directory/'runtime-provenance.json').write_text(json.dumps({'executable':'game.exe'}))
            runtime[role]=manifest(directory)
            command += ['--'+role+'-exe',str(directory/'game.exe')]
        command += ['--output',str(self.root/'session')]
        self.record=dict(schema=1,source=str(self.source),source_files=source_inventory(self.source),
            python=dict(path=sys.executable,binary=str(Path(sys.base_prefix)/'python.exe'),sha256=sha256(Path(sys.base_prefix)/'python.exe')),
            assets={'treasure':str(self.asset)},inputs={'treasure':inventory(self.asset)},
            runtime=runtime,command=command,session=str(self.root/'session'))
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.record))

    def test_check_is_read_only(self):
        before=manifest(self.root)
        self.assertEqual(check(self.path)['command'],self.record['command'])
        self.assertEqual(manifest(self.root),before)

    def test_asset_mutation_rejected(self):
        self.asset.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Asset input changed'): check(self.path)

    def test_source_mutation_rejected(self):
        (self.source/'scripts/sample.py').write_text('# edited')
        with self.assertRaisesRegex(ValueError,'source changed'): check(self.path)

    def test_runtime_missing_or_extra_rejected(self):
        (self.root/'cave/game.exe').unlink()
        with self.assertRaisesRegex(ValueError,'Runtime bundle changed'): check(self.path)
        (self.root/'cave/game.exe').write_bytes(b'executable')
        (self.root/'cave/extra.dll').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError,'Runtime bundle changed'): check(self.path)

    def test_command_tampering_rejected(self):
        self.record['command'][2]='different.module'; self.save()
        with self.assertRaisesRegex(ValueError,'command differs'): check(self.path)

    def test_session_preserved(self):
        session=self.root/'session'; session.mkdir(); (session/'save').write_bytes(b'save')
        with self.assertRaisesRegex(ValueError,'session already exists'): check(self.path)
        self.assertEqual((session/'save').read_bytes(),b'save')

    def test_prepare_refuses_existing_output_before_input_io(self):
        with self.assertRaisesRegex(ValueError,'New output required'):
            prepare({},self.root,None,[],None)


if __name__ == '__main__':
    unittest.main()
