"""Prepare only a small Breadbug visual display; no gameplay actor registration."""
import hashlib
import json
import math
from pathlib import Path
from experimental.pikmin2_animation import sample_frames
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_convert import convert


def sha(raw):return hashlib.sha256(raw).hexdigest()

def read_verified(path,expected):
    data=path.read_bytes()
    if sha(data)!=expected:raise ValueError('Source asset hash mismatch: '+path.name)
    return data


def placements_text(placements):
    if not isinstance(placements,list) or not 1<=len(placements)<=8:raise ValueError('Expected1..8 visual placements')
    seen=set();lines=[]
    for row in placements:
        if set(row)!={'display_id','kind','position','yaw_degrees'}:raise ValueError('Invalid visual placement fields')
        identity=row['display_id'];kind=row['kind'];position=row['position'];yaw=row['yaw_degrees']
        if type(identity) is not int or not 0<=identity<=0xffffffff or identity in seen or kind not in ('wait','move','nest'):raise ValueError('Invalid display identity/kind')
        seen.add(identity)
        if not isinstance(position,list) or len(position)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>100000 for v in position):raise ValueError('Invalid XYZ')
        if type(yaw) not in (int,float) or not math.isfinite(yaw) or not -360<=yaw<=360:raise ValueError('Invalid visual yaw')
        lines.append(f'{identity} {kind} '+ ' '.join(format(v,'.9g') for v in position+[yaw]))
    return lines


def prepare(imported,output,placements,pose_limit=8):
    rows=placements_text(placements)
    if type(pose_limit) is not int or not 2<=pose_limit<=12:raise ValueError('Expected2..12 samples')
    raw=(imported/'breadbugs.json').read_bytes();metadata=json.loads(raw)
    if metadata.get('schema')!=1:raise ValueError('Unsupported Breadbug import')
    small=metadata['species']['PanModoki'];nest=metadata['species']['PanHouse']
    modelpath=imported/'PanModoki/enemy.bmd';read_verified(modelpath,small['model_sha256'])
    nestpose=nest['static_pose']
    if nestpose.get('file')!='nest.mod':raise ValueError('Missing bounded nest model')
    nestdata=read_verified(imported/'PanHouse/nest.mod',nestpose['sha256'])
    motions=[]
    for label,name in (('wait','wait1.bca'),('move','move1.bca')):
        clips=[c for c in small['clips'] if c['file']==name]
        if len(clips)!=1:raise ValueError('Missing source animation')
        data=read_verified(imported/'PanModoki'/name,clips[0]['sha256'])
        duration,_=bca_pose(data,0,len(small['joints']),allow_scale=True)
        frames=sample_frames(duration,pose_limit)
        motions.append((label,data,duration,frames))
    output.mkdir(parents=True,exist_ok=False);models=output/'models';models.mkdir()
    files={};config=['P2_BREADBUG_VISUAL_1'];clips=[]
    for label,data,duration,frames in motions:
        config.append(f'{label} {duration} {len(frames)} '+' '.join(map(str,frames)))
        for i,frame in enumerate(frames):
            _,pose=bca_pose(data,frame,len(small['joints']),allow_scale=True)
            name=f'breadbug_{label}_{i:02}.mod';convert(modelpath,models/name,True,bake_rigid=True,pose=pose)
            files[name]=sha((models/name).read_bytes())
        clips.append(dict(name=label,source_duration=duration,frames=frames))
    (models/'breadbug_nest.mod').write_bytes(nestdata);files['breadbug_nest.mod']=sha(nestdata)
    config.extend([str(len(rows)),*rows]);text='\n'.join(config)+'\n';(output/'p2-breadbug-visual.txt').write_text(text)
    result=dict(schema=1,source_import_sha256=sha(raw),family='PanModoki',behavior='visual_only_no_gameplay_actor',
                native_validated=False,clips=clips,files=files,placements=placements,config_sha256=sha(text.encode()))
    (output/'breadbug-visual.json').write_text(json.dumps(result,indent=2));return result


def install(profile,run):
    metadata=json.loads((profile/'breadbug-visual.json').read_text())
    room=run/'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or room.resolve()!=room.absolute():raise ValueError('Expected private non-junction model directory')
    if metadata.get('schema')!=1 or metadata.get('behavior')!='visual_only_no_gameplay_actor':raise ValueError('Unsupported profile')
    config=read_verified(profile/'p2-breadbug-visual.txt',metadata['config_sha256'])
    files={}
    for name,digest in metadata['files'].items():
        if Path(name).name!=name or not name.startswith('breadbug_') or not name.endswith('.mod'):raise ValueError('Unsafe profile model name')
        files[name]=read_verified(profile/'models'/name,digest)
    if (run/'p2-breadbug-visual.txt').exists() or any((room/name).exists() for name in files):raise ValueError('Refusing existing visual installation')
    for name,data in files.items():(room/name).write_bytes(data)
    (run/'p2-breadbug-visual.txt').write_bytes(config)
    return metadata
