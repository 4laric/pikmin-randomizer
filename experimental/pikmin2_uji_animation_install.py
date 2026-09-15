"""Install validated sampled Uji visuals into an already private room stage."""
import argparse
import hashlib
import json
from pathlib import Path
from experimental.pikmin2_sheargrub_animation import CLIPS, MAX_POSES, CLIP_BYTES, TOTAL_BYTES, mapping
from experimental.pikmin2_animation import resource_chunks


def validate(bank):
    manifest_bytes=(bank/'animation-bank.json').read_bytes()
    report=json.loads(manifest_bytes)
    if report.get('schema')!=1 or report.get('policy')!='P2_UJI_VISUAL_BANK_1' or set(report.get('species',{}))!=set(CLIPS):
        raise ValueError('Unsupported Uji bank')
    files=[];total=0;lines=['P2_UJI_ANIMATION_1']
    for species,names in CLIPS.items():
        info=report['species'][species]
        if info.get('motion_mapping')!=mapping(species) or [c.get('name') for c in info.get('clips',[])]!=list(names):
            raise ValueError('Unexpected Uji clip mapping/order')
        lines.append(species);reference=None
        for clip in info['clips']:
            duration=clip['source_frames'];poses=clip['poses']
            if type(duration) is not int or not 1<=duration<=10000 or not 1<=len(poses)<=MAX_POSES:
                raise ValueError('Invalid Uji duration/count')
            frames=[p['frame'] for p in poses]
            if any(type(f) is not int for f in frames) or frames[0]!=0 or frames[-1]!=duration-1 or any(a>=b for a,b in zip(frames,frames[1:])):
                raise ValueError('Invalid Uji frame sequence')
            lines.append(f"{clip['name']} {len(poses)} {duration} "+' '.join(map(str,frames)))
            size=0
            for i,pose in enumerate(poses):
                expected=f"uji_{species}_{clip['name']}_{i:02}.mod"
                if pose['file']!=expected:raise ValueError('Unexpected Uji pose filename')
                raw=(bank/species/expected).read_bytes();size+=len(raw);total+=len(raw)
                if not raw or size>CLIP_BYTES or total>TOTAL_BYTES or len(raw)!=pose['bytes'] or hashlib.sha256(raw).hexdigest()!=pose['sha256']:
                    raise ValueError('Uji pose size/hash mismatch')
                resources=resource_chunks(raw)
                if reference is not None and resources!=reference:raise ValueError('Uji resource mismatch')
                reference=resources;files.append((expected,raw))
    if total!=report.get('total_bytes'):raise ValueError('Uji total size mismatch')
    return '\n'.join(lines)+'\n',files,hashlib.sha256(manifest_bytes).hexdigest()


def install(bank,run):
    text,files,digest=validate(bank)
    destination=run/'assets/dataDir/courses/pikmin2room'
    if not destination.is_dir() or not (run/'p2-sheargrub.txt').is_file():
        raise ValueError('Expected prepared private Sheargrub stage')
    # Guard against shared or junction-backed output. Existing assets must stay inside run.
    root=run.resolve()
    if not destination.resolve().is_relative_to(root):raise ValueError('Shared model destination')
    targets=[destination/name for name,_ in files]+[run/'p2-sheargrub-animation.txt',run/'uji-animation-install.json']
    if any(p.exists() for p in targets):raise ValueError('Animation already installed or target collision')
    for name,raw in files:(destination/name).write_bytes(raw)
    (run/'p2-sheargrub-animation.txt').write_bytes(text.encode())
    audit=dict(schema=1,manifest_sha256=digest,protocol_sha256=hashlib.sha256(text.encode()).hexdigest(),
               model_count=len(files),total_bytes=sum(len(raw) for _,raw in files))
    (run/'uji-animation-install.json').write_text(json.dumps(audit,indent=2)+'\n')
    return audit


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bank',type=Path,required=True);p.add_argument('--run',type=Path,required=True)
    a=p.parse_args();print(json.dumps(install(a.bank,a.run)))
