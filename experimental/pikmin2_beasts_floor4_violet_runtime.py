"""Single source-slot Violet native proxy survey, without campaign mutations."""
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess

from experimental.pikmin2_beasts_floor4_entry import stage_profile
from experimental.pikmin2_beasts_floor4 import fixture as walking_fixture
from experimental.pikmin2_beasts_floor3_runtime import sha
from experimental.pikmin2_beasts_floor2_runtime import conversion_witnesses
from experimental.pikmin2_beasts_party_snapshot import party_snapshot
from experimental.pikmin2_generator_pose import write_position,validate_position
from experimental.pikmin2_collision import ground_height
from scripts.preview_pikmin2_room import records

IDENTITY='forest_1:floor4:BlackPom:0'
POSITION=[295.,0.,-875.]
APPROACH=[(0,-550),(0,-640),(0,-720),(0,-830),(10,-950),(25,-1080),(170,-1190),(315,-1080),(295,-935)]


def audit_approach(collision):
    points=[(0,-425)]+APPROACH;probes=0
    for (ax,az),(bx,bz) in zip(points,points[1:]):
        length=math.hypot(bx-ax,bz-az)
        for step in range(31):
            t=step/30
            for offset in (-10,0,10):
                x=ax+(bx-ax)*t-offset*(bz-az)/length;z=az+(bz-az)*t+offset*(bx-ax)/length
                y=ground_height(collision['vertices'],collision['triangles'],x,z)
                if y is None or not math.isfinite(y):raise ValueError('Unsupported engineering captain approach')
                probes+=1
    return dict(probes=probes,width=20,source_routes_modified=False,engineering_captain_steering=True)


def validate_plan(plan,assembly_hash):
    if plan.get('policy')!='P2_BEASTS_FLOOR4_VIOLET_PLAN_1' or plan.get('cave')!='forest_1' or plan.get('floor')!=4 or plan.get('assembly_sha256')!=assembly_hash:
        raise ValueError('Wrong source plan or assembly binding')
    f=plan['flower'];g=plan['generation_context'];population=g['global_plus_cave_purple']
    if type(population) is not int or not 0<=population<=2147483647:raise ValueError('Invalid declared population')
    if (f['identity'],f['generator_id'],f['instance'],f['unit'],f['source_slot'],f['source']['type'],f['position'])!=(IDENTITY,62002,2,'room_north3_1_tsuchi',0,8,POSITION):
        raise ValueError('Unsupported source flower candidate')
    if plan['slots_per_flower']!=5 or g['spawned_generators']!=[62002] or g['conversion_budgets']!={IDENTITY:5} or g['suppression_applies'] is not False or g['native_global_population_verified'] is not False:
        raise ValueError('Wrong source generation budget or population claim')
    return f


def stage(assets,assembly,purple,pod,output,plan_path,token):
    raw=plan_path.read_bytes();plan=json.loads(raw);flower=validate_plan(plan,sha((assembly/'assembly.json').read_bytes()))
    approach=audit_approach(json.loads((assembly/'collision.json').read_bytes()))
    party=dict(health=1.,squad=[dict(species='red',maturity=0) for _ in range(20)])
    directory=stage_profile(assets,assembly,purple,pod,output,party,token)
    path=directory/'assets/dataDir/stages/chal0/default.gen';actors=bytearray(path.read_bytes())
    templates=[r for r in records(assets/'dataDir/stages/chal0/default.gen') if r[72:80]==b'ssob\x02\0\0\0']
    if not templates:raise ValueError('Missing native Pom template')
    record=bytearray(templates[0]);struct.pack_into('<I',record,8,62002)
    record[16:48]=b'preview violet floor4'.ljust(32,b'\0');write_position(record,flower['position']);struct.pack_into('>I',record,80,69)
    if struct.unpack_from('>I',actors,20)[0]!=22:raise ValueError('Unexpected base actors')
    struct.pack_into('>I',actors,20,23);actors.extend(record);validate_position(record,POSITION)
    path.write_bytes(actors);(directory/'violet.json').write_bytes(raw)
    report=json.loads((directory/'survey.json').read_bytes())
    report.update(policy='P2_BEASTS_FLOOR4_VIOLET_SURVEY_1',source_plan_sha256=sha(raw),generation_context=plan['generation_context'],flower=flower,source_yaw_applied=False,approach_audit=approach)
    report['input_sha256'].update({'assets/dataDir/stages/chal0/default.gen':sha(actors),'violet.json':sha(raw)})
    report['limitations'].append('One existing P1 Pom Violet proxy, not source P2 Pom FSM/model parity; five throws and native pluck actions are scripted.')
    (directory/'survey.json').write_text(json.dumps(report,indent=2)+'\n')
    return directory


def fixture(source,output):
    walking_fixture(source,output);raw=output.read_text();marker='class RoomApp : public PlugPikiApp {'
    if raw.count(marker)!=1 or raw.count('floorThreeSurvey(n);')!=1:raise ValueError('External survey anchors changed')
    helper=Path(__file__).with_name('pikmin2_beasts_floor4_violet_survey.inc').read_text()
    output.write_text(raw.replace(marker,helper+'\n'+marker).replace('floorThreeSurvey(n);','floorFourViolet(n);'))
    return output


