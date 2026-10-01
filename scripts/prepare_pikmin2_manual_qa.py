"""Prepare and guard a private manual one-trip QA launch; never automate gameplay."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from scripts.bundle_pikmin2_fixture import bundle, pe_imports, sha256
from scripts.compare_pikmin2_extractions import manifest

REQUIRED = ('assets', 'source_import', 'pocket', 'treasure', 'pod1', 'pod2', 'purple', 'imported')
OPTIONAL = ('transitions', 'snow', 'roster', 'transition_assets')


def inventory(path):
    path = Path(path).absolute()
    if path.resolve() != path or path.is_symlink():
        raise ValueError(f'Linked input: {path}')
    if path.is_file():
        return {'file': sha256(path)}
    return {'tree': manifest(path)}


def source_inventory(source):
    files = {}
    for directory in ('scripts', 'experimental', 'randomizer'):
        root = source / directory
        if not root.is_dir():
            raise ValueError('Missing launcher source directory')
        for path in sorted(root.rglob('*.py')):
            if path.resolve() != path.absolute():
                raise ValueError('Linked launcher source')
            files[path.relative_to(source).as_posix()] = sha256(path)
    return files


def prepare(config, output, objdump, dll_roots, system_directory):
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('New output required; never reuse a historical session')
    source = Path(__file__).resolve().parents[1]
    if set(config) != {'surface_exe', 'cave_exe', 'assets'}:
        raise ValueError('Expected surface_exe, cave_exe and assets config keys')
    assets = config['assets']
    if not isinstance(assets, dict) or not set(REQUIRED) <= assets.keys() or set(assets) - set(REQUIRED + OPTIONAL):
        raise ValueError('Invalid asset argument set')
    assets = {key: str(Path(value).absolute()) for key, value in assets.items()}
    inputs = {key: inventory(path) for key, path in assets.items()}
    before = source_inventory(source)
    if output.parent.resolve() != output.parent or not output.parent.is_dir():
        raise ValueError('Expected existing non-linked output parent')
    output.mkdir()
    exes = {}
    for role in ('surface', 'cave'):
        result = bundle(Path(config[role + '_exe']), dll_roots, system_directory,
                        output / role, lambda path: pe_imports(path, objdump))
        exes[role] = str(output / role / result['executable'])
    command = [sys.executable, '-m', 'scripts.play_pikmin2_surface']
    for key, value in assets.items():
        command.extend(['--' + key.replace('_', '-'), value])
    command += ['--surface-exe', exes['surface'], '--cave-exe', exes['cave'],
                '--output', str(output / 'session')]
    record = dict(schema=1, source=str(source), source_files=before,
                  python=dict(path=sys.executable, binary=str(Path(sys.base_prefix) / 'python.exe'),
                              sha256=sha256(Path(sys.base_prefix) / 'python.exe')),
                  assets=assets, inputs=inputs, command=command,
                  runtime={role: manifest(output / role) for role in exes},
                  session=str(output / 'session'), gameplay_validated=False)
    # Check again after potentially lengthy copies; no manifest on failed preparation.
    if source_inventory(source) != before or any(inventory(assets[k]) != v for k, v in inputs.items()):
        raise ValueError('Source/assets changed during preparation')
    with (output / 'qa-launch.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    return record


def check(path):
    path = Path(path).absolute()
    record = json.loads(path.read_text(encoding='utf-8'))
    if record.get('schema') != 1:
        raise ValueError('Unsupported QA manifest')
    source = Path(record['source'])
    if source_inventory(source) != record['source_files']:
        raise ValueError('Launcher source changed; retain the original checkout')
    if sha256(Path(record['python']['binary'])) != record['python']['sha256']:
        raise ValueError('Python executable changed')
    for key, value in record['inputs'].items():
        if inventory(record['assets'][key]) != value:
            raise ValueError(f'Asset input changed: {key}')
    for role, value in record['runtime'].items():
        if manifest(path.parent / role) != value:
            raise ValueError(f'Runtime bundle changed: {role}')
    expected = [record['python']['path'], '-m', 'scripts.play_pikmin2_surface']
    for key, value in record['assets'].items():
        expected += ['--' + key.replace('_', '-'), value]
    for role in ('surface', 'cave'):
        runtime = json.loads((path.parent / role / 'runtime-provenance.json').read_text())
        expected += ['--' + role + '-exe', str(path.parent / role / runtime['executable'])]
    expected += ['--output', str(path.parent / 'session')]
    if record['command'] != expected or record['session'] != str(path.parent / 'session'):
        raise ValueError('Launch command differs from declared inputs')
    if Path(record['session']).exists():
        raise ValueError('Fresh-session launch only; session already exists and is preserved')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    prep = sub.add_parser('prepare')
    for name in ('config', 'output', 'objdump', 'system-directory'):
        prep.add_argument('--' + name, type=Path, required=True)
    prep.add_argument('--dll-root', action='append', type=Path, required=True)
    for mode in ('check', 'launch'):
        sub.add_parser(mode).add_argument('manifest', type=Path)
    args = parser.parse_args()
    if args.mode == 'prepare':
        result = prepare(json.loads(args.config.read_text(encoding='utf-8-sig')), args.output,
                         args.objdump, args.dll_root, args.system_directory)
        print(json.dumps(dict(prepared=True, command=result['command'])))
    else:
        result = check(args.manifest)
        if args.mode == 'launch':
            return subprocess.run(result['command'], cwd=result['source']).returncode
        print(json.dumps(dict(checked=True, command=result['command'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
