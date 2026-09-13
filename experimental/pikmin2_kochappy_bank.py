"""Separate Dwarf Red visual/health bank; arena placement is supplied by the caller."""
import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path
from experimental.pikmin2_animation import CLIPS,CLIP_BYTES,TOTAL_BYTES,parse_bank as parse_timing,resource_chunks,sample_frames
from experimental.pikmin2_convert import blocks,convert,u16
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_kochappy_profile import GROUPS,profiles

PROFILE='P2_KOCHAPPY_PROFILE_1\nspecies Kochappy\nhealth 200\n'
HEADER='P2_KOCHAPPY_BANK_1'


def parse_bank(text):
    tokens=text.split()
    if not tokens or tokens[0]!=HEADER:raise ValueError('Expected separate Kochappy bank')
    return parse_timing('P2_SNOW_2 '+' '.join(tokens[1:]))


def validate_files(directory,bank):
    paths=[];total=0;reference=None
    for name,info in bank.items():
        count=0
        for index in range(info['poses']):
            path=directory/f'kochappy_{name}_{index:02}.mod';size=path.stat().st_size
            count+=size;total+=size
            if not size or count>CLIP_BYTES or total>TOTAL_BYTES:raise ValueError('Kochappy bank exceeds byte budget')
            resources=resource_chunks(path.read_bytes())
            if reference is not None and reference!=resources:raise ValueError('Kochappy materials/textures differ between poses')
            reference=resources;paths.append(path)
    return paths,total


def build(imported,output,pose_limit=12):
    if type(pose_limit)is not int or not 2<=pose_limit<=24:raise ValueError('Expected 2..24 pose limit')
    reference=json.loads((imported/'kochappy-profile.json').read_text())
    if reference.get('schema')!=1 or reference.get('next_species')!='Kochappy':raise ValueError('Expected Kochappy reference import')
    values=profiles({name:[v['parameters'][g] for g in GROUPS] for name,v in reference['variants'].items()})
    model=imported/'dwarf-red.bmd';data=model.read_bytes()
    if hashlib.sha256(data).hexdigest()!=reference['exported_model_sha256']:raise ValueError('Reference model hash mismatch')
    motions={}
    for name in CLIPS:
        clip=(imported/'source-animation'/(name+'.bca')).read_bytes()
        if hashlib.sha256(clip).hexdigest()!=reference['shared_animation_sha256'][name+'.bca']:raise ValueError('Reference clip hash mismatch')
        motions[name]=clip
    joints=u16(blocks(data)['JNT1'],8);rows=[HEADER];report={};started=time.perf_counter()
    output.mkdir(parents=True,exist_ok=False)
    for name,clip in motions.items():
        duration,_=bca_pose(clip,0,joints,allow_scale=True);frames=sample_frames(duration,pose_limit)
        rows.append(f'{name} {len(frames)} {duration} '+' '.join(map(str,frames)))
        for i,frame in enumerate(frames):
            _,pose=bca_pose(clip,frame,joints,allow_scale=True)
            convert(model,output/f'kochappy_{name}_{i:02}.mod',True,bake_rigid=True,pose=pose)
        report[name]={'poses':len(frames),'source_frames':duration,'frames':frames}
    bank='\n'.join(rows)+'\n';paths,total=validate_files(output,parse_bank(bank))
    result={'schema':1,'species':'Kochappy','source_id':1,'health':200,'motions':report,
            'reference_sha256':hashlib.sha256((imported/'kochappy-profile.json').read_bytes()).hexdigest(),
            'file_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'cost':{'poses':sum(v['poses'] for v in report.values()),'mod_bytes':total,'extract_seconds':time.perf_counter()-started,'clip_budget':CLIP_BYTES,'total_budget':TOTAL_BYTES},
            'supported':'Source Red visuals and health200; P1 native family AI/physics/event timing.',
            'not_implemented':['source Purple stun10s','P2 FSM/event parity','arena lifecycle acceptance']}
    (output/'kochappy-bank.json').write_text(json.dumps(result,indent=2));(output/'p2-kochappy-bank.txt').write_text(bank);(output/'p2-kochappy-profile.txt').write_text(PROFILE)
    return result


def install(imported,run,generator_ids):
    ids=list(generator_ids)
    if not ids or len(ids)>100 or len(set(ids))!=len(ids) or any(type(i)is not int or not 0<=i<=0xffffffff for i in ids):raise ValueError('Expected unique unsigned generator IDs')
    metadata=json.loads((imported/'kochappy-bank.json').read_text())
    if (metadata.get('schema'),metadata.get('species'),metadata.get('source_id'),metadata.get('health'))!=(1,'Kochappy',1,200):raise ValueError('Wrong family profile')
    if (imported/'p2-kochappy-profile.txt').read_text().split()!=PROFILE.split():raise ValueError('Unsupported Kochappy health profile')
    bank_text=(imported/'p2-kochappy-bank.txt').read_text();bank=parse_bank(bank_text)
    if bank!=metadata['motions']:raise ValueError('Kochappy bank metadata mismatch')
    paths,_=validate_files(imported,bank)
    if set(metadata['file_sha256'])!={p.name for p in paths} or any(hashlib.sha256(p.read_bytes()).hexdigest()!=metadata['file_sha256'][p.name] for p in paths):raise ValueError('Kochappy bank file hash mismatch')
    config_names=('p2-kochappy-profile.txt','p2-kochappy-bank.txt','p2-kochappy-actors.txt')
    if any((run/name).exists() for name in config_names):raise ValueError('Kochappy already installed')
    snow=run/'p2-snow-actors.txt'
    if snow.exists():
        tokens=snow.read_text().split()
        if len(tokens)<2 or tokens[0]!='P2_SNOW_ACTORS_1' or int(tokens[1])!=len(tokens)-2:raise ValueError('Invalid existing Snow bindings')
        if set(ids)&set(map(int,tokens[2:])):raise ValueError('Kochappy/Snow actor overlap')
    destination=run/'assets/dataDir/courses/pikmin2room'
    if not destination.is_dir() or destination.is_symlink() or destination.is_junction():raise ValueError('Expected private arena asset directory')
    for path in paths:shutil.copyfile(path,destination/path.name)
    (run/'p2-kochappy-profile.txt').write_text(PROFILE);(run/'p2-kochappy-bank.txt').write_text(bank_text)
    (run/'p2-kochappy-actors.txt').write_text(f'P2_KOCHAPPY_ACTORS_1 {len(ids)}\n'+'\n'.join(map(str,ids))+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--imported',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--pose-limit',type=int,default=12)
    args=parser.parse_args();print(json.dumps(build(args.imported,args.output,args.pose_limit),indent=2))
