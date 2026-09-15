"""Optional fire proxy visuals and separately opted-in noninteractive water display."""
import json,math,struct
from pathlib import Path
from experimental.pikmin2_breadbug_visual import read_verified,sha
from experimental.pikmin2_tank_assets import event_frames
from scripts.preview_pikmin2_room import records
CLIPS=('dead','move1','flick','attack','waitact1','waitact2','type5')

def actor_ids(rows,ids):
    if not isinstance(ids,list) or not 1<=len(ids)<=8 or any(type(i)is not int or not 0<=i<=0xffffffff for i in ids) or len(set(ids))!=len(ids):raise ValueError('Invalid Tank identities')
    for identity in ids:
        found=[r for r in rows if len(r)>80 and struct.unpack_from('<I',r,8)[0]==identity]
        if len(found)!=1 or found[0][72:76]!=b'iket' or found[0][80]!=15:raise ValueError('Expected one existing P1 Tank15 per identity')
    return ids

def plan(profile,manifest_sha256,rows,ids,water=None):
    raw=read_verified(profile/'tank.json',manifest_sha256);data=json.loads(raw);actor_ids(rows,ids)
    if data.get('schema')!=1 or data.get('events_executed') is not False or set(data.get('variants',{}))!={'Tank','Wtank'}:raise ValueError('Unsupported Tank source profile')
    for variant,identity,interaction in [('Tank',24,'InteractFire'),('Wtank',25,'InteractBubble')]:
        if data['variants'][variant].get('enemy_id')!=identity or data['variants'][variant].get('interaction')!=interaction:raise ValueError('Variant identity/receiver mismatch')
    clips=data['variants']['Tank']['clips']
    if [Path(c['file']).stem for c in clips]!=list(CLIPS):raise ValueError('Invalid source clip order')
    lines=['P2_TANK_VISUAL_1'];files={};total=0
    for name,clip in zip(CLIPS,clips):
        duration=clip['duration'];frames=clip['frames'];event_frames(duration,clip['events'],3)
        if clip['status']!='converted' or not 2<=len(frames)<=40 or any(type(f)is not int or not 0<=f<duration for f in frames) or frames!=sorted(set(frames)) or frames[0]!=0 or frames[-1]!=duration-1 or len(clip['poses'])!=len(frames) or not {e[0] for e in clip['events']}.issubset(frames):raise ValueError('Invalid complete source samples')
        lines.append(f'{name} {duration} {len(frames)} '+' '.join(map(str,frames)))
        for i,(frame,pose) in enumerate(zip(frames,clip['poses'])):
            source=f'{name}_{i:02}.mod'
            if pose['frame']!=frame or pose['file']!=source:raise ValueError('Pose identity mismatch')
            model=read_verified(profile/'Tank'/source,pose['sha256']);total+=len(model)
            if not model or len(model)>16*1024*1024 or total>64*1024*1024:raise ValueError('Model budget exceeded')
            files[f'tank_fire_{name}_{i:02}.mod']=model
    lines.extend([str(len(ids)),*[f'{i} 15' for i in ids]])
    if water is None:lines.append('0')
    else:
        if set(water)!={'display_id','position','yaw_degrees','noninteractive'} or water['noninteractive'] is not True:raise ValueError('Explicit noninteractive water display required')
        identity=water['display_id'];xyz=water['position'];yaw=water['yaw_degrees']
        if type(identity)is not int or not 0<=identity<=0xffffffff or identity in ids or not isinstance(xyz,list) or len(xyz)!=3 or any(type(v)not in(int,float) or not math.isfinite(v) or abs(v)>100000 for v in xyz) or type(yaw)not in(int,float) or not math.isfinite(yaw) or abs(yaw)>360:raise ValueError('Invalid water display pose')
        clips=data['variants']['Wtank']['clips'];clip=next(c for c in clips if c['file']=='waitact2.bca');pose=clip['poses'][0]
        if clip['status']!='converted' or pose['frame']!=0 or pose['file']!='waitact2_00.mod':raise ValueError('Missing static water pose')
        files['tank_water_static.mod']=read_verified(profile/'Wtank/waitact2_00.mod',pose['sha256'])
        if not files['tank_water_static.mod'] or len(files['tank_water_static.mod'])>16*1024*1024 or total+len(files['tank_water_static.mod'])>64*1024*1024:raise ValueError('Water model budget')
        lines.extend(['1',f'{identity} '+' '.join(format(v,'.9g') for v in xyz+[yaw])])
    return ('\n'.join(lines)+'\n').encode(),files

def install(profile,manifest_sha256,run,ids,water=None):
    room=run/'assets/dataDir/courses/pikmin2room';gen=run/'assets/dataDir/stages/chal0/default.gen'
    if not room.is_dir() or room.resolve()!=room.absolute() or gen.resolve()!=gen.absolute():raise ValueError('Expected private non-junction stage')
    config,files=plan(profile,manifest_sha256,records(gen),ids,water)
    if (run/'p2-tank-visual.txt').exists() or (run/'tank-visual-install.json').exists() or any((room/n).exists() for n in files):raise ValueError('Refusing existing Tank installation')
    for name,raw in files.items():(room/name).write_bytes(raw)
    (run/'p2-tank-visual.txt').write_bytes(config)
    result=dict(schema=1,source_manifest_sha256=manifest_sha256,config_sha256=sha(config),files={n:sha(b) for n,b in files.items()},generator_sha256=sha(gen.read_bytes()),actors=ids,fire_behavior='unchanged P1 Tank proxy',water=water,water_behavior='noninteractive static display; no creature, collision, AI or receivers',native_ready=False)
    (run/'tank-visual-install.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result
