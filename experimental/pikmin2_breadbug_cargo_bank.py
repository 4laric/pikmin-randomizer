"""Source-backed small Breadbug cargo poses; no native actor or AI changes."""
import argparse,json
from pathlib import Path
from experimental.pikmin2_breadbug_visual import read_verified,sha
from experimental.pikmin2_animation import sample_frames
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_convert import convert

CLIPS={'back':('move2.bca',[[10,0],[39,1]]),'hide':('type3.bca',[[20,2]])}

def mapping(state,*,alive,has_cargo):
    """A visual-only bridge between verified P1 states and P2 source motions."""
    if type(state) is not int or type(alive) is not bool or type(has_cargo) is not bool:raise ValueError('Invalid actor observation')
    if not alive:return None
    if state==9:return {'visible':False,'clip':None,'phase':'hidden'}
    if not has_cargo:return None
    if state==5:return {'visible':True,'clip':'back','phase':'intro'}
    if state==6:return {'visible':True,'clip':'back','phase':'loop'}
    if state==8:return {'visible':True,'clip':'hide','phase':'once'}
    return None

def prepare(imported,output,pose_limit=8):
    if type(pose_limit) is not int or not 2<=pose_limit<=8:raise ValueError('Expected 2..8 base samples')
    raw=(imported/'breadbugs.json').read_bytes();metadata=json.loads(raw)
    if metadata.get('schema')!=1:raise ValueError('Unsupported source import')
    small=metadata['species']['PanModoki'];model=imported/'PanModoki/enemy.bmd'
    read_verified(model,small['model_sha256']);motions=[]
    for label,(name,expected_events) in CLIPS.items():
        matches=[c for c in small['clips'] if c['file']==name]
        if len(matches)!=1 or matches[0]['events']!=expected_events:raise ValueError('Unverified source clip/event mapping')
        clip=matches[0];data=read_verified(imported/'PanModoki'/name,clip['sha256'])
        duration,_=bca_pose(data,0,len(small['joints']),allow_scale=True)
        if duration!=clip['source_frames'] or any(not 0<=e[0]<duration for e in expected_events):raise ValueError('Source duration/event mismatch')
        frames=sorted(set(sample_frames(duration,pose_limit))|{e[0] for e in expected_events})
        motions.append((label,clip,data,duration,frames))
    output.mkdir(parents=True,exist_ok=False);models=output/'models';models.mkdir();rows=[];files={}
    for label,clip,data,duration,frames in motions:
        for i,frame in enumerate(frames):
            _,pose=bca_pose(data,frame,len(small['joints']),allow_scale=True)
            name=f'breadbug_cargo_{label}_{i:02}.mod';convert(model,models/name,True,bake_rigid=True,pose=pose)
            files[name]=sha((models/name).read_bytes())
        rows.append(dict(name=label,source_file=clip['file'],source_sha256=clip['sha256'],duration=duration,frames=frames,events=clip['events'],loop=[10,39] if label=='back' else None))
    result=dict(schema=1,family='PanModoki',purpose='visual_cargo_reference_only',source_import_sha256=sha(raw),source_model_sha256=small['model_sha256'],clips=rows,files=files,native_ready=False,events_executed=False,corpse_carry_excluded='type5.bca')
    (output/'breadbug-cargo-bank.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--imported',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--pose-limit',type=int,default=8);a=p.parse_args()
    print(json.dumps(prepare(a.imported,a.output,a.pose_limit),indent=2))
