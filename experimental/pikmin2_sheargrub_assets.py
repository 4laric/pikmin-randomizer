"""Local UjiA/UjiB source pose assets; no native behavior substitution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from experimental.pikmin2_assets import disc_files,archive_files
from experimental.pikmin2_convert import blocks,convert,u16,u32
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_animation import sample_frames


def sha(data):return hashlib.sha256(data).hexdigest()


def animation_rows(text):
    clean=re.sub(r'#[^\r\n]*','',text)
    count=int(clean.split()[0]);rows=[]
    for block in re.findall(r'\{([^{}]*)\}',clean):
        fields=block.split()
        if len(fields)<3 or not re.fullmatch(r'[a-z0-9_]+\.bca',fields[1]) or fields[-1]!='-1':raise ValueError('Invalid animation registration')
        events=fields[2:-1]
        if len(events)%2:raise ValueError('Invalid animation event pairs')
        rows.append({'file':fields[1],'events':[[int(events[i]),int(events[i+1])] for i in range(0,len(events),2)]})
    if len(rows)!=count or len({r['file'] for r in rows})!=count:raise ValueError('Animation registry count/identity mismatch')
    return rows


def joints(model):
    data=blocks(model)['JNT1'];count=u16(data,8);offset=u32(data,20)
    if offset+4>len(data) or u16(data,offset)!=count:raise ValueError('Invalid joint name table')
    names=[]
    for i in range(count):
        entry=offset+4+4*i
        if entry+4>len(data):raise ValueError('Truncated joint table')
        start=offset+u16(data,entry+2)
        if start>=len(data):raise ValueError('Invalid joint name offset')
        end=data.find(b'\0',start)
        if end<0:raise ValueError('Unterminated joint name')
        names.append(data[start:end].decode('ascii'))
    return names


def extract(iso,output,pose_limit=3):
    if type(pose_limit)!=int or not 2<=pose_limit<=8:raise ValueError('Pose limit must be2..8')
    output.mkdir(parents=True,exist_ok=False);index=disc_files(iso);hashes={};result={'schema':1,'species':{},'native_ready':False}
    with iso.open('rb') as disc:
        def read(path):
            at,size=index[path];disc.seek(at);raw=disc.read(size)
            if len(raw)!=size:raise ValueError('Truncated disc resource')
            hashes[path]=sha(raw);return raw
        motions=archive_files(read('enemy/data/UjiA/anim.szs'))
        params=archive_files(read('enemy/parm/enemyParms.szs'))
        for species in ('UjiA','UjiB'):
            root=output/species;root.mkdir();model=archive_files(read(f'enemy/data/{species}/model.szs'))['enemy.bmd']
            modelpath=root/'enemy.bmd';modelpath.write_bytes(model);names=joints(model)
            metadata={}
            for name in ('enemyanimmgr.txt','enemyparm.txt','enemycoll.txt','enemystoneinfo.txt'):
                raw=params[species.lower()+'/'+name];(root/name).write_bytes(raw);metadata[name]=sha(raw)
            rows=animation_rows((root/'enemyanimmgr.txt').read_text(encoding='shift_jis'));clips=[]
            for row in rows:
                raw=motions[row['file']];(root/row['file']).write_bytes(raw)
                clip=dict(row,sha256=sha(raw),status='unsupported',poses=[])
                try:
                    duration,_=bca_pose(raw,0,len(names),allow_scale=True)
                    clip['source_frames']=duration
                    for i,frame in enumerate(sample_frames(duration,pose_limit)):
                        _,pose=bca_pose(raw,frame,len(names),allow_scale=True)
                        name=Path(row['file']).stem+f'_{i:02}.mod'
                        conversion=convert(modelpath,root/name,True,bake_rigid=True,pose=pose)
                        conversion['source']='enemy.bmd';conversion['output']=name
                        (root/Path(name).with_suffix('.json')).write_text(json.dumps(conversion,indent=2)+'\n')
                        clip['poses'].append(dict(file=name,frame=frame,sha256=sha((root/name).read_bytes()),conversion=conversion))
                    clip['status']='converted'
                except ValueError as error:clip['unsupported_reason']=str(error)
                clips.append(clip)
            tex=blocks(model)['TEX1']
            result['species'][species]=dict(model_sha256=sha(model),joints=names,embedded_texture_count=u16(tex,8),metadata_sha256=metadata,
                animation_family='UjiA',clips=clips,behavior_required=('Female bridge-directed attack1; no Pikmin bite' if species=='UjiA' else 'Male attack2 bites/captures Pikmin; separate Eat state'),
                runtime_status='unsupported; source assets only')
    result['source_sha256']=hashes
    result['limitations']=['Sampled rigid poses with approximate materials; no skeletal playback or event execution.','Collision and parameter text preserved, not replaced with mesh-bound guesses.','Separate source FSMs, bridge ownership, bite/eat attachment, burrowing and lifecycle remain unimplemented.']
    (output/'sheargrubs.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--iso',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--pose-limit',type=int,default=3)
    a=p.parse_args();r=extract(a.iso,a.output,a.pose_limit)
    print(json.dumps({s:{'joints':len(v['joints']),'clips':len(v['clips']),'converted':sum(c['status']=='converted' for c in v['clips'])} for s,v in r['species'].items()}))
