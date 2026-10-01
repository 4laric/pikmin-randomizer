"""Strict private Uji visual config preparation; native proxy integration is separate."""
import hashlib
import json
from pathlib import Path

SPECIES={'UjiA':1,'UjiB':2}


def plan(imported,actors):
    actors=list(actors)
    if not 1<=len(actors)<=100:raise ValueError('Expected1..100 actors')
    ids=set();metadata=json.loads((imported/'sheargrubs.json').read_text());files={}
    if metadata.get('schema')!=1:raise ValueError('Unsupported import schema')
    rows=['P2_SHEARGRUB_1',str(len(actors))]
    for generator,species in actors:
        if type(generator)!=int or not 0<=generator<=0xffffffff or generator in ids or species not in SPECIES:raise ValueError('Invalid/duplicate actor identity')
        ids.add(generator);rows.append(f'{generator} {species} {SPECIES[species]}')
        for clip,index,label in [('move',0,'live'),('dead',-1,'dead')]:
            options=[c for c in metadata['species'][species]['clips'] if c['file']==clip+'.bca']
            if len(options)!=1 or options[0]['status']!='converted' or not options[0]['poses']:raise ValueError('Required source pose unavailable')
            pose=options[0]['poses'][index];name=pose['file']
            if Path(name).name!=name or not name.endswith('.mod'):raise ValueError('Unsafe pose filename')
            data=(imported/species/name).read_bytes()
            if hashlib.sha256(data).hexdigest()!=pose['sha256']:raise ValueError('Pose hash mismatch')
            files[f'uji_{species}_{label}.mod']=data
    return '\n'.join(rows)+'\n',files


def install(imported,run,actors):
    config,files=plan(imported,actors)
    room=run/'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or room.resolve()!=room.absolute():raise ValueError('Expected private non-junction room')
    for name,data in files.items():
        target=room/name
        if target.exists():raise ValueError('Refusing existing visual target')
    if (run/'p2-sheargrub.txt').exists():raise ValueError('Refusing existing actor config')
    for name,data in files.items():(room/name).write_bytes(data)
    (run/'p2-sheargrub.txt').write_text(config)
    return {'species':sorted({s for _,s in actors}),'proxy_behavior':'P1 KabekuiA/KabekuiB; not source P2 FSM','files':sorted(files)}

def stage_pair(imported,assets,run):
    """Add one source-visual pair, explicitly using native P1 proxy species."""
    import re
    import struct
    from scripts.preview_pikmin2_room import generator,records
    path=run/'assets/dataDir/stages/chal0/default.gen'
    if path.resolve()!=path.absolute() or not path.is_file():raise ValueError('Expected private generator')
    raw=generator(assets);starts=[m.start() for m in re.finditer(b'    0.0v',raw)]+[len(raw)]
    template=next(raw[a:b] for a,b in zip(starts,starts[1:]) if raw[a+16:a+48].rstrip(b'\0')==b'preview dwarf bulborb')
    existing=path.read_bytes();entries=records(path);used={struct.unpack_from('<I',r,8)[0] for r in entries}
    actors=[(60000,'UjiA'),(60001,'UjiB')]
    if used & {i for i,s in actors}:raise ValueError('Generator IDs already used')
    # Install validates all source files before modifying the stage generator.
    result=install(imported,run,actors)
    for (identity,species),x in zip(actors,(940,1100)):
        entry=bytearray(template);struct.pack_into('<I',entry,8,identity);entry[80]=18 if species=='UjiA' else 19
        entry[16:48]=('proxy '+species).encode().ljust(32,b'\0');struct.pack_into('>3f',entry,48,x,0,50);entries.append(entry)
    header=bytearray(existing[:24]);struct.pack_into('>I',header,20,len(entries));path.write_bytes(header+b''.join(entries))
    (run/'sheargrub-proxy.json').write_text(json.dumps(dict(result,placements=[{'generator':i,'species':s,'position':[x,0,50]} for (i,s),x in zip(actors,(940,1100))],native_validated=False),indent=2)+'\n')
    return result
