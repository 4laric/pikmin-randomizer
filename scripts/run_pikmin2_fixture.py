"""Fail-fast, bounded launcher for already staged private native fixture arenas."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from fixture_platform import is_windows, runtime_evidence, linux_admission, linux_development_context

from run_pikmin2_cave_fixture import supervise

ROOT = Path(__file__).resolve().parents[1]


def launch(exe, directory, args, markers, timeout=60, toolchain=None, *, canonical_root=None, session_root=None,
           development_launch=False):
    directory = Path(directory).resolve(strict=True)
    canonical_root = Path(canonical_root or ROOT).resolve(strict=True)
    if not directory.is_relative_to((canonical_root / 'output').resolve()):
        raise ValueError('Fixture run must be staged under private output/')
    if session_root is not None and not directory.is_relative_to(Path(session_root).resolve(strict=True)):
        raise ValueError('Fixture run must belong to the supplied session')
    result_path = directory / 'run-result.json'
    if result_path.exists() or (directory / 'native.log').exists():
        raise ValueError('Use a fresh run directory; existing evidence is preserved')
    try:
        if type(development_launch) is not bool:
            raise ValueError('Development execution must be an explicit boolean choice')
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
        env = dict(os.environ)
        runtime = runtime_evidence(exe, toolchain, env, include_sdl=False, cwd=directory)
        if is_windows():
            env = {k:v for k,v in env.items() if k.lower() != 'path'}
            env['PATH'] = runtime['runtime_directory'] + os.pathsep + os.environ.get('PATH', '')
        env.update(SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540')
        provenance = dict(exe=str(exe), exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                          cwd=str(directory), boot_assets=inputs, runtime=runtime,
                          execution_mode='development' if development_launch else 'controller' if not is_windows() else 'windows')
        if is_windows():
            provenance['runtime_dlls'] = runtime['dlls']
        if not is_windows():
            if development_launch:
                context = linux_development_context(exe, canonical_root, session_root or directory, directory, runtime)
                provenance['development_execution'] = context
                (directory / 'development-execution.json').write_text(json.dumps(context, indent=2), encoding='utf-8')
            else:
                if canonical_root != ROOT.resolve():
                    raise ValueError('Linux launcher must use its own pinned root checkout')
                admission = linux_admission(exe, canonical_root, session_root or directory, directory)
                if admission['exe_sha256'] != runtime['executable']['sha256']:
                    raise ValueError('Executable changed between dependency inspection and admission')
                (directory / 'admission.json').write_text(json.dumps(admission, indent=2), encoding='utf-8')
        elif session_root is not None:
            # Preserve captain admission policy; generic Windows fixtures retain their existing behavior.
            admission = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command',
                "$o=Get-CimInstance Win32_OperatingSystem;$g=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -match 'nectar|fixture.*exe'});@{ram=100*(1-$o.FreePhysicalMemory/$o.TotalVisibleMemorySize);games=$g.Count}|ConvertTo-Json"], text=True))
            ram, games = admission.get('ram'), admission.get('games')
            if (type(ram) not in (int, float) or not math.isfinite(ram) or not 0 <= ram <= 90
                    or type(games) is not int or not 0 <= games < 6):
                raise ValueError('Captain runtime capacity admission rejected')
            (directory / 'admission.json').write_text(json.dumps(admission, indent=2), encoding='utf-8')
        (directory / 'run-inputs.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
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
    parser.add_argument('--development-launch', action='store_true',
                        help='Explicit private development execution; Linux uses real ELF/capacity evidence instead of controller proof')
    args = parser.parse_args()
    result = launch(args.exe, args.run_dir, args.arg, args.pass_marker, args.timeout, development_launch=args.development_launch)
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
