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


def export(source=ROOT / 'native', target=ROOT / 'engine'):
    source = Path(source)
    target = Path(target)
    names = subprocess.check_output(['git', '-C', str(source), 'ls-files', '-z']).decode().split('\0')
    count = 0
    for name in filter(None, names):
        path = Path(name)
        if path.parts[0] in {'.github', '.vscode'} or path.suffix.lower() in {'.exe', '.gz'}:
            continue
        data = (source / path).read_bytes()
        if b'\0' in data:
            raise ValueError(f'Unexpected binary source: {name}')
        out = target / path
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / path, out)
        count += 1
    print(f'Exported {count} source files from {source} (no history, binaries or local untracked files).')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'native',
                        help='native worktree/checkout to export (default: native/)')
    parser.add_argument('--target', type=Path, default=ROOT / 'engine',
                        help='engine snapshot destination (default: engine/)')
    args = parser.parse_args()
    export(args.source, args.target)
