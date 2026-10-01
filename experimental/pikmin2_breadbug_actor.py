"""Opt in existing P1 TEKI_Collec8 to P2 visuals, preserving native P1 behavior."""
import json
from pathlib import Path
import struct
from experimental.pikmin2_breadbug_visual import read_verified,sha
from scripts.preview_pikmin2_room import records


def actor_rows(generator_rows,identities):
    if not isinstance(identities,list) or not 1<=len(identities)<=8 or any(type(i) is not int or not 0<=i<=0xffffffff for i in identities) or len(set(identities))!=len(identities):raise ValueError('Invalid actor IDs')
    result=[]
    for identity in identities:
        matches=[r for r in generator_rows if len(r)>=81 and struct.unpack_from('<I',r,8)[0]==identity]
        if len(matches)!=1 or matches[0][72:76]!=b'iket' or matches[0][80]!=8:raise ValueError('Expected exactly one existing TEKI_Collec8 generator')
        result.append(f'{identity} 8')
    return result


def plan(profile,generator_rows,identities):
    rows=actor_rows(generator_rows,identities)
    metadata=json.loads((profile/'breadbug-visual.json').read_text())
    if metadata.get('schema')!=1 or metadata.get('family')!='PanModoki' or metadata.get('behavior')!='visual_only_no_gameplay_actor':raise ValueError('Unsupported source profile')
    files={};lines=['P2_BREADBUG_ACTOR_PROXY_1']
    clips=metadata.get('clips',[])
    if [c.get('name') for c in clips]!=['wait','move']:raise ValueError('Missing source motion clips')
    for clip in clips:
        frames=clip['frames'];duration=clip['source_duration'];name=clip['name']
        if type(duration) is not int or not 2<=duration<=10000 or not isinstance(frames,list) or not 2<=len(frames)<=12 or any(type(f) is not int for f in frames) or frames!=sorted(set(frames)) or frames[0]!=0 or frames[-1]!=duration-1:raise ValueError('Invalid source samples')
        lines.append(f'{name} {duration} {len(frames)} '+' '.join(map(str,frames)))
        for i in range(len(frames)):
            source=f'breadbug_{name}_{i:02}.mod';destination=f'breadbug_actor_{name}_{i:02}.mod'
            files[destination]=read_verified(profile/'models'/source,metadata['files'][source])
    lines.extend([str(len(rows)),*rows])
    return ('\n'.join(lines)+'\n').encode(),files


def install(profile,run,identities):
    room=run/'assets/dataDir/courses/pikmin2room';generator=run/'assets/dataDir/stages/chal0/default.gen'
    if not room.is_dir() or room.resolve()!=room.absolute() or generator.resolve()!=generator.absolute():raise ValueError('Expected private non-junction stage/model files')
    config,files=plan(profile,records(generator),identities)
    if (run/'p2-breadbug-actor.txt').exists() or (run/'breadbug-actor-proxy.json').exists() or any((room/name).exists() for name in files):raise ValueError('Refusing existing actor profile/models')
    for name,data in files.items():(room/name).write_bytes(data)
    (run/'p2-breadbug-actor.txt').write_bytes(config)
    result=dict(schema=1,family='PanModoki',behavior='P1_TEKI_Collec8_proxy',native_validated=False,generators=identities,
                generator_sha256=sha(generator.read_bytes()),config_sha256=sha(config),files={k:sha(v) for k,v in files.items()},
                unchanged=['P1 AI','P1 collision','P1 cargo/nest behavior','P1 corpse model','P1 receipts'])
    (run/'breadbug-actor-proxy.json').write_text(json.dumps(result,indent=2));return result
