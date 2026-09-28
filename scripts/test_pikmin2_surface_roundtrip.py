"""Actual fixture processes: bounded source entrance -> cave -> bounded entrance."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import struct
import uuid

from experimental import pikmin2_campaign as cave
from experimental.pikmin2_surface_ledger import SurfaceLedger
from experimental.pikmin2_surface_runner import NativeContent,SurfaceRunner
from scripts.stage_pikmin2_entrance import prepare as stage_boundary
from scripts.preview_pikmin2_room import records,replace_embedded_routes
from experimental.pikmin2_collision import route_ini
from scripts.test_pikmin2_surface_native import FixtureProcess,executable_identity,expected_receipts


def stage_surface(args,snapshot,content,mode):
    run=stage_boundary(args.assets,args.source_import,args.pocket,args.treasure,args.output/'surfaces')
    path=run/'assets/dataDir/stages/chal0/default.gen'
    data=path.read_bytes();starts=[m.start() for m in re.finditer(b'    0.0v',data)]+[len(data)]
    rows=[];count=0
    for a,b in zip(starts,starts[1:]):
        row=bytearray(data[a:b])
        if row[16:48].rstrip(b'\0')==b'preview red pikmin':
            if count>=len(snapshot['squad']):continue
            count+=1
        rows.append(row)
    if count!=len(snapshot['squad']):raise ValueError('Surface fixture supports at most20 survivors')
    # Existing checkpoint writer requires a Pod even when an anchor is configured.
    # Keep this receiver inside the sealed pocket; custom fixture forbids hauling.
    goal=bytearray(records(args.assets/'dataDir/stages/practice/default.gen')[1])
    goal[16:48]=b'fixture remote Pod'.ljust(32,b'\0');struct.pack_into('>3f',goal,48,-190,80,1190)
    struct.pack_into('>I',goal,8,9000);rows.append(goal)
    position=snapshot['position']
    path.write_bytes(b'1.0v'+struct.pack('>4fI',*position,0,len(rows))+b''.join(rows))
    stage=run/'assets/dataDir/stages/chal0.ini'
    stage.write_bytes(re.sub(rb'(?m)^navi_start[^\r\n]*',f'navi_start {position[0]} {position[2]}'.encode(),stage.read_bytes()))
    modeldir=run/'assets/dataDir/courses/pikmin2room'
    route=route_ini([dict(id=0,position=[-190,80,1190],radius=20,links=[])]).encode()
    (modeldir/'room.mod').write_bytes(replace_embedded_routes((modeldir/'room.mod').read_bytes(),route))
    (modeldir/'room.ini').write_bytes(route)
    for name in ('pod.mod','treasure.mod'):(modeldir/name).write_bytes((args.pod1/name).read_bytes())
    for model in args.purple.glob('*.mod'):(modeldir/model.name).write_bytes(model.read_bytes())
    (run/'p2-pod.txt').write_bytes((args.pod1/'p2-pod.txt').read_bytes())
    (run/'p2-purple.txt').write_bytes((args.purple/'p2-purple.txt').read_bytes())
    state=cave.initial(content);state.update({k:snapshot[k] for k in ('squad','health','receipts')})
    token=uuid.uuid4().hex
    (run/'p2-cave-entry.txt').write_text(cave.entry_text(state,token))
    (run/'p2-cave-transition.txt').write_text('P2_CAVE_TRANSITION_1\nhole -190 80 1160 30\n')
    (run/'p2-economy.txt').write_text(cave.ledger_text(snapshot['receipts']))
    (run/'surface-fixture.txt').write_text(mode+' '+' '.join(map(str,position))+f' {sum(snapshot["receipts"].values())}\n')
    return run,state,token


def native_position(run,token):
    lines=(run/'surface-position.txt').read_text().splitlines()
    if len(lines)!=2 or lines[0]!=token:raise ValueError('Stale/incomplete surface position')
    result=list(map(float,lines[1].split()))
    if len(result)!=3 or not all(math.isfinite(v) for v in result):raise ValueError('Invalid surface position')
    if (result[0]+190)**2+(result[2]-1160)**2>60**2 or abs(result[1]-80)>1:
        raise ValueError('Surface transfer outside validated source pocket')
    return result


def run_test(args):
    args.output.mkdir(parents=True,exist_ok=False)
    provenance=dict(surface=executable_identity(args.surface_exe),cave=executable_identity(args.cave_exe))
    (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2))
    content=NativeContent(args.assets,args.imported,[args.pod1,args.pod2],args.purple,args.treasure,
                          args.transitions,args.snow,args.roster,args.transition_assets)
    seed_snapshot=dict(region='valley_of_repose',day=2,time=8.5,position=[-210.,80.,1160.],
                       squad=[dict(species='red',maturity=0) for _ in range(20)],health=1.,receipts={})
    surface_process=FixtureProcess(args.timeout)
    entrance,state,token=stage_surface(args,seed_snapshot,content.identity,'enter')
    with (entrance/'native.log').open('w') as log:
        result=surface_process([str(args.surface_exe),'--experimental-pikmin2-room'],cwd=entrance,stdout=log,stderr=-2)
    if result.returncode!=42:raise RuntimeError(f'Surface entry exit {result.returncode}; {entrance}')
    handed=cave.transition(state,token,(entrance/'p2-cave-transfer.txt').read_text(),cave.read_ledger(entrance/'p2-economy.txt'),{})
    snapshot=dict(seed_snapshot,position=native_position(entrance,token))
    snapshot.update({k:handed[k] for k in ('squad','health','receipts')})
    ledger=SurfaceLedger(args.output/'session',content.identity,uuid.uuid4().hex)
    ledger.create(snapshot);ledger.enter_cave(0,uuid.uuid4().hex)
    cave_process=FixtureProcess(args.timeout)
    final=SurfaceRunner(ledger,content,args.cave_exe,cave_process).resume()
    assert final['phase']=='surface' and final['surface']['receipts']==expected_receipts(args.roster)
    returned=final['surface'];assert returned['position']==snapshot['position']
    assert Counter(p['species'] for p in returned['squad'])=={'red':9,'purple':10}
    destination,_,return_token=stage_surface(args,returned,content.identity,'return')
    with (destination/'native.log').open('w') as log:
        result=surface_process([str(args.surface_exe),'--experimental-pikmin2-room'],cwd=destination,stdout=log,stderr=-2)
    if result.returncode!=0:raise RuntimeError(f'Surface return exit {result.returncode}; {destination}')
    restored_position=native_position(destination,return_token)
    position_drift=math.dist(restored_position,snapshot['position'])
    assert position_drift<1., 'Native settled more than one unit from restored source position'
    assert 'PASS P2_SURFACE_RETURN' in (destination/'native.log').read_text(errors='replace')
    assert cave.read_ledger(destination/'p2-economy.txt')==returned['receipts']
    before=len(cave_process.runs);assert SurfaceRunner(ledger,content,args.cave_exe,cave_process).resume()==final
    assert len(cave_process.runs)==before
    report=dict(provenance=provenance,final=final,surface_runs=surface_process.runs,cave_runs=cave_process.runs,
                source_position=snapshot['position'],native_return_position=restored_position,native_position_settling_drift=position_drift,fixture_only=True,full_world_restore=False,physical_F6_input_tested=False)
    (args.output/'result.json').write_text(json.dumps(report,indent=2))
    print('PASS actual native bounded entrance -> two cave floors -> bounded native return; party/health/receipts/source position preserved.')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','source-import','pocket','treasure','pod1','pod2','purple','imported','surface-exe','cave-exe','output'):
        p.add_argument('--'+name,type=Path,required=True)
    for name in ('transitions','snow','roster','transition-assets'):p.add_argument('--'+name,type=Path)
    p.add_argument('--timeout',type=int,default=120);args=p.parse_args()
    for name,value in vars(args).items():
        if isinstance(value,Path):setattr(args,name,value.resolve())
    run_test(args)
