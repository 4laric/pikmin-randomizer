"""Ordinary supervisor for the opt-in, versioned two-floor developer journey."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from randomizer.cave_floor import atomic_write
from randomizer.cave_journey import Session, identity, validate, POLICY, read_json
from randomizer.test_run import apply_test_run_env
from experimental.pikmin2_cave_items import parse_items_text
from scripts.stage_pikmin2_playable_cave import stage
from scripts.play_pikmin2_cave import live_runtime_paths, runtime_capacity


@contextmanager
def exclusive(path):
    import msvcrt
    with path.open('a+b') as lock:
        lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        yield


def package_inputs(package):
    meta = read_json(package/'package.json')
    if meta.get('schema') != 3 or meta.get('policy') != POLICY or type(meta.get('files')) is not dict:
        raise ValueError('unsupported journey package')
    for name, digest in meta['files'].items():
        path = package/name
        if (not name or Path(name).is_absolute() or '..' in Path(name).parts
                or not path.resolve().is_relative_to(package) or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise ValueError('journey package input changed: '+name)
    journey = validate(read_json(package/'journey.json'))
    if identity(journey) != meta.get('fingerprint') or set(meta.get('blueprints', {})) != {'1','2'}:
        raise ValueError('foreign journey package identity')
    for n in (1,2):
        descriptor = read_json(package/f'floor-{n}/cave.json')
        if descriptor != journey['floors'][n-1]['descriptor']:
            raise ValueError('floor descriptor differs from journey')
        if set(meta['blueprints'][str(n)]) != {'cave.json','layout.json','render.mod','collision.json',
                                               'assets/dataDir/courses/pikmin2room/room.mod'}:
            raise ValueError('missing floor geometry blueprint')
        for name, digest in meta['blueprints'][str(n)].items():
            if meta['files'].get(f'floor-{n}/{name}') != digest:
                raise ValueError('floor blueprint differs from package input')
    for name in ('journey.json','nectar.exe','cave-generator.exe','floor-1/p2-cave-items.txt','floor-2/p2-cave-items.txt'):
        if name not in meta['files']:
            raise ValueError('missing pinned journey input: '+name)
    return meta, journey


def main(package, agent_test=False):
    package = Path(package).resolve()
    meta, journey = package_inputs(package)
    workspace = Path(meta['workspace']).resolve()
    if not package.is_relative_to(workspace/'output'):
        raise ValueError('journey package must remain under its private workspace output/')
    directory = package/'session'
    directory.mkdir(exist_ok=True)
    placements = {n: parse_items_text((package/f'floor-{n}/p2-cave-items.txt').read_text()) for n in (1,2)}
    report = dict(schema=1, journey=identity(journey), children=[])
    with exclusive(directory/'launch.lock'):
        session = Session(directory, journey, placements)
        session.initialize()
        state, recovered = session.recover(live_runtime_paths())
        report['recovered_boundary'] = recovered
        report['starting_floor'] = state['floor']
        while True:
            floor = state['floor']
            spec = journey['floors'][floor-1]
            run = directory/'runs'/uuid.uuid4().hex
            # Initial ordinary entry uses stage's required Red baseline. A
            # destination entry uses only the actually committed incoming squad.
            prior = None if floor == 1 else dict(state['entry'], receipts=session.ledger(floor))
            stage(spec['descriptor'],Path(meta['assets']),Path(meta['pod']),
                  package/'nectar.exe',package/'cave-generator.exe',run,spec['salt'],prior)
            for name, digest in meta['blueprints'][str(floor)].items():
                if hashlib.sha256((run/name).read_bytes()).hexdigest() != digest:
                    raise ValueError('regenerated floor geometry differs from pinned package: '+name)
            session.begin(run, state)
            env = os.environ.copy()
            for key in list(env):
                if key.startswith(('PIKMIN_CAVE_','PIKMIN_P2_','PIKMIN_RANDOMIZER_AUTOPLAY')):
                    del env[key]
            env['PIKMIN_RANDOMIZER_AUTOPLAY'] = '0'
            env['PIKMIN_P2_ITEM_RECEIPT_PATH'] = str(session.ledger_path(floor))
            env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
            if agent_test:
                env['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS'] = '1'
                apply_test_run_env(env, workspace)
            else:
                env.pop('PIKMIN_RANDOMIZER_TEST_BACKGROUND',None)
                env.pop('PIKMIN_RANDOMIZER_TEST_VISIBLE',None)
            command = [sys.executable,str(workspace/'scripts/run_pikmin2_fixture.py'),
                       '--exe',str(run/'nectar.exe'),'--run-dir',str(run),
                       '--arg=--experimental-pikmin2-room','--pass-marker','P2_CAVE_RESTORE','--timeout','60']
            # Hold shared admission only until the real native child emits
            # output (or its wrapper exits), rather than serializing gameplay.
            with (run/'supervisor.log').open('w',encoding='utf-8') as log:
                with exclusive(Path(tempfile.gettempdir())/'pikmin-randomizer-runtime-admission.lock'):
                    runtime_capacity()
                    child = subprocess.Popen(command,cwd=workspace,env=env,stdout=log,stderr=subprocess.STDOUT)
                    native_log = run/'native.log'
                    while child.poll() is None and (not native_log.exists() or native_log.stat().st_size == 0):
                        time.sleep(.1)
                child.wait()
            raw = json.loads((run/'run-result.json').read_text())
            code = raw.get('exit_code')
            report['children'].append(dict(floor=floor,run=str(run),exit_code=code,
                                           elapsed_seconds=raw.get('elapsed_seconds')))
            if raw.get('timed_out') or raw.get('captain_down') or code not in (0,42):
                atomic_write(directory/'last-launch.json',json.dumps(report,indent=2)+'\n')
                raise RuntimeError('native journey failed; preserved pending run: '+str(run))
            has_transfer = (run/'p2-cave-transfer.txt').exists()
            if code == 42 and not has_transfer:
                raise ValueError('native42 missing actual transfer')
            if code == 0 and has_transfer:
                raise ValueError('unsaved exit unexpectedly supplied a boundary')
            state, transitioned = session.recover()
            if code == 42 and not transitioned:
                raise ValueError('native boundary did not commit')
            if transitioned:
                print('Actual floor1 boundary committed. Launching generated floor2 with incoming survivors.',flush=True)
                continue
            report.update(final_floor=state['floor'],revision=state['revision'],entry=state['entry'])
            atomic_write(directory/'last-launch.json',json.dumps(report,indent=2)+'\n')
            print('Journey stopped on floor '+str(state['floor'])+'; relaunch retains that floor and its boundary squad.')
            return report
