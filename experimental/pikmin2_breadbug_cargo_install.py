"""Add a verified optional cargo bank to an existing private Breadbug actor."""
import json
from experimental.pikmin2_breadbug_actor import plan,records
from experimental.pikmin2_breadbug_visual import read_verified,sha

def install(bank,visual_profile,run):
    room=run/'assets/dataDir/courses/pikmin2room';generator=run/'assets/dataDir/stages/chal0/default.gen'
    if not room.is_dir() or room.resolve()!=room.absolute() or generator.resolve()!=generator.absolute():raise ValueError('Expected private stage/models')
    metadata=json.loads((bank/'breadbug-cargo-bank.json').read_text());base=json.loads((visual_profile/'breadbug-visual.json').read_text());actor=json.loads((run/'breadbug-actor-proxy.json').read_text())
    if metadata.get('schema')!=1 or metadata.get('family')!='PanModoki' or metadata.get('purpose')!='visual_cargo_reference_only' or metadata.get('events_executed') is not False:raise ValueError('Unsupported cargo bank')
    if metadata.get('source_import_sha256')!=base.get('source_import_sha256') or not metadata.get('source_import_sha256'):raise ValueError('Different source import')
    config,existing=plan(visual_profile,records(generator),actor['generators'])
    if read_verified(run/'p2-breadbug-actor.txt',actor['config_sha256'])!=config:raise ValueError('Actor profile mismatch')
    for name,data in existing.items():
        if read_verified(room/name,actor['files'][name])!=data:raise ValueError('Actor models mismatch')
    clips=metadata.get('clips',[])
    if [c.get('name') for c in clips]!=['back','hide']:raise ValueError('Expected Back/Hide clips')
    lines=['P2_BREADBUG_CARGO_1'];files={}
    for clip in clips:
        name=clip['name'];frames=clip['frames'];events=[[10,0],[39,1]] if name=='back' else [[20,2]]
        if clip.get('source_file')!=('move2.bca' if name=='back' else 'type3.bca') or clip.get('duration')!=49 or clip.get('events')!=events:raise ValueError('Unverified cargo motion')
        if not isinstance(frames,list) or not 2<=len(frames)<=12 or any(type(f) is not int or not 0<=f<49 for f in frames) or frames!=sorted(set(frames)) or frames[0]!=0 or frames[-1]!=48 or not {e[0] for e in events}.issubset(frames):raise ValueError('Invalid cargo samples')
        lines.append(f'{name} 49 {len(frames)} '+' '.join(map(str,frames)))
        for i in range(len(frames)):
            file=f'breadbug_cargo_{name}_{i:02}.mod';files[file]=read_verified(bank/'models'/file,metadata['files'][file])
    if set(files)!=set(metadata['files']):raise ValueError('Unexpected cargo models')
    if any((room/name).exists() for name in files) or (run/'p2-breadbug-cargo.txt').exists() or (run/'breadbug-cargo-install.json').exists():raise ValueError('Refusing existing cargo bank')
    for name,data in files.items():(room/name).write_bytes(data)
    raw=('\n'.join(lines)+'\n').encode();(run/'p2-breadbug-cargo.txt').write_bytes(raw)
    result=dict(schema=1,config_sha256=sha(raw),bank_sha256=sha((bank/'breadbug-cargo-bank.json').read_bytes()),actor_config_sha256=sha(config),files={n:sha(b) for n,b in files.items()},gameplay_events_executed=False)
    (run/'breadbug-cargo-install.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result
