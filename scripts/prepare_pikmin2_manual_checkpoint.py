"""Copy a frozen manual cave package into a new, bounded private play profile.

No native card or gameplay state is edited. Assets remain at their legal local
source. The copied host gains a wall-clock bound; native controls are unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare(source, destination, seconds=600):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve()
    if not 30 <= seconds <= 1800:
        raise ValueError('Play duration must be 30..1800 seconds')
    if destination.exists():
        raise ValueError('Use a new destination; existing saves and logs are preserved')
    if source == destination or source in destination.parents:
        raise ValueError('Destination must be outside the source package')
    metadata = json.loads((source / 'package.json').read_text())
    assets = Path(metadata['assets']).resolve(strict=True)
    for group in ('host_files_sha256', 'launcher_sha256'):
        for name, expected in metadata[group].items():
            path = source / name
            if not path.resolve().is_relative_to(source) or digest(path) != expected:
                raise ValueError('Frozen host differs from pin: ' + name)
    for name, expected in metadata.get('sidecar_files_sha256', {}).items():
        path = source / name
        if not path.resolve().is_relative_to(source) or digest(path) != expected:
            raise ValueError('Frozen sidecar differs from pin: ' + name)
    if metadata.get('manifest_sha256') and digest(source / 'manifest.json') != metadata['manifest_sha256']:
        raise ValueError('Frozen manifest differs from pin')
    for name, expected in metadata['binaries'].items():
        path = source / 'bin' / name
        if path.resolve().parent != (source / 'bin').resolve() or digest(path) != expected:
            raise ValueError('Packaged binary differs from pin: ' + name)
    for name, expected in metadata['starting_session_sha256'].items():
        path = source / 'starting-session' / name
        if not path.resolve().is_relative_to((source / 'starting-session').resolve()):
            raise ValueError('Starting-session path escapes package')
        if digest(path) != expected:
            raise ValueError('Starting checkpoint differs from pin: ' + name)
    for name in ('consFont.bti', 'bigFont.bti'):
        if not (assets / 'dataDir' / name).is_file():
            raise ValueError('Legal local boot asset is unavailable: ' + name)
    original = (source / 'play.py').read_text()
    old = 'if args.smoke_seconds and time.monotonic()-started>=args.smoke_seconds:break'
    revised = ('if args.smoke_seconds and time.monotonic() - started >= args.smoke_seconds:\n'
               '                        break')
    if original.count(old) == 1:
        bounded = original.replace(old,
            f"if time.monotonic()-started >= (args.smoke_seconds or {seconds}):result['owned_stop_reason']='wall-clock-bound';break")
        old_return = 'return 0 if args.smoke_seconds else process.returncode'
        new_return = "return 0 if args.smoke_seconds or result.get('owned_stop_reason') == 'wall-clock-bound' else process.returncode"
    elif original.count(revised) == 1:
        bounded = original.replace(revised,
            f"if time.monotonic() - started >= (args.smoke_seconds or {seconds}):\n"
            "                        result['owned_stop_reason'] = 'wall-clock-bound'\n"
            '                        break')
        old_return = '        return process.returncode\n'
        new_return = "        return 0 if result.get('owned_stop_reason') == 'wall-clock-bound' else process.returncode\n"
    else:
        raise ValueError('Unsupported manual host version; inspect before adapting')
    if original.count(old_return) != 1:
        raise ValueError('Unsupported manual host exit handling')
    bounded = bounded.replace(old_return, new_return)
    destination.mkdir(parents=True)
    # Exact package modules, including the roster docs needed by seed validation.
    for name in ('bin', 'randomizer', 'experimental', 'docs', 'sidecars', 'starting-session'):
        shutil.copytree(source / name, destination / name,
                        ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('package.json', 'manifest.json', 'README.md'):
        shutil.copy2(source / name, destination / name)
    if (source / 'evidence').is_dir():
        shutil.copytree(source / 'evidence', destination / 'evidence')
    shutil.copytree(source / 'starting-session', destination / 'human-session')
    (destination / 'play.py').write_text(bounded, encoding='utf-8')
    (destination / 'Start.cmd').write_text(
        '@echo off\r\ncd /d "%~dp0"\r\npy -3.12 "%~dp0play.py"\r\nif errorlevel 1 pause\r\n',
        encoding='utf-8', newline='')
    receipt = dict(source=str(source), native_source=metadata['native_source'],
                   executable_sha256=metadata['binaries']['nectar.exe'],
                   assets=str(assets), play_seconds=seconds,
                   source_host_sha256=digest(source / 'play.py'),
                   bounded_host_sha256=digest(destination / 'play.py'),
                   starting_session_sha256=metadata['starting_session_sha256'],
                   gameplay_accepted=False, state_injection=False)
    (destination / 'preparation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=600)
    args = parser.parse_args()
    receipt = prepare(args.package, args.output, args.seconds)
    print(json.dumps({key: receipt[key] for key in
                      ('native_source', 'executable_sha256', 'play_seconds', 'gameplay_accepted')}))
    print('Launcher: ' + str(args.output.resolve() / 'Start.cmd'))


if __name__ == '__main__':
    main()
