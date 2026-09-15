import hashlib,json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experimental.pikmin2_frog_install import plan,install,SPECIES,CLIPS
from experimental.pikmin2_frog_arena import roster

class FrogInstallTests(unittest.TestCase):
 def seed(self,root):
  bank=root/'bank';bank.mkdir();m=dict(schema=1,policy='P2_FROG_IMPORT_1',disc_id='GPVE01',disc_revision=0,species={},total_pose_bytes=0)
  raw=b''.join(struct.pack('>II',t,1)+b'x' for t in (32,34,48))+struct.pack('>II',65535,0)
  for species,id in SPECIES.items():
   (bank/species).mkdir();clips=[]
   for name in CLIPS:
    poses=[]
    for i in range(2):
     file=f'frog_{species}_{name}_{i:02}.mod';(bank/species/file).write_bytes(raw)
     poses.append(dict(frame=i,file=file,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()));m['total_pose_bytes']+=len(raw)
    clips.append(dict(name=name,source_frames=2,status='converted',poses=poses))
   m['species'][species]=dict(enemy_id=id,clips=clips)
  (bank/'frogs.json').write_text(json.dumps(m));return bank,m
 def test_exact_bytes_and_refuse_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);bank,_=self.seed(root);run=root/'run';room=run/'assets/dataDir/courses/pikmin2room';room.mkdir(parents=True)
   audit=install(bank,run,[(201001,'Frog'),(201002,'MaroFrog')]);raw=(run/'p2-frog.txt').read_bytes()
   self.assertNotIn(b'\r',raw);self.assertEqual(hashlib.sha256(raw).hexdigest(),audit['protocol_sha256']);self.assertEqual(audit['models'],44)
   before={str(p):p.read_bytes() for p in run.rglob('*') if p.is_file()}
   with self.assertRaises(ValueError):install(bank,run,[(201001,'Frog')])
   self.assertEqual(before,{str(p):p.read_bytes() for p in run.rglob('*') if p.is_file()})
 def test_invalid_identity_and_frame(self):
  with tempfile.TemporaryDirectory() as d:
   bank,m=self.seed(Path(d))
   for actors in ([],[(True,'Frog')],[(1,'Frog'),(1,'MaroFrog')],[(1,'Iwagen')]):
    with self.assertRaises(ValueError):plan(bank,actors)
   m['species']['Frog']['clips'][0]['poses'][0]['frame']=True;(bank/'frogs.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):plan(bank,[(1,'Frog')])
 def test_corrupt_model_no_mutation(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);bank,m=self.seed(root);run=root/'run';room=run/'assets/dataDir/courses/pikmin2room';room.mkdir(parents=True)
   (bank/'MaroFrog'/m['species']['MaroFrog']['clips'][-1]['poses'][-1]['file']).write_bytes(b'changed')
   with self.assertRaises(ValueError):install(bank,run,[(1,'Frog')])
   self.assertEqual(list(room.iterdir()),[]);self.assertFalse((run/'p2-frog.txt').exists())
 def test_unsafe_filename(self):
  with tempfile.TemporaryDirectory() as d:
   bank,m=self.seed(Path(d));m['species']['Frog']['clips'][0]['poses'][0]['file']='../outside.mod';(bank/'frogs.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):plan(bank,[(1,'Frog')])
 def test_arena_types_offsets_and_collision(self):
  def row(id=1):
   r=bytearray(110);r[:8]=b'    0.0v';struct.pack_into('<I',r,8,id);r[72:76]=b'iket';struct.pack_into('>3f',r,60,1,2,3);return bytes(r)
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'dataDir/stages/practice/default.gen';p.parent.mkdir(parents=True);p.write_bytes(bytes(24))
   with patch('experimental.pikmin2_frog_arena.records',return_value=[row()]),patch('experimental.pikmin2_frog_arena.generator',return_value=bytes(24)+row()):data,actors=roster(root)
   self.assertEqual(struct.unpack_from('>I',data,20)[0],5)
   for n,a in enumerate(actors):
    r=data[24+110*(n+1):24+110*(n+2)];self.assertEqual(r[80],[0,33,0,33][n]);self.assertEqual(struct.unpack_from('>3f',r,48),tuple(a['position']));self.assertEqual(struct.unpack_from('>3f',r,60),(0,0,0))
   with patch('experimental.pikmin2_frog_arena.records',return_value=[row(201001)]),patch('experimental.pikmin2_frog_arena.generator',return_value=bytes(24)+row()):
    with self.assertRaises(ValueError):roster(root)

if __name__=='__main__':unittest.main()
