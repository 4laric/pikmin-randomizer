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
from scripts.stage_pikmin2_playable_cave import stage, verify_species_banks, read_species_banks, SPECIES_MODEL_DIR
from experimental.pikmin2_cave_lane41_generator import _seed_uint64
from scripts.stage_pikmin2_cave_route import stage_surface,sha


def floor_inputs(run):
    required=['p2-cave-entry.txt','p2-cave-bud-entry.txt','p2-cave-item-receipts.txt',
              'p2-cave-transition.txt','p2-cave-items.txt','p2-cave-rooms.txt',
              'p2-cave-gates.txt','p2-cave-barriers.txt','p2-cave-floor.txt','p2-pod.txt','nectar.exe',
              'assets/dataDir/stages/chal0.ini','assets/dataDir/stages/chal0/default.gen',
              'assets/dataDir/courses/pikmin2room/room.ini','assets/dataDir/courses/pikmin2room/room.mod',
              'assets/dataDir/courses/pikmin2room/pod.mod','assets/dataDir/courses/pikmin2room/treasure.mod']
    for name in required:
        if not (run/name).is_file():raise ValueError('missing route floor input: '+name)
    native=[path.relative_to(run).as_posix() for path in (run/'assets/dataDir/stages/chal0').glob('*.gen')]
    native += [path.relative_to(run).as_posix() for prefix in ('purple','white')
               for path in (run/SPECIES_MODEL_DIR).glob(prefix+'_*.mod')
               if (run/f'p2-{prefix}.txt').is_file()]
    return sorted(set(required+native+[path.name for path in run.glob('p2-*') if path.is_file()]))


def route_species_banks(package,records):
    banks=verify_species_banks(package,records)
    # Route floors as well as surfaces exclude the unreviewed impact bank.
    read_species_banks(banks,surface=True)
    return banks


def route_inputs(package):
    meta,journey=package_inputs(package);route=read_json(package/'route-package.json')
    if route.get('schema')!=1:raise ValueError('unsupported route package')
    run=package/'surface-blueprint/run'
    for name,digest in route['files'].items():
        path=(run/name).resolve()
        if not path.is_relative_to(run) or not path.is_file() or sha(path)!=digest:raise ValueError('surface blueprint changed: '+name)
    Route.validate_surface(route['surface'])
    route_species_banks(package,route.get('species_banks',{}))
    return meta,journey,route


def verify_run_banks(run,records,species):
    """Compare copies against package pins, not a possibly changed source read."""
    for member in species:
        for name,digest in records[str(member)]['files'].items():
            path=run/(SPECIES_MODEL_DIR+'/'+name if name.endswith('.mod') else name)
            if not path.resolve().is_relative_to(run.resolve()) or not path.is_file() or sha(path)!=digest:
                raise ValueError('staged species bank differs from package: '+name)


def private_file(directory,name):
    directory=Path(directory).resolve();relative=Path(name)
    if not name or relative.is_absolute() or '..' in relative.parts:
        raise ValueError('foreign pinned path: '+str(name))
    path=directory
    for part in relative.parts:
        path=path/part
        if path.is_symlink() or path.is_junction(): raise ValueError('linked pinned path: '+str(name))
    if not path.resolve().is_relative_to(directory) or not path.is_file():
        raise ValueError('missing or escaping pinned path: '+str(name))
    return path


def capture_package_pins(package,meta,spec):
    """Snapshot the admitted authority once; subsequent phases never reload it."""
    pins=dict(meta['files'])
    for name,value in (('package.json',meta),('route-package.json',spec)):
        path=private_file(package,name)
        if read_json(path)!=value: raise ValueError('package metadata changed during admission')
        pins[name]=sha(path)
    for name,digest in spec['files'].items(): pins['surface-blueprint/run/'+name]=digest
    for name,digest in spec['geometry'].items():
        key='surface-blueprint/run/'+name
        if key in pins and pins[key]!=digest: raise ValueError('conflicting surface geometry pin')
        pins[key]=digest
    for bank in spec.get('species_banks',{}).values():
        for name,digest in bank['files'].items(): pins[bank['directory']+'/'+name]=digest
    verify_package_pins(package,pins)
    return pins