def validate(log,token):
    if not re.fullmatch('[0-9a-f]{64}',token):raise ValueError('Invalid expected token')
    if any(x in log for x in ('FAIL ','P2_CAVE_TRANSFER','P2_BEASTS_FAILURE','P2_POD_RECEIPT','P2_TREASURE_DELIVERED')):raise ValueError('Unexpected failure, transfer or reward')
    markers=['P2_CAVE_READY floor=4 survivors=20 health=1',f'P2_BEASTS_ENTRY_READY floor=4 token={token} descent=disabled',f'P2_FLOOR4_VIOLET_BOUNDARY token={token} descent=disabled',
        'P2_BEASTS_READY reds=20 flowers=1 cargo=0','P2_FLOOR4_VIOLET_SPROUTS reds=15 purple=0 sprouts=5','P2_BEASTS_CAPTAIN_PLUCK purple=1',
        'PASS P2_BEASTS_FLOOR4_VIOLET reds=15 purple=5 sprouts=0 cargo=0 pokos=0 repairs_unchanged=1']
    for line in markers:
        prefix='PASS P2_BEASTS_' if line.startswith('PASS ') else line.split(' ')[0]+' '
        if [value for value in log.splitlines() if value.startswith(prefix)]!=[line]:raise ValueError('Missing or conflicting native phase')
    if [log.index(x) for x in markers]!=sorted(log.index(x) for x in markers):raise ValueError('Native phases reordered')
    flowers=re.findall(r'^P2_FLOOR4_VIOLET_FLOWER generator=(\d+) x=([^ ]+) y=([^ ]+) z=([^ ]+) live_x=([^ ]+) live_y=([^ ]+) live_z=([^ ]+) ground=([^\n]+)$',log,re.M)
    if len(flowers)!=1 or flowers[0][0]!='62002':raise ValueError('Native flower identity differs')
    values=list(map(float,flowers[0][1:]))
    if any(not math.isfinite(x) for x in values) or any(abs(a-b)>.1 for a,b in zip(values,POSITION+POSITION+[0.])):raise ValueError('Native flower position differs')
    points=re.findall(r'^P2_FLOOR4_VIOLET_POINT index=(\d+) x=([^ ]+) y=([^ ]+) z=([^ ]+) ground=([^\n]+)$',log,re.M)
    if len(points)!=len(APPROACH):raise ValueError('Missing grounded approach')
    for index,((i,x,y,z,g),(gx,gz)) in enumerate(zip(points,APPROACH)):
        x,y,z,g=map(float,(x,y,z,g))
        if int(i)!=index or not all(map(math.isfinite,(x,y,z,g))) or math.hypot(x-gx,z-gz)>20 or abs(y-g)>=5:raise ValueError('Wrong native approach point')
    throws=re.findall(r'^P2_FLOOR4_VIOLET_THROW original=(\d+) generator=(\d+)$',log,re.M)
    if set(throws)!={(str(i),'62002') for i in range(5)}:raise ValueError('Native throws differ')
    if sum(line.startswith('P2_FLOOR4_VIOLET_THROW') for line in log.splitlines())!=len(throws):raise ValueError('Malformed throw evidence')
    if not log.rindex('P2_FLOOR4_VIOLET_POINT')<log.index('P2_FLOOR4_VIOLET_THROW')<log.rindex('P2_FLOOR4_VIOLET_THROW')<log.index('P2_FLOOR4_VIOLET_SPROUTS'):raise ValueError('Throws outside conversion phase')
    witnesses=conversion_witnesses(log.replace('P2_FLOOR4_VIOLET_SPROUTS','P2_BEASTS_SPROUTS'),[62002])
    party=party_snapshot(log,dict(red=15,purple=5,sprouts=0))
    if party['health']!=1. or any(p['maturity']!=0 for p in party['squad']):raise ValueError('Final party health/maturity differs')
    return dict(party=party,witnesses=witnesses,approach_points=len(APPROACH))


def run(exe,directory,timeout=180):
    if (directory/'native.log').exists() or (directory/'acceptance.json').exists():raise ValueError('Fresh run required')
    report=json.loads((directory/'survey.json').read_bytes())
    if report['policy']!='P2_BEASTS_FLOOR4_VIOLET_SURVEY_1':raise ValueError('Wrong survey policy')
    paths=dict(report['input_sha256']);paths['survey.json']=sha((directory/'survey.json').read_bytes())
    executable_hash=sha(exe.read_bytes())
    if any(sha((directory/n).read_bytes())!=h for n,h in paths.items()):raise ValueError('Stage changed before run')
    evidence=dict(issue=338,passed=False,executable_sha256=executable_hash,input_sha256=paths,source_plan_sha256=report['source_plan_sha256'])
    env=dict(os.environ,SDL_AUDIODRIVER='dummy',PATH='C:/msys64/mingw64/bin'+os.pathsep+os.environ.get('PATH',''))
    with (directory/'native.log').open('w') as log:
        try:evidence['returncode']=subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:evidence['timeout']=True
    evidence['log_sha256']=sha((directory/'native.log').read_bytes())
    try:
        if evidence.get('returncode')!=0:raise ValueError('Native run failed or timed out')
        evidence['native']=validate((directory/'native.log').read_text(errors='replace'),report['boundary_token'])
        if any((directory/n).exists() for n in ('p2-cave-transfer.txt','p2-cave-transfer.tmp')):raise ValueError('Unexpected transfer file')
        if any(sha((directory/n).read_bytes())!=h for n,h in paths.items()) or sha(exe.read_bytes())!=executable_hash:raise ValueError('Inputs/executable changed')
        evidence['passed']=True
    except ValueError as error:evidence['error']=str(error)
    (directory/'acceptance.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if not evidence['passed']:raise ValueError(evidence['error'])
    return evidence
