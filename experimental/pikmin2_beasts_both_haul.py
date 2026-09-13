"""Two source treasures sharing native Pod/economy, diagnostic only (#371)."""
import json,math,os,re,struct,subprocess
from pathlib import Path
from experimental import pikmin2_beasts_floor3_haul_runtime as green
from experimental import pikmin2_beasts_floor3_donut_runtime as donut
from experimental.pikmin2_generator_pose import write_position
from scripts.preview_pikmin2_room import generator
from experimental.pikmin2_beasts_floor3_runtime import fixture as base_fixture,sha
LEDGER=green.LEDGER+f'treasure:{donut.INSTANCE} 230\n'.encode()

def stage(assets,assembly,purple,pod,package,green_plan,donut_plan,output,token,*,initial_ledger=None):
    if initial_ledger is not None and initial_ledger.read_bytes()!=green.LEDGER:raise ValueError('Partial restart requires exact green receipt')
    plan=donut_plan.read_bytes();model=(package/'treasures/donutswhite/treasure.mod').read_bytes()
    donut.validate_plan(json.loads(plan),sha((assembly/'assembly.json').read_bytes()),sha((package/'floor3.json').read_bytes()),sha(model))
    d=green.stage(assets,assembly,purple,pod,package,green_plan,output,token,replay_ledger=initial_ledger)
    actors=d/'assets/dataDir/stages/chal0/default.gen';raw=bytearray(actors.read_bytes());template=generator(assets)
    starts=[m.start() for m in re.finditer(b'    0.0v',template)]+[len(template)]
    rows=[template[a:b] for a,b in zip(starts,starts[1:]) if template[a+16:a+48].rstrip(b'\0')==b'preview treasure bolt']
    if len(rows)!=1 or struct.unpack_from('>I',raw,20)[0]!=23:raise ValueError('Cargo template/count changed')
    row=bytearray(rows[0]);struct.pack_into('<I',row,8,63001);row[16:48]=b'preview floor3 donut'.ljust(32,b'\0');write_position(row,[175,20.5,-55]);raw.extend(row);struct.pack_into('>I',raw,20,24)
    changes={'assets/dataDir/stages/chal0/default.gen':bytes(raw),'assets/dataDir/courses/pikmin2room/donutswhite.mod':model,'donut-haul.json':plan,
        'p2-cargo.txt':f'P2_CARGO_1\n2\n63000 {green.INSTANCE} dia_c_green 150 12 20\n63001 {donut.INSTANCE} donutswhite 230 15 25\n'.encode()}
    report=json.loads((d/'survey.json').read_bytes())
    for name,data in changes.items():(d/name).write_bytes(data);report['input_sha256'][name]=sha(data)
    report.update(policy='P2_BEASTS_BOTH_HAUL_1',initial_pokos=150 if initial_ledger else 0,source_donut_plan_sha256=sha(plan))
    report['limitations']=['Two source visual/economy treasures on donor pellet physics; not authentic donut radius50/height5.',
        'Scripted20Red Transport assignment and captain/formation controller approach; no actor teleports or source route edits.',
        'No campaign rewards, native descent, terminal marker, enemies or full floor3 gameplay claim.',
        'Legacy treasure-receipt.txt tracks first preview cargo only; exact native events and two-row economy prove both deliveries.']
    (d/'survey.json').write_text(json.dumps(report,indent=2)+'\n');return d

def fixture(source,output):
    base_fixture(source,output);s=output.read_text()
    for a in ('class RoomApp : public PlugPikiApp {','floorThreeSurvey(n);','if(pc_p2_preview_cargo_free_ready())'):
        if s.count(a)!=1:raise ValueError('Fixture anchor changed')
    helper=Path(__file__).with_name('pikmin2_beasts_both_haul.inc').read_text()
    output.write_text(s.replace('class RoomApp : public PlugPikiApp {',helper+'\nclass RoomApp : public PlugPikiApp {').replace('floorThreeSurvey(n);','bothHaul(n);').replace('if(pc_p2_preview_cargo_free_ready())','if(pc_p2_preview_ready())'));return output

