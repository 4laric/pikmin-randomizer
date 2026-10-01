"""Bounded ordinary-input surface/cave route with durable boundary recovery."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import re
import struct
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.cave_floor import atomic_write,fingerprint
from randomizer.cave_route import Route
from randomizer.cave_journey import read_json
from randomizer.test_run import apply_test_run_env
from experimental.pikmin2_cave_items import parse_items_text
from scripts.play_pikmin2_cave_journey import package_inputs,exclusive as windows_exclusive
from scripts.play_pikmin2_cave import live_runtime_paths as windows_live_runtime_paths,runtime_capacity as windows_runtime_capacity
from scripts.fixture_platform import is_windows
from scripts.stage_pikmin2_playable_cave import stage, verify_species_banks, read_species_banks, SPECIES_MODEL_DIR
from experimental.pikmin2_cave_lane41_generator import _seed_uint64
from scripts.stage_pikmin2_cave_route import stage_surface,sha
ROOT=Path(__file__).resolve().parents[1]


@contextmanager
def exclusive(path):
    if is_windows():
        with windows_exclusive(path):yield
    else:
        import fcntl
        with Path(path).open('a+b') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            try:yield
            finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def live_runtime_paths():
    if is_windows():return windows_live_runtime_paths()
    paths=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:paths.append(str((entry/'exe').resolve(strict=True)))
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError as error:raise RuntimeError('Cannot identify Linux runtime paths safely') from error
    return paths


def require_controller_recipe(workspace):
    if not is_windows():
        if Path(workspace).resolve()!=ROOT:
            raise RuntimeError('Linux route controller requires its own pinned root checkout')
        # The common provider validates fixed broker proof, but this multi-phase
        # route has no selected catalog recipe yet. Do not substitute a generic
        # fixture proof or dispatch uncatalogued gameplay from a build job.
        raise RuntimeError('Linux multi-phase route recipe is not catalogued/admitted; portable staging only')


def runtime_capacity():
    if not is_windows():raise RuntimeError('Linux route runtime requires catalogued broker admission')
    return windows_runtime_capacity()


def fixture_child(exe,run,args,marker,canonical_root,session):
    """Use this checkout's provider with explicit private session ownership."""
    require_controller_recipe(canonical_root)
    sys.path.insert(0,str(ROOT/'scripts'))
    from run_pikmin2_fixture import launch
    return launch(exe,run,args,[marker],60,canonical_root=canonical_root,session_root=session)


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
    route=read_json(package/'route-package.json')
    if type(route.get('schema')) is not int or route['schema'] not in (1,2):raise ValueError('unsupported route package')
    if route['schema']==2:
        meta,journey=wfg_package_inputs(package)
        if (route.get('profile')!=journey['policy'] or route.get('first_destination')!='forest_2/f_02'
            or route.get('later_destination')!='forest_1' or type(route.get('acquisition_index')) is not int
            or route['acquisition_index']!=0 or set(route.get('species_banks',{}))!={'3','4'}):
            raise ValueError('foreign WFG route package')
    else:meta,journey=package_inputs(package)
    run=package/'surface-blueprint/run'
    for name,digest in route['files'].items():
        path=(run/name).resolve()
        if not path.is_relative_to(run) or not path.is_file() or sha(path)!=digest:raise ValueError('surface blueprint changed: '+name)
    if route['schema']==2:
        name='p2-cave-route-destination.txt'
        if name not in route['files'] or private_file(run,name).read_text()!=f"P2_CAVE_ROUTE_DESTINATION_1 {'0'*32} forest_2/f_02\n":
            raise ValueError('missing or foreign WFG surface destination')
    Route.validate_surface(route['surface'])
    route_species_banks(package,route.get('species_banks',{}))
    return meta,journey,route


