"""#235 adapter for Kimi #234 manifest: sampled noninteractive Bulblax display."""
import argparse,json,math,re
from pathlib import Path
from experimental.pikmin2_bulblax_install import validate,MANIFEST,MATERIAL_POLICY
from experimental.pikmin2_bulblax_bank import parse_bank,validate_files
from experimental.pikmin2_bulblax_assets import SPECIES,CLIPS
from experimental.pikmin2_breadbug_visual import sha,read_verified

CONFIG='p2-bulblax-visual.txt'


def protocol(clips,placements):
    if not 1<=len(clips)<=29 or not 1<=len(placements)<=8:raise ValueError('Display budget')
    lines=['P2_BULBLAX_VISUAL_1',str(len(clips))];seen=set()
    for c in clips:
        key=(c['species'],c['name']);frames=c['frames'];duration=c['duration']
        if key in seen or c['species'] not in SPECIES or c['name'] not in CLIPS[c['species']]:raise ValueError('Invalid clip identity')
        seen.add(key)
        if type(duration)is not int or not 1<=duration<=10000 or not isinstance(frames,list) or not 1<=len(frames)<=12 or any(type(f)is not int or not 0<=f<duration for f in frames) or frames!=sorted(set(frames)):raise ValueError('Invalid clip timing')
        lines.append(f"{SPECIES[c['species']]} {c['name']} {duration} {len(frames)} "+' '.join(map(str,frames)))
    lines.append(str(len(placements)));ids=set()
    for p in placements:
        i=p['placement_id'];xyz=p['xyz'];yaw=p.get('yaw',0)
        if type(i)is not int or not 0<=i<=0xffffffff or i in ids or (p['species'],p['clip']) not in seen:raise ValueError('Invalid display identity')
        ids.add(i)
        if not isinstance(xyz,list) or len(xyz)!=3 or any(type(v)not in (int,float) or not math.isfinite(v) or abs(v)>100000 for v in xyz) or type(yaw)not in (int,float) or not math.isfinite(yaw) or abs(yaw)>360:raise ValueError('Invalid display transform')
        lines.append(f"{i} {SPECIES[p['species']]} {p['clip']} "+' '.join(format(v,'.9g') for v in xyz+[yaw]))
    return ('\n'.join(lines)+'\n').encode('ascii')


def prepare(manifest,bank,output):
    manifest=Path(manifest);bank=Path(bank);m=validate(manifest,bank);report=json.loads((bank/'bulblax-bank.json').read_bytes())
    if m['normal_policy']!=report.get('normal_policy',{}) or m['material_policy']!=MATERIAL_POLICY:raise ValueError('Approximation policy mismatch')
    parsed=parse_bank((bank/'p2-bulblax-bank.txt').read_text());validate_files(bank,parsed)
    clips=[dict(species=s,name=c['name'],duration=c['source_frames'],frames=c['sampled_frames']) for s,rows in m['clips'].items() for c in rows]
    config=protocol(clips,m['placements']);files={}
    for row in m['models']:
        name=Path(row['path']).name
        if name in files or report['file_sha256'].get(name)!=row['sha256']:raise ValueError('Pose identity mismatch')
        files[name]=read_verified(bank/row['path'],row['sha256'])
    output=Path(output);output.mkdir(parents=True,exist_ok=False);(output/'models').mkdir()
    for name,data in files.items():(output/'models'/name).write_bytes(data)
    (output/CONFIG).write_bytes(config)
    result=dict(schema=1,kind='bulblax_sampled_display',source_manifest_sha256=sha(manifest.read_bytes()),bank_sha256=m['bank']['sha256'],files={n:sha(d) for n,d in files.items()},clips=clips,placements=m['placements'],normal_policy=m['normal_policy'],material_policy=m['material_policy'],unsupported_frames=m['unsupported_frames'],config_sha256=sha(config),native_ready=False,behavior='noninteractive_no_actor_collision_rewards')
    (output/'bulblax-visual.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result


def install(profile,run,*,species=None):
    profile=Path(profile);m=json.loads((profile/'bulblax-visual.json').read_bytes())
    if m.get('schema')!=1 or m.get('kind')!='bulblax_sampled_display':raise ValueError('Unsupported display profile')
    if read_verified(profile/CONFIG,m['config_sha256'])!=protocol(m['clips'],m['placements']):raise ValueError('Config differs from metadata')
    expected={f"bulblax_{c['species']}_{c['name']}_{i:02}.mod" for c in m['clips'] for i in range(len(c['frames']))}
    if set(m['files'])!=expected:raise ValueError('Model set differs from clip mapping')
    files={name:read_verified(profile/'models'/name,d) for name,d in m['files'].items()}
    if sum(map(len,files.values()))>16*1024*1024:raise ValueError('Bank budget')
    for c in m['clips']:
        if sum(len(files[f"bulblax_{c['species']}_{c['name']}_{i:02}.mod"]) for i in range(len(c['frames'])))>1024*1024:raise ValueError('Clip budget')
    selected=m['placements'] if species is None else [p for p in m['placements'] if p['species']==species]
    config=protocol(m['clips'],selected)
    room=Path(run)/'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or room.resolve()!=room.absolute():raise ValueError('Expected private room directory')
    if (Path(run)/CONFIG).exists() or any((room/n).exists() for n in files):raise ValueError('Refusing existing display install')
    for name,data in files.items():(room/name).write_bytes(data);read_verified(room/name,m['files'][name])
    (Path(run)/CONFIG).write_bytes(config)
    return dict(placements=selected,clips=m['clips'],config_sha256=sha(config),profile_sha256=sha((profile/'bulblax-visual.json').read_bytes()))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--bank',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.manifest,a.bank,a.output)
