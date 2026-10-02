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


def process_cgroup(pid):
    groups=[line.split(':',2)[2] for line in (Path('/proc')/str(pid)/'cgroup').read_text().splitlines() if line.startswith('0::')]
    if len(groups)!=1 or not groups[0].startswith('/'):raise RuntimeError('Cannot identify owned cgroup safely')
    return groups[0]


def process_uid(pid):return (Path('/proc')/str(pid)).stat().st_uid


def process_executable(pid):return str((Path('/proc')/str(pid)/'exe').resolve(strict=True))


def live_runtime_paths():
    if is_windows():return windows_live_runtime_paths()
    owned_cgroup=process_cgroup('self');uid=os.getuid();paths=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        pid=int(entry.name)
        try:
            if process_uid(pid)!=uid:continue
            if process_cgroup(pid)!=owned_cgroup:continue
            paths.append(process_executable(pid))
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError as error:raise RuntimeError('Cannot identify an owned Linux runtime safely') from error
    return paths


def require_controller_recipe(workspace,exe=None,session=None,run=None):
    if is_windows():return None
    if Path(workspace).resolve()!=ROOT.resolve():
        raise RuntimeError('Linux route controller requires its own pinned root checkout')
    if any(value is None for value in (exe,session,run)):
        raise RuntimeError('Linux recipe requires actual copied executable/session/run')
    from scripts.pikmin2_cave_linux_runtime import recipe_admission
    return recipe_admission(exe,ROOT,session,run)


def runtime_capacity(exe=None,session=None,run=None):
    if is_windows():return windows_runtime_capacity()
    return require_controller_recipe(ROOT,exe,session,run)


def fixture_child(exe,run,args,marker,canonical_root,session,phase=None,token=None,action=None,title=None):
    """Use this checkout's unchanged provider with explicit session ownership."""
    if not is_windows():
        require_controller_recipe(canonical_root,exe,session,run)
        from scripts.pikmin2_cave_linux_runtime import launch_linux_fixture
        return launch_linux_fixture(exe,run,args,marker,canonical_root,session,
                                    phase=phase,token=token,action=action,title=title)
    sys.path.insert(0,str(ROOT/'scripts'))
    from run_pikmin2_fixture import launch
    return launch(exe,run,args,[marker],60,canonical_root=canonical_root,session_root=session)


def fresh_acquisition(state):
    return (state['phase']=='acquisition' and state['visit']==1
            and state.get('wfg_white_boundary') is None
            and state['entry']['health']==1
            and state['entry']['squad']==[[1,0]]*20)


LINUX_SETTINGS=b'debugKeys=0\nwindowWidth=960\nwindowHeight=540\ndisplayMode=0\n'


def stage_linux_settings(run):
    path=Path(run)/'pikmin_settings.conf'
    # Exclusive creation refuses existing files and link entries. The private
    # per-phase settings are immutable pending inputs, never global preferences.
    with path.open('xb') as stream:stream.write(LINUX_SETTINGS)
    return path.name