def wfg_package_inputs(package):
    from randomizer.cave_journey import validate,identity
    meta=read_json(package/'package.json')
    if (type(meta.get('schema')) is not int or meta['schema']!=4
        or meta.get('policy')!='wfg-pw-acquisition-route-v1' or type(meta.get('files')) is not dict):
        raise ValueError('unsupported WFG journey package')
    verify_package_pins(package,meta['files'])
    journey=validate(read_json(package/'journey.json'))
    if (journey.get('schema')!='p2-cave-journey/2' or identity(journey)!=meta.get('fingerprint')
        or set(meta.get('blueprints',{}))!={'0','1','2'}):raise ValueError('foreign WFG journey identity')
    names={'cave.json','layout.json','render.mod','collision.json','assets/dataDir/courses/pikmin2room/room.mod'}
    required={'journey.json','nectar.exe','cave-generator.exe','floor-0/p2-cave-route-pom.txt'}
    for index,spec in enumerate(journey['floors']):
        prefix=f'floor-{index}/'
        if read_json(package/(prefix+'cave.json'))!=spec['descriptor']:raise ValueError('foreign WFG phase descriptor')
        if set(meta['blueprints'][str(index)])!=names:raise ValueError('missing WFG phase geometry')
        for name,digest in meta['blueprints'][str(index)].items():
            if meta['files'].get(prefix+name)!=digest:raise ValueError('WFG geometry differs from package pin')
        required.update(prefix+name for name in ('p2-cave-floor.txt','p2-cave-entry.txt','p2-cave-bud-entry.txt',
            'p2-cave-item-receipts.txt','p2-cave-items.txt','p2-cave-transition.txt','p2-cave-rooms.txt',
            'p2-cave-gates.txt','p2-cave-barriers.txt','p2-pod.txt','p2-purple.txt','p2-white.txt'))
        if index and (package/(prefix+'p2-cave-route-pom.txt')).exists():raise ValueError('WFG bodies outside acquisition phase')
    if not required.issubset(meta['files']):raise ValueError('missing immutable WFG semantic input')
    return meta,journey


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


def verify_copied_inputs(run,pins,phase,index=None):
    names={name:name for name in pins if len(Path(name).parts)==1 and name.lower().endswith('.dll')}
    names['nectar.exe']='nectar.exe'
    if phase!='surface':
        names['cave-generator.exe']='cave-generator.exe'
        prefix=f'floor-{int(phase[-1]) if index is None else index}/'
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


def generator_invariants(blob):
    """Freeze opaque template/body bytes while allowing the actual party count."""
    if len(blob)<24 or blob[:4]!=b'1.0v':raise ValueError('unsupported immutable generator framing')
    starts=[m.start() for m in re.finditer(b'    0.0v',blob)]
    if not starts or starts[0]!=24 or len(starts)!=struct.unpack_from('>I',blob,20)[0]:
        raise ValueError('immutable generator record count differs')
    ends=starts[1:]+[len(blob)];scaffold=[];pikis=[]
    for begin,end in zip(starts,ends):
        row=blob[begin:end]
        if len(row)<96:raise ValueError('short immutable generator record')
        if row[72:76]==b'ikip':
            if struct.unpack_from('<I',row,8)[0]!=1000+len(pikis):
                raise ValueError('immutable Pikmin generator ID differs')
            row=bytearray(row);row[8:12]=bytes(4);row[48:60]=bytes(12);pikis.append(bytes(row))
        else:scaffold.append(row)
    if not pikis or len(pikis)>100 or len(set(pikis))!=1:
        raise ValueError('incompatible immutable Pikmin template')
    return blob[:20],scaffold,pikis[0]


def verify_generator_copy(package,run,index,pins):
    name=f'floor-{index}/assets/dataDir/stages/chal0/default.gen'
    original=private_file(package,name)
    if sha(original)!=pins.get(name):raise ValueError('original generator blueprint changed')
    current=private_file(run,'assets/dataDir/stages/chal0/default.gen')
    if generator_invariants(original.read_bytes())!=generator_invariants(current.read_bytes()):
        raise ValueError('runtime generator template or body changed')


