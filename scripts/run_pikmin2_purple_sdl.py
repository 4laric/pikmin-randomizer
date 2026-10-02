"""Pinned Purple SDL acquisition and initialized-captain guard acceptance.
Use one reviewed root checkout with the portable overlay and admitted executable.
Preflight never stages assets or launches native. Save/resume requires reviewed successor pins.
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
import time

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
    p.add_argument('--mode', choices=('sdl_acquire', 'sdl_save_resume', *GUARDS), required=True)
    p.add_argument('--profile', choices=('ordinary-off',), required=True)
    p.add_argument('--preflight-only', action='store_true')
    p.add_argument('--development-launch', action='store_true',
                   help='Use the owned private development launcher without controller admission')
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
                canonical_root=a.root, session_root=a.session,
                development_launch=getattr(a, 'development_launch', False))
        finally:
            stop.set()
            thread.join()
        report['raw_run'] = result
        if os.name != 'nt' and not getattr(a, 'development_launch', False):
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
        report['source_binding'] = ('Private development launch: executable hash verified; native/root/source pins are metadata qualified by separate build provenance'
                                    if getattr(a, 'development_launch', False) else 'controller native/root commit pins+native source digest+target/source path+executable hash and exact SDL mode; native_source_sha256 separately recorded artifact provenance'
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


def validate_checkpoint(data, *, filename, fingerprint, maturity, benefit_count, check_count):
    if not (type(maturity) is int and 0 <= maturity <= 2 and type(benefit_count) is int and 3 <= benefit_count <= 7):
        raise ValueError("Invalid pinned expectations")
    if type(check_count) is not int or check_count < 0 or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ValueError("Invalid seed expectations")
    if filename != "00000000000000000001.sav":
        raise ValueError("Expected exactly first native generation")
    header, card = data.split(b"\n", 1)
    if len(card) != 32768:
        raise ValueError("Native card payload size mismatch")
    fields = header.decode("ascii").split(" ")
    if len(fields) != 3 + benefit_count + 6 + 1 or fields[:3] != ["PIKMIN_CAMPAIGN_PURPLE_1", fingerprint, "1"]:
        raise ValueError("Checkpoint seed/version/generation/schema mismatch")
    if any(not re.fullmatch(r"0|[1-9][0-9]*", x) for x in fields[3:]):
        raise ValueError("Noncanonical native integer")
    used = list(map(int, fields[3:3+benefit_count]))
    if any(x > check_count for x in used):
        raise ValueError("Consumed benefit out of native range")
    stock = list(map(int, fields[3+benefit_count:-1]))
    expected = [0]*6
    expected[maturity] = 1
    if stock != expected:
        raise ValueError("Expected one Purple of saved maturity, no White/duplicate stock")
    checksum = 14695981039346656037
    for byte in header.rsplit(b" ", 1)[0] + b"\n" + card:
        checksum = ((checksum ^ byte)*1099511628211) & ((1 << 64)-1)
    if int(fields[-1]) != checksum:
        raise ValueError("Checkpoint checksum mismatch")
    return {"sha256": hashlib.sha256(data).hexdigest(), "generation": 1, "stock": stock, "card_bytes": len(card)}


# Output-only save/resume extension. Requires a separately reviewed native successor.
def checkpoint_schema(bootstrap):
    rows = bootstrap.read_text(encoding='ascii').splitlines()
    matches = [line.split() for line in rows if line.startswith('BENEFITS ')]
    require(len(matches) == 1 and len(matches[0]) == 2, 'One actual bootstrap BENEFITS row required')
    value = int(matches[0][1])
    require(1 <= value <= 32, 'Unsupported bootstrap BENEFITS flags')
    bits = value - 1
    return 7 if bits & 16 else 6 if bits & 8 else 5 if bits & 4 else 4 if bits & 1 else 3


def genuine_card(session_dir, *, fingerprint, maturity, benefit_count, check_count):
    campaign = session_dir / 'campaign'
    require(campaign.is_dir() and not campaign.is_symlink() and not campaign.is_junction(), 'Real private campaign directory required')
    require(campaign.resolve().parent == session_dir.resolve(), 'Campaign directory escaped session')
    cards = list(campaign.glob('*.sav'))
    require(len(cards) == 1, 'Exactly one genuine native checkpoint required')
    card = cards[0]
    require(card.is_file() and not card.is_symlink() and not card.is_junction(), 'Checkpoint must be a regular nonlink file')
    require(card.resolve().parent == campaign.resolve() and card.stat().st_nlink == 1, 'Checkpoint escaped session or aliases another file')
    require(card.stat().st_size <= 34000, 'Oversized checkpoint')
    data = validate_checkpoint(card.read_bytes(), filename=card.name, fingerprint=fingerprint,
        maturity=maturity, benefit_count=benefit_count, check_count=check_count)
    return dict(data, path=str(card), fingerprint=fingerprint, maturity=maturity)


def native_success(result, log, handshaken, errors):
    require(not errors and handshaken, 'Actual handshake/heartbeat failed')
    require(result.get('passed') and result.get('exit_code') == 0 and not result.get('timed_out')
        and not result.get('captain_down'), 'Native phase did not finish successfully')
    require(result.get('timeout_seconds') == 60 and 0 < result.get('elapsed_seconds', 0) <= 60,
        'Native phase exceeded strict60 budget')
    require(type(result.get('pid')) is int and result['pid'] > 0, 'Native process identity missing')
    if os.name != 'nt':
        require(result.get('owned_process_group') == result['pid'], 'Native owned process group missing')
    require('P2_FIXTURE_WINDOW width=960 height=540' in log, 'Window evidence missing')


def save_observations(result, log, handshaken, errors):
    native_success(result, log, handshaken, errors)
    acquisition = oracle('sdl_acquire', result, log, handshaken, errors)
    require(acquisition.get('selection') == '4' and acquisition.get('strength') == '10', 'Acquired Purple identity/strength missing')
    begin = fields(log, 'P2_PURPLE_ORDINARY_SAVE_BEGIN')
    saved = fields(log, 'P2_PURPLE_ORDINARY_SAVE_PASS')
    for key in ('direct_stock_helpers', 'clock_advanced'):
        require(begin.get(key) == '0' and saved.get(key) == '0', 'Save shortcut: ' + key)
    require(begin.get('SDL_menu_input') == '1' and begin.get('field') == '20' and begin.get('stock') == '0', 'Ordinary fresh save baseline missing')
    require(saved.get('stock') == '1' and saved.get('generations') == '1'
        and saved.get('external_checkpoint_validation_required') == '1', 'Native save evidence missing')
    day, maturity = int(saved['day']), int(saved['maturity'])
    require(day == int(saved['day_before']) + 1 and saved['day_before'] == begin['day']
        and day == int(begin['expected_day']) and saved['maturity'] == begin['maturity'] and 0 <= maturity <= 2, 'Save day/maturity changed')
    commits = re.findall(r'^\[Pikmin Randomizer\] CAMPAIGN_SAVED generation=(\d+)$', log, re.M)
    require(commits == ['1'], 'Exactly one actual native commit required')
    markers = ['P2_PURPLE_SDL_START ', 'P2_VIOLET_WITNESS ', 'P2_VIOLET_CONVERT ',
               'P2_PURPLE_SDL_ACQUISITION_PASS ', 'P2_PURPLE_ORDINARY_SAVE_BEGIN ',
               '[Pikmin Randomizer] CAMPAIGN_SAVED generation=1', 'P2_PURPLE_ORDINARY_SAVE_PASS ']
    require([log.index(p) for p in markers] == sorted(log.index(p) for p in markers), 'Save markers out of order')
    require(not re.search(r'^P2_PURPLE_(?:PERSIST|SCRIPTED_THROW)', log, re.M), 'Legacy persistence/scripted route forbidden')
    return {'acquisition': acquisition, 'begin': begin, 'saved': saved, 'day': day, 'maturity': maturity}


def resume_observations(result, log, handshaken, errors, expected):
    native_success(result, log, handshaken, errors)
    data = fields(log, 'P2_PURPLE_ORDINARY_RESUME_PASS')
    for key, value in {'day': str(expected['day']), 'maturity': str(expected['maturity']), 'stock': '1',
            'native_population': '20', 'generations': '1', 'checkpoint_resumed': '1',
            'direct_stock_helpers': '0', 'withdrawal_ui_validated': '0', 'saved_bytes_injected': '0'}.items():
        require(data.get(key) == value, 'Resume mismatch: ' + key)
    require('CAMPAIGN_SAVED' not in log and 'P2_PURPLE_SDL_ACQUISITION_PASS' not in log
        and 'P2_VIOLET_WITNESS' not in log and 'P2_VIOLET_CONVERT' not in log
        and not re.search(r'^P2_PURPLE_(?:PERSIST|SCRIPTED_THROW)', log, re.M), 'Resume unexpectedly reacquired or wrote a save')
    return data


def stage_save_run(a, m, manifest, session):
    run = m['randomizer.runner'].NativeRun(session, purple_campaign=True)
    run.write_state(True)
    m['experimental.pikmin2_family_install'].install_layout(run.directory,
        manifest['p2_layout'], a.content, actor_bindings={b['target']: int(b['target']) for b in manifest['p2_layout']['bindings']},
        retail_assets=a.assets, cache_dir=a.session / 'p2-content-cache')
    m['randomizer.purple_campaign'].stage_campaign(run.directory, a.assets, a.bank, a.motion, manifest)
    verify_imports(a.root)
    immutable = {str(p.relative_to(run.directory)): digest(p) for p in run.directory.glob('p2*.txt')}
    bootstrap = Path(run.bootstrap).resolve(strict=True)
    require(bootstrap.is_relative_to(run.directory.resolve()), 'Bootstrap escaped actual NativeRun')
    immutable[bootstrap.relative_to(run.directory.resolve()).as_posix()] = digest(bootstrap)
    frozen = {'assets': inventory(run.directory / 'assets'), 'immutable_files': immutable}
    write_new(run.directory / 'save-staged-inputs.json', frozen)
    return run, frozen


def launch_save_phase(a, m, run, frozen, mode, expected=None):
    report = {'mode': mode, 'passed': False, 'run': str(run.directory), 'timeout_seconds': 60}
    stop, errors = threading.Event(), []
    # Clear inherited expectations/injections. Never copy a predecessor's process environment blindly.
    saved_env = {k: v for k, v in os.environ.items() if k.startswith('P2_PURPLE_') or k == 'P2_FIXTURE_FORCE_CAPTAIN_DOWN'}
    for key in saved_env:
        os.environ.pop(key, None)
    os.environ.update(PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', PIKMIN_P2_ROOM_WINDOW='960x540', P2_PURPLE_COMBAT_MODE=mode)
    if expected:
        os.environ.update(P2_PURPLE_EXPECT_DAY=str(expected['day']), P2_PURPLE_EXPECT_MATURITY=str(expected['maturity']))
    def pulse():
        while not stop.wait(.2):
            try:
                run.poll()
                run.write_state(True)
            except Exception as error:
                errors.append(repr(error))
                return
    thread = threading.Thread(target=pulse, daemon=True)
    try:
        thread.start()
        markers = ['P2_PURPLE_SDL_ACQUISITION_PASS', 'P2_PURPLE_ORDINARY_SAVE_PASS'] if mode == 'sdl_dayend' else ['P2_PURPLE_ORDINARY_RESUME_PASS']
        try:
            result = m['run_pikmin2_fixture'].launch(a.exe, run.directory, ['--randomizer-seed', str(run.bootstrap)],
                markers, 60, toolchain=a.exe.parent if os.name == 'nt' else None, canonical_root=a.root, session_root=a.session,
                development_launch=getattr(a, 'development_launch', False))
        finally:
            stop.set()
            thread.join()
        report['raw_run'] = result
        if os.name != 'nt' and not getattr(a, 'development_launch', False):
            proof_path = run.directory / 'admission.json'
            proof = json.loads(proof_path.read_text())
            for key, value in {'NATIVE_SHA': a.native_pin, 'PIKMIN_SHA': a.root_pin, 'FIXTURE_SOURCE_SHA256': a.native_source_sha256}.items():
                require(proof['pins'][key] == value, 'Admitted source mismatch: ' + key)
            require(proof['target'] == 'pikmin_ci_fixture_purple_combat' and proof['source'] == 'tools/preview_p2_purple_combat.cpp', 'Wrong admitted fixture')
            report['admission_sha256'] = digest(proof_path)
        run.poll()
        report.update(actual_native_run_handshake=run.handshaken, heartbeat_errors=errors)
        log_path = run.directory / 'native.log'
        log = log_path.read_text(errors='replace')
        report['native_log_sha256'] = digest(log_path)
        report['observations'] = (save_observations(result, log, run.handshaken, errors) if mode == 'sdl_dayend'
            else resume_observations(result, log, run.handshaken, errors, expected))
        require(inventory(run.directory / 'assets') == frozen['assets'], 'Staged assets changed')
        require(all(digest(run.directory / p) == sha for p, sha in frozen['immutable_files'].items()), 'Staged source input changed')
        require(digest(a.exe) == a.exe_sha256, 'Executable changed')
        report['passed'] = True
    except Exception as error:
        report['reason'] = repr(error)
    finally:
        stop.set()
        if thread.is_alive():
            thread.join()
        for key in list(os.environ):
            if key.startswith('P2_PURPLE_') or key == 'P2_FIXTURE_FORCE_CAPTAIN_DOWN':
                os.environ.pop(key, None)
        os.environ.update(saved_env)
        write_new(run.directory / 'save-phase-acceptance.json', report)
    return report


def verify_save_inputs(a, inputs, code):
    require({n: inventory(getattr(a, n)) for n in inputs} == inputs, 'Source asset input changed')
    require(git(a.root, 'rev-parse', 'HEAD') == a.root_pin and not git(a.root, 'status', '--porcelain', '--untracked-files=no'), 'Root pin/worktree changed')
    require(all(digest(a.root / p) == sha for p, sha in code.items()), 'Imported driver/code changed')
    require(digest(a.exe) == a.exe_sha256, 'Executable changed')


def record_checkpoint_boundary(a, report, session, run, boundary, schema, card):
    # Metadata only. The card is always produced by native and read by genuine_card.
    sequence = len(report['checkpoint_boundaries']) + 1
    expected = ('before_save', 'after_save', 'before_resume', 'after_resume')
    require(sequence <= len(expected) and boundary == expected[sequence - 1], 'Checkpoint boundary out of order')
    paths = sorted(str(p.relative_to(a.session)) for p in a.session.rglob('*.sav'))
    require((card is None and not paths) if boundary == 'before_save' else card is not None,
            'Checkpoint boundary lacks expected card state')
    receipt = {
        'schema_version': 1, 'sequence': sequence, 'boundary': boundary,
        'mode': 'sdl_dayend' if sequence <= 2 else 'natural_resume',
        'observed_monotonic_ns': time.monotonic_ns(), 'observed_unix_ns': time.time_ns(), 'driver_pid': os.getpid(),
        'session': str(a.session.resolve()), 'fingerprint': session.fingerprint,
        'manifest_sha256': digest(a.session / 'fixture-seed.json'),
        'root_pin': a.root_pin, 'native_pin': a.native_pin,
        'native_source_sha256': a.native_source_sha256, 'exe_sha256': a.exe_sha256,
        'run': str(run.directory.resolve()), 'run_token': run.token,
        'bootstrap_sha256': digest(run.bootstrap), 'benefit_count': schema,
        'check_count': len(session.names), 'checkpoint_paths': paths, 'cards': [] if card is None else [card],
    }
    path = a.session / ('checkpoint-boundary-%02d-%s.json' % (sequence, boundary))
    write_new(path, receipt)
    report['checkpoint_boundaries'].append({'boundary': boundary, 'path': str(path), 'sha256': digest(path)})


def execute_save_resume(a, m):
    a.session.mkdir(parents=True, exist_ok=False)
    report = {'passed': False, 'mode': a.mode, 'profile': a.profile, 'timeout_seconds_per_native_child': 60,
        'root_pin': a.root_pin, 'native_pin': a.native_pin, 'native_source_sha256': a.native_source_sha256,
        'exe_sha256': a.exe_sha256, 'phases': [], 'checkpoint_boundaries': [], 'live_AP_server': False, 'saved_bytes_injected': False,
        'scope': 'SDL acquisition/native day-save/fresh-process same-card resume; initial withdrawal fixture-assisted; no combat/delivery/ordinary withdrawal/live AP/human acceptance'}
    inputs = {n: inventory(getattr(a, n)) for n in ('assets', 'bank', 'motion', 'content')}
    code = {str(Path(module.__file__).resolve().relative_to(a.root)): digest(module.__file__) for module in m.values()}
    driver_path = Path(__file__).resolve()
    require(driver_path.is_relative_to(a.root), 'Driver must be adopted inside pinned root')
    code[str(driver_path.relative_to(a.root))] = digest(driver_path)
    write_new(a.session / 'source-inputs.json', inputs)
    write_new(a.session / 'code-inputs.json', code)
    try:
        seed = m['randomizer.seed']
        manifest = seed.generate('purple1071-haul', mode='ap', slot='Purple1071', expanded=True,
            starting_area='forest', starting_color='red', starting_flarlic=2, collection_checks=True,
            permanent_checks=True, combined_captain=True, bomb_rock_weight=1,
            goal_mode='emperor_bulblax', p2_enemies=True, p2_species=[2])
        manifest['p2_layout'] = m['experimental.pikmin2_seed_bridge'].resolve_layout(manifest['seed'], manifest['slot'], ['3640055869'], [2])
        seed.validate(manifest)
        write_new(a.session / 'fixture-seed.json', manifest)
        manifest_sha = digest(a.session / 'fixture-seed.json')
        m['randomizer.purple_campaign'].bind_campaign_mode(a.session, manifest, a.bank, a.motion)
        session = m['randomizer.session'].Session(manifest, a.session)
        first, frozen = stage_save_run(a, m, manifest, session)
        require(not list(a.session.rglob('*.sav')), 'Fresh save requires zero checkpoint files')
        schema = checkpoint_schema(first.bootstrap)
        record_checkpoint_boundary(a, report, session, first, 'before_save', schema, None)
        saved = launch_save_phase(a, m, first, frozen, 'sdl_dayend')
        report['phases'].append(saved)
        require(saved['passed'], 'Save child failed; resume not launched')
        expected = saved['observations']
        card_args = dict(fingerprint=session.fingerprint, maturity=expected['maturity'], benefit_count=schema, check_count=len(session.names))
        card = genuine_card(a.session, **card_args)
        report['checkpoint'] = card
        record_checkpoint_boundary(a, report, session, first, 'after_save', schema, card)
        require(digest(a.session / 'fixture-seed.json') == manifest_sha, 'Manifest changed during save')
        verify_save_inputs(a, inputs, code)
        # Reopen through normal APIs; no bootstrap/card/session-byte copying or construction.
        restored = m['randomizer.session'].Session(manifest, a.session)
        require(restored.fingerprint == session.fingerprint and restored.names == session.names, 'Restored session identity changed')
        second, frozen2 = stage_save_run(a, m, manifest, restored)
        require(second.directory != first.directory and second.token != first.token, 'Fresh NativeRun identity required')
        require(checkpoint_schema(second.bootstrap) == schema, 'Resume schema drift')
        before_resume = genuine_card(a.session, **card_args)
        record_checkpoint_boundary(a, report, restored, second, 'before_resume', schema, before_resume)
        require(before_resume == card, 'Card changed before resume launch')
        verify_save_inputs(a, inputs, code)
        resumed = launch_save_phase(a, m, second, frozen2, 'natural_resume', expected)
        report['phases'].append(resumed)
        require(resumed['passed'], 'Fresh resume child failed')
        require(resumed['raw_run']['pid'] != saved['raw_run']['pid'], 'Distinct native process evidence required')
        after_resume = genuine_card(a.session, **card_args)
        record_checkpoint_boundary(a, report, restored, second, 'after_resume', schema, after_resume)
        require(after_resume == card, 'Resume changed checkpoint or generation')
        require(digest(a.session / 'fixture-seed.json') == manifest_sha, 'Manifest changed during resume')
        report.update(passed=True, reason='Ordinary SDL save and fresh same-card resume passed', manifest_sha256=manifest_sha)
    except Exception as error:
        report['reason'] = repr(error)
    finally:
        try:
            after = {n: inventory(getattr(a, n)) for n in inputs}
            write_new(a.session / 'source-inputs-after.json', after)
            require(after == inputs, 'Source asset input changed')
            require(git(a.root, 'rev-parse', 'HEAD') == a.root_pin and not git(a.root, 'status', '--porcelain', '--untracked-files=no'), 'Root pin/worktree changed')
            require(all(digest(a.root / p) == sha for p, sha in code.items()), 'Imported driver/code changed')
            require(digest(a.exe) == a.exe_sha256, 'Executable changed')
        except Exception as error:
            report.update(passed=False, immutable_error=repr(error))
        write_new(a.session / 'acceptance.json', report)
    return report


def main():
    a = parser().parse_args()
    try:
        modules = preflight(a)
        if a.preflight_only:
            print(json.dumps({'preflight': True, 'staged': False, 'launched': False, 'root_pin': a.root_pin}))
            return 0
        result = execute_save_resume(a, modules) if a.mode == 'sdl_save_resume' else execute(a, modules)
        print(json.dumps(result, indent=2))
        return 0 if result['passed'] else 1
    except Exception as error:
        print(json.dumps({'passed': False, 'launched': False, 'error': repr(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
