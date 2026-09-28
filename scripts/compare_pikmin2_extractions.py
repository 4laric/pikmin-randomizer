"""Compare private extraction trees without excluding or normalizing file contents."""
import argparse
import hashlib
import json
from pathlib import Path


def manifest(root):
    root = Path(root).absolute()
    if not root.is_dir() or root.resolve() != root:
        raise ValueError('Expected an existing, non-linked directory')
    files = {}

    def visit(directory):
        for path in sorted(directory.iterdir()):
            if path.is_symlink() or path.resolve() != path.absolute():
                raise ValueError(f'Linked path: {path}')
            if path.is_dir():
                visit(path)
            elif path.is_file():
                before = path.stat()
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(block)
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError(f'File changed while reading: {path}')
                files[path.relative_to(root).as_posix()] = {
                    'size': after.st_size, 'sha256': digest.hexdigest()}
            else:
                raise ValueError(f'Unsupported path: {path}')

    visit(root)
    if not files:
        raise ValueError('Empty extraction tree')
    return dict(sorted(files.items()))


def compare(left, right):
    manifests = [manifest(left), manifest(right)]
    a, b = manifests
    changed = sorted(name for name in a.keys() & b.keys() if a[name] != b[name])
    only_left, only_right = sorted(a.keys() - b.keys()), sorted(b.keys() - a.keys())
    return {
        'schema': 1,
        'identical': not (changed or only_left or only_right),
        'changed': changed, 'only_left': only_left, 'only_right': only_right,
        'trees': [dict(root=str(Path(root).absolute()), files=files,
                       file_count=len(files), total_bytes=sum(f['size'] for f in files.values()),
                       sha256=hashlib.sha256(json.dumps(files, sort_keys=True,
                           separators=(',', ':')).encode('utf-8')).hexdigest())
                  for root, files in zip((left, right), manifests)],
    }


def write_report(left, right, output):
    output = Path(output).absolute()
    for root in (left, right):
        if output.resolve().is_relative_to(Path(root).resolve()):
            raise ValueError('Report must be outside input trees')
    if output.exists():
        raise ValueError('Refusing existing report')
    result = compare(left, right)
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--left', required=True, type=Path)
    parser.add_argument('--right', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = write_report(args.left, args.right, args.output)
    print(json.dumps({key: result[key] for key in ('identical', 'changed', 'only_left', 'only_right')}))
    return 0 if result['identical'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
