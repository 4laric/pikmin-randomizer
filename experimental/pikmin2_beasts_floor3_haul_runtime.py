"""Source-plan-bound engineering pellet haul, without campaign authorization."""
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
from experimental.pikmin2_beasts_floor3_runtime import stage as base_stage,fixture as base_fixture,sha
from experimental.pikmin2_beasts_floor3_entry import entry_text
from experimental.pikmin2_generator_pose import write_position
from scripts.preview_pikmin2_room import generator

INSTANCE='forest_1:floor3:treasure:dia_c_green:0'
LEDGER=f'P2_ECONOMY_1\ntreasure:{INSTANCE} 150\n'.encode()
RECEIPT=f'treasure={INSTANCE} count=1 pokos=150\r\n'.encode()  # Native Windows text-mode receipt.


def validate_plan(plan,assembly_hash,package_hash,model_hash):
    if (plan.get('policy'),plan.get('cave'),plan.get('floor'))!=('P2_BEASTS_FLOOR3_HAUL_PLAN_1','forest_1',3):raise ValueError('Wrong haul plan')
    if plan['assembly_sha256']!=assembly_hash or plan['treasure_package_sha256']!=package_hash:raise ValueError('Plan source package mismatch')
    c=plan['cargo']
    if (c['instance'],c['model'],c['source_row'],c['source_slot'],c['source_unit'],c['position'],c['value'],c['weight'],c['slots'],c['model_sha256'])!=(INSTANCE,'dia_c_green',1,0,'room_north_1_hiba_tsuchi',[-85,0,-960],150,12,20,model_hash):raise ValueError('Unsupported source cargo')
    if plan['pod']!=[-85,0,-280] or plan['route']['waypoint_ids']!=[9,8,7,0] or plan['campaign_reward_authorized'] is not False:raise ValueError('Wrong route/Pod or authorization claim')
    return c


def stage(assets,assembly,purple,pod,package,plan_path,output,token,*,replay_ledger=None):
    party=dict(health=1.,squad=[dict(species='red',maturity=0) for _ in range(20)])
    entry=entry_text(party,token).encode()
    assembly_metadata=json.loads((assembly/'assembly.json').read_bytes())
    if not all(center in [s['center'] for s in assembly_metadata['seam_audit']] for center in ([-85,0,-510],[-85,0,-340])):raise ValueError('Expected source assembly seams')
    plan_raw=plan_path.read_bytes();plan=json.loads(plan_raw);package_raw=(package/'floor3.json').read_bytes()
    model=(package/'treasures/dia_c_green/treasure.mod').read_bytes()
    validate_plan(plan,sha((assembly/'assembly.json').read_bytes()),sha(package_raw),sha(model))
    if replay_ledger is not None and replay_ledger.read_bytes()!=LEDGER:raise ValueError('Replay requires exact one-receipt ledger')
    directory=base_stage(assets,assembly,purple,pod,output,party,anchor_positions=dict(start=(-85,-850),pod=(-85,-280),ship=(85,240)))
    actors_path=directory/'assets/dataDir/stages/chal0/default.gen';actors=bytearray(actors_path.read_bytes())
    raw=generator(assets);starts=[m.start() for m in re.finditer(b'    0.0v',raw)]+[len(raw)]
    templates=[raw[a:b] for a,b in zip(starts,starts[1:]) if raw[a+16:a+48].rstrip(b'\0')==b'preview treasure bolt']
    if len(templates)!=1 or struct.unpack_from('>I',actors,20)[0]!=22:raise ValueError('Cargo generator framing changed')
    row=bytearray(templates[0]);struct.pack_into('<I',row,8,63000);row[16:48]=b'preview floor3 dia green'.ljust(32,b'\0');write_position(row,[-85,0,-960])
    struct.pack_into('>I',actors,20,23);actors.extend(row)
    overrides={'assets/dataDir/stages/chal0/default.gen':bytes(actors),'assets/dataDir/courses/pikmin2room/dia_c_green.mod':model,
        'p2-cargo.txt':f'P2_CARGO_1\n1\n63000 {INSTANCE} dia_c_green 150 12 20\n'.encode(),
        'p2-pod.txt':b'P2_POD_1\ndia_c_green 150 12 20\nKochappy 0\n','p2-cave-entry.txt':entry,
        'p2-floor3-boundary.txt':(token+'\n').encode(),'haul.json':plan_raw,'source-floor3.json':package_raw}
    report=json.loads((directory/'survey.json').read_bytes())
    (directory/'p2-cargo-free.txt').unlink();del report['input_sha256']['p2-cargo-free.txt']
    for name,data in overrides.items():(directory/name).write_bytes(data)
    if replay_ledger is not None:(directory/'p2-economy.txt').write_bytes(LEDGER)
    report.update(policy='P2_BEASTS_FLOOR3_HAUL_SURVEY_1',boundary_token=token,token_source='caller_declared_diagnostic',
        party_restore_protocol_floor=3,native_profile='forest_1',source_plan_sha256=sha(plan_raw),replay=replay_ledger is not None,
        initial_economy_sha256=sha(LEDGER) if replay_ledger is not None else None,descent_enabled=False)
    report['input_sha256'].update({name:sha(data) for name,data in overrides.items()})
    report['limitations']=['One source-slot treasure with real pellet transport and Pod economy; no campaign reward authorization.',
        'Engineering captain/party spawn near cargo and scripted Transport actions; no actor position forcing during runtime.',
        'Beasts lifecycle remains inactive with cargo enabled; floor3 diagnostic restore/readback only.',
        'Other treasure, hazards and actors omitted; no floor4 descent or full floor3 gameplay claim.']
    (directory/'survey.json').write_text(json.dumps(report,indent=2)+'\n');return directory


