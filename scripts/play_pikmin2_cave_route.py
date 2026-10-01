"""Bounded ordinary-input surface/cave route with durable boundary recovery."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.cave_floor import atomic_write,fingerprint
from randomizer.cave_route import Route
from randomizer.cave_journey import read_json
from randomizer.test_run import apply_test_run_env
from experimental.pikmin2_cave_items import parse_items_text
from scripts.play_pikmin2_cave_journey import package_inputs,exclusive
from scripts.play_pikmin2_cave import live_runtime_paths,runtime_capacity
from scripts.stage_pikmin2_playable_cave import stage
from scripts.stage_pikmin2_cave_route import stage_surface,sha


def route_inputs(package):
    meta,journey=package_inputs(package);route=read_json(package/'route-package.json')
    if route.get('schema')!=1:raise ValueError('unsupported route package')
    run=package/'surface-blueprint/run'
    for name,digest in route['files'].items():
        path=(run/name).resolve()
        if not path.is_relative_to(run) or not path.is_file() or sha(path)!=digest:raise ValueError('surface blueprint changed: '+name)
    Route.validate_surface(route['surface'])
    return meta,journey,route


def main(package,agent_test=False,max_phases=4):
    if type(max_phases) is not int or not 1<=max_phases<=8:raise ValueError('phase budget must be 1-8')
    package=Path(package).resolve();meta,journey,spec=route_inputs(package)
    workspace=Path(meta['workspace']).resolve()
    if not package.is_relative_to(workspace/'output'):raise ValueError('private output package required')
    directory=package/'route-session';directory.mkdir(exist_ok=True)
    placements={n:parse_items_text((package/f'floor-{n}/p2-cave-items.txt').read_text()) for n in (1,2)}
    report=dict(schema=1,children=[],gameplay_accepted=False)
    with exclusive(directory/'launch.lock'):
        route=Route(directory,journey,placements,spec['receipt_identity'])
        route.initialize(spec['surface']);state,recovered=route.recover(live_runtime_paths())
        report['recovered_boundary']=recovered
        if route.pending_path.exists():raise ValueError('interrupted native run has no durable boundary; preserving party without relaunch/reset')
        for _ in range(max_phases):
            phase=state['phase'];target=directory/'runs'/uuid.uuid4().hex
            if phase=='surface':
                token=uuid.uuid4().hex
                run,inputs=stage_surface(Path(meta['assets']),Path(spec['bundle']),spec['receipt_identity'],target,
                    package/'nectar.exe',state['surface'],token)
                for name,digest in spec['geometry'].items():
                    if sha(run/name)!=digest:raise ValueError('surface geometry changed')
                args=['--arg=--experimental-pikmin2-surface','--arg=tutorial'];marker='P2_CAVE_SURFACE_READY'
            else:
                n=int(phase[-1]);floor=journey['floors'][n-1];run=target
                checkpoint=dict(state['entry'],receipts=route.ledger(n))
                stage(floor['descriptor'],Path(meta['assets']),Path(meta['pod']),package/'nectar.exe',
                      package/'cave-generator.exe',run,floor['salt'],checkpoint)
                for name,digest in meta['blueprints'][str(n)].items():
                    if sha(run/name)!=digest:raise ValueError('floor geometry changed: '+name)
                token=fingerprint(floor['descriptor'])[:32]
                inputs=['p2-cave-entry.txt','p2-cave-items.txt','p2-cave-buds.txt','p2-cave-exit.txt','nectar.exe']
                # Pin every local checkpoint sidecar that stage actually supplied.
                inputs=[name for name in inputs if (run/name).is_file()]
                inputs+=list(meta['blueprints'][str(n)])
                args=['--arg=--experimental-pikmin2-room'];marker='P2_CAVE_RESTORE'
            route.begin(run,state,token,inputs)
            env=os.environ.copy()
            for key in list(env):
                if key.startswith(('PIKMIN_CAVE_','PIKMIN_P2_','PIKMIN_RANDOMIZER_AUTOPLAY')):del env[key]
            env.update(PIKMIN_RANDOMIZER_AUTOPLAY='0',PIKMIN_P2_ROOM_WINDOW='960x540')
            if phase!='surface':env['PIKMIN_P2_ITEM_RECEIPT_PATH']=str(route.ledger_path(int(phase[-1])))
            if agent_test:
                apply_test_run_env(env,workspace);env['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS']='1'
            command=[sys.executable,str(workspace/'scripts/run_pikmin2_fixture.py'),'--exe',str(run/'nectar.exe'),
                     '--run-dir',str(run),*args,'--pass-marker',marker,'--timeout','60']
            with (run/'supervisor.log').open('w',encoding='utf8') as log:
                with exclusive(Path(tempfile.gettempdir())/'pikmin-randomizer-runtime-admission.lock'):
                    runtime_capacity();child=subprocess.Popen(command,cwd=workspace,env=env,stdout=log,stderr=subprocess.STDOUT)
                    deadline=time.monotonic()+65
                    while child.poll() is None and (not (run/'native.log').exists() or not (run/'native.log').stat().st_size):
                        if time.monotonic()>deadline:child.kill();child.wait();raise RuntimeError('runtime wrapper failed to start bounded native child')
                        time.sleep(.1)
                child.wait(timeout=75)
            raw=read_json(run/'run-result.json');code=raw.get('exit_code')
            report['children'].append(dict(phase=phase,run=str(run),exit_code=code,elapsed_seconds=raw.get('elapsed_seconds')))
            atomic_write(directory/'last-launch.json',json.dumps(report,indent=2)+'\n')
            if raw.get('timed_out') or raw.get('captain_down') or code not in (0,42):raise RuntimeError('native child failed; pending route preserved: '+str(run))
            name='p2-cave-surface-transfer.txt' if phase=='surface' else 'p2-cave-transfer.txt'
            if code==42 and not (run/name).exists():raise ValueError('native42 has no actual boundary')
            if code==0:
                route.stop_unsaved();break
            state,changed=route.recover(live_runtime_paths())
            if not changed:raise ValueError('native boundary did not commit')
            print('Actual native boundary committed: '+phase+' -> '+state['phase'],flush=True)
        report.update(final_phase=state['phase'],revision=state['revision'],visit=state['visit'])
        atomic_write(directory/'last-launch.json',json.dumps(report,indent=2)+'\n')
        return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path)
    p.add_argument('--agent-test',action='store_true');p.add_argument('--max-phases',type=int,default=4)
    a=p.parse_args();print(json.dumps(main(a.package,a.agent_test,a.max_phases),indent=2))
