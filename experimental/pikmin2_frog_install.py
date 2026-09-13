"""Strict source-bound Frog visual installation; native P1 physics and rewards remain."""
import argparse
import hashlib
import json
from pathlib import Path
from experimental.pikmin2_frog_assets import SPECIES, CLIPS, MAX_POSES, CLIP_BYTES, TOTAL_BYTES
from experimental.pikmin2_animation import resource_chunks


def plan(bank, actors):
    actors=list(actors)
    if not 1<=len(actors)<=32:raise ValueError('Expected 1..32 actors')
    seen=set()
    for identity,species in actors:
        if type(identity) is not int or not 0<=identity<=0xffffffff or identity in seen or species not in SPECIES:
            raise ValueError('Invalid or duplicate Frog actor')
        seen.add(identity)
    raw=(bank/'frogs.json').read_bytes();manifest=json.loads(raw)
    if manifest.get('schema')!=1 or manifest.get('policy')!='P2_FROG_IMPORT_1' or manifest.get('disc_id')!='GPVE01' or manifest.get('disc_revision')!=0 or set(manifest.get('species',{}))!=set(SPECIES):
        raise ValueError('Unexpected Frog source manifest')
    lines=['P2_FROG_1',str(len(actors))]+[f'{i} {s}' for i,s in actors]
    files=[];total=0
    for species,enemy_id in SPECIES.items():
        info=manifest['species'][species]
        if info.get('enemy_id')!=enemy_id or [c.get('name') for c in info.get('clips',[])]!=list(CLIPS):raise ValueError('Unexpected Frog species/clip identity')
        lines.append(species);reference=None
        for clip in info['clips']:
            duration=clip['source_frames'];poses=clip['poses'];frames=[p['frame'] for p in poses]
            if clip.get('status')!='converted' or type(duration) is not int or not 1<=duration<=10000 or not 2<=len(poses)<=MAX_POSES or any(type(f) is not int for f in frames) or frames[0]!=0 or frames[-1]!=duration-1 or any(a>=b for a,b in zip(frames,frames[1:])):raise ValueError('Invalid Frog frame sequence')
            lines.append(f"{clip['name']} {len(poses)} {duration} "+' '.join(map(str,frames)))
            size=0
            for index,pose in enumerate(poses):
                name=f"frog_{species}_{clip['name']}_{index:02}.mod"
                if pose['file']!=name:raise ValueError('Unexpected Frog pose filename')
                data=(bank/species/name).read_bytes();size+=len(data);total+=len(data)
                if not data or size>CLIP_BYTES or total>TOTAL_BYTES or len(data)!=pose['bytes'] or hashlib.sha256(data).hexdigest()!=pose['sha256']:raise ValueError('Frog pose size/hash mismatch')
                resources=resource_chunks(data)
                if reference is not None and reference!=resources:raise ValueError('Frog immutable resource mismatch')
                reference=resources;files.append((name,data))
    if total!=manifest.get('total_pose_bytes'):raise ValueError('Frog total byte mismatch')
    return ('\n'.join(lines)+'\n').encode(),files,hashlib.sha256(raw).hexdigest()


def install(bank, run, actors):
    protocol,files,digest=plan(Path(bank),actors)
    run=Path(run);room=run/'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or not room.resolve().is_relative_to(run.resolve()):raise ValueError('Expected private model destination')
    targets=[room/name for name,_ in files]+[run/'p2-frog.txt',run/'frog-install.json']
    if any(p.exists() or p.is_symlink() for p in targets):raise ValueError('Refusing existing Frog target')
    for name,data in files:(room/name).write_bytes(data)
    (run/'p2-frog.txt').write_bytes(protocol)
    result=dict(schema=1,manifest_sha256=digest,protocol_sha256=hashlib.sha256(protocol).hexdigest(),models=len(files),bytes=sum(len(data) for _,data in files),native_ready=False,behavior='P1 Frog/Frow proxy; native P1 rewards unchanged')
    (run/'frog-install.json').write_bytes((json.dumps(result,sort_keys=True,indent=2)+'\n').encode())
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bank',type=Path,required=True);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--actor',action='append',required=True,help='generator:species')
    a=p.parse_args();print(json.dumps(install(a.bank,a.run,[(int(v.split(':')[0]),v.split(':')[1]) for v in a.actor])))