def validate(log,token,initial,ledger,partial):
    if ledger!=LEDGER or partial!=green.LEDGER:raise ValueError('Wrong exact two/one-row economy')
    if initial not in (0,150) or not re.fullmatch('[0-9a-f]{64}',token):raise ValueError('Wrong initial/token')
    if any(x in log for x in ('FAIL ','P2_CAVE_TRANSFER','P2_BEASTS_FAILURE')):raise ValueError('Native failure/transfer')
    markers=[f'P2_BEASTS_ENTRY_READY floor=3 token={token} descent=disabled','P2_BOTH_READY cargo=2 configs_distinct=1 survivors=20',
        'P2_BOTH_DELIVERED index=0 total=150 duplicate_credit=0','P2_BOTH_APPROACH goals=5 survivors=20',
        'P2_BOTH_DELIVERED index=1 total=380 duplicate_credit=0','PASS P2_BOTH_HAUL cargo=2 pokos=380 receipts=2 repairs_unchanged=1 descent=disabled']
    if any(log.splitlines().count(x)!=1 for x in markers) or [log.index(x) for x in markers]!=sorted(log.index(x) for x in markers):raise ValueError('Missing/duplicate/reordered native phases')
    if [x for x in log.splitlines() if x.startswith('P2_CAVE_READY ')]!=['P2_CAVE_READY floor=3 survivors=20 health=1']:raise ValueError('Wrong restored party')
    events=re.findall(r'P2_POD_RECEIPT id=([^ ]+) value=(\d+) new=(\d+) pokos=(\d+) seeds=(\d+)',log)
    if log.count('P2_POD_RECEIPT')!=2:raise ValueError('Extra/malformed Pod receipt')
    if events!=[('treasure:'+green.INSTANCE,'150',str(int(initial==0)),'150','0'),('treasure:'+donut.INSTANCE,'230','1','380','0')]:raise ValueError('Wrong distinct native receipts')
    event_positions=[m.start() for m in re.finditer('P2_POD_RECEIPT',log)]
    if not log.index(markers[1])<event_positions[0]<log.index(markers[2])<log.index(markers[3])<event_positions[1]<log.index(markers[4]):raise ValueError('Receipt phase mismatch')
    walks=re.findall(r'^P2_BOTH_WALK goal=(\d+) x=([^ ]+) y=([^ ]+) z=([^\n]+)$',log,re.M)
    if [int(w[0]) for w in walks]!=list(range(5)) or any(not all(math.isfinite(float(v)) for v in w[1:]) for w in walks):raise ValueError('Missing native approach goals')
    allpoints=re.findall(r'^P2_BOTH_POINT index=([01]) x=([^ ]+) y=([^ ]+) z=([^ ]+) attached=(\d+)$',log,re.M)
    if len(allpoints)!=sum(x.startswith('P2_BOTH_POINT') for x in log.splitlines()):raise ValueError('Malformed cargo trace')
    traces={}
    for i,weight in ((0,12),(1,15)):
        points=re.findall(rf'^P2_BOTH_POINT index={i} x=([^ ]+) y=([^ ]+) z=([^ ]+) attached=(\d+)$',log,re.M)
        if len(points)<5 or max(int(p[3]) for p in points)<weight:raise ValueError('Missing actual carrier trace')
        if any(not all(math.isfinite(float(v)) for v in p[:3]) or not 0<=int(p[3])<=20 for p in points):raise ValueError('Bad trace')
        traces[str(i)]=dict(points=len(points),peak_attached=max(int(p[3]) for p in points))
        coords=[(float(p[0]),float(p[2])) for p in points]
        if i==0 and not(any(z<-900 for x,z in coords) and any(z>=-340 for x,z in coords)):raise ValueError('Green missing source/seams')
        if i==1 and not(any(x>120 and z>-100 for x,z in coords) and any(x<0 and z<-200 for x,z in coords)):raise ValueError('Donut missing blockroom route')
    return dict(total=380,receipts=2,initial=initial,traces=traces)

def run(exe,d,timeout=360):
    report=json.loads((d/'survey.json').read_bytes());paths=dict(report['input_sha256']);paths['survey.json']=sha((d/'survey.json').read_bytes());eh=sha(exe.read_bytes())
    if report['policy']!='P2_BEASTS_BOTH_HAUL_1' or any((d/n).exists() for n in ('native.log','acceptance.json','treasure-receipt.txt')):raise ValueError('Fresh both stage required')
    if any(sha((d/n).read_bytes())!=h for n,h in paths.items()):raise ValueError('Changed input')
    if report['initial_pokos']==150:
        if (d/'p2-economy.txt').read_bytes()!=green.LEDGER:raise ValueError('Changed partial ledger')
    elif (d/'p2-economy.txt').exists():raise ValueError('Unexpected initial ledger')
    result=dict(issue=371,passed=False,input_sha256=paths,executable_sha256=eh)
    env=dict(os.environ,SDL_AUDIODRIVER='dummy',PATH='C:/msys64/mingw64/bin'+os.pathsep+os.environ.get('PATH',''))
    with (d/'native.log').open('w') as out:
        try:result['returncode']=subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=d,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:result['timeout']=True
    result['log_sha256']=sha((d/'native.log').read_bytes())
    try:
        if result.get('returncode')!=0:raise ValueError('Native both haul failed/timed out')
        result['native']=validate((d/'native.log').read_text(errors='replace'),report['boundary_token'],report['initial_pokos'],(d/'p2-economy.txt').read_bytes(),(d/'partial-economy.txt').read_bytes())
        if any(sha((d/n).read_bytes())!=h for n,h in paths.items()) or sha(exe.read_bytes())!=eh:raise ValueError('Changed input/executable')
        if any((d/n).exists() for n in ('p2-cave-transfer.txt','p2-cave-transfer.tmp','p2-beasts-cargo-terminal.txt')):raise ValueError('Unexpected terminal/transfer')
        result.update(passed=True,economy_sha256=sha((d/'p2-economy.txt').read_bytes()),partial_sha256=sha((d/'partial-economy.txt').read_bytes()))
    except (ValueError,OSError) as e:result['error']=str(e)
    (d/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['passed']:raise ValueError(result['error'])
    return result
