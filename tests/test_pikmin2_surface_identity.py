import contextlib,io,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
from experimental.pikmin2_surface_identity import surface_identity
from experimental.pikmin2_surface_runner import NativeContent
from scripts import play_pikmin2_surface as single,play_pikmin2_surface_loop as repeat

class IdentityTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.source=self.root/'source';self.pocket=self.root/'pocket';self.source.mkdir();self.pocket.mkdir();self.treasure=self.root/'treasure.mod';self.treasure.write_bytes(b'treasure')
  self.files=[self.source/'surface-render.mod']+[self.pocket/n for n in ['entrance-pocket.json','entrance-collision.json','surface-water.json']]
  for f in self.files:f.write_bytes(f.name.encode())
 def identity(self):return surface_identity('a'*64,self.treasure,self.source,self.pocket)
 def test_changed_bytes_same_path(self):
  baseline=self.identity()
  for f in [self.treasure]+self.files:
   with self.subTest(file=f.name):
    original=f.read_bytes();f.write_bytes(original+b'changed');self.assertNotEqual(self.identity(),baseline);f.write_bytes(original)
 def test_different_path_identical_bytes(self):
  baseline=self.identity();other=self.root/'copy.mod';other.write_bytes(self.treasure.read_bytes())
  self.assertEqual(surface_identity('a'*64,other,self.source,self.pocket),baseline)
 def test_optional_surface_preserves_cave_api(self):
  with patch('experimental.pikmin2_campaign.content_identity',return_value='a'*64):
   args=[self.root,self.root,[self.root,self.root],self.root,self.treasure]
   self.assertEqual(NativeContent(*args).identity,'a'*64)
   self.assertEqual(NativeContent(*args,source_import=self.source,pocket=self.pocket).identity,self.identity())
 def test_both_launchers_reject_and_preserve(self):
  for module,name in [(single,'entry-command.json'),(repeat,'loop-identity.json')]:
   for stored in ['a'*64,self.identity()]:
    with self.subTest(launcher=name,legacy=stored=='a'*64):
     output=self.root/(name+stored[:4]);output.mkdir();command=output/name;command.write_text(json.dumps({'content':stored,'campaign':'c'*32}));session=output/'session';session.mkdir();save=session/'surface-ledger.json';save.write_bytes(b'preserved checkpoint')
     before=(command.read_bytes(),save.read_bytes());old=self.treasure.read_bytes();self.treasure.write_bytes(old+b'changed')
     args=SimpleNamespace(output=output,assets=self.root,imported=self.root,pod1=self.root,pod2=self.root,purple=self.root,treasure=self.treasure,source_import=self.source,pocket=self.pocket,transitions=None,snow=None,roster=None,transition_assets=None,surface_exe=self.root/'missing.exe',cave_exe=self.root/'missing.exe')
     process=Mock()
     with patch('experimental.pikmin2_campaign.content_identity',return_value='a'*64),contextlib.redirect_stdout(io.StringIO()),self.assertRaisesRegex(ValueError,'Content changed or legacy'):
      module.play(args,process)
     process.assert_not_called();self.assertEqual(before,(command.read_bytes(),save.read_bytes()));self.assertFalse(list(output.glob('launch-*.json')));self.treasure.write_bytes(old)

if __name__=='__main__':unittest.main()
