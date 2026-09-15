"""Deterministic local Honeywisp source bank; no native reward or AI execution."""
import argparse, hashlib, json, time, subprocess
from pathlib import Path
from experimental.pikmin2_assets import disc_files, archive_files
from experimental.pikmin2_sheargrub_assets import animation_rows, joints
from experimental.pikmin2_breadbug_assets import parameter_blocks, collision_nodes
from experimental.pikmin2_convert import blocks, convert
from experimental.pikmin2_rigid import joint_matrices
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_animation import sample_frames

EXPECTED = [('waitl.bca', [[0,0],[99,1]]), ('damage.bca', [[5,2]]), ('run.bca', [[0,0],[9,1]]), ('appear1.bca', []), ('hide1.bca', [])]
MAX_BYTES = 8 * 1024 * 1024
MAX_SECONDS = 120

def sha(raw): return hashlib.sha256(raw).hexdigest()

def validate(rows, names, params, limit):
    if type(limit) is not int or not 2 <= limit <= 8: raise ValueError('Expected 2..8 base poses')
    if [(r['file'], r['events']) for r in rows] != EXPECTED: raise ValueError('Unexpected Qurione motion contract')
    if any(names.count(n) != 1 for n in ('water','body_jnt2')): raise ValueError('Missing or ambiguous attachment joint')
    if len(params) != 3 or set(params[2]) != {'fp01','fp02','fp03','fp04','fp05'}: raise ValueError('Unexpected proper parameter block')

def extract(iso, output, pose_limit=4):
    started=time.monotonic(); index=disc_files(iso); sources={}
    with iso.open('rb') as disc:
        disc.seek(0); disc_id=disc.read(8).hex()
        def read(name):
            at,size=index[name];disc.seek(at);raw=disc.read(size)
            if len(raw)!=size: raise ValueError('Truncated source resource')
            sources[name]=sha(raw);return raw
        model=archive_files(read('enemy/data/Qurione/model.szs'))['enemy.bmd']
        anim=archive_files(read('enemy/data/Qurione/anim.szs'))
        parm=archive_files(read('enemy/parm/enemyParms.szs'))
    rawparams=parm['qurione/enemyparm.txt']; params=parameter_blocks(rawparams)
    rows=animation_rows(parm['qurione/enemyanimmgr.txt'].decode('shift_jis')); names=joints(model)
    validate(rows,names,params,pose_limit)
    collision=collision_nodes(parm['qurione/enemycoll.txt'],len(names))
    output.mkdir(parents=True,exist_ok=False); (output/'enemy.bmd').write_bytes(model)
    for name in ('enemyparm.txt','enemyanimmgr.txt','enemycoll.txt'):
        (output/name).write_bytes(parm['qurione/'+name])
    clips=[]; bytecount=0
    for row in rows:
        raw=anim[row['file']];(output/row['file']).write_bytes(raw)
        duration,_=bca_pose(raw,0,len(names),allow_scale=True)
        if any(not 0<=f<duration for f,_ in row['events']): raise ValueError('Event outside clip')
        frames=sorted(set(sample_frames(duration,pose_limit))|{f for f,_ in row['events']})
        clip=dict(row,duration=duration,source_sha256=sha(raw),loop=[e[0] for e in row['events']] if row['file'] in ('waitl.bca','run.bca') else None,poses=[])
        for i,frame in enumerate(frames):
            _,pose=bca_pose(raw,frame,len(names),allow_scale=True)
            matrices=joint_matrices(blocks(model),pose)
            filename=Path(row['file']).stem+f'_{i:02}.mod'
            try:
                report=convert(output/'enemy.bmd',output/filename,True,bake_rigid=True,pose=pose)
            except ValueError as error:
                clip['blocker']=str(error);break
            report['source']='enemy.bmd';report['output']=filename
            (output/Path(filename).with_suffix('.json')).write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf-8')
            bytecount+=(output/filename).stat().st_size
            if bytecount>MAX_BYTES or time.monotonic()-started>MAX_SECONDS: raise ValueError('Import budget exceeded')
            clip['poses'].append(dict(file=filename,frame=frame,sha256=sha((output/filename).read_bytes()),attachment_model_space={n:matrices[names.index(n)] for n in ('water','body_jnt2')}))
        clips.append(clip)
    reference=Path(__file__).resolve().parents[1]/'native/pikmin2-research'
    source_paths=['src/plugProjectNishimuraU/'+n for n in ('Qurione.cpp','QurioneState.cpp','QurioneAnimator.cpp','QurioneMgr.cpp')]+['include/Game/Entities/Qurione.h']
    source_evidence={n:sha((reference/n).read_bytes()) for n in source_paths}
    source_revision=subprocess.check_output(['git','-C',str(reference),'rev-parse','HEAD'],text=True).strip()
    result=dict(schema=1,source_revision=source_revision,source_files=source_evidence,source_id=16,catalog_id='Qurione',disc_header_hex=disc_id,resources=sources,model_sha256=sha(model),joints=names,parameter_blocks=params,collision=collision,clips=clips,converted_mod_bytes=bytecount,budgets=dict(max_mod_bytes=MAX_BYTES,max_seconds=MAX_SECONDS,base_samples=pose_limit,max_poses=5*(pose_limit+2)),reward=dict(dependency='Egg',attachment_joint='water',release=dict(clip='damage.bca',frame=5,key=2),events_executed=False),native_ready=False)
    (output/'qurione.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--iso',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--pose-limit',type=int,default=4);a=p.parse_args()
    r=extract(a.iso,a.output,a.pose_limit);print(json.dumps(dict(bytes=r['converted_mod_bytes'],clips=[dict(file=c['file'],poses=len(c['poses']),blocker=c.get('blocker')) for c in r['clips']])))
