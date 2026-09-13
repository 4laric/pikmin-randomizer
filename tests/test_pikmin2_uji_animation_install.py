import hashlib,json,struct,tempfile,unittest
from pathlib import Path
from experimental.pikmin2_uji_animation_install import validate,install
from experimental.pikmin2_sheargrub_animation import CLIPS,mapping

class InstallerTests(unittest.TestCase):
 def seed(self,root):
  bank=root/'bank';bank.mkdir();report=dict(schema=1,policy='P2_UJI_VISUAL_BANK_1',species={},total_bytes=0)
  raw=b''.join(struct.pack('>II',tag,1)+b'x' for tag in (32,34,48))+struct.pack('>II',65535,0)
  for species,names in CLIPS.items():
   (bank/species).mkdir();clips=[]
   for name in names:
    file=f'uji_{species}_{name}_00.mod';(bank/species/file).write_bytes(raw)
    clips.append(dict(name=name,source_frames=1,poses=[dict(frame=0,file=file,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())]));report['total_bytes']+=len(raw)
   report['species'][species]=dict(motion_mapping=mapping(species),clips=clips)
  (bank/'animation-bank.json').write_text(json.dumps(report));return bank,report
 def test_valid_install_and_collision(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);bank,_=self.seed(root);run=root/'run';(run/'assets/dataDir/courses/pikmin2room').mkdir(parents=True);(run/'p2-sheargrub.txt').write_text('source')
   audit=install(bank,run)
   self.assertEqual(audit['model_count'],16)
   self.assertEqual(audit['protocol_sha256'],hashlib.sha256((run/'p2-sheargrub-animation.txt').read_bytes()).hexdigest())
   before=(run/'p2-sheargrub-animation.txt').read_bytes()
   with self.assertRaises(ValueError):install(bank,run)
   self.assertEqual((run/'p2-sheargrub-animation.txt').read_bytes(),before)
 def test_bad_identity_frames_and_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   bank,report=self.seed(Path(d));manifest=bank/'animation-bank.json'
   pose=report['species']['UjiA']['clips'][0]['poses'][0]
   pose['file']='../outside';manifest.write_text(json.dumps(report))
   with self.assertRaises(ValueError):validate(bank)
   pose['file']='uji_UjiA_dead_00.mod';pose['frame']=True;manifest.write_text(json.dumps(report))
   with self.assertRaises(ValueError):validate(bank)
   pose['frame']=0;manifest.write_text(json.dumps(report));(bank/'UjiA'/pose['file']).write_bytes(b'changed')
   with self.assertRaises(ValueError):validate(bank)

if __name__=='__main__':unittest.main()
