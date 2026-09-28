"""Deterministic local Tank/Wtank source poses, metadata and emitter contract."""
import argparse,json,math,subprocess,time
from pathlib import Path
from experimental.pikmin2_assets import disc_files,archive_files
from experimental.pikmin2_breadbug_assets import sha,parameter_blocks,collision_nodes
from experimental.pikmin2_sheargrub_assets import animation_rows,joints
from experimental.pikmin2_animation import sample_frames
from experimental.pikmin2_enemy import replace_texture_zero
from experimental.pikmin2_convert import blocks,decode,write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import joint_matrices
from experimental.pikmin2_skinning import draw_matrices

VARIANTS={'Tank':(24,'fire_butadokkuri_main_s3tc.bti','InteractFire'),'Wtank':(25,'mizu_butadokkuri_main_s3tc.bti','InteractBubble')}
SOURCE_FILES=['include/Game/Entities/Tank.h','src/plugProjectYamashitaU/enemyInfo.cpp',*[f'src/plugProjectNishimuraU/{n}.cpp' for n in ('Tank','TankState','TankMgr','Ftank','FtankMgr','Wtank','WtankMgr')],'src/plugProjectKandoU/interactPiki.cpp','src/plugProjectKandoU/interactNavi.cpp']
MAX_ARCHIVE=32*1024*1024
MAX_MODEL=16*1024*1024
MAX_TOTAL=256*1024*1024

def write_pose(converted,target):
    report=write_model(converted,target,'enemy.bmd')
    report.update(source='enemy.bmd',output=target.name,weighted_pose_baked=True)
    target.with_suffix('.json').write_bytes((json.dumps(report,indent=2,sort_keys=True)+'\n').encode())

def event_frames(duration,events,limit):
    if type(duration) is not int or not 2<=duration<=10000 or type(limit) is not int or not 2<=limit<=8:raise ValueError('Invalid duration/sample budget')
    if not isinstance(events,list) or len(events)>32:raise ValueError('Invalid event budget')
    last=-1
    for row in events:
        if not isinstance(row,list) or len(row)!=2 or any(type(v) is not int for v in row) or not 0<=row[0]<duration or not 0<=row[1]<=255 or row[0]<last:raise ValueError('Invalid ordered source event')
        last=row[0]
    return sorted(set(sample_frames(duration,limit))|{e[0] for e in events})

def loop_bounds(events):
    starts=[f for f,k in events if k==0];ends=[f for f,k in events if k==1]
    if not starts and not ends:return None
    if len(starts)!=1 or len(ends)!=1 or starts[0]>=ends[0]:raise ValueError('Unmatched or reversed source loop')
    return [starts[0],ends[0]]

def emitter(matrix):
    if len(matrix)!=3 or any(len(r)!=4 for r in matrix) or any(not math.isfinite(v) for r in matrix for v in r):raise ValueError('Invalid hoppe transform')
    axis=[r[0] for r in matrix];length=math.sqrt(sum(v*v for v in axis))
    if length<1e-12:raise ValueError('Degenerate hoppe direction')
    axis=[v/length for v in axis]
    return dict(matrix=matrix,direction=axis,origin=[matrix[i][3]+10*axis[i]-(10 if i==1 else 0) for i in range(3)],space='model-space analogue; world transform must precede source world-Y offset')

def receiver(species,pikmin,*,invincible=False,transittable=True):
    if species not in VARIANTS or pikmin not in ('red','yellow','blue','white','purple','bulbmin'):raise ValueError('Unknown source receiver')
    immune=('red','bulbmin') if species=='Tank' else ('blue','bulbmin')
    return None if invincible or not transittable or pikmin in immune else ('fire_panic' if species=='Tank' else 'water_panic')