def main(package,agent_test=False,max_phases=4):
    if type(max_phases) is not int or not 1<=max_phases<=8:raise ValueError('phase budget must be 1-8')
    package=Path(package).resolve();meta,journey,spec=route_inputs(package)
    package_pins=capture_package_pins(package,meta,spec)
    workspace=Path(meta['workspace']).resolve()
    require_controller_recipe(workspace)
    if not package.is_relative_to(workspace/'output'):raise ValueError('private output package required')
    directory=package/'route-session';directory.mkdir(exist_ok=True)
    wfg=spec['schema']==2
    phase_indices={'acquisition':0,'floor1':1,'floor2':2} if wfg else {'floor1':1,'floor2':2}
    placements={n:parse_items_text((package/f'floor-{n}/p2-cave-items.txt').read_text()) for n in phase_indices.values()}
    report=dict(schema=2 if wfg else 1,children=[],gameplay_accepted=False)
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
                    package/'nectar.exe',state['surface'],token,banks or None,route_identity,
                    destination='forest_2/f_02' if wfg else None)
                for name,digest in spec['geometry'].items():
                    if sha(run/name)!=digest:raise ValueError('surface geometry changed')
                args=['--arg=--experimental-pikmin2-surface','--arg=tutorial'];marker='P2_CAVE_SURFACE_READY'
            else:
                n=route.phase_indices[phase];floor=journey['floors'][n if wfg else n-1];run=target
                checkpoint=dict(state['entry'],receipts=route.ledger(n))
                stage(floor['descriptor'],Path(meta['assets']),Path(meta['pod']),package/'nectar.exe',
                      package/'cave-generator.exe',run,floor['salt'],checkpoint,banks or None)
                if ((phase=='acquisition')!=(run/'p2-cave-route-pom.txt').is_file()):
                    raise ValueError('acquisition body binding differs from actual phase')
                for name,digest in meta['blueprints'][str(n)].items():
                    if sha(run/name)!=digest:raise ValueError('floor geometry changed: '+name)
                token=fingerprint(floor['descriptor'])[:32]
                inputs=floor_inputs(run)
                inputs+=list(meta['blueprints'][str(n)])
                args=['--arg=--experimental-pikmin2-room'];marker='P2_CAVE_RESTORE'
            selected=sorted({s for s,m in state['surface']['squad'] if s>2}) if phase=='surface' else sorted(banks)
            verify_run_banks(run,spec.get('species_banks',{}),selected)
            verify_package_pins(package,package_pins)
            inputs+=verify_copied_inputs(run,package_pins,phase,None if phase=='surface' else n)
            if phase!='surface':verify_generator_copy(package,run,n,package_pins)
            route.begin(run,state,token,inputs)
            env=os.environ.copy()
            for key in list(env):
                if key.startswith(('PIKMIN_CAVE_','PIKMIN_P2_','PIKMIN_RANDOMIZER_AUTOPLAY')):del env[key]
            env.update(PIKMIN_RANDOMIZER_AUTOPLAY='0',PIKMIN_P2_ROOM_WINDOW='960x540')
            if phase!='surface':env['PIKMIN_P2_ITEM_RECEIPT_PATH']=str(route.ledger_path(n))
            if agent_test:
                apply_test_run_env(env,workspace);env['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS']='1'
            command=[sys.executable,str(Path(__file__).resolve()),'--fixture-child','--exe',str(run/'nectar.exe'),
                     '--run-dir',str(run),'--canonical-root',str(workspace),'--session-root',str(directory),
                     *args,'--pass-marker',marker]
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
    if sys.argv[1:2]==['--fixture-child']:
        p=argparse.ArgumentParser(description='Private pinned fixture provider bridge')
        for name in ('exe','run-dir','canonical-root','session-root'):p.add_argument('--'+name,type=Path,required=True)
        p.add_argument('--arg',action='append',default=[]);p.add_argument('--pass-marker',required=True)
        a=p.parse_args(sys.argv[2:])
        result=fixture_child(a.exe,a.run_dir,a.arg,a.pass_marker,a.canonical_root,a.session_root)
        print(json.dumps(result,indent=2));raise SystemExit(0 if result.get('passed') else 1)
    else:
        p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path)
        p.add_argument('--agent-test',action='store_true');p.add_argument('--max-phases',type=int,default=4)
        a=p.parse_args();print(json.dumps(main(a.package,a.agent_test,a.max_phases),indent=2))
