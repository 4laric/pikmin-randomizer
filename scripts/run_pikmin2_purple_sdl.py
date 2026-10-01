"""Pinned Purple SDL acquisition and initialized-captain guard acceptance.
Use one reviewed root checkout with the portable overlay and admitted executable.
Preflight never stages assets or launches native. No save/resume mode is exposed.
"""
import argparse
import ast
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading

GUARDS = ('health', 'manager', 'global', 'dead_state', 'missing', 'health_pause', 'missing_movie')
ROOT_MODULES = ('randomizer.seed', 'randomizer.session', 'randomizer.runner',
                'randomizer.purple_campaign', 'experimental.pikmin2_family_install',
                'experimental.pikmin2_seed_bridge', 'scripts.preview_pikmin2_room',
                'fixture_platform', 'run_pikmin2_fixture')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def write_new(path, data):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('root', 'assets', 'bank', 'motion', 'content', 'exe', 'session'):
        p.add_argument('--' + key, type=Path, required=True)
    for key in ('root-pin', 'native-pin', 'overlay-sha256', 'platform-sha256', 'exe-sha256', 'native-source-sha256'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--mode', choices=('sdl_acquire', *GUARDS), required=True)
    p.add_argument('--profile', choices=('ordinary-off',), required=True)
    p.add_argument('--preflight-only', action='store_true')
    return p


def portable_overlay_ready(source):
    tree = ast.parse(source)
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'overlay'), None)
    require(fn is not None, 'Overlay entry point missing')
    # Recognize the existing reviewed1174 early Linux return before _winapi.
    portable_return = None
    windows_import = len(fn.body)
    for index, node in enumerate(fn.body):
        if isinstance(node, ast.Import) and any(x.name == '_winapi' for x in node.names):
            windows_import = min(windows_import, index)
        if (isinstance(node, ast.If) and isinstance(node.test, ast.UnaryOp)
                and isinstance(node.test.op, ast.Not) and isinstance(node.test.operand, ast.Call)
                and isinstance(node.test.operand.func, ast.Name) and node.test.operand.func.id == 'is_windows'
                and len(node.body) == 1 and isinstance(node.body[0], ast.Return)
                and isinstance(node.body[0].value, ast.Call)
                and isinstance(node.body[0].value.func, ast.Name)
                and node.body[0].value.func.id == 'copy_private_tree'):
            portable_return = index
    require(portable_return is not None and portable_return < windows_import,
            'Reviewed1174 early Linux copy seam absent; Windows-only overlay refused')


def preflight(a):
    for name in ('root', 'assets', 'bank', 'motion', 'content'):
        value = getattr(a, name).resolve(strict=True)
        require(value.is_dir(), name + ' must be a directory')
        setattr(a, name, value)
    a.exe = a.exe.resolve(strict=True)
    require(a.exe.is_file(), 'Executable must be a file')
    require(not os.path.lexists(a.session), 'Fresh session required')
    a.session = a.session.resolve()
    private = (a.root / 'output').resolve()
    require(a.session != private and a.session.is_relative_to(private), 'Session must be beneath pinned root/output')
    for source in (a.assets, a.bank, a.motion, a.content):
        require(not a.session.is_relative_to(source) and not source.is_relative_to(a.session), 'Input/session overlap')
    require(re.fullmatch('[0-9a-f]{40}', a.root_pin), 'Exact root commit required')
    require(re.fullmatch('[0-9a-f]{40}', a.native_pin), 'Exact native commit required')
    for name in ('overlay_sha256', 'platform_sha256', 'exe_sha256', 'native_source_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', getattr(a, name)), 'Exact SHA256 required: ' + name)
    require(git(a.root, 'rev-parse', 'HEAD') == a.root_pin, 'Root commit mismatch')
    require(not git(a.root, 'status', '--porcelain', '--untracked-files=no'), 'Tracked root checkout must be clean')
    require(digest(a.exe) == a.exe_sha256, 'Executable mismatch')
    overlay = a.root / 'scripts/preview_pikmin2_room.py'
    platform = a.root / 'scripts/fixture_platform.py'
    require(digest(overlay) == a.overlay_sha256, 'Reviewed overlay source mismatch')
    require(digest(platform) == a.platform_sha256, 'Reviewed platform helper mismatch')
    # Never silently replace the shared overlay or synthesize a platform shim.
    if os.name != 'nt':
        portable_overlay_ready(overlay.read_text(encoding='utf-8'))
    for module in ROOT_MODULES:
        require(module not in sys.modules, 'Root module already imported before pin validation: ' + module)
    sys.path[:0] = [str(a.root), str(a.root / 'scripts')]
    modules = {name: importlib.import_module(name) for name in ROOT_MODULES}
    verify_imports(a.root)
    launch = modules['run_pikmin2_fixture'].launch
    require({'canonical_root', 'session_root'} <= set(inspect.signature(launch).parameters), 'Portable launcher API absent')
    require(Path(modules['run_pikmin2_fixture'].ROOT).resolve() == a.root, 'Launcher root differs')
    return modules