def extract(iso,output,source,pose_limit=3):
    event_frames(2,[],pose_limit);index=disc_files(iso)
    revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    source_hashes={name:sha((source/name).read_bytes()) for name in SOURCE_FILES}
    output.mkdir(parents=True,exist_ok=False);resource_hashes={};budget=0
    result=dict(schema=1,disc='GPVE01 revision 0',source_revision=revision,source_files_sha256=source_hashes,resource_sha256=resource_hashes,native_ready=False,events_executed=False,variants={})
    with iso.open('rb') as disc:
        def read(path):
            offset,size=index[path]
            if not 0<size<=MAX_ARCHIVE:raise ValueError('Resource budget exceeded')
            disc.seek(offset);raw=disc.read(size)
            if len(raw)!=size:raise ValueError('Truncated source resource')
            resource_hashes[path]=sha(raw);return raw
        params=archive_files(read('enemy/parm/enemyParms.szs'));model=archive_files(read('enemy/data/Tank/model.szs'))['enemy.bmd'];motions=archive_files(read('enemy/data/Tank/anim.szs'))
        names=joints(model)
        if names.count('hoppe')!=1 or len(names)>128:raise ValueError('Expected bounded unique hoppe joint')
        rows=animation_rows(params['tank/enemyanimmgr.txt'].decode('shift_jis'))
        if [r['file'] for r in rows]!=['dead.bca','move1.bca','flick.bca','attack.bca','waitact1.bca','waitact2.bca','type5.bca']:raise ValueError('Unverified Tank animation registration')
        result.update(joints=names,emitter_joint=names.index('hoppe'),collision=collision_nodes(params['tank/enemycoll.txt'],len(names)),base_model_sha256=sha(model))
        shared=output/'shared';shared.mkdir();(shared/'enemy.bmd').write_bytes(model)
        for name in ('enemycoll.txt','enemyanimmgr.txt','enemystoneinfo.txt'):(shared/name).write_bytes(params['tank/'+name])
        for row in rows:(shared/row['file']).write_bytes(motions[row['file']])
        for variant,(identity,texture_name,interaction) in VARIANTS.items():
            root=output/variant;root.mkdir();texture=read(f'enemy/data/{variant}/{texture_name}');(root/texture_name).write_bytes(texture)
            rendered=replace_texture_zero(model,texture);(root/'enemy.bmd').write_bytes(rendered)
            parm=params[variant.lower()+'/enemyparm.txt'];(root/'enemyparm.txt').write_bytes(parm);parsed=parameter_blocks(parm)
            general=[b for b in parsed if all(k in b for k in ('fp00','fp14','fp22','fp24'))]
            if len(general)!=1:raise ValueError('Ambiguous general parameter block')
            clips=[]
            for row in rows:
                raw=motions[row['file']];clip=dict(row,sha256=sha(raw),status='source_only',poses=[])
                try:
                    duration,_=bca_pose(raw,0,len(names),allow_scale=True);frames=event_frames(duration,row['events'],pose_limit);clip.update(duration=duration,frames=frames,loop=loop_bounds(row['events']))
                    for i,frame in enumerate(frames):
                        _,pose=bca_pose(raw,frame,len(names),allow_scale=True);anchor=emitter(joint_matrices(blocks(model),pose)[names.index('hoppe')]);filename=Path(row['file']).stem+f'_{i:02}.mod'
                        try:
                            matrices=draw_matrices(blocks(rendered),pose);converted=decode(rendered,True,bake_rigid=True,draw_matrices=matrices);write_pose(converted,root/filename)
                            data=(root/filename).read_bytes()
                            if len(data)>MAX_MODEL or budget+len(data)>MAX_TOTAL:raise RuntimeError('Pose byte budget exceeded; import aborted')
                            budget+=len(data);clip['poses'].append(dict(frame=frame,file=filename,sha256=sha(data),bytes=len(data),emitter=anchor))
                        except ValueError as error:clip.setdefault('unsupported',[]).append(dict(frame=frame,reason=str(error)))
                    clip['status']='converted' if len(clip['poses'])==len(frames) else 'blocked'
                except ValueError as error:clip.update(status='blocked',unsupported_reason=str(error))
                clips.append(clip)
            result['variants'][variant]=dict(enemy_id=identity,concrete_class='Ftank::Obj' if variant=='Tank' else 'Wtank::Obj',interaction=interaction,model_sha256=sha(rendered),texture_sha256=sha(texture),parameter_sha256=sha(parm),parameter_blocks=parsed,general=general[0],clips=clips)
    result['budget']=dict(pose_bytes=budget,poses=sum(len(c['poses']) for v in result['variants'].values() for c in v['clips']),max_total_bytes=MAX_TOTAL,max_pose_bytes=MAX_MODEL,base_samples=pose_limit)
    result['limitations']=['Approximate materials; source mat_dokkuri_main differed display-list/texture-coordinate flags are not runtime J3D behavior.','Weighted source poses baked using supported converter; no native animation or effect execution.','No native registration, collision, elemental receiver, map-clipped breath, damage, corpse or lifecycle validation.','Hoppe origin metadata requires owner world transform before applying the source world-Y offset.']
    (output/'tank.json').write_bytes((json.dumps(result,indent=2,sort_keys=True)+'\n').encode());return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','output','source'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--pose-limit',type=int,default=3);a=p.parse_args();start=time.perf_counter();r=extract(a.iso,a.output,a.source,a.pose_limit)
    print(json.dumps(dict(seconds=time.perf_counter()-start,budget=r['budget'],clips={v:[(c['file'],c['status']) for c in data['clips']] for v,data in r['variants'].items()})))