def fixture(source,output):
    base_fixture(source,output);raw=output.read_text();marker='class RoomApp : public PlugPikiApp {'
    anchors=(marker,'floorThreeSurvey(n);','if(pc_p2_preview_cargo_free_ready())')
    if any(raw.count(x)!=1 for x in anchors):raise ValueError('Haul fixture anchors changed')
    helper=Path(__file__).with_name('pikmin2_beasts_floor3_haul_survey.inc').read_text()
    output.write_text(raw.replace(marker,helper+'\n'+marker).replace(anchors[1],'floorThreeHaul(n);').replace(anchors[2],'if(pc_p2_preview_ready())'))
    return output


def validate(log,token,receipt,ledger,*,replay=False):
    if receipt!=RECEIPT or ledger!=LEDGER:raise ValueError('Wrong exact native receipt/ledger')
    if not re.fullmatch('[0-9a-f]{64}',token):raise ValueError('Wrong diagnostic token')
    if any(x in log for x in ('FAIL ','P2_CAVE_TRANSFER','P2_BEASTS_FAILURE','P2_VIOLET_','P2_TREASURE_DELIVERED')):raise ValueError('Unexpected failure/reward/transfer')
    markers=[f'P2_BEASTS_ENTRY_READY floor=3 token={token} descent=disabled',
        f'P2_FLOOR3_HAUL_READY token={token} generator=63000 value=150 weight=12 slots=20 initial_pokos={150 if replay else 0} x=-85.000 y=0.000 z=-960.000',
        'P2_FLOOR3_HAUL_ASSIGNED carriers=20 native_transport=1 positions_unchanged=1',
        'P2_FLOOR3_HAUL_SEAM north','P2_FLOOR3_HAUL_SEAM south',
        'PASS P2_FLOOR3_HAUL cargo=1 value=150 seeds=0 repairs_unchanged=1 descent=disabled']
    for line in markers:
        if log.splitlines().count(line)!=1:raise ValueError('Missing or duplicate native phase')
    if [line for line in log.splitlines() if line.startswith('P2_BEASTS_ENTRY_READY ')]!=[markers[0]]:raise ValueError('Conflicting native profile')
    if [line for line in log.splitlines() if line.startswith('P2_CAVE_READY ')]!=['P2_CAVE_READY floor=3 survivors=20 health=1']:raise ValueError('Wrong restored native party')
    if [log.index(x) for x in markers]!=sorted(log.index(x) for x in markers):raise ValueError('Native hauling phases reordered')
    receipts=re.findall(r'P2_POD_RECEIPT id=([^ ]+) value=(\d+) new=(\d+) pokos=(\d+) seeds=(\d+)',log)
    expected=[('treasure:'+INSTANCE,'150',str(0 if replay else 1),'150','0'),('treasure:'+INSTANCE,'150','0','150','0')]
    if receipts!=expected or log.count('P2_POD_RECEIPT')!=2:raise ValueError('Unexpected Pod receipts or duplicate credit')
    delivered=re.findall(r'^P2_FLOOR3_HAUL_DELIVERED max_attached=(\d+) seams=2 duplicate_credit=0 reopened_receipts=1 pokos=150 repairs_unchanged=1$',log,re.M)
    if len(delivered)!=1 or not 12<=int(delivered[0])<=20:raise ValueError('Missing carrier/reopen evidence')
    points=re.findall(r'^P2_FLOOR3_HAUL_POINT x=([^ ]+) y=([^ ]+) z=([^ ]+) attached=(\d+) ground=([^\n]+)$',log,re.M)
    if len(points)<5 or sum(line.startswith('P2_FLOOR3_HAUL_POINT') for line in log.splitlines())!=len(points):raise ValueError('Missing or malformed native hauling trace')
    zs=[]
    for x,y,z,attached,ground in points:
        x,y,z,ground=map(float,(x,y,z,ground))
        if not all(map(math.isfinite,(x,y,z,ground))) or abs(x+85)>70 or not -1100<=z<=-180 or not 0<=int(attached)<=20:raise ValueError('Native cargo left audited corridor')
        zs.append(z)
    if min(zs)>-900 or max(zs)<-340:raise ValueError('Cargo did not traverse room and corridor')
    if not log.index('P2_FLOOR3_HAUL_SEAM south')<log.index('P2_POD_RECEIPT')<log.rindex('P2_POD_RECEIPT')<log.index('P2_FLOOR3_HAUL_DELIVERED')<log.index(markers[-1]):raise ValueError('Delivery phases reordered')
    return dict(value=150,weight=12,slots=20,trace_points=len(points),max_attached=int(delivered[0]),replay=replay)


