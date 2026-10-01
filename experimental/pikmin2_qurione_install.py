"""Strict source-bound Honeywisp visual-only installation; host nectar remains P1."""
import hashlib,json,math,re
from pathlib import Path
from experimental.pikmin2_qurione_assets import EXPECTED
from experimental.pikmin2_kochappy_bank import resource_chunks

def sha(data):return hashlib.sha256(data).hexdigest()
def verified(path,digest):
    raw=path.read_bytes()
    if sha(raw)!=digest:raise ValueError('Source hash mismatch: '+path.name)
    return raw

def payload(imported,expected_source_sha256):
    raw=verified(imported/'qurione.json',expected_source_sha256);meta=json.loads(raw)
    if (meta.get('schema'),meta.get('catalog_id'),meta.get('source_id'))!=(1,'Qurione',16):raise ValueError('Wrong source identity')
    verified(imported/'enemy.bmd',meta['model_sha256'])
    if [(c['file'],c['events']) for c in meta['clips']]!=EXPECTED:raise ValueError('Unexpected motion mapping')
    files={};lines=['P2_QURIONE_BANK_1'];resources=None;total=0
    for clip in meta['clips']:
        name=Path(clip['file']).stem;duration=clip['duration'];poses=clip['poses']
        verified(imported/clip['file'],clip['source_sha256'])
        if type(duration)is not int or not 1<=duration<=10000 or not 2<=len(poses)<=10 or clip.get('blocker'):raise ValueError('Invalid clip')
        frames=[p['frame'] for p in poses]
        if any(type(f)is not int for f in frames) or frames!=sorted(set(frames)) or frames[0]!=0 or frames[-1]!=duration-1:raise ValueError('Invalid source frames')
        if any(f not in frames for f,_ in clip['events']):raise ValueError('Missing event sample')
        lines.append(f'{name} {len(poses)} {duration} '+' '.join(map(str,frames)))
        clipbytes=0
        for i,p in enumerate(poses):
            if p['file']!=f'{name}_{i:02}.mod':raise ValueError('Unsafe model filename')
            data=verified(imported/p['file'],p['sha256']);r=resource_chunks(data)
            if resources is not None and resources!=r:raise ValueError('Materials differ between poses')
            resources=r;clipbytes+=len(data);total+=len(data)
            if not data or clipbytes>512*1024 or total>2*1024*1024:raise ValueError('Native bank budget exceeded')
            files[f'qurione_{name}_{i:02}.mod']=data
    return files, ('\n'.join(lines)+'\n').encode()

def install(imported,run,generator_ids,expected_source_sha256):
    ids=list(generator_ids)
    if not 1<=len(ids)<=8 or any(type(i)is not int or not 0<=i<=0xffffffff for i in ids) or len(set(ids))!=len(ids):raise ValueError('Invalid actor IDs')
    files,bank=payload(imported,expected_source_sha256)
    directory=run/'assets/dataDir/courses/pikmin2room'
    if not directory.is_dir() or any(p.is_symlink() or p.is_junction() for p in [directory,*directory.parents] if p.exists()):raise ValueError('Expected private model directory')
    configs={'p2-qurione-bank.txt':bank,'p2-qurione-actors.txt':('P2_QURIONE_ACTORS_1 '+str(len(ids))+'\n'+'\n'.join(map(str,ids))+'\n').encode()}
    for existing in run.glob('p2-*-actors.txt'):
        tokens=existing.read_text().split()
        if len(tokens)<2 or not tokens[1].isdigit() or int(tokens[1])!=len(tokens)-2:raise ValueError('Malformed existing bindings')
        if set(ids)&set(map(int,tokens[2:])):raise ValueError('Actor binding overlap')
    if any((run/n).exists() for n in configs) or any((directory/n).exists() for n in files):raise ValueError('Refusing existing installation')
    for name,data in files.items():(directory/name).write_bytes(data)
    for name,data in configs.items():(run/name).write_bytes(data)
    return dict(source_sha256=expected_source_sha256,files={n:sha(d) for n,d in files.items()},configs={n:sha(d) for n,d in configs.items()},reward='P2 Egg (real host birth via lane-20 P2Egg policy)',native_runtime='untested')
