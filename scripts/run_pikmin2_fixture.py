"""Fail-fast, bounded launcher for already staged private native fixture arenas."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from run_pikmin2_cave_fixture import supervise

ROOT = Path(__file__).resolve().parents[1]


def launch(exe, directory, args, markers, timeout=60, toolchain=Path('C:/msys64/mingw64/bin')):
    directory = Path(directory).resolve(strict=True)
    if not directory.is_relative_to((ROOT / 'output').resolve()):
        raise ValueError('Fixture run must be staged under private output/')
    result_path = directory / 'run-result.json'
    if result_path.exists() or (directory / 'native.log').exists():
        raise ValueError('Use a fresh run directory; existing evidence is preserved')
    try:
        if not math.isfinite(timeout) or not 0 < timeout <= 300:
            raise ValueError('Fixture timeout must be 1-300 seconds')
        if not markers or any(not m.strip() for m in markers):
            raise ValueError('Explicit expected fixture PASS marker required')
        exe = Path(exe).resolve(strict=True)
        inputs = {}
        for relative in ['dataDir/consFont.bti', 'dataDir/bigFont.bti']:
            path = directory / 'assets' / relative
            if path.is_junction() or not path.is_file() or path.stat().st_size < 32:
                raise ValueError(f'Missing/unreadable staged boot asset: {path}')
            inputs[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        dlls = {}
        for name in ['libstdc++-6.dll', 'libgcc_s_seh-1.dll', 'libwinpthread-1.dll']:
            path = toolchain / name
            dlls[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            local = exe.parent / name
            if local.exists() and hashlib.sha256(local.read_bytes()).hexdigest() != dlls[name]:
                raise ValueError(f'Conflicting executable-local runtime DLL: {local}')
        env = {k:v for k,v in os.environ.items() if k.lower() != 'path'}
        env['PATH'] = str(toolchain) + os.pathsep + os.environ.get('PATH', '')
        env.update(SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540')
        provenance = dict(exe=str(exe), exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                          cwd=str(directory), boot_assets=inputs, runtime_dlls=dlls)
        (directory / 'run-inputs.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    except (OSError, ValueError) as error:
        result = dict(passed=False, launched=False, error=str(error))
        result_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
        return result
    return supervise([str(exe), *args], directory, timeout, env, required_markers=markers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--arg', action='append', default=[])
    parser.add_argument('--pass-marker', action='append', required=True)
    args = parser.parse_args()
    result = launch(args.exe, args.run_dir, args.arg, args.pass_marker, args.timeout)
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
