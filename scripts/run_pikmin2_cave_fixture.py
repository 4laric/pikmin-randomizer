"""Prepare a private, readable cave overlay and supervise a real guarded boot (#671)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import math


MARKERS = ('P2_CAVE_READY', 'P2_CAVE_GENERATE_PASS', 'PASS CAVE_GUARDED_BOOT')


def clone_assets(source, destination):
    """Copy files; share only valid directory targets. Never mutate source links."""
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for entry in source.iterdir():
        target = entry
        if entry.is_junction() or entry.is_symlink():
            raw = os.readlink(entry)
            if raw.startswith(('\\??\\', '\\\\?\\')):
                raw = raw[4:]
                if raw.startswith('UNC\\'):
                    raw = '\\\\' + raw[4:]
            target = Path(raw)
            if not target.is_absolute():
                target = entry.parent / target
        dest = destination / entry.name
        if target.is_file():
            shutil.copy2(target, dest)
        elif target.is_dir():
            if entry.is_junction() or entry.is_symlink():
                import _winapi
                _winapi.CreateJunction(str(target.absolute()), str(dest.absolute()))
            else:
                clone_assets(target, dest)
        else:
            raise ValueError(f'Unreadable overlay input: {entry} -> {target}')


def prepare(source, destination):
    source, destination = Path(source).absolute(), Path(destination).absolute()
    if source == destination or source in destination.parents:
        raise ValueError('Run destination must be separate from the source run')
    destination.mkdir(parents=True, exist_ok=False)
    for name in ('p2-cave-entry.txt', 'p2-cave-generate.txt', 'p2-cave-runtime-inputs.json'):
        shutil.copy2(source / name, destination / name)
    for path in source.glob('p2-*'):
        if path.is_file():
            shutil.copy2(path, destination / path.name)
    clone_assets(source / 'assets', destination / 'assets')
    for name in ('consFont.bti', 'bigFont.bti'):
        path = destination / 'assets/dataDir' / name
        with path.open('rb') as stream:
            if not stream.read(32):
                raise ValueError(f'Empty boot font: {path}')
    return destination


def supervise(argv, directory, timeout=60, env=None, required_markers=None):
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Timeout must be positive')
    directory = Path(directory)
    log_path = directory / 'native.log'
    record = {'argv': list(map(str, argv)), 'timeout_seconds': timeout, 'passed': False}
    start = time.monotonic()
    proc = None
    try:
        with log_path.open('wb') as log:
            proc = subprocess.Popen(argv, cwd=directory, env=env, stdout=log,
                                    stderr=subprocess.STDOUT)
            record['pid'] = proc.pid
            try:
                record['exit_code'] = proc.wait(timeout=timeout)
                record['timed_out'] = False
            except subprocess.TimeoutExpired:
                record['timed_out'] = True
                proc.kill()
                record['exit_code'] = proc.wait(timeout=10)
        text = log_path.read_text(errors='replace')
        record['markers'] = {marker: marker in text for marker in
                             (MARKERS if required_markers is None else required_markers)}
        record['captain_down'] = 'P2_FIXTURE_CAPTAIN_DOWN' in text
        record['passed'] = (not record['timed_out'] and record['exit_code'] == 0
                            and all(record['markers'].values()) and not record['captain_down'])
    except BaseException as error:
        record['error'] = str(error)
        raise
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)
        record['elapsed_seconds'] = round(time.monotonic() - start, 3)
        (directory / 'run-result.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--baseline-assets', type=Path,
                        help='Explicit boot smoke test: regenerate the standard 20-Pikmin arena; not lane gameplay acceptance')
    args = parser.parse_args()
    exe = args.exe.resolve(strict=True)
    directory = prepare(args.source_run, args.run_dir)
    if args.baseline_assets:
        from preview_pikmin2_room import generator
        path = directory / 'assets/dataDir/stages/chal0/default.gen'
        if not path.resolve().is_relative_to(directory.resolve()) or path.is_junction() or path.is_symlink():
            raise ValueError('Baseline replacement requires a private arena file')
        path.write_bytes(generator(args.baseline_assets.resolve(strict=True)))
    provenance = {'exe_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
                  'baseline_smoke_only': bool(args.baseline_assets),
                  'inputs': {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in [*directory.glob('p2-*'), directory / 'assets/dataDir/stages/chal0/default.gen']
                             if path.is_file()}}
    (directory / 'run-inputs.json').write_text(json.dumps(provenance, indent=2) + '\n')
    env = dict(os.environ)
    env['SDL_AUDIODRIVER'] = 'dummy'
    record = supervise([str(exe), '--experimental-pikmin2-room'], directory, args.timeout, env)
    record.update(provenance)
    (directory / 'run-result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
