"""Verify exported engine/pc_port family files match the native family branch.

Compares the Bulblax-family source files on a native branch against their exported
copies under engine/pc_port on a root branch. Content is read straight from each
repository with `git show` so a dirty shared checkout cannot affect the result.
CRLF is normalized to LF before hashing, because the native and root checkouts can
disagree on line endings on Windows.

Exit status is 0 only when every family file is present on both sides and matches
after normalization.
"""
import argparse
import hashlib
import subprocess
from pathlib import Path

# Family-owned files on the native branch, relative to the native repo root.
# The root export is the same names under engine/pc_port/.
FAMILY_FILES = (
    'pc_p2_btk.h',
    'pc_p2_bulblax_visual.cpp',
    'pc_p2_king.cpp',
    'pc_p2_queen.cpp',
    'pc_p2_queen_policy.h',
)


def git_show(repo, rev, path):
    result = subprocess.run(
        ['git', '-C', str(repo), 'show', f'{rev}:{path}'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        return None
    return result.stdout


def resolve_rev(repo, rev):
    result = subprocess.run(
        ['git', '-C', str(repo), 'rev-parse', rev],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise SystemExit(f'Cannot resolve {rev!r} in {repo}: {result.stderr.strip()}')
    return result.stdout.strip()


def normalize_lf(data):
    return data.replace(b'\r\n', b'\n')


def sha256(data):
    return hashlib.sha256(normalize_lf(data)).hexdigest()


def check(root, native, native_rev, root_rev):
    native_commit = resolve_rev(native, native_rev)
    root_commit = resolve_rev(root, root_rev)
    print(f'native {native_rev} = {native_commit}')
    print(f'root   {root_rev} = {root_commit}')
    print(f'{"file":<30} {"native":<12} {"root":<12} {"LF-normalized SHA-256":<64} status')

    failures = []
    for name in FAMILY_FILES:
        native_bytes = git_show(native, native_commit, f'pc_port/{name}')
        root_bytes = git_show(root, root_commit, f'engine/pc_port/{name}')
        if native_bytes is None or root_bytes is None:
            missing = 'native' if native_bytes is None else 'root'
            print(f'{name:<30} {"MISSING" if native_bytes is None else "ok":<12} '
                  f'{"MISSING" if root_bytes is None else "ok":<12} {"":<64} MISSING({missing})')
            failures.append(name)
            continue
        native_raw = hashlib.sha256(native_bytes).hexdigest()
        root_raw = hashlib.sha256(root_bytes).hexdigest()
        native_norm = sha256(native_bytes)
        match = native_norm == sha256(root_bytes)
        raw = 'raw-eq' if native_raw == root_raw else 'raw-diff'
        status = 'MATCH' if match else 'MISMATCH'
        print(f'{name:<30} {native_raw[:12]:<12} {root_raw[:12]:<12} {native_norm:<64} {status} ({raw})')
        if not match:
            failures.append(name)

    return failures


def main():
    root_default = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=root_default,
                        help='root repository (default: repository containing this script)')
    parser.add_argument('--native', type=Path, default=None,
                        help='native repository (default: <root>/native)')
    parser.add_argument('--native-rev', default='opencode/p2-batch5-actor-hooks')
    parser.add_argument('--root-rev', default='opencode/p2-batch5-bulblax')
    args = parser.parse_args()
    native = args.native if args.native else args.root / 'native'
    failures = check(args.root, native, args.native_rev, args.root_rev)
    if failures:
        print(f'\n{len(failures)} mismatch(es): {", ".join(failures)}')
        return 1
    print('\nAll family files match after CRLF/LF normalization.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