def linux_phase_environment(env,phase,fresh=False):
    from scripts.pikmin2_cave_linux_runtime import phase_environment
    result=phase_environment(env,phase,fresh_acquisition=fresh)
    # The reviewed Linux recipe owns a private offscreen Xvfb display. SDL must
    # map its parent there even when agent-test preferences remove visibility.
    result.update(PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',PIKMIN_RANDOMIZER_TEST_VISIBLE='1',SDL_VIDEODRIVER='x11')
    return result


def linux_dialog(phase):
    # Requires native dialog-evidence-v02 WFG terminal-action candidate, not 847.
    if phase=='surface':return 'enter','White Flower Garden'
    if phase=='acquisition':return 'leave','White Flower Garden'
    if phase=='floor1':return 'descend','Emergence Cave'
    if phase=='floor2':return 'leave','Emergence Cave'
    raise ValueError('unsupported Linux route phase')


def recovery_route(package):
    meta,journey,spec=route_inputs(package)
    if spec['schema']!=2:raise ValueError('Linux recovery recipe requires WFG route')
    directory=package/'route-session'
    placements={n:parse_items_text((package/f'floor-{n}/p2-cave-items.txt').read_text()) for n in (0,1,2)}
    return Route(directory,journey,placements,spec['receipt_identity'])


def durable_route_state(route):
    # The new Route.load verifies every retained input/transfer/bud/receipt hash.
    # Do not accept an older Route implementation that forgets durable history.
    state=route.load()
    proofs=state.get('boundary_proofs')
    if type(proofs) is not list or len(proofs)!=state['revision']:
        raise ValueError('fixed Linux recipe requires immutable durable boundary proof history')
    return state


def recover_boundary_child(package):
    """Fixed fault point after Route's real atomic state write, before unlink."""
    if is_windows():raise RuntimeError('Linux recovery recipe only')
    package=Path(package).resolve(strict=True);route=recovery_route(package)
    pending=read_json(route.pending_path);run=Path(pending['run']).resolve(strict=True)
    require_controller_recipe(ROOT,run/'nectar.exe',route.directory,run)
    result=read_json(run/'run-result.json')
    if result.get('exit_code')!=42 or result.get('timed_out') or result.get('captain_down'):
        raise ValueError('recovery fault requires actual successful native42')
    require_linux_phase_acceptance(run,pending['phase'],pending['token'],ROOT,route.directory)
    if durable_route_state(route)['revision']!=pending['revision']:raise ValueError('fault point already passed')
    import randomizer.cave_route as route_module
    original=route_module.atomic_write
    def fault_after_state(path,text):
        original(path,text)
        if Path(path).resolve()==route.state_path.resolve():os._exit(87)
    route_module.atomic_write=fault_after_state
    try:route.recover(live_runtime_paths())
    finally:route_module.atomic_write=original
    raise RuntimeError('actual boundary did not reach fixed state-write fault')


def recover_fault_once(package,route):
    """Restart one source-bound child; prove duplicate recovery changes nothing."""
    pending=read_json(route.pending_path);run=Path(pending['run']).resolve(strict=True)
    require_controller_recipe(ROOT,run/'nectar.exe',route.directory,run)
    require_linux_phase_acceptance(run,pending['phase'],pending['token'],ROOT,route.directory)
    receipt=route.directory/'recovery-once.json'
    if receipt.exists():raise ValueError('recovery fault already attempted')
    before=durable_route_state(route);boundary=run/('p2-cave-surface-transfer.txt' if pending['phase']=='surface' else 'p2-cave-transfer.txt')
    digest=sha(boundary);ledger={str(n):sha(route.ledger_path(n)) for n in route.manifests}
    atomic_write(receipt,json.dumps(dict(status='started',revision=before['revision'],run=str(run),sha256=digest))+'\n')
    command=[sys.executable,str(Path(__file__).resolve()),'--recover-boundary-once',str(package)]
    env=os.environ.copy()
    from scripts.pikmin2_cave_linux_runtime import phase_environment
    env=phase_environment(env,pending['phase'])
    child=subprocess.Popen(command,cwd=ROOT,env=env,start_new_session=True,
                           stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:output,_=child.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        import signal
        os.killpg(child.pid,signal.SIGKILL);child.communicate()
        raise RuntimeError('bounded recovery child timed out')
    if child.returncode!=87:raise RuntimeError('recovery child missed fixed fault: '+str(child.returncode)+' '+output)
    durable=durable_route_state(route);state_hash=sha(route.state_path)
    latest=durable['boundary_proofs'][-1]
    buds=None if pending['phase']=='surface' else dict(name='p2-cave-bud-transfer.txt',sha256=sha(run/'p2-cave-bud-transfer.txt'))
    receipts=None if pending['phase']=='surface' else route.ledger(route.phase_indices[pending['phase']])
    expected=dict(schema=1,revision=before['revision']+1,phase=pending['phase'],run=str(run),
        token=pending['token'],inputs=pending['inputs'],transfer=dict(name=boundary.name,sha256=digest),
        buds=buds,receipts=receipts)
    if latest!=expected:raise ValueError('durable proof differs from original pending inputs/full bud boundary')
    if (durable['revision']!=before['revision']+1
        or durable['boundary_proofs'][:-1]!=before['boundary_proofs'] or durable['last_boundary']!=dict(run=str(run),sha256=digest)
        or not route.pending_path.exists() or sha(boundary)!=digest
        or any(sha(route.ledger_path(n))!=ledger[str(n)] for n in route.manifests)):
        raise ValueError('state-write fault changed boundary or ledger identity')
    state,changed=route.recover(live_runtime_paths())
    if changed or state!=durable or sha(route.state_path)!=state_hash or route.pending_path.exists():
        raise ValueError('recovery did not consume already committed boundary exactly once')
    again,changed=route.recover(live_runtime_paths())
    if changed or again!=durable or sha(route.state_path)!=state_hash:
        raise ValueError('duplicate recovery changed committed state')
    atomic_write(receipt,json.dumps(dict(status='passed',revision=durable['revision'],run=str(run),
        sha256=digest,state_sha256=state_hash,ledgers=ledger,child_exit=87),indent=2)+'\n')
    return state,True


def require_linux_phase_acceptance(run,phase,token,root,session,wrapper_exit=None):
    run=Path(run).resolve(strict=True);exe=run/'nectar.exe'
    proof=require_controller_recipe(root,exe,session,run)
    accepted=read_json(run/'cave-linux-runtime-result.json')
    raw=read_json(run/'run-result.json');cleanup=read_json(run/'route-wrapper-cleanup.json')
    if (accepted.get('schema')!=1 or accepted.get('phase')!=phase or accepted.get('token')!=token
        or accepted.get('run')!=str(run) or accepted.get('exe')!=str(exe)
        or accepted.get('source_sha256')!=proof['pins']['FIXTURE_SOURCE_SHA256']
        or accepted.get('raw_result_sha256')!=sha(run/'run-result.json')
        or accepted.get('admission_sha256')!=sha(run/'admission.json')
        or accepted.get('linux_route_phase_accepted') is not True
        or accepted.get('gameplay_accepted') is not False or accepted.get('error')
        or raw.get('exit_code')!=42 or raw.get('timed_out') or raw.get('captain_down')):
        raise RuntimeError('Linux actual native42/modal acceptance failed; pending boundary preserved')
    if (cleanup.get('schema')!=1 or cleanup.get('run')!=str(run) or cleanup.get('exe')!=str(exe)
        or cleanup.get('source_sha256')!=proof['pins']['FIXTURE_SOURCE_SHA256']
        or cleanup.get('cleanup_complete') is not True or cleanup.get('error') is not None
        or cleanup.get('cleanup_errors')!=[] or type(cleanup.get('wrapper_exit')) is not int
        or cleanup['wrapper_exit']!=0 or (wrapper_exit is not None and wrapper_exit!=cleanup['wrapper_exit'])):
        raise RuntimeError('actual wrapper exit/cleanup proof rejected; pending boundary preserved')
    native=cleanup.get('native');wrapper=cleanup.get('wrapper')
    returned=[event for event in accepted.get('dialogs',[]) if event.get('event')=='os-return']
    if (type(native) is not dict or type(wrapper) is not dict or len(returned)!=1
        or type(raw.get('pid')) is not int or native.get('pid')!=raw['pid']
        or type(wrapper.get('pid')) is not int or wrapper['pid']<=1
        or type(native.get('start')) is not str or not native['start'].isdigit()
        or type(wrapper.get('start')) is not str or not wrapper['start'].isdigit()
        or raw.get('owned_process_group')!=raw['pid'] or native.get('pgid')!=raw['pid']
        or native.get('sid')!=raw['pid'] or native.get('ppid')!=wrapper.get('pid')
        or native.get('exe')!=str(exe) or native.get('cwd')!=str(run)
        or native.get('cgroup')!=proof['cgroup'] or returned[0].get('pid')!=raw['pid']
        or returned[0].get('native_start')!=native.get('start')
        or wrapper.get('pgid')!=wrapper.get('pid') or wrapper.get('sid')!=wrapper.get('pid')
        or wrapper.get('exe')!=str(Path(sys.executable).resolve()) or wrapper.get('cwd')!=str(Path(root).resolve())
        or wrapper.get('cgroup')!=proof['cgroup']):
        raise RuntimeError('actual wrapper/native PID/start lineage rejected; pending boundary preserved')
    return raw


def require_linux_pending_boundary(route):
    if not route.pending_path.exists():return
    pending=read_json(route.pending_path);run=Path(pending['run']).resolve(strict=True)
    source=run/('p2-cave-surface-transfer.txt' if pending['phase']=='surface' else 'p2-cave-transfer.txt')
    if source.exists():
        require_linux_phase_acceptance(run,pending['phase'],pending['token'],ROOT,route.directory)


def require_linux_committed_boundaries(route):
    state=durable_route_state(route)
    for proof in state['boundary_proofs']:
        require_linux_phase_acceptance(Path(proof['run']),proof['phase'],proof['token'],ROOT,route.directory)
    return state


def linux_phase_budget(max_phases,state):
    if type(max_phases) is not int or max_phases!=5:
        raise ValueError('fixed Linux whole-journey recipe requires exactly five boundaries')
    revision=state['revision']
    if type(revision) is not int or not 0<=revision<=5:
        raise ValueError('fixed Linux milestone cannot continue beyond revision5')
    phases=('surface','acquisition','floor1','floor2','surface','acquisition')
    visits=(0,1,1,1,1,2)
    if state['phase']!=phases[revision] or state['visit']!=visits[revision]:
        raise ValueError('fixed Linux milestone state differs from its phase/revision')
    return 5-revision


def proc_fields(pid):
    return (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()


def proc_identity(pid):
    proc=Path('/proc')/str(pid)
    fields=proc_fields(pid)
    groups=[line.split(':',2)[2] for line in (proc/'cgroup').read_text().splitlines() if line.startswith('0::')]
    if len(groups)!=1:raise ValueError('owned child cgroup unreadable')
    return dict(pid=pid,state=fields[0],ppid=int(fields[1]),pgid=int(fields[2]),sid=int(fields[3]),
                start=fields[19],cgroup=groups[0],exe=str((proc/'exe').resolve(strict=True)),
                cwd=str((proc/'cwd').resolve(strict=True)))


def owned_identity(pid,exe,cwd,cgroup,parent=None):
    actual=proc_identity(pid)
    if (actual['state']=='Z' or actual['pgid']!=pid or actual['sid']!=pid
        or actual['exe']!=str(Path(exe).resolve(strict=True))
        or actual['cwd']!=str(Path(cwd).resolve(strict=True)) or actual['cgroup']!=cgroup
        or (parent is not None and actual['ppid']!=parent)):
        raise ValueError('process is not the exact owned child/session')
    return actual


def discover_owned_native(wrapper,run,proof):
    found=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            fields=proc_fields(int(path.name))
            if int(fields[1])!=wrapper.pid:continue
            record=proc_identity(int(path.name))
        except (FileNotFoundError,ProcessLookupError):continue
        if record['ppid']!=wrapper.pid or record['exe']!=str((run/'nectar.exe').resolve()):continue
        record=owned_identity(record['pid'],run/'nectar.exe',run,proof['cgroup'],wrapper.pid)
        if sha(run/'nectar.exe')!=proof['exe_sha256']:raise ValueError('native copy changed during launch')
        found.append(record)
    if len(found)>1:raise ValueError('ambiguous native ownership')
    return found[0] if found else None


def owned_group_members(identity):
    members=[];leader=False
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            fields=proc_fields(int(path.name))
            if int(fields[2])!=identity['pid'] or fields[0]=='Z':continue
            record=proc_identity(int(path.name))
        except (FileNotFoundError,ProcessLookupError):continue
        # Require the live original leader before signalling this group. A
        # leaderless group cannot be distinguished from recycled PID ownership.
        if (record['sid']!=identity['pid'] or record['cgroup']!=identity['cgroup']
            or int(record['start'])<int(identity['start'])):
            raise ValueError('owned group identity changed')
        if record['pid']==identity['pid'] and any(record[k]!=identity[k] for k in ('start','exe','cwd','sid','pgid','cgroup')):
            raise ValueError('owned process PID reused or changed')
        if record['pid']==identity['pid']:leader=True
        if record['state']!='Z':members.append(record)
    if members and not leader:raise ValueError('live group lacks original PID/start leader; broker attention required')
    return members


def cleanup_owned_group(identity):
    import signal
    # Never signal a guessed PID or a group discovered solely by name.
    for sig,duration in ((signal.SIGTERM,1),(signal.SIGKILL,2)):
        if not owned_group_members(identity):return True
        try:os.killpg(identity['pid'],sig)
        except ProcessLookupError:pass
        deadline=time.monotonic()+duration
        while time.monotonic()<deadline:
            if not owned_group_members(identity):return True
            time.sleep(.05)
    return not owned_group_members(identity)


def launch_route_wrapper(command,workspace,env,log,run,directory):
    """Linux-only wrapper/session ownership; retain separate native group proof."""
    child=None;wrapper=None;native=None;failure=None;cleaned=False
    try:
        with exclusive(Path(tempfile.gettempdir())/'pikmin-randomizer-runtime-admission.lock'):
            proof=runtime_capacity(run/'nectar.exe',directory,run)
            child=subprocess.Popen(command,cwd=workspace,env=env,stdout=log,stderr=subprocess.STDOUT,
                                   start_new_session=True)
            wrapper=owned_identity(child.pid,sys.executable,workspace,proof['cgroup'],os.getpid())
            deadline=time.monotonic()+65
            while child.poll() is None:
                discovered=discover_owned_native(child,run,proof)
                if discovered is not None:
                    if native is not None and any(discovered[k]!=native[k] for k in ('pid','ppid','pgid','sid','start','exe','cwd','cgroup')):raise ValueError('native ownership changed')
                    native=discovered
                if native is not None and (run/'native.log').exists() and (run/'native.log').stat().st_size:break
                if time.monotonic()>deadline:raise RuntimeError('runtime wrapper failed to start bounded native child')
                time.sleep(.1)
        child.wait(timeout=75)
        return child
    except BaseException as error:
        failure=str(error);raise
    finally:
        errors=[]
        if child is not None:
            if native is None and child.poll() is None:
                try:native=discover_owned_native(child,run,proof)
                except BaseException as error:errors.append('native ownership discovery: '+str(error))
            if native is None and (run/'native.log').exists():
                errors.append('native launch occurred without captured PID/start ownership; no guessed group signal')
            for label,identity in (('native',native),('wrapper',wrapper)):
                if identity is None:continue
                try:
                    if not cleanup_owned_group(identity):errors.append('owned '+label+' group still live')
                except BaseException as error:errors.append(label+' cleanup: '+str(error))
            if wrapper is None and child.poll() is None:
                # Popen owns this exact child; never guess a native group.
                child.kill();errors.append('wrapper ownership could not be fully established')
            try:child.wait(timeout=3)
            except BaseException as error:errors.append('wrapper reap: '+str(error))
            cleaned=not errors
        atomic_write(run/'route-wrapper-cleanup.json',json.dumps(dict(schema=1,
            run=str(run),exe=str(run/'nectar.exe'),source_sha256=proof['pins']['FIXTURE_SOURCE_SHA256'] if child is not None else None,
            wrapper_exit=child.returncode if child is not None else None,
            wrapper=wrapper,native=native,cleanup_complete=cleaned,error=failure,cleanup_errors=errors),indent=2)+'\n')
        if errors:raise RuntimeError('owned wrapper cleanup failed; preserving pending boundary: '+'; '.join(errors))


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
    if not is_windows() and max_phases!=5:raise ValueError('fixed Linux whole-journey recipe requires exactly five boundaries')
    package=Path(package).resolve();meta,journey,spec=route_inputs(package)
    package_pins=capture_package_pins(package,meta,spec)
    workspace=Path(meta['workspace']).resolve()
    require_controller_recipe(workspace,package/'nectar.exe',package,package)
    if not package.is_relative_to(workspace/'output'):raise ValueError('private output package required')
    directory=package/'route-session';directory.mkdir(exist_ok=True)
    wfg=spec['schema']==2
    if not is_windows() and not wfg:raise ValueError('Linux fixed recipe requires WFG route')
    phase_indices={'acquisition':0,'floor1':1,'floor2':2} if wfg else {'floor1':1,'floor2':2}
    placements={n:parse_items_text((package/f'floor-{n}/p2-cave-items.txt').read_text()) for n in phase_indices.values()}
    report=dict(schema=2 if wfg else 1,children=[],gameplay_accepted=False)
    with exclusive(directory/'launch.lock'):
        route=Route(directory,journey,placements,spec['receipt_identity'])
        route.initialize(spec['surface'])
        if not is_windows() and (directory/'recovery-once.json').exists():
            if read_json(directory/'recovery-once.json').get('status')!='passed':
                raise ValueError('interrupted recovery fault requires review; preserving evidence')
        if not is_windows():
            current=require_linux_committed_boundaries(route);linux_phase_budget(max_phases,current)
            if route.pending_path.exists() and read_json(route.pending_path)['revision']>=5:
                raise ValueError('pending later WFG phase requires a separate fixed recipe')
            require_linux_pending_boundary(route)
        state,recovered=route.recover(live_runtime_paths())
        if not is_windows() and state!=durable_route_state(route):raise ValueError('durable Linux history differs from recovered route')
        report['recovered_boundary']=recovered
        if route.pending_path.exists():raise ValueError('interrupted native run has no durable boundary; preserving party without relaunch/reset')
        remaining=max_phases if is_windows() else linux_phase_budget(max_phases,state)
        for _ in range(remaining):
            verify_package_pins(package,package_pins)
            if not is_windows():require_linux_committed_boundaries(route)
            banks=route_species_banks(package,spec.get('species_banks',{}))
            route_identity=dict(seed=_seed_uint64(journey['seed']),
                                slot_hash=hashlib.sha256(journey['slot'].encode('utf-8')).hexdigest(),
                                receipt_identity=spec['receipt_identity'])
            phase=state['phase']
            if not is_windows() and phase=='acquisition' and state['visit']==1 and not fresh_acquisition(state):
                raise ValueError('fresh WFG recipe requires actual20 Red leaf HP1 baseline without prior White proof')
            target=directory/'runs'/uuid.uuid4().hex
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
            if not is_windows():inputs.append(stage_linux_settings(run))
            route.begin(run,state,token,inputs)
            env=os.environ.copy()
            for key in list(env):
                if key.startswith(('PIKMIN_CAVE_','PIKMIN_P2_','PIKMIN_RANDOMIZER_AUTOPLAY')):del env[key]
            env.update(PIKMIN_RANDOMIZER_AUTOPLAY='0',PIKMIN_P2_ROOM_WINDOW='960x540')
            if phase!='surface':env['PIKMIN_P2_ITEM_RECEIPT_PATH']=str(route.ledger_path(n))
            if agent_test:
                apply_test_run_env(env,workspace);env['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS']='1'
            if not is_windows():env=linux_phase_environment(env,phase,fresh_acquisition(state))
            command=[sys.executable,str(Path(__file__).resolve()),'--fixture-child','--exe',str(run/'nectar.exe'),
                     '--run-dir',str(run),'--canonical-root',str(workspace),'--session-root',str(directory),
                     *args,'--pass-marker',marker]
            if not is_windows():
                action,title=linux_dialog(phase)
                command+=['--phase',phase,'--token',token,'--action',action,'--title',title]
            with (run/'supervisor.log').open('w',encoding='utf8') as log:
                if not is_windows():child=launch_route_wrapper(command,workspace,env,log,run,directory)
                else:
                    with exclusive(Path(tempfile.gettempdir())/'pikmin-randomizer-runtime-admission.lock'):
                        runtime_capacity();child=subprocess.Popen(command,cwd=workspace,env=env,stdout=log,stderr=subprocess.STDOUT)
                        deadline=time.monotonic()+65
                        while child.poll() is None and (not (run/'native.log').exists() or not (run/'native.log').stat().st_size):
                            if time.monotonic()>deadline:child.kill();child.wait();raise RuntimeError('runtime wrapper failed to start bounded native child')
                            time.sleep(.1)
                    child.wait(timeout=75)
            if not is_windows():
                require_linux_phase_acceptance(run,phase,token,workspace,directory,child.returncode)
            raw=read_json(run/'run-result.json');code=raw.get('exit_code')
            report['children'].append(dict(phase=phase,run=str(run),exit_code=code,elapsed_seconds=raw.get('elapsed_seconds')))
            atomic_write(directory/'last-launch.json',json.dumps(report,indent=2)+'\n')
            if raw.get('timed_out') or raw.get('captain_down') or code not in (0,42):raise RuntimeError('native child failed; pending route preserved: '+str(run))
            name='p2-cave-surface-transfer.txt' if phase=='surface' else 'p2-cave-transfer.txt'
            if code==42 and not (run/name).exists():raise ValueError('native42 has no actual boundary')
            if code==0:
                route.stop_unsaved();break
            if not is_windows() and not (directory/'recovery-once.json').exists():
                state,changed=recover_fault_once(package,route)
            else:state,changed=route.recover(live_runtime_paths())
            if not changed:raise ValueError('native boundary did not commit')
            if not is_windows() and state!=durable_route_state(route):raise ValueError('Linux boundary lost immutable history')
            print('Actual native boundary committed: '+phase+' -> '+state['phase'],flush=True)
        report.update(final_phase=state['phase'],revision=state['revision'],visit=state['visit'])
        atomic_write(directory/'last-launch.json',json.dumps(report,indent=2)+'\n')
        return report


if __name__=='__main__':
    if sys.argv[1:2]==['--recover-boundary-once']:
        p=argparse.ArgumentParser(description='Fixed source-bound post-state-write recovery fault')
        p.add_argument('package',type=Path);a=p.parse_args(sys.argv[2:]);recover_boundary_child(a.package)
    elif sys.argv[1:2]==['--fixture-child']:
        p=argparse.ArgumentParser(description='Private pinned fixture provider bridge')
        for name in ('exe','run-dir','canonical-root','session-root'):p.add_argument('--'+name,type=Path,required=True)
        p.add_argument('--arg',action='append',default=[]);p.add_argument('--pass-marker',required=True)
        for name in ('phase','token','action','title'):p.add_argument('--'+name)
        a=p.parse_args(sys.argv[2:])
        result=fixture_child(a.exe,a.run_dir,a.arg,a.pass_marker,a.canonical_root,a.session_root,a.phase,a.token,a.action,a.title)
        print(json.dumps(result,indent=2))
        accepted=result.get('passed') if is_windows() else result.get('linux_route_phase_accepted') is True
        raise SystemExit(0 if accepted else 1)
    else:
        p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path)
        p.add_argument('--agent-test',action='store_true');p.add_argument('--max-phases',type=int,default=4)
        a=p.parse_args();print(json.dumps(main(a.package,a.agent_test,a.max_phases),indent=2))
