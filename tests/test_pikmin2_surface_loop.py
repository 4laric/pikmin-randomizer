from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from experimental import pikmin2_campaign as cave
from experimental.pikmin2_surface_ledger import SurfaceLedger
from scripts import play_pikmin2_surface_loop as loop


class SurfaceLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.exe=self.root/'game.exe';self.exe.write_bytes(b'test')
        self.args=SimpleNamespace(output=self.root/'output',surface_exe=self.exe,cave_exe=self.exe,
            assets=None,imported=None,pod1=None,pod2=None,purple=None,treasure=None,transitions=None,
            snow=None,roster=None,transition_assets=None)
        self.content=SimpleNamespace(identity='a'*64,stage=self.cave_stage)
        self.surface_runs=0;self.cave_runs=0

    def run_dir(self):
        run=self.root/uuid.uuid4().hex;run.mkdir();return run

    def write_run(self,run,cp,token):
        (run/'p2-cave-entry.txt').write_text(cave.entry_text(cp,token))
        (run/'p2-economy.txt').write_text(cave.ledger_text(cp['receipts']))

    def surface_stage(self,args,content,snapshot,mode,process):
        cp=cave.initial(content.identity);cp.update({k:deepcopy(snapshot[k]) for k in ('squad','health','receipts')})
        run=self.run_dir();token=uuid.uuid4().hex;self.write_run(run,cp,token)
        (run/'kind').write_text('surface');return run,cp,token

    def cave_stage(self,cp,token,runs):
        run=self.run_dir();self.write_run(run,cp,token);(run/'kind').write_text('cave')
        return run,{'treasure:repeat':100}

    def process(self,argv,*,cwd,**kwargs):
        kind=(cwd/'kind').read_text();text=(cwd/'p2-cave-entry.txt').read_text()
        if kind=='surface':
            self.surface_runs+=1
            if self.surface_runs==3:return SimpleNamespace(returncode=0)
            token=text.splitlines()[1]
            (cwd/'surface-position.txt').write_text(token+f'\n{-210+self.surface_runs} 80 1160\n')
        else:
            self.cave_runs+=1
            receipts=cave.read_ledger(cwd/'p2-economy.txt');receipts['treasure:repeat']=100
            (cwd/'p2-economy.txt').write_text(cave.ledger_text(receipts))
        (cwd/'p2-cave-transfer.txt').write_text(text.replace('P2_CAVE_ENTRY_1','P2_CAVE_TRANSFER_1'))
        return SimpleNamespace(returncode=42)

    def test_two_visits_then_close_and_resume_same_surface_command(self):
        with patch.object(loop,'NativeContent',return_value=self.content),patch.object(loop,'launch_surface',side_effect=self.surface_stage) as stage:
            final=loop.play(self.args,self.process)
            self.assertEqual((self.surface_runs,self.cave_runs),(3,4))
            self.assertEqual(final['revision'],8)
            self.assertEqual(final['surface']['position'],[-208.,80.,1160.])
            self.assertEqual(final['surface']['receipts'],{'treasure:repeat':100})
            with patch.object(loop,'SurfaceRunner') as runner:
                resumed=loop.play(self.args,lambda *a,**kw:SimpleNamespace(returncode=0))
                runner.assert_not_called()
            self.assertEqual(final,resumed);self.assertEqual(stage.call_count,3)

    def test_pending_commit_replays_after_unlink_interruption(self):
        directory=self.root/'session';ledger=SurfaceLedger(directory,'a'*64,'b'*32)
        ledger.create(loop.initial_snapshot());run,cp,token=self.surface_stage(None,self.content,loop.initial_snapshot(),'enter',None)
        self.process([],cwd=run)
        path=self.root/'pending.json';command=dict(campaign=ledger.campaign,content=ledger.content,
              revision=0,token=token,run=str(run));path.write_text(json.dumps(command))
        original=Path.unlink
        def unlink(p,*a,**kw):
            if p==path:raise OSError('interrupted cleanup')
            return original(p,*a,**kw)
        with patch.object(Path,'unlink',unlink),self.assertRaisesRegex(OSError,'cleanup'):
            loop.consume_command(path,ledger)
        committed=ledger.read();self.assertEqual(committed['revision'],1)
        self.assertEqual(loop.consume_command(path,ledger),committed)
        self.assertFalse(path.exists())

    def test_foreign_command_and_missing_live_position_rejected(self):
        ledger=SurfaceLedger(self.root/'session','a'*64,'b'*32);ledger.create(loop.initial_snapshot())
        run,_,token=self.surface_stage(None,self.content,loop.initial_snapshot(),'enter',None)
        self.process([],cwd=run);path=self.root/'pending.json'
        command=dict(campaign='c'*32,content=ledger.content,revision=0,token=token,run=str(run))
        path.write_text(json.dumps(command))
        with self.assertRaisesRegex(ValueError,'another campaign'):loop.consume_command(path,ledger)
        command['campaign']=ledger.campaign;path.write_text(json.dumps(command));(run/'surface-position.txt').unlink()
        with self.assertRaisesRegex(ValueError,'actual native position'):loop.consume_command(path,ledger)
        self.assertEqual(ledger.read()['revision'],0)


if __name__=='__main__':unittest.main()
