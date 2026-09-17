"""Player launch packaging for the pinned P2 seed (issue #643)."""
import hashlib
import json
from pathlib import Path

SEED_DIRNAME = 'p2-monsters-20260916'
SEED_FILENAME = 'seed.json'
GENERATOR_DIRNAME = 'generator'
SNAPSHOT_COMMIT = 'e72f350ec89321b1b6d321739baa5fb44211614d'
ADMITTED_PIN = (23, 44, 54, 57, 59, 60, 61, 62, 78)
REFUSED_IDS = frozenset({9, 79})
PLAY_CMD = 'Play.cmd'
LAUNCH_PY = 'launch.py'


class SeedRejected(ValueError):
    pass


class PreflightFailed(ValueError):
    pass


FAMILY_PROVIDERS = {
    23: {'name': 'Sarai', 'installer': 'experimental/pikmin2_bombsarai_install.py',
         'assets': ('experimental/pikmin2_sarai_assets.py',
                    'experimental/pikmin2_bombsarai_assets.py'),
         'native': ('pc_p2_bombsarai_arena.cpp', 'pc_p2_sarai_manager.cpp'),
         'sidecar_only': False},
    44: {'name': 'BlueKochappy', 'installer': 'experimental/pikmin2_dwarf_orange_install.py',
         'assets': ('experimental/pikmin2_dwarf_orange_bank.py',),
         'native': ('pc_p2_dwarf_orange.cpp', 'pc_p2_kochappy.cpp'),
         'sidecar_only': False},
    54: {'name': 'Mamuta', 'installer': 'experimental/pikmin2_mamuta_install.py',
         'assets': ('experimental/pikmin2_mamuta_assets.py',),
         'native': ('pc_p2_mamuta.cpp',),
         'sidecar_only': False},
    57: {'name': 'Kurage', 'installer': None, 'assets': (),
         'native': ('pc_p2_kurage.cpp',), 'sidecar_only': True},
    59: {'name': 'FireOtakara', 'installer': 'experimental/pikmin2_dweevil_install.py',
         'assets': ('experimental/pikmin2_dweevil_assets.py',),
         'native': ('pc_p2_dweevil.cpp', 'pc_p2_otakara.cpp'),
         'sidecar_only': False},
    60: {'name': 'WaterOtakara', 'installer': 'experimental/pikmin2_dweevil_install.py',
         'assets': ('experimental/pikmin2_dweevil_assets.py',),
         'native': ('pc_p2_dweevil.cpp', 'pc_p2_otakara.cpp'),
         'sidecar_only': False},
    61: {'name': 'GasOtakara', 'installer': 'experimental/pikmin2_dweevil_install.py',
         'assets': ('experimental/pikmin2_dweevil_assets.py',),
         'native': ('pc_p2_dweevil.cpp', 'pc_p2_otakara.cpp'),
         'sidecar_only': False},
    62: {'name': 'ElecOtakara', 'installer': 'experimental/pikmin2_dweevil_install.py',
         'assets': ('experimental/pikmin2_dweevil_assets.py',),
         'native': ('pc_p2_dweevil.cpp', 'pc_p2_otakara.cpp'),
         'sidecar_only': False},
    78: {'name': 'MiniHoudai', 'installer': None, 'assets': (),
         'native': (), 'sidecar_only': True},
}


