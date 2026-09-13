"""Refresh the public engine snapshot from the isolated local native checkout."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def export(source=None, destination=None):
    source = Path(source) if source is not None else ROOT / 'native'
    destination = Path(destination) if destination is not None else ROOT / 'engine'
    names = subprocess.check_output(['git', '-C', str(source), 'ls-files', '-z']).decode().split('\0')
    count = 0
    for name in filter(None, names):
        path = Path(name)
        if path.parts[0] in {'.github', '.vscode'} or path.suffix.lower() in {'.exe', '.gz'}:
            continue
        data = (source / path).read_bytes()
        if b'\0' in data:
            raise ValueError(f'Unexpected binary source: {name}')
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / path, target)
        count += 1
    print(f'Exported {count} source files (no history, binaries or local untracked files).')

if __name__ == '__main__':
    export()
