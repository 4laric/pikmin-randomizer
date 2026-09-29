"""Refresh the public engine snapshot from a local native worktree/checkout.

Defaults to the shared ``native/`` checkout, but ``--source`` may point at any
native worktree (e.g. a private integration line) so exporting never has to
wait for the shared checkout to be clean. Modified tracked files are copied
from the worktree as-is; the recorded dirty baseline is expected.
"""
import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

# Binary files the native line carries for builds this snapshot does not ship
# (the Android app, its SDL copy and the touch-control layer, which desktop
# builds leave off). Binaries under these folders are skipped.
SKIPPED_BINARY_PREFIXES = (
    'android/',
    'third_party/SDL2-android/',
    'pc_port/touch/assets/',
)
# Binary build inputs the desktop build does need: the Windows resource script
# embeds packaging/icon/nectar.ico. These are copied as they are. Any other
# binary still stops the export.
COPIED_BINARY_PREFIXES = (
    'packaging/icon/',
)


def skippable_binary(name):
    return name.startswith(SKIPPED_BINARY_PREFIXES)


def export(source=None, target=None):
    source = Path(source) if source is not None else ROOT / 'native'
    target = Path(target) if target is not None else ROOT / 'engine'
    names = subprocess.check_output(['git', '-C', str(source), 'ls-files', '-z']).decode().split('\0')
    count = skipped = 0
    for name in filter(None, names):
        path = Path(name)
        if path.parts[0] in {'.github', '.vscode'} or path.suffix.lower() in {'.exe', '.gz'}:
            continue
        data = (source / path).read_bytes()
        if b'\0' in data and not name.startswith(COPIED_BINARY_PREFIXES):
            if skippable_binary(name):
                skipped += 1
                continue
            raise ValueError(f'Unexpected binary source: {name}')
        out = target / path
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / path, out)
        count += 1
    print(f'Exported {count} source files from {source} (no history, binaries or local untracked files; '
          f'{skipped} Android/touch image assets skipped).')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'native',
                        help='native worktree/checkout to export (default: native/)')
    parser.add_argument('--target', type=Path, default=ROOT / 'engine',
                        help='engine snapshot destination (default: engine/)')
    args = parser.parse_args()
    export(args.source, args.target)