def sha256_file(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_seed(seed_dir):
    seed_dir = Path(seed_dir)
    try:
        return json.loads((seed_dir / SEED_FILENAME).read_text(encoding='utf-8'))
    except OSError as exc:
        raise SeedRejected('Cannot read seed: ' + str(exc))
    except ValueError as exc:
        raise SeedRejected('Seed is not valid JSON: ' + str(exc))


def validate_seed(seed):
    if not isinstance(seed, dict):
        raise SeedRejected('Seed must be a JSON object')
    if seed.get('game') != 'Pikmin Randomizer':
        raise SeedRejected('Not a Pikmin Randomizer seed')
    if seed.get('seed') != 'p2-monsters-20260916' or seed.get('slot') != 'Player1':
        raise SeedRejected('Seed/slot mismatch for p2-monsters-20260916 Player1')
    layout = seed.get('p2_layout')
    if not isinstance(layout, dict) or not isinstance(layout.get('bindings'), list):
        raise SeedRejected('Missing p2_layout bindings')
    ids = set()
    for binding in layout['bindings']:
        if not isinstance(binding, dict):
            raise SeedRejected('Malformed p2 binding')
        source_id = binding.get('source_id')
        if type(source_id) is not int:
            raise SeedRejected('P2 binding without integer source_id')
        if source_id in REFUSED_IDS:
            raise SeedRejected('Refused non-pinned identity in bindings: %d' % source_id)
        if source_id not in ADMITTED_PIN:
            raise SeedRejected('Binding outside admitted pin: %d' % source_id)
        ids.add(source_id)
    if set(ids) != set(ADMITTED_PIN):
        raise SeedRejected('Bindings do not cover exactly the admitted pin: %s' % sorted(ids))
    return {'bindings': len(layout['bindings']), 'identities': sorted(ids)}
def audit_content(seed, tree_root, native_root=None):
    tree_root = Path(tree_root)
    native_root = Path(native_root) if native_root else None
    summary = validate_seed(seed)
    report = {}
    for source_id in summary['identities']:
        provider = FAMILY_PROVIDERS[source_id]
        entry = {'name': provider['name'], 'sidecar_only': provider['sidecar_only'],
                 'installer': None, 'assets': {}, 'native': {}, 'ok': False, 'gap': None}
        if provider['sidecar_only']:
            entry['gap'] = ('sidecar-only identity (muse_packaging stages sidecars, '
                            'no full asset installation)')
            report[source_id] = entry
            continue
        installer_path = tree_root / provider['installer']
        if not installer_path.is_file():
            entry['gap'] = 'missing family installer: ' + provider['installer']
            report[source_id] = entry
            continue
        entry['installer'] = provider['installer']
        missing_assets = [a for a in provider['assets']
                          if not (tree_root / a).is_file()]
        entry['assets'] = {a: (tree_root / a).is_file() for a in provider['assets']}
        if missing_assets:
            entry['gap'] = 'missing family assets: ' + ', '.join(missing_assets)
            report[source_id] = entry
            continue
        if native_root is None:
            entry['gap'] = 'no native tree provided for binding check'
            report[source_id] = entry
            continue
        missing_native = []
        for module in provider['native']:
            found = (native_root / 'pc_port' / module).is_file() or (native_root / module).is_file()
            entry['native'][module] = found
            if not found:
                missing_native.append(module)
        if missing_native:
            entry['gap'] = 'missing native host module: ' + ', '.join(missing_native)
            report[source_id] = entry
            continue
        entry['ok'] = True
        report[source_id] = entry
    return report


def preflight(seed_dir, tree_root, native_root=None, native_exe=None):
    seed_dir = Path(seed_dir)
    seed = load_seed(seed_dir)
    summary = validate_seed(seed)
    report = audit_content(seed, tree_root, native_root)
    gaps = []
    for source_id in summary['identities']:
        gap = report[source_id]['gap']
        if gap:
            gaps.append('%d %s: %s' % (source_id, report[source_id]['name'], gap))
    evidence = {
        'seed': str(seed_dir / SEED_FILENAME),
        'seed_sha256': sha256_file(seed_dir / SEED_FILENAME),
        'snapshot': SNAPSHOT_COMMIT,
        'generator': str(seed_dir / GENERATOR_DIRNAME),
        'identities': summary['identities'],
        'bindings': summary['bindings'],
    }
    if native_exe is not None:
        exe_path = Path(native_exe)
        if exe_path.is_file():
            evidence['native_exe'] = str(exe_path)
            evidence['native_exe_sha256'] = sha256_file(exe_path)
        else:
            gaps.append('native executable missing: %s' % exe_path)
    else:
        gaps.append('no native executable provided')
    return (not gaps, gaps, evidence)


def session_dir(seed_dir, base=None):
    root = Path(base) if base else Path.home() / 'AppData' / 'Roaming' / 'PikminRandomizer'
    return root / 'sessions' / SEED_DIRNAME


def play_cmd_text(session_path, python_cmd, launch_name, seed_dir):
    lines = [
        '@echo off',
        'setlocal',
        'rem PLAYER launch for p2-monsters-20260916 (issue #643). Double-click to play.',
        'rem Runs preflight first; refuses ordinary P1 content when P2 content is missing.',
        'set "SEED_DIR=%~dp0"',
        'set "SESSION=' + session_path + '"',
        '"' + python_cmd + '" "' + launch_name + '" --seed-dir "' + seed_dir + '" --launch || pause',
    ]
    return '\r\n'.join(lines) + '\r\n'


def launch_py_text(snapshot, generator_dirname, tree_dir, native_dir_or_null, exe_or_null):
    lines = [
        '"""Checked PLAYER launcher for p2-monsters-20260916 (issue #643)."""',
        'import sys',
        'from pathlib import Path',
        '',
        'SEED_DIR = Path(__file__).resolve().parent',
        'SNAPSHOT = "' + snapshot + '"',
        '',
        '',
        'def main(argv):',
        '    import argparse',
        '    parser = argparse.ArgumentParser()',
        '    parser.add_argument("--seed-dir", type=Path, default=SEED_DIR)',
        '    parser.add_argument("--launch", action="store_true")',
        '    args = parser.parse_args(argv)',
        '    sys.path.insert(0, str(Path(__file__).resolve().parent / "' + generator_dirname + '"))',
        '    from experimental.pikmin2_player_package import preflight',
        '    ok, gaps, evidence = preflight(args.seed_dir, Path(__file__).resolve().parent / "' + generator_dirname + '", ' + native_dir_or_null + ', ' + exe_or_null + ')',
        '    print("preflight ok=" + str(ok))',
        '    for gap in gaps:',
        '        print("GAP: " + gap)',
        '    if not ok:',
        '        raise SystemExit("Refusing PLAYER launch: missing P2 content. No P1 fallback.")',
        '    if args.launch:',
        '        print("Launching pinned session; native handshake follows from the executable.")',
        '    return 0',
        '',
        '',
        'if __name__ == "__main__":',
        '    raise SystemExit(main(sys.argv[1:]))',
    ]
    return '\n'.join(lines) + '\n'


def write_launch_package(seed_dir, tree_dir, native_dir_or_null, exe_or_null, session_base=None):
    seed_dir = Path(seed_dir)
    ok, gaps, evidence = preflight(seed_dir, tree_dir, native_dir_or_null, exe_or_null)
    if not ok:
        raise PreflightFailed('; '.join(gaps))
    session = session_dir(seed_dir, session_base)
    play = play_cmd_text(str(session), 'py -3.12', LAUNCH_PY, str(seed_dir))
    (seed_dir / PLAY_CMD).write_text(play, encoding='utf-8', newline='')
    launch = launch_py_text(SNAPSHOT_COMMIT, GENERATOR_DIRNAME, str(tree_dir),
                            repr(native_dir_or_null), repr(exe_or_null))
    (seed_dir / LAUNCH_PY).write_text(launch, encoding='utf-8', newline='')
    return {'play_cmd': str(seed_dir / PLAY_CMD), 'launch_py': str(seed_dir / LAUNCH_PY),
            'session': str(session), 'evidence': evidence}