def verify_package_pins(package,pins):
    for name,digest in pins.items():
        if sha(private_file(package,name))!=digest: raise ValueError('original package input changed: '+name)
    expected={name for name in pins if len(Path(name).parts)==1 and name.lower().endswith('.dll')}
    actual={p.name for p in Path(package).iterdir() if p.name.lower().endswith('.dll')}
    if actual!=expected: raise ValueError('package DLL inventory changed')


def verify_copied_inputs(run,pins,phase):
    names={name:name for name in pins if len(Path(name).parts)==1 and name.lower().endswith('.dll')}
    names['nectar.exe']='nectar.exe'
    if phase!='surface':
        names['cave-generator.exe']='cave-generator.exe'
        prefix=f'floor-{int(phase[-1])}/'
        dynamic={'p2-cave-entry.txt','p2-cave-bud-entry.txt','p2-cave-item-receipts.txt'}
        for name in pins:
            if name.startswith(prefix):
                local=name[len(prefix):]
                if local.startswith('p2-') and local not in dynamic: names[local]=name
    for local,original in names.items():
        if sha(private_file(run,local))!=pins[original]: raise ValueError('copied runtime input changed: '+local)
    actual={p.name for p in Path(run).iterdir() if p.name.lower().endswith('.dll')}
    if actual!={name for name in names if name.lower().endswith('.dll')}: raise ValueError('runtime DLL inventory changed')
    return sorted(names)


def main(package,agent_test=False,max_phases=4):
    if type(max_phases) is not int or not 1<=max_phases<=8:raise ValueError('phase budget must be 1-8')
    package=Path(package).resolve();meta,journey,spec=route_inputs(package)
    package_pins=capture_package_pins(package,meta,spec)
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
            verify_package_pins(package,package_pins)
            banks=route_species_banks(package,spec.get('species_banks',{}))
            route_identity=dict(seed=_seed_uint64(journey['seed']),
                                slot_hash=hashlib.sha256(journey['slot'].encode('utf-8')).hexdigest(),
                                receipt_identity=spec['receipt_identity'])
            phase=state['phase'];target=directory/'runs'/uuid.uuid4().hex
            if phase=='surface':
                token=uuid.uuid4().hex
                run,inputs=stage_surface(Path(meta['assets']),Path(spec['bundle']),spec['receipt_identity'],target,
                    package/'nectar.exe',state['surface'],token,banks or None,route_identity)
                for name,digest in spec['geometry'].items():
                    if sha(run/name)!=digest:raise ValueError('surface geometry changed')
                args=['--arg=--experimental-pikmin2-surface','--arg=tutorial'];marker='P2_CAVE_SURFACE_READY'
            else:
                n=int(phase[-1]);floor=journey['floors'][n-1];run=target
                checkpoint=dict(state['entry'],receipts=route.ledger(n))
                stage(floor['descriptor'],Path(meta['assets']),Path(meta['pod']),package/'nectar.exe',
                      package/'cave-generator.exe',run,floor['salt'],checkpoint,banks or None)
                for name,digest in meta['blueprints'][str(n)].items():
                    if sha(run/name)!=digest:raise ValueError('floor geometry changed: '+name)
                token=fingerprint(floor['descriptor'])[:32]
                inputs=floor_inputs(run)
                inputs+=list(meta['blueprints'][str(n)])
                args=['--arg=--experimental-pikmin2-room'];marker='P2_CAVE_RESTORE'
            selected=sorted({s for s,m in state['surface']['squad'] if s>2}) if phase=='surface' else sorted(banks)
            verify_run_banks(run,spec.get('species_banks',{}),selected)
            verify_package_pins(package,package_pins)
            inputs+=verify_copied_inputs(run,package_pins,phase)
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
