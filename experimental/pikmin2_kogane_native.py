"""Typed native sidecar; leaves Kimi v1 installation unchanged."""
import json,struct,hashlib
from pathlib import Path
from experimental.pikmin2_kogane_install import plan
from experimental.pikmin2_convert import blocks,u16,u32

def emit(bank,run,arena,expected_manifest_sha256):
 raw=(bank/'beetles.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=expected_manifest_sha256:raise ValueError('Manifest hash mismatch')
 rows=[a for a in arena['actors'] if a['species']!='P1 Chappy'];ids=[a['generator'] for a in rows]
 _,_,_,files,meta=plan(bank,ids)
 if not files:raise ValueError('Native display requires complete bank')
 model=(bank/'shared/enemy.bmd').read_bytes()
 if hashlib.sha256(model).hexdigest()!=meta['shared']['model_sha256']:raise ValueError('Model hash mismatch')
 b=blocks(model);m=b['MAT3'];names=u32(m,20)
 labels=[m[names+u16(m,names+6+4*i):].split(b'\0',1)[0].decode('ascii') for i in range(u16(m,8))]
 if labels.count('karada')!=1:raise ValueError('Expected unique karada material')
 target=labels.index('karada');h=b['INF1'];at=u32(h,20);mat=None;shapes=[]
 while True:
  typ,index=struct.unpack_from('>HH',h,at);at+=4
  if typ==0:break
  if typ==0x11:mat=index
  if typ==0x12 and mat==target:shapes.append(index)
 if len(shapes)!=1:raise ValueError('Ambiguous karada shape')
 species={'kogane':9,'wealthy':10,'fart':11}
 text=['P2_KOGANE_NATIVE_1',f'karada {shapes[0]}',f'actors {len(rows)}']
 for row in rows:
  kind=row['species']
  if kind not in species:raise ValueError('Unknown typed species')
  text.append(f"{row['generator']} {species[kind]}")
 for clip in meta['shared']['clips']:
  frames=[p['frame'] for p in clip['poses']];duration=clip['source_frames']
  if not 2<=len(frames)<=24 or frames!=sorted(set(frames)) or frames[0]!=0 or frames[-1]!=duration-1:raise ValueError('Invalid source frames')
  text.append(f"{Path(clip['file']).stem} {len(frames)} {duration} "+' '.join(map(str,frames)))
 for name,data in files.items():
  if (run/'assets/dataDir/courses/pikmin2room'/name).read_bytes()!=data:raise ValueError('Installed bank drift')
 dest=run/'p2-kogane-native.txt'
 if dest.exists():raise ValueError('Refusing existing native sidecar')
 payload=('\n'.join(text)+'\n').encode();dest.write_bytes(payload);return hashlib.sha256(payload).hexdigest()
