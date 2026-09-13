"""Private native floor-three geometry survey; party restoration only, no campaign entry."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import uuid

from experimental.pikmin2_beasts_floor2 import decode_no_cargo
from experimental.pikmin2_beasts_party_restore import entry_text, restore_party
from experimental.pikmin2_collision import ground_height
from scripts.preview_pikmin2_room import generator, overlay

GOALS = [(-85,-280),(-85,-390),(-85,-470),(-85,-580),(-85,-735),(-85,-1000),
         (-85,-735),(-85,-580),(-85,-470),(-85,-390),(-85,-280),(-85,-120)]


def sha(raw): return hashlib.sha256(raw).hexdigest()


def stage(assets, assembly, purple, pod, output, party, *, floor=3, goals=GOALS, anchor_positions=None):
    party=restore_party(party)
    report=json.loads((assembly/'assembly.json').read_bytes())
    if floor not in (3,4,5) or report['policy']!=f'P2_BEASTS_FLOOR{floor}_ASSEMBLY_1' or report['floor']!=floor:
        raise ValueError('Expected audited floor-three assembly')
    for name,digest in report['output_sha256'].items():
        if sha((assembly/name).read_bytes())!=digest:raise ValueError('Assembly changed: '+name)
    room=json.loads((assembly/'collision.json').read_bytes())
    def grounded(x,z):
        y=ground_height(room['vertices'],room['triangles'],x,z)
        if y is None:raise ValueError('Engineering anchor lacks ground')
        return [x,y,z]
    selected=anchor_positions or dict(start=(-85,-120),pod=(-200,65),ship=(85,240))
    anchors={name:grounded(*position) for name,position in selected.items()}
    if set(anchors)!={'start','pod','ship'} or len(goals)!=12:raise ValueError('Expected engineering anchors and12 survey goals')
    for x,z in goals:grounded(x,z)
    raw=generator(assets);starts=[m.start() for m in re.finditer(b'    0.0v',raw)]+[len(raw)]
    entries=[];count=0
    for a,b in zip(starts,starts[1:]):
        entry=bytearray(raw[a:b]);label=bytes(entry[16:48]).rstrip(b'\0')
        if label in (b'preview treasure bolt',b'preview dwarf bulborb'):continue
        if label==b'preview red pikmin':
            position=grounded(anchors['start'][0]-25+(count%5)*12,anchors['start'][2]-90+(count//5)*12);count+=1
        else:
            key={b'preview red onion':'pod',b'preview ship':'ship'}.get(label)
            if key is None:raise ValueError('Unexpected scaffold actor')
            position=anchors[key]
        struct.pack_into('>3f',entry,48,*position);entries.append(entry)
    actors=b'1.0v'+struct.pack('>4fI',*anchors['start'],45,len(entries))+b''.join(entries)
    decode_no_cargo(actors,0)
    ini=(assets/'dataDir/stages/chal0.ini').read_bytes()
    ini=re.sub(rb'(?m)^map_file[^\r\n]*',b'map_file courses/pikmin2room/room.mod',ini)
    ini=re.sub(rb'(?m)^navi_start[^\r\n]*',f'navi_start {float(anchors["start"][0])} {float(anchors["start"][2])}'.encode(),ini)
    overrides={'dataDir/stages/chal0.ini':ini,'dataDir/stages/chal0/default.gen':actors,
        'dataDir/courses/pikmin2room/room.mod':(assembly/'room.mod').read_bytes(),
        'dataDir/courses/pikmin2room/room.ini':(assembly/'room.ini').read_bytes(),
        'dataDir/courses/pikmin2room/pod.mod':(pod/'pod.mod').read_bytes()}
    models=sorted(purple.glob('*.mod'))
    if not models:raise ValueError('Missing Purple pose bank')
    for path in models:overrides['dataDir/courses/pikmin2room/'+path.name]=path.read_bytes()
    empty=b'1.0v'+struct.pack('>4fI',*anchors['start'],45,0)
    for path in (assets/'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/'+path.name,empty)
    run=output.resolve()/uuid.uuid4().hex;run.mkdir(parents=True)
    overlay(assets,run/'assets',overrides)
    configs={'p2-cargo-free.txt':b'P2_CARGO_FREE_1\n','p2-pod.txt':b'P2_POD_1\ncargo_free 0 1 1\nKochappy 0\n',
             'p2-purple.txt':(purple/'p2-purple.txt').read_bytes(),
             'p2-cave-entry.txt':entry_text(party,uuid.uuid4().hex).encode()}
    for name,data in configs.items():(run/name).write_bytes(data)
    readiness=dict(schema=1,policy=f'P2_BEASTS_FLOOR{floor}_SURVEY_1',floor=floor,party=party,anchors=anchors,goals=goals,
        native_ready=False,campaign_entry=False,party_restore_protocol_floor=2,
        assembly_sha256=sha((assembly/'assembly.json').read_bytes()),
        input_sha256={**{'assets/'+name:sha(data) for name,data in overrides.items()},**{name:sha(data) for name,data in configs.items()}},
        limitations=['Engineering party-only restore uses existing floor2 loader; no floor3 campaign launch.',
                     'Captain controller traversal, not squad carrying or natural gameplay.',
                     'Hiba, plants, treasures, cave exit and receipts omitted.'])
    (run/'survey.json').write_text(json.dumps(readiness,indent=2)+'\n')
    return run


def fixture(source, output):
    raw=source.read_text()
    marker='class RoomApp : public PlugPikiApp {'
    dispatch='if(beastsFloor2Enabled && pc_p2_preview_cargo_free_ready()) {'
    call='beastsFloor2Fixture(n);'
    if raw.count(marker)!=1 or raw.count(dispatch)!=1 or raw.count(call)!=1:
        raise ValueError('Frozen room fixture anchors changed')
    helper=(Path(__file__).with_name('pikmin2_beasts_floor3_survey.inc')).read_text()
    raw=raw.replace(marker,helper+'\n'+marker).replace(dispatch,'if(pc_p2_preview_cargo_free_ready()) {').replace(call,'floorThreeSurvey(n);')
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise ValueError('Fixture output must be fresh')
    output.write_text(raw)
    return output


def validate(log, party, *, boundary_token=None, goals=GOALS):
    party=restore_party(party)
    if any(s in log for s in ('FAIL ','P2_POD_RECEIPT','P2_TREASURE_DELIVERED','P2_VIOLET_')):
        raise ValueError('Native failure or unexpected action')
    native_entries=re.findall(r'^P2_BEASTS_ENTRY_READY floor=3 token=([0-9a-f]{64}) descent=disabled$',log,re.M)
    verified=re.findall(r'^P2_FLOOR3_BOUNDARY_VERIFIED token=([0-9a-f]{64}) descent=disabled$',log,re.M)
    if boundary_token is not None:
        if not isinstance(boundary_token,str) or not re.fullmatch('[0-9a-f]{64}',boundary_token):raise ValueError('Invalid expected boundary')
        if native_entries!=[boundary_token] or verified!=[boundary_token] or log.count('P2_CAVE_READY floor=3 ')!=1:
            raise ValueError('Native floor3 boundary binding differs')
        if re.findall(r'^P2_CAVE_READY floor=(\d+) ',log,re.M)!=['3'] or not log.index('P2_BEASTS_ENTRY_READY')<log.index('P2_FLOOR3_BOUNDARY_VERIFIED')<log.index('P2_FLOOR3_SURVEY_READY'):
            raise ValueError('Native entry phases differ')
        if 'P2_CAVE_TRANSFER' in log:raise ValueError('Unexpected floor4 handoff')
    elif native_entries or verified:raise ValueError('Unexpected native boundary')
    if len(native_entries)!=sum(l.startswith('P2_BEASTS_ENTRY_READY') for l in log.splitlines()) or len(verified)!=sum(l.startswith('P2_FLOOR3_BOUNDARY_VERIFIED') for l in log.splitlines()):
        raise ValueError('Malformed native entry evidence')
    if log.count('P2_ROOM_CARGO_FREE_READY cargo=0')!=1 or log.count('PASS P2_FLOOR3_SURVEY goals=12 cargo=0 pokos=0 repairs_unchanged=1')!=1:
        raise ValueError('Missing survey readiness or completion')
    points=re.findall(r'^P2_FLOOR3_POINT index=(\d+) x=([-\d.]+) y=([-\d.]+) z=([-\d.]+) ground=([-\d.]+)$',log,re.M)
    if len(points)!=len(goals) or sum(l.startswith('P2_FLOOR3_POINT') for l in log.splitlines())!=len(points):
        raise ValueError('Malformed survey points')
    for expected,(index,x,y,z,ground) in enumerate(points):
        x,y,z,ground=map(float,(x,y,z,ground))
        if int(index)!=expected or math.hypot(x-goals[expected][0],z-goals[expected][1])>20 or abs(y-ground)>5:
            raise ValueError('Survey point is unordered, distant or ungrounded')
    from experimental.pikmin2_beasts_party_snapshot import party_snapshot
    from collections import Counter
    counts=Counter(p['species'] for p in party['squad'])
    if log.count('P2_FLOOR3_SURVEY_READY')!=1 or not log.index('P2_FLOOR3_SURVEY_READY')<log.index('P2_FLOOR3_POINT index=0')<log.index('P2_FLOOR3_POINT index=11')<log.index('P2_BEASTS_PARTY health='):
        raise ValueError('Survey phases out of order')
    # Reuse the strict survivor parser after mapping our already-checked phase markers.
    mapped=log.replace('P2_FLOOR3_SURVEY_READY',f'P2_BEASTS_READY reds={counts["red"]} flowers=0 cargo=0').replace('PASS P2_FLOOR3_SURVEY','PASS P2_BEASTS_SURVEY')
    actual=party_snapshot(mapped,dict(red=counts['red'],purple=counts['purple'],sprouts=0),restored=True)
    if actual['squad']!=party['squad'] or not math.isclose(actual['health'],party['health'],rel_tol=1e-6):
        raise ValueError('Native party changed')
    return dict(points=len(points),party=actual)


def run(exe, directory, timeout=120):
    if (directory/'native.log').exists() or (directory/'acceptance.json').exists():
        raise ValueError('Survey run must be fresh')
    report=json.loads((directory/'survey.json').read_bytes())
    paths=report['input_sha256'];paths['survey.json']=sha((directory/'survey.json').read_bytes())
    executable_hash=sha(exe.read_bytes())
    for name,digest in paths.items():
        if sha((directory/name).read_bytes())!=digest:raise ValueError('Stage changed before launch')
    env=dict(os.environ,SDL_AUDIODRIVER='dummy',PATH='C:/msys64/mingw64/bin'+os.pathsep+os.environ.get('PATH',''))
    evidence=dict(schema=1,issue=317 if report.get('boundary_token') else 311,passed=False,exe=str(exe),executable_sha256=executable_hash,input_sha256=paths)
    if report.get('boundary_token'):evidence.update(native_floor=3,native_profile='forest_1',boundary_token=report['boundary_token'])
    with (directory/'native.log').open('w') as log:
        try:evidence['returncode']=subprocess.run([str(exe),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:evidence['timeout']=True
    try:
        if evidence.get('returncode')!=0:raise ValueError('Native process failed or timed out')
        log_text=(directory/'native.log').read_text(errors='replace')
        if report['floor'] in (4,5):
            if 'P2_FLOOR3' in log_text or report.get('boundary_token'):raise ValueError('Wrong engineering survey profile')
            log_text=log_text.replace(f'P2_FLOOR{report["floor"]}','P2_FLOOR3')
            evidence['issue']=330 if report['floor']==4 else 333
        evidence['survey']=validate(log_text,report['party'],boundary_token=report.get('boundary_token'),goals=report['goals'])
        if (directory/'p2-cave-transfer.txt').exists() or (directory/'p2-cave-transfer.tmp').exists():raise ValueError('Unexpected floor transfer file')
        if any(sha((directory/name).read_bytes())!=digest for name,digest in paths.items()) or sha(exe.read_bytes())!=executable_hash:
            raise ValueError('Inputs or executable changed')
        evidence['passed']=True
    except ValueError as error:evidence['error']=str(error)
    (directory/'acceptance.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if not evidence['passed']:raise ValueError(evidence['error'])
    return evidence


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    f=sub.add_parser('fixture');f.add_argument('--source',type=Path,required=True);f.add_argument('--output',type=Path,required=True)
    s=sub.add_parser('stage')
    for name in ('assets','assembly','purple','pod','output','party'):s.add_argument('--'+name,type=Path,required=True)
    r=sub.add_parser('run');r.add_argument('--exe',type=Path,required=True);r.add_argument('--stage',type=Path,required=True)
    a=p.parse_args()
    if a.command=='fixture':print(fixture(a.source,a.output))
    elif a.command=='stage':print(stage(a.assets.resolve(),a.assembly.resolve(),a.purple.resolve(),a.pod.resolve(),a.output,json.loads(a.party.read_bytes())))
    else:
        result=run(a.exe.resolve(),a.stage.resolve())
        print(json.dumps(dict(passed=result['passed'],stage=str(a.stage),executable_sha256=result['executable_sha256'])))
