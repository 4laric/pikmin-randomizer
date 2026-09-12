import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experimental import pikmin2_campaign as cave
from scripts import play_pikmin2_surface as manual


class ManualSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.run=self.root/'run';self.run.mkdir()
        self.content=SimpleNamespace(identity='a'*64)
        self.command=dict(run=str(self.run),checkpoint=cave.initial('a'*64),token='b'*32,
                          campaign='c'*32,trip='d'*32)
        self.write_transfer()

    def write_transfer(self,failed=False):
        count=0 if failed else 20;health=0 if failed else .75
        (self.run/'p2-cave-transfer.txt').write_text(f'P2_CAVE_TRANSFER_1\n{"b"*32}\n1 {health} {count}\n'+f'{cave.SPECIES.index("red")} 0\n'*count)
        (self.run/'p2-economy.txt').write_text(cave.ledger_text({}))
        (self.run/'surface-position.txt').write_text('b'*32+'\n-205.125 80 1161.25\n')

    def test_actual_snapshot_replay_is_exactly_once(self):
        first=manual.consume_entry(self.root,self.command,self.content).read()
        second=manual.consume_entry(self.root,self.command,self.content).read()
        self.assertEqual(first,second);self.assertEqual(first['revision'],1)
        self.assertEqual(first['surface']['position'],[-205.125,80,1161.25])
        self.assertEqual(first['trip']['checkpoint']['health'],.75)

    def test_failed_entry_persisted_without_ledger_or_revival(self):
        self.write_transfer(True)
        with self.assertRaisesRegex(RuntimeError,'failed'):manual.consume_entry(self.root,self.command,self.content)
        self.assertTrue((self.root/'failed-entry.json').exists())
        self.assertFalse((self.root/'session/surface-ledger.json').exists())

    def test_missing_position_cannot_commit_entry(self):
        (self.run/'surface-position.txt').unlink()
        with self.assertRaises(FileNotFoundError):manual.consume_entry(self.root,self.command,self.content)
        self.assertFalse((self.root/'session/surface-ledger.json').exists())

    def test_conflicting_native_replay_refused(self):
        manual.consume_entry(self.root,self.command,self.content)
        (self.run/'surface-position.txt').write_text('b'*32+'\n-200 80 1160\n')
        with self.assertRaisesRegex(ValueError,'Conflicting'):manual.consume_entry(self.root,self.command,self.content)

    def test_larger_party_not_truncated_or_staged(self):
        snapshot=manual.initial_snapshot();snapshot['squad']*=2
        with patch.object(manual,'stage_surface') as stage:
            with self.assertRaisesRegex(ValueError,'exceeds20'):
                manual.launch_surface(None,self.content,snapshot,'returned',None)
            stage.assert_not_called()

    def test_manual_staging_removes_fixture_control(self):
        (self.run/'surface-fixture.txt').write_text('enter')
        with patch.object(manual,'stage_surface',return_value=(self.run,{},'token')):
            manual.launch_surface(None,self.content,manual.initial_snapshot(),'returned',None)
        self.assertFalse((self.run/'surface-fixture.txt').exists())
        self.assertEqual((self.run/'manual-entrance.txt').read_text(),'returned\n')

    def test_failed_session_never_launches(self):
        (self.root/'failed-entry.json').write_text('{}')
        args=SimpleNamespace(output=self.root,assets=None,imported=None,pod1=None,pod2=None,purple=None,
                             treasure=None,transitions=None,snow=None,roster=None,transition_assets=None)
        with patch.object(manual,'NativeContent',return_value=self.content),patch.object(manual.subprocess,'run') as process:
            with self.assertRaisesRegex(RuntimeError,'failed'):manual.play(args,process)
            process.assert_not_called()

    def test_closed_entrance_reuses_command_without_creating_cave(self):
        exe=self.root/'manual.exe';exe.write_bytes(b'test executable')
        (self.run/'p2-cave-transfer.txt').unlink()
        args=SimpleNamespace(output=self.root,assets=None,imported=None,pod1=None,pod2=None,purple=None,
             treasure=None,transitions=None,snow=None,roster=None,transition_assets=None,surface_exe=exe,cave_exe=exe)
        with patch.object(manual,'NativeContent',return_value=self.content),\
             patch.object(manual,'launch_surface',return_value=(self.run,self.command['checkpoint'],self.command['token'])) as stage,\
             patch.object(manual.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as process:
            self.assertIsNone(manual.play(args,process));self.assertIsNone(manual.play(args,process))
            self.assertEqual(stage.call_count,1);self.assertEqual(process.call_count,2)
        self.assertFalse((self.root/'session/surface-ledger.json').exists())

    def test_launcher_failure_keeps_replay_command(self):
        exe=self.root/'manual.exe';exe.write_bytes(b'test executable')
        (self.run/'p2-cave-transfer.txt').unlink()
        args=SimpleNamespace(output=self.root,assets=None,imported=None,pod1=None,pod2=None,purple=None,
             treasure=None,transitions=None,snow=None,roster=None,transition_assets=None,surface_exe=exe,cave_exe=exe)
        with patch.object(manual,'NativeContent',return_value=self.content),\
             patch.object(manual,'launch_surface',return_value=(self.run,self.command['checkpoint'],self.command['token'])),\
             patch.object(manual.subprocess,'run',side_effect=OSError('launch failed')) as process:
            with self.assertRaisesRegex(OSError,'launch failed'):manual.play(args,process)
        self.assertTrue((self.root/'entry-command.json').exists())
        self.assertFalse((self.root/'session/surface-ledger.json').exists())


if __name__=='__main__':unittest.main()
