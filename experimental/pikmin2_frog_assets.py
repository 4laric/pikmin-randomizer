"""Source-backed, bounded local Frog/MaroFrog import; no native actor install."""
import argparse,hashlib,json,math,re,struct,subprocess
from pathlib import Path
from experimental.pikmin2_assets import disc_files,archive_files
from experimental.pikmin2_sheargrub_assets import animation_rows,joints
from experimental.pikmin2_breadbug_assets import parameter_blocks,collision_nodes
from experimental.pikmin2_pod import pellet_catalog
from experimental.pikmin2_convert import blocks,decode,write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import resource_chunks

SPECIES={'Frog':17,'MaroFrog':18}
CLIPS=('dead','wait1','waitact2','move1','waitact1','type1','wait2','type2','attack','damage','type5')
MAX_POSES=12
CLIP_BYTES=512*1024
TOTAL_BYTES=10*1024*1024
LOOPS={0:'stop at end',1:'reset to start and stop',2:'repeat',3:'reverse once then stop',4:'ping-pong repeat'}

def sha(data):return hashlib.sha256(data).hexdigest()

def event_frames(duration,events,limit=MAX_POSES):
    if type(duration) is not int or not 1<=duration<=10000 or type(limit) is not int or not 2<=limit<=MAX_POSES:
        raise ValueError('Invalid Frog duration/pose cap')
    required={0,duration-1}
    for row in events:
        if len(row)!=2 or any(type(x) is not int for x in row) or not 0<=row[0]<duration or not 0<=row[1]<=100:
            raise ValueError('Invalid Frog event frame/type')
        required.add(row[0])
    if len(required)>limit:raise ValueError('Event boundaries exceed pose cap')
    while len(required)<min(limit,duration):
        pairs=list(zip(sorted(required),sorted(required)[1:]));a,b=max(pairs,key=lambda p:(p[1]-p[0],-p[0]))
        if b-a<2:break
        required.add((a+b)//2)
    return sorted(required)

def profile(raw):
    parsed=parameter_blocks(raw)
    general=[b for b in parsed if all(k in b for k in ('fp00','fp12','fp20','fp24'))]
    proper=[b for b in parsed if set(b)=={'fp01','fp02','fp03','fp04'}]
    if len(general)!=1 or len(proper)!=1:raise ValueError('Expected distinct Frog general/proper blocks')
    g,p=general[0],proper[0]
    fields=dict(health=g['fp00'],sight_radius=g['fp12'],attack_range=g['fp20'],attack_damage=g['fp24'],
                air_time=p['fp01'],jump_speed=p['fp02'],jump_fail_chance=p['fp03'],fall_speed=p['fp04'])
    if any(not math.isfinite(v) or v<0 for v in fields.values()) or fields['jump_fail_chance']>1 or fields['health']<=0:
        raise ValueError('Invalid Frog retail parameters')
    return dict(parameter_blocks=parsed,fields=fields)

def check_budget(total,clip,size):
    if any(type(v) is not int or v<0 for v in (total,clip,size)) or size==0 or total+size>TOTAL_BYTES or clip+size>CLIP_BYTES:
        raise RuntimeError('Frog bank byte budget exceeded; no completed manifest')

def corpse(fields):
    result={k:int(fields[k]) for k in ('min','max','pikicountmin','pikicountmax','money')}
    if not 1<=result['min']<=result['max'] or not 0<=result['pikicountmin']<=result['pikicountmax'] or result['money']<0:raise ValueError('Invalid Frog corpse config')
    result.update(offset=[float(v) for v in fields['offset']],radius=float(fields['radius']),pickup_radius=float(fields['p_radius']),height=float(fields['height']))
    if any(not math.isfinite(v) for v in result['offset']+[result['radius'],result['pickup_radius'],result['height']]) or min(result['radius'],result['pickup_radius'])<=0 or result['height']<0:raise ValueError('Nonfinite Frog corpse config')
    return result

def extract(iso,source,output,limit=MAX_POSES):
    event_frames(1,[],limit)
    if output.exists():raise ValueError('Output already exists')
    head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if not re.fullmatch('[0-9a-f]{40}',head):raise ValueError('Invalid source revision')
    index=disc_files(iso);source_hashes={}
    with iso.open('rb') as disc:
        header=disc.read(8)
        if header[:6]!=b'GPVE01':raise ValueError('Expected supplied US GPVE01 disc')
        def read(name):
            at,size=index[name];disc.seek(at);raw=disc.read(size)
            if len(raw)!=size:raise ValueError('Truncated ISO resource')
            source_hashes[name]=sha(raw);return raw
        params=archive_files(read('enemy/parm/enemyParms.szs'))
        carcasses=pellet_catalog(read('user/Abe/Pellet/us/carcass_config.txt').decode('shift_jis'))
        output.mkdir(parents=True)
        report=dict(schema=1,policy='P2_FROG_IMPORT_1',disc_id=header[:6].decode(),disc_revision=header[7],source_revision=head,
                    source_sha256=source_hashes,native_ready=False,gameplay_events_executed=False,species={},total_pose_bytes=0)
        for species,identity in SPECIES.items():
            root=output/species;root.mkdir();model=archive_files(read(f'enemy/data/{species}/model.szs'))['enemy.bmd'];model_blocks=blocks(model)
            motions=archive_files(read(f'enemy/data/{species}/anim.szs'));names=joints(model);(root/'enemy.bmd').write_bytes(model)
            metadata={}
            for filename in ('enemyparm.txt','enemyanimmgr.txt','enemycoll.txt','enemystoneinfo.txt'):
                raw=params[species.lower()+'/'+filename];metadata[filename]=sha(raw);(root/filename).write_bytes(raw)
            rows=animation_rows(params[species.lower()+'/enemyanimmgr.txt'].decode('shift_jis'))
            if tuple(Path(r['file']).stem for r in rows)!=CLIPS:raise ValueError('Unexpected Frog registry')
            info=dict(enemy_id=identity,role='concrete spawnable',model_sha256=sha(model),joints=names,metadata_sha256=metadata,skinning=dict(envelopes=struct.unpack_from('>H',model_blocks['EVP1'],8)[0],draw_matrices=struct.unpack_from('>H',model_blocks['DRW1'],8)[0],weighted_baking=True),
                      collision=collision_nodes(params[species.lower()+'/enemycoll.txt'],len(names)),
                      corpse=corpse(carcasses[species]),clips=[],**profile(params[species.lower()+'/enemyparm.txt']))
            reference=None
            for row in rows:
                raw=motions[row['file']];(root/row['file']).write_bytes(raw);duration,_=bca_pose(raw,0,len(names),allow_scale=True)
                if raw[40] not in LOOPS:raise ValueError('Unsupported source loop attribute')
                frames=event_frames(duration,row['events'],limit)
                clip=dict(name=Path(row['file']).stem,source_sha256=sha(raw),source_frames=duration,events=row['events'],
                          loop_attribute=raw[40],loop_semantics=LOOPS[raw[40]],event_loop_boundaries=[r for r in row['events'] if r[1] in (0,1)],poses=[],status='unsupported')
                clip_bytes=0
                try:
                    for number,frame in enumerate(frames):
                        _,pose=bca_pose(raw,frame,len(names),allow_scale=True)
                        matrices=draw_matrices(model_blocks,pose)
                        decoded=decode(model,True,bake_rigid=True,draw_matrices=matrices)
                        name=f"frog_{species}_{clip['name']}_{number:02}.mod"
                        conversion=write_model(decoded,root/name,'enemy.bmd');conversion.update(source='enemy.bmd',output=name)
                        data=(root/name).read_bytes()
                        try:check_budget(report['total_pose_bytes'],clip_bytes,len(data))
                        except RuntimeError:
                            (root/name).unlink();raise
                        clip_bytes+=len(data);report['total_pose_bytes']+=len(data)
                        resources=resource_chunks(data)
                        if reference is not None and resources!=reference:raise ValueError('Frog pose changes immutable render resources')
                        reference=resources
                        clip['poses'].append(dict(file=name,frame=frame,bytes=len(data),sha256=sha(data)))
                        (root/Path(name).with_suffix('.json')).write_bytes((json.dumps(conversion,sort_keys=True,indent=2)+'\n').encode())
                    clip['status']='converted'
                except ValueError as error:clip['unsupported_reason']=str(error)
                info['clips'].append(clip)
            report['species'][species]=info
        report['limitations']=['Sampled weighted poses; material/TEV approximation, no native installation.','Event frames and loop metadata preserved, not executed.','P1 counterparts proposed proxies only; P2 jump targeting, crush collision, water/stone receivers and lifecycle remain unimplemented.']
        (output/'frogs.json').write_bytes((json.dumps(report,sort_keys=True,indent=2)+'\n').encode())
        return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','source','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--pose-limit',type=int,default=MAX_POSES);a=p.parse_args();r=extract(a.iso,a.source,a.output,a.pose_limit)
    print(json.dumps({'bytes':r['total_pose_bytes'],'species':{s:{'clips':len(v['clips']),'converted':sum(c['status']=='converted' for c in v['clips'])} for s,v in r['species'].items()}}))
