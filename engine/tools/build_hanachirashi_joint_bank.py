"""Build private, complete retail joint/collision samples for source55.
No legal resource data is checked into source control. Use --root to locate the
randomizer's existing source-qualified J3D readers, --assets for the extracted
flying bank, and --output for an ignored private runtime sidecar.
"""
import argparse,sys,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.root))
from experimental.pikmin2_convert import blocks
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import joint_matrices
info=json.loads((a.assets/'flying.json').read_text())['species']['Hanachirashi'];nodes=info['collision'];species=a.assets/'Hanachirashi'
if len(nodes)!=9 or info['enemy_id']!=55:raise ValueError('Literal source55 collision contract mismatch')
model=blocks((species/'enemy.bmd').read_bytes());emitter=info['joints'].index('hana3')
lines=['P2_HANACHIRASHI_JOINTS_1 55 11 9']
for clip in info['clips']:
 raw=(species/(clip['name']+'.bca')).read_bytes();duration=clip['source_frames'];lines.append(f"clip {clip['name']} {duration}")
 for frame in range(duration):
  actual,pose=bca_pose(raw,frame,len(info['joints']),allow_scale=True)
  if actual!=duration:raise ValueError('Retail duration changed')
  world=joint_matrices(model,local_overrides=pose);em=[world[emitter][axis][3] for axis in range(3)];values=em[:]
  for node in nodes:
   matrix=world[node['joint']];centre=[sum(matrix[r][c]*node['offset'][c] for c in range(3))+matrix[r][3] for r in range(3)]
   values+=centre+[matrix[r][c] for r in range(3) for c in range(3)]
  if any(not math.isfinite(x) or abs(x)>10000 for x in values):raise ValueError('Invalid retail joint sample')
  lines.append('frame '+str(frame)+' '+' '.join(f'{x:.9g}' for x in values))
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text('\n'.join(lines)+'\n');print(f'Complete source55 joint bank: {sum(c["source_frames"] for c in info["clips"])} frames, {a.output}')
