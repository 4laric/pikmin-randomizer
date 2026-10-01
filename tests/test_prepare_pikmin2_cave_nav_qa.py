import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from scripts import prepare_pikmin2_cave_nav_qa as qa
from experimental.pikmin2_campaign import initial

class NavQATests(unittest.TestCase):
    def seed(self):
        c='a'*64;campaign='b'*32;trip='d'*32
        cp=initial(c);cp.update(floor=2,revision=1)
        surface=dict(region='valley_of_repose',day=2,time=8.5,position=[0,0,0],squad=cp['squad'],health=1.,receipts={})
        state=dict(schema=1,campaign=campaign,content=c,origin='c'*64,revision=2,phase='cave',surface=surface,trip=dict(id=trip,cave='tutorial_1',token='e'*32,checkpoint=cp),events={'enter:'+trip:'f'*64,'floor:'+'0'*32:'1'*64})
        return dict(campaign=campaign,content=c,trip=trip),state
    def test_clone_identity_and_floor_rejection(self):
        entry,state=self.seed();raw=json.dumps(state).encode();self.assertEqual(2,qa.seed_state(json.dumps(entry),raw)['revision'])
        bad=dict(entry,campaign='0'*32)
        with self.assertRaises(ValueError):qa.seed_state(json.dumps(bad),raw)
        state['trip']['checkpoint'].update(floor=1,revision=0)
        with self.assertRaises(ValueError):qa.seed_state(json.dumps(entry),json.dumps(state))
    def test_protected_snapshot_detects_change(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'ledger').write_bytes(b'original');before=qa.protected_snapshot(p)
            (p/'ledger').write_bytes(b'changed');self.assertNotEqual(before,qa.protected_snapshot(p))
    def test_protected_snapshot_does_not_follow_junction(self):
        try:import _winapi
        except ImportError:self.skipTest('Windows junction test')
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);root=base/'package';root.mkdir();target=base/'assets';target.mkdir();(target/'do-not-read').write_bytes(b'assets');_winapi.CreateJunction(str(target),str(root/'assets'))
            snapshot=qa.protected_snapshot(root);self.assertEqual(['assets'],list(snapshot));self.assertIn('link',snapshot['assets'])
    def test_launch_forces_diagnostic_and_uses_clone_command_without_native(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'diagnostic-qa.json';p.write_bytes(b'{}');record=dict(environment=qa.DIAGNOSTIC_ENV,command=['python','-B','-m','scripts.play_pikmin2_surface','--output',str(p.parent/'session')])
            calls=[]
            def process(command,**kwargs):calls.append((command,kwargs));return SimpleNamespace(returncode=0)
            with patch.object(qa,'check',return_value=record),patch.dict('os.environ',{'PIKMIN_CAVE_NAV_DIAGNOSTICS':'0'}):self.assertEqual(0,qa.launch(p,process))
            self.assertEqual('1',calls[0][1]['env']['PIKMIN_CAVE_NAV_DIAGNOSTICS']);self.assertEqual(record['command'],calls[0][0]);self.assertEqual(p.parent/'launcher-source',calls[0][1]['cwd'])
    def test_guard_failure_never_dispatches(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'manifest';p.write_bytes(b'{}');called=[]
            with patch.object(qa,'check',side_effect=ValueError('changed checkpoint')):
                with self.assertRaises(ValueError):qa.launch(p,lambda *a,**kw:called.append(a))
            self.assertEqual([],called)
    def test_command_cannot_target_original_session(self):
        r=dict(python={'path':'python'},assets={'assets':'original-assets'},executables={'surface':'manual.exe','cave':'nectar.exe'})
        root=Path('C:/private-package');command=qa.make_command(root,r)
        self.assertEqual(str(root/'session'),command[-1]);self.assertIn(str(root/'cave/nectar.exe'),command)

if __name__=='__main__':unittest.main()
