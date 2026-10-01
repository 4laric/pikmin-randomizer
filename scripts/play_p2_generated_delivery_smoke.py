"""Short, fresh-session physical-input source44 AP smoke (#1131)."""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_p2_generated_delivery import prepare
from randomizer.runner import ap_connect

ARCHIVE_SHA = '4b4f015f1a76e8ffc89fecda26bf4d2ed2e0b1cbc2f015720e27e628d5695ead'
MANIFEST_SHA = '3214e1186af72e6d5c427d4535a7f01eddbab9c157604d91ebd4f80ee04c05fe'
MODES = ('human', 'ready', 'down', 'missing', 'reset')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def game_environment(mode, toolchain):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('PIKMIN_', 'P2_', 'COOP_')) and k != 'SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS'}
    env['PATH'] = str(toolchain) + os.pathsep + env.get('PATH', '')
    env['PIKMIN_RANDOMIZER_AUTOPLAY'] = '0'
    # Inherit into the child CRT; SDL_setenv alone is insufficient on Windows.
    env['PIKMIN_RANDOMIZER_TEST_BACKGROUND'] = '2' if mode == 'human' else '1'
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    if mode == 'ready': env['P2_GENERATED_MANUAL_READY_ONLY'] = '1'
    if mode == 'down': env['P2_GENERATED_MANUAL_FORCE_CAPTAIN_DOWN'] = '1'
    if mode == 'missing': env['P2_GENERATED_MANUAL_FORCE_MISSING_CAPTAIN'] = '1'
    return env


def stop_owned(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)