def run(exe,directory,timeout=240):
    if any((directory/n).exists() for n in ('native.log','acceptance.json','treasure-receipt.txt')):raise ValueError('Fresh haul stage required')
    report=json.loads((directory/'survey.json').read_bytes())
    if report['policy']!='P2_BEASTS_FLOOR3_HAUL_SURVEY_1':raise ValueError('Wrong haul survey')
    economy=directory/'p2-economy.txt'
    if report['replay']:
        if not economy.exists() or economy.read_bytes()!=LEDGER:raise ValueError('Replay economy changed')
    elif economy.exists():raise ValueError('Fresh economy already exists')
    paths=dict(report['input_sha256']);paths['survey.json']=sha((directory/'survey.json').read_bytes());exe_hash=sha(exe.read_bytes())
    if any(sha((directory/n).read_bytes())!=h for n,h in paths.items()):raise ValueError('Input changed before launch')
    result=dict(issue=343,passed=False,executable_sha256=exe_hash,input_sha256=paths,replay=report['replay'])
    env=dict(os.environ,SDL_AUDIODRIVER='dummy',PATH='C:/msys64/mingw64/bin'+os.pathsep+os.environ.get('PATH',''))
    with (directory/'native.log').open('w') as log:
        try:result['returncode']=subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:result['timeout']=True
    result['log_sha256']=sha((directory/'native.log').read_bytes())
    try:
        if result.get('returncode')!=0:raise ValueError('Native haul failed or timed out')
        receipt=(directory/'treasure-receipt.txt').read_bytes();ledger=economy.read_bytes()
        result['native']=validate((directory/'native.log').read_text(errors='replace'),report['boundary_token'],receipt,ledger,replay=report['replay'])
        result.update(receipt_sha256=sha(receipt),economy_sha256=sha(ledger))
        if any((directory/n).exists() for n in ('p2-cave-transfer.txt','p2-cave-transfer.tmp')):raise ValueError('Unexpected floor transfer')
        if any(sha((directory/n).read_bytes())!=h for n,h in paths.items()) or sha(exe.read_bytes())!=exe_hash:raise ValueError('Input/executable changed')
        result['passed']=True
    except (ValueError,OSError) as error:result['error']=str(error)
    (directory/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['passed']:raise ValueError(result['error'])
    return result