def verify_imports(root):
    for name, module in list(sys.modules.items()):
        if (name.split('.')[0] in ('randomizer', 'experimental', 'scripts')
                or name.startswith('run_pikmin2_') or name == 'fixture_platform'):
            path = getattr(module, '__file__', None)
            if path:
                require(Path(path).resolve().is_relative_to(root), 'Foreign root import: ' + name)


def inventory(directory):
    result = {}
    def walk(path, relative, ancestors):
        real = path.resolve(strict=True)
        if real.is_dir():
            require(real not in ancestors, 'Source directory link cycle')
            for child in sorted(path.iterdir()):
                walk(child, relative / child.name, ancestors | {real})
        else:
            require(real.is_file(), 'Nonregular input')
            result[relative.as_posix()] = {'size': real.stat().st_size, 'sha256': digest(real)}
    walk(directory, Path(), set())
    return result


def fields(log, prefix):
    lines = [line for line in log.splitlines() if line.startswith(prefix + ' ')]
    require(len(lines) == 1, prefix + ' expected exactly once')
    return dict(re.findall(r'(\w+)=([^ ]+)', lines[0]))


def oracle(mode, result, log, handshaken, errors):
    require(not errors, 'Heartbeat failed: ' + repr(errors))
    require(handshaken, 'Actual NativeRun capability handshake missing')
    require('P2_FIXTURE_WINDOW width=960 height=540' in log, 'Window adoption evidence missing')
    require(not result.get('timed_out'), '60-second child timed out')
    if mode == 'sdl_acquire':
        marker = 'P2_PURPLE_SDL_ACQUISITION_PASS'
        require(result.get('passed') and not result.get('captain_down'), 'Bounded positive failed')
        require('P2_PURPLE_SDL_START field=20 red=20' in log, 'Starting live20 Reds missing')
        require('P2_PURPLE_SCRIPTED_THROW' not in log and 'scripted_throw=1' not in log, 'Scripted throw evidence forbidden')
        require(re.findall(r'^P2_VIOLET_WITNESS sequence=\d+ generator=(\d+) input=(\w+)$', log, re.M)
                == [('1347768321', 'red')], 'Original Violet single Red witness missing')
        require(re.findall(r'^P2_VIOLET_CONVERT count=(\d+)$', log, re.M) == ['1'], 'Single conversion missing')
        require(log.index('P2_VIOLET_WITNESS') < log.index(marker), 'Conversion must precede acquisition')
        data = fields(log, marker)
        for key in ('scripted_throw', 'direct_throw_api', 'actor_state_writes'):
            require(data.get(key) == '0', key + ' must be zero')
        for key in ('native_throw_state_observed', 'SDL_pluck'):
            require(data.get(key) == '1', key + ' missing')
        require((data.get('field'), data.get('red'), data.get('purple')) == ('20', '19', '1'), 'Population mismatch')
        return data
    require(result.get('exit_code') == 86 and result.get('captain_down'), 'Initialized guard must exit86')
    expected = {'P2_PURPLE_GUARD_ARMED', 'P2_PURPLE_GUARD_INJECTED', 'P2_FIXTURE_CAPTAIN_DOWN'}
    require(set(result.get('markers', {})) == expected and all(result['markers'][key] is True for key in expected), 'Guard marker set incomplete')
    require(not re.search(r'^P2_PURPLE_\w*_PASS(?:\s|$)', log, re.M), 'Positive PASS in guard case')
    armed = fields(log, 'P2_PURPLE_GUARD_ARMED')
    injected = fields(log, 'P2_PURPLE_GUARD_INJECTED')
    down = fields(log, 'P2_FIXTURE_CAPTAIN_DOWN')
    require(armed['case'] == mode and armed['initialized'] == '1' and int(armed['tick']) > 0, 'Guard not initialized')
    require(float(armed['health_before']) > 1 and int(armed['field']) == 20 and int(armed['state']) in (0, 17), 'Guard baseline invalid')
    require(down['tick'] == armed['tick'], 'Guard must fail in same engine frame')
    if mode.startswith('health'):
        require(float(down['hp']) == 0, 'Health guard mismatch')
    if mode.startswith('missing'):
        require(down['present'] == '0' and injected['manager_present'] == '0', 'Missing guard mismatch')
    for case, key in (('manager', 'manager_dead'), ('global', 'orima_dead'), ('dead_state', 'dead_state')):
        if mode == case:
            require(down[key] == '1', 'Guard condition missing')
    if mode == 'health_pause':
        require(injected['pause'] == '1', 'Pause injection missing')
    if mode == 'missing_movie':
        require(injected['movie'] == '1', 'Movie injection missing')
    return {'armed': armed, 'injected': injected, 'down': down}


