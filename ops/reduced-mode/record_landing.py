"""Record the integration receipt for a reduced-mode lane whose work is already on the canonical lines.

A lane that reached handoff_ready keeps its pool worker until it is `done`, and only an integration
receipt makes it done. This builds that receipt from what landed and submits it through the release's
own `receipt` command, which re-proves every changed file against the landed commits (workflow/landing.py).

  record_landing.py --root <ws> --lane <key> [--validation <log>] [--dry-run]

- root_commit / native_commit default to the current heads of the declared integration lines
  (config.json integration_lines), which must contain the lane's branch head.
- validation: the build/test log you merge-tested with (hashed into the receipt). Required unless --dry-run.
- export evidence: a JSON written here recording that the native line head is on its push remote
  (`git ls-remote`), since the reduced-mode export is the push by land-batch.ps1.
- --dry-run runs landing.inspect only and prints the problems integrate would refuse with.
  A lane that changed no files needs --already-landed (the receipt then names the commit holding its bytes).

A file the landing changed after the lane (a merge resolution, e.g. a CMakeLists union) makes
landing.prove refuse "does not contain the reviewed bytes"; declare it with --port FILE (repeatable),
which needs the lane's shared review approved first (see docs/PIKMIN2_REDUCED_MODE_INTEGRATOR.md).
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

RELEASE = Path(__file__).resolve().parents[2]


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--lane', required=True)
    p.add_argument('--validation', type=Path)
    p.add_argument('--root-commit')
    p.add_argument('--native-commit')
    p.add_argument('--already-landed', action='store_true')
    p.add_argument('--port', action='append', default=[], help='FILE changed by the landing after the lane (needs an approved review)')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args(argv)
    sys.path.insert(0, str(RELEASE))
    from workflow.registry import Registry
    from workflow import landing
    root = a.root.resolve()
    config = json.loads((root / 'output/workflow/controller/config.json').read_text(encoding='utf-8-sig'))
    lines = config['integration_lines']
    reg = Registry(root / 'output/workflow/registry.sqlite3', root)
    lane = reg.snapshot()['lanes'][a.lane]
    root_line = root / lines['root']['repo']
    native_line = root / lines['native']['repo']
    record = dict(root_commit=a.root_commit or git(root_line, 'rev-parse', lines['root']['ref']))
    if a.already_landed:
        record['kind'] = 'already_landed'
    if lane.get('native'):
        record['native_commit'] = a.native_commit or git(native_line, 'rev-parse', lines['native']['ref'])
    if a.port:
        record['ports'] = [dict(repo='native' if lane.get('native') else 'root', file=f) for f in a.port]
    attestation, problems = landing.inspect(root, lane, record)
    print(json.dumps(dict(lane=a.lane, state=lane['state'], generation=lane['generation'], record=record,
                          files_changed=attestation['files_changed'], problems=[x['detail'] for x in problems]), indent=1))
    if a.dry_run:
        return 1 if problems else 0
    if problems:
        raise SystemExit('Refused: fix the problems above (land the bytes, --already-landed, or --port) first')
    if not a.validation or not a.validation.is_file():
        raise SystemExit('--validation <merge-test log> is required')
    out = root / 'output/reduced' / a.lane
    out.mkdir(parents=True, exist_ok=True)
    validation = out / 'receipt-validation.log'
    validation.write_bytes(a.validation.read_bytes())
    record.update(validation_path=str(validation.relative_to(root)).replace('\\', '/'), validation_sha256=sha256(validation))
    if lane.get('native'):
        remote = lines['native'].get('remote', 'fork')
        pushed = git(native_line, 'ls-remote', remote, lines['native']['ref']).split()[:1]
        export = out / 'receipt-export.json'
        export.write_text(json.dumps(dict(action='pushed', remote=remote, ref=lines['native']['ref'],
                                          remote_head=pushed[0] if pushed else None, native_commit=record['native_commit']),
                                     indent=1), encoding='utf-8')
        if not pushed or not git(native_line, 'merge-base', '--is-ancestor', record['native_commit'], pushed[0]) == '':
            raise SystemExit(f'native_commit is not on {remote}/{lines["native"]["ref"]}; push the line first')
        record.update(native_dirty='' if not git(native_line, 'status', '--porcelain', '--untracked-files=no') else 'dirty',
                      export_evidence=str(export.relative_to(root)).replace('\\', '/'), export_sha256=sha256(export))
    request = out / 'receipt-request.json'
    request.write_text(json.dumps(dict(key=a.lane, generation=lane['generation'], record=record,
                                       root_worktree=lines['root']['repo'],
                                       native_worktree=lines['native']['repo'] if lane.get('native') else None), indent=1),
                       encoding='utf-8')
    return subprocess.run([sys.executable, str(RELEASE / 'scripts/pikmin2_workflow.py'), '--root', str(root),
                           '--request', str(request), 'receipt']).returncode


if __name__ == '__main__':
    raise SystemExit(main())