async def attempt(args, index):
    folder = args.workspace / 'output' / 'p2-generated-manual' / (uuid.uuid4().hex + f'-{index}')
    server = folder / 'ap'; server.mkdir(parents=True)
    historical = args.workspace / 'output/generated-delivery-consumer-1119/private-ap-01'
    source_archive = historical / 'generated/AP_p2-journal-1096.zip'
    source_manifest = historical / 'actual-manifest.json'
    if digest(source_archive) != ARCHIVE_SHA or digest(source_manifest) != MANIFEST_SHA:
        raise ValueError('Original genuine AP archive/manifest hash mismatch')
    archive = server / 'original.zip'; shutil.copyfile(source_archive, archive)
    manifest = json.loads(source_manifest.read_text())
    (server / 'actual-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
    template = (historical / 'server.py').read_text()
    old_archive = (historical / 'generated/AP_p2-journal-1096.zip').as_posix()
    template = template.replace('38411', str(port)).replace(old_archive, archive.as_posix())
    if archive.as_posix() not in template or old_archive in template:
        raise ValueError('Private AP template archive substitution failed')
    script = server / 'server.py'; script.write_text(template)
    audit, session, run = prepare(folder / 'stage', args.content, args.assets,
                                  supplied_manifest=manifest, minimal_surroundings=False)
    game = Path(audit['game'])
    cache = args.workspace / 'output/generated-delivery-consumer-1119/run-01/game/shader_cache'
    if cache.is_dir(): shutil.copytree(cache, game / 'shader_cache')
    provenance = json.loads(args.fixture.with_name('provenance.json').read_text())
    entry = provenance.get('artifacts', {}).get(str(args.fixture))
    if provenance.get('status') != 'built' or not entry or entry['sha256'] != digest(args.fixture):
        raise ValueError('Manual fixture must match its built provenance')
    # Canonical supervisor only launches/kills the native child it owns.
    sys.path.insert(0, str(args.workspace / 'scripts'))
    spec = importlib.util.spec_from_file_location('manual_owned_supervisor', args.workspace / 'scripts/run_pikmin2_cave_fixture.py')
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    env = game_environment(args.mode, args.toolchain)
    for name in ('libstdc++-6.dll', 'libgcc_s_seh-1.dll', 'libwinpthread-1.dll'):
        local = args.fixture.parent / name
        if local.exists() and digest(local) != digest(args.toolchain / name):
            raise ValueError('Conflicting executable-local DLL: ' + name)
    inputs = dict(mode=args.mode, attempt=index, archive_sha256=ARCHIVE_SHA,
                  manifest_sha256=MANIFEST_SHA, fixture_sha256=digest(args.fixture),
                  provenance_sha256=digest(args.fixture.with_name('provenance.json')),
                  native_head=provenance['expected_native_head'], native_source=provenance['source'],
                  launcher_root=str(ROOT),
                  launcher_root_head=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                  launcher_root_dirty=subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True),
                  launcher_sha256=digest(__file__),
                  bootstrap=str(run.bootstrap.resolve()), bootstrap_sha256=digest(run.bootstrap),
                  saved_bootstrap='bootstrap-input.txt',
                  server_script_sha256=digest(script), supervisor_sha256=digest(args.workspace / 'scripts/run_pikmin2_cave_fixture.py'),
                  environment={k:v for k,v in env.items() if k.startswith(('PIKMIN_', 'P2_'))},
                  full_original_surroundings=True, fresh_server_save_session=True,
                  native_timeout_seconds=args.seconds, human_judgment_recorded=False)
    shutil.copyfile(run.bootstrap, folder / 'bootstrap-input.txt')
    (folder / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
    connection = heartbeat = None; process = None
    with (server / 'server.log').open('w') as log:
        server_env = os.environ.copy(); server_env.update(PYTHONUTF8='1', PYTHONPATH=str(ROOT))
        try:
            process = subprocess.Popen([sys.executable, str(script)], cwd=server, env=server_env,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            deadline = time.monotonic() + 30
            while 'PRIVATE_AP_SERVER_READY' not in (server / 'server.log').read_text(errors='replace'):
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError('Fresh private AP server did not become ready')
                await asyncio.sleep(.1)
            ready = [False]
            connection = asyncio.create_task(ap_connect(session, f'ws://127.0.0.1:{port}', '', ready))
            deadline = time.monotonic() + 20
            while not ready[0]:
                if connection.done(): await connection
                if time.monotonic() >= deadline: raise RuntimeError('Private AP authentication deadline')
                await asyncio.sleep(.1)
            if session.data['ap_identity'] is None: raise RuntimeError('Missing genuine AP identity')
            run.write_state(True)
            async def maintain():
                reset_sent = False
                while True:
                    if connection.done(): await connection
                    run.poll(); run.write_state(run.handshaken and ready[0])
                    if args.mode == 'reset' and not reset_sent:
                        native_log = game / 'native.log'
                        if native_log.exists() and 'P2_GENERATED_MANUAL_READY' in native_log.read_text(errors='replace'):
                            (game / 'manual-reset.request').write_text('automated reset-file test after actual READY\n')
                            reset_sent = True
                    await asyncio.sleep(.1)
            heartbeat = asyncio.create_task(maintain())
            print(f'Fresh attempt {index}: {folder}', flush=True)
            marker = 'P2_GENERATED_MANUAL_READY' if args.mode == 'ready' else 'PASS P2_GENERATED_MANUAL_DELIVERY'
            raw = await asyncio.to_thread(supervisor.supervise,
                [str(args.fixture), '--randomizer-seed', str(run.bootstrap.resolve())], game,
                args.seconds, env, [marker])
            if heartbeat.done(): await heartbeat
            run.poll()
            native_log = (game / 'native.log').read_text(errors='replace')
            if args.mode in ('down', 'missing'):
                accepted = raw['exit_code'] == 86 and raw['captain_down'] and not raw['timed_out'] and 'PASS P2_GENERATED_MANUAL' not in native_log
            elif args.mode == 'reset':
                accepted = raw['exit_code'] == 90 and 'P2_GENERATED_MANUAL_RESET_REQUEST' in native_log and not raw['timed_out']
            else:
                accepted = raw['passed']
            result = dict(raw=raw, bounded_mode_result=accepted, checked=list(session.data['checked']),
                          reset_requested=raw['exit_code'] == 90, human_judgment_recorded=False)
            (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            return raw['exit_code'], accepted
        finally:
            tasks = [task for task in (heartbeat, connection) if task is not None]
            for task in tasks: task.cancel()
            if tasks: await asyncio.gather(*tasks, return_exceptions=True)
            (server / 'server.stop').write_text('owned private server stop\n')
            if process is not None and process.poll() is None:
                try: await asyncio.to_thread(process.wait, timeout=5)
                except subprocess.TimeoutExpired: stop_owned(process)


async def run(args):
    for index in range(1, args.max_resets + 2):
        raw, accepted = await attempt(args, index)
        if args.mode == 'human' and raw == 90 and index <= args.max_resets:
            print('Reset requested; starting a new AP server, save and session.', flush=True)
            continue
        return 0 if accepted else raw if raw in (86, 90) else 1


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--assets', type=Path, default=Path(os.environ.get('APPDATA', '')) / 'PikminRandomizer/game-data/assets')
    parser.add_argument('--content', type=Path)
    parser.add_argument('--toolchain', type=Path, default=Path('C:/msys64/mingw64/bin'))
    parser.add_argument('--mode', choices=MODES, default='human')
    parser.add_argument('--seconds', type=int, default=60, choices=range(1, 61))
    parser.add_argument('--max-resets', type=int, default=5, choices=range(0, 21))
    args = parser.parse_args(argv)
    args.workspace = args.workspace.resolve(); args.fixture = args.fixture.resolve()
    args.toolchain = args.toolchain.resolve()
    args.assets = args.assets.resolve(); args.content = (args.content or args.workspace / 'output/p2-content-dense').resolve()
    return args


def main():
    args = parse_args()
    if args.mode == 'human':
        print('60-second enemy delivery check: physical gamepad if connected, otherwise keyboard.\n'
              'Default keyboard: WASD move/face toward target; Space throw; Shift whistle.\n'
              'Classic controls are selected; saved custom key bindings still apply.\n'
              'Find and defeat the original source44 dwarf enemy, then let Pikmin carry it to the Onion.\n'
              'F7 starts a fresh attempt. Close the window to stop. Full surroundings remain intact.\n'
              'Startup skips movies/tutorial and withdraws20 Reds from native Onion stock.\n'
              'Your gameplay judgment is not recorded automatically.', flush=True)
    return asyncio.run(run(args))


if __name__ == '__main__':
    raise SystemExit(main())