def execute(a, m):
    a.session.mkdir(parents=True, exist_ok=False)
    report = {'passed': False, 'mode': a.mode, 'profile': a.profile, 'timeout_seconds': 60,
              'root_pin': a.root_pin, 'native_pin': a.native_pin, 'native_source_sha256': a.native_source_sha256,
              'exe_sha256': a.exe_sha256, 'scope': 'SDL acquisition or initialized guard only; native starting withdrawal fixture; no save/resume/combat/delivery/ordinary withdrawal claim'}
    inputs = {name: inventory(getattr(a, name)) for name in ('assets', 'bank', 'motion', 'content')}
    write_new(a.session / 'source-inputs.json', inputs)
    code_inputs = {str(Path(module.__file__).resolve().relative_to(a.root)): digest(module.__file__)
                   for module in m.values()}
    write_new(a.session / 'code-inputs.json', code_inputs)
    run = None
    try:
        seed = m['randomizer.seed']
        manifest = seed.generate('purple1071-haul', mode='ap', slot='Purple1071', expanded=True,
            starting_area='forest', starting_color='red', starting_flarlic=2, collection_checks=True,
            permanent_checks=True, combined_captain=True, bomb_rock_weight=1,
            goal_mode='emperor_bulblax', p2_enemies=True, p2_species=[2])
        manifest['p2_layout'] = m['experimental.pikmin2_seed_bridge'].resolve_layout(manifest['seed'], manifest['slot'], ['3640055869'], [2])
        seed.validate(manifest)
        write_new(a.session / 'fixture-seed.json', manifest)
        campaign = m['randomizer.purple_campaign']
        campaign.bind_campaign_mode(a.session, manifest, a.bank, a.motion)
        session = m['randomizer.session'].Session(manifest, a.session)
        run = m['randomizer.runner'].NativeRun(session, purple_campaign=True)
        run.write_state(True)
        installed = m['experimental.pikmin2_family_install'].install_layout(run.directory,
            manifest['p2_layout'], a.content, actor_bindings={r['target']: int(r['target']) for r in manifest['p2_layout']['bindings']},
            retail_assets=a.assets, cache_dir=a.session / 'p2-content-cache')
        purple = campaign.stage_campaign(run.directory, a.assets, a.bank, a.motion, manifest)
        verify_imports(a.root)
        write_new(a.session / 'fixture-setup.json', {'run': str(run.directory), 'bootstrap': str(run.bootstrap),
            'bindings': installed['bindings'], 'purple': purple, 'local_state_heartbeat': True, 'live_AP_server': False})
        staged_assets = inventory(run.directory / 'assets')
        immutable = {str(p.relative_to(run.directory)): digest(p) for p in run.directory.glob('p2*.txt')}
        bootstrap = Path(run.bootstrap).resolve(strict=True)
        require(bootstrap.is_relative_to(run.directory.resolve()), 'Bootstrap outside actual run')
        immutable[bootstrap.relative_to(run.directory.resolve()).as_posix()] = digest(bootstrap)
        write_new(a.session / 'staged-inputs.json', {'assets': staged_assets, 'immutable_files': immutable})
        os.environ.update(PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', PIKMIN_P2_ROOM_WINDOW='960x540', P2_PURPLE_COMBAT_MODE='sdl_acquire')
        for key in ('P2_PURPLE_GUARD_CASE', 'P2_FIXTURE_FORCE_CAPTAIN_DOWN', 'P2_PURPLE_AIM_SCALE'):
            os.environ.pop(key, None)
        if a.mode in GUARDS:
            os.environ['P2_PURPLE_GUARD_CASE'] = a.mode
        stop, errors = threading.Event(), []
        def pulse():
            while not stop.wait(.2):
                try:
                    run.poll()
                    run.write_state(True)
                except Exception as error:
                    errors.append(repr(error))
                    return
        thread = threading.Thread(target=pulse, daemon=True)
        thread.start()
        markers = (['P2_PURPLE_GUARD_ARMED', 'P2_PURPLE_GUARD_INJECTED', 'P2_FIXTURE_CAPTAIN_DOWN']
                   if a.mode in GUARDS else ['P2_PURPLE_SDL_ACQUISITION_PASS'])
        try:
            result = m['run_pikmin2_fixture'].launch(a.exe, run.directory, ['--randomizer-seed', str(run.bootstrap)],
                markers, 60, toolchain=a.exe.parent if os.name == 'nt' else None,
                canonical_root=a.root, session_root=a.session)
        finally:
            stop.set()
            thread.join()
        report['raw_run'] = result
        if os.name != 'nt':
            proof = json.loads((run.directory / 'admission.json').read_text())
            require(proof['pins']['NATIVE_SHA'] == a.native_pin, 'Admitted native commit mismatch')
            require(proof['pins']['PIKMIN_SHA'] == a.root_pin, 'Admitted root commit mismatch')
            require(proof['target'] == 'pikmin_ci_fixture_purple_combat', 'Wrong admitted fixture target')
            require(proof['source'] == 'tools/preview_p2_purple_combat.cpp', 'Wrong admitted fixture source')
            require(proof['pins']['FIXTURE_SOURCE_SHA256'] == a.native_source_sha256, 'Admitted native source bytes mismatch')
        run.poll()
        report.update(actual_native_run_handshake=run.handshaken, heartbeat_errors=errors)
        logpath = run.directory / 'native.log'
        require(logpath.is_file(), 'Launcher refused before native log; inspect raw_run')
        log = logpath.read_text(errors='replace')
        report['native_log_sha256'] = digest(logpath)
        report['observations'] = oracle(a.mode, result, log, run.handshaken, errors)
        require(digest(a.exe) == a.exe_sha256, 'Executable changed')
        require(inventory(run.directory / 'assets') == staged_assets, 'Staged assets changed')
        require(all(digest(run.directory / name) == value for name, value in immutable.items()), 'Immutable staged input changed')
        after = {name: inventory(getattr(a, name)) for name in inputs}
        write_new(a.session / 'source-inputs-after.json', after)
        require(after == inputs, 'Source input changed during staging/runtime')
        require(git(a.root, 'rev-parse', 'HEAD') == a.root_pin, 'Root pin changed')
        require(not git(a.root, 'status', '--porcelain', '--untracked-files=no'), 'Root tracked files changed')
        require(all(digest(a.root / name) == value for name, value in code_inputs.items()), 'Imported code changed')
        report['source_binding'] = ('controller native/root commit pins+native source digest+target/source path+executable hash and exact SDL mode; native_source_sha256 separately recorded artifact provenance'
                                    if os.name != 'nt' else 'Windows artifact/source provenance requires separate reviewed receipt; log fields alone do not certify source')
        report.update(passed=True, reason='Bounded initialized guard PASS' if a.mode in GUARDS else 'Bounded SDL acquisition PASS')
    except Exception as error:
        report['reason'] = repr(error)
    finally:
        after_path = a.session / 'source-inputs-after.json'
        if not after_path.exists():
            try:
                after = {name: inventory(getattr(a, name)) for name in inputs}
                write_new(after_path, after)
                if after != inputs:
                    report.update(passed=False, source_immutability_error='Source input changed')
            except Exception as error:
                report.update(passed=False, source_immutability_error=repr(error))
        if run is not None:
            write_new(a.session / 'output-evidence.json', inventory(run.directory))
        write_new(a.session / 'acceptance.json', report)
    return report


def main():
    a = parser().parse_args()
    try:
        modules = preflight(a)
        if a.preflight_only:
            print(json.dumps({'preflight': True, 'staged': False, 'launched': False, 'root_pin': a.root_pin}))
            return 0
        result = execute(a, modules)
        print(json.dumps(result, indent=2))
        return 0 if result['passed'] else 1
    except Exception as error:
        print(json.dumps({'passed': False, 'launched': False, 'error': repr(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
