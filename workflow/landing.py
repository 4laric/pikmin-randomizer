"""Prove that a receipt's commits contain the bytes a lane produced; read-only, bounded git.

For root and native separately, every file the lane changed between its recorded base
and head must be blob-identical at the receipt commit, reachable through ancestry, or
covered by an explicit per-file port declaration. Git never fetches here, and any git
error refuses the receipt.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from .handoff import Rejected, digest, local_path, nonempty, require
from .provenance import cli

SHA, HEX64 = re.compile(r'[0-9a-f]{40}'), re.compile(r'[0-9a-f]{64}')
KINDS = ('landed', 'already_landed')
CONFIG = 'output/workflow/controller/config.json'  # Controller config; integration_lines is read, never written.
DEFAULT_REPOS = {'root': '.', 'native': 'native'}
ENGINE = {'root': ('engine/', 'include/'), 'native': ('pc_port/', 'src/', 'include/', 'cmake/', 'CMakeLists.txt')}
PORT_FIELDS = {'repo', 'file', 'reviewed_blob', 'landed_blob', 'interdiff_sha256', 'reason', 'evidence'}
# interdiff_sha256 is the sha256 of the stdout of:
#   git --literal-pathspecs <INTERDIFF> <lane head> <receipt commit> -- <file>
INTERDIFF = ('diff', '--no-color', '--no-ext-diff', '--no-textconv', '--no-renames', '--no-relative', '--full-index',
             '-U3', '--inter-hunk-context=0', '--indent-heuristic', '--diff-algorithm=myers',
             '--src-prefix=a/', '--dst-prefix=b/')
TIMEOUT = 120
_REDIRECTS = ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_COMMON_DIR',
              'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_NAMESPACE', 'GIT_REPLACE_REF_BASE', 'GIT_CONFIG_PARAMETERS')
INSTRUCTION = (' Landing proof: integrate verifies, per repository, that every file the lane changed base..head is '
    'blob-identical at root_commit/native_commit or that the lane head is an ancestor of it, and that the commit is on the '
    'declared integration line (or, if none is declared, on a branch other than the lane\'s own worktree branch). Run '
    'integrate from inside your own live launch session: the lander is that session (optional lander {lane, generation} '
    'must name it). For a file you had to adapt or leave out, '
    'add record.ports entries {repo root|native, file, reviewed_blob, landed_blob (null if left out), interdiff_sha256 '
    '(sha256 of the stdout of: git --literal-pathspecs ' + ' '.join(INTERDIFF) +
    ' <lane head> <receipt commit> -- <file>), reason, '
    'evidence {path,sha256}}; ports of #186 shared-review or engine files (root engine/, include/; native pc_port/, src/, '
    'include/, cmake/, CMakeLists.txt) need an approved landing review at exactly <lane head>..<receipt commit> recorded '
    'by another authenticated lane (never you) through ' + cli('approvals') + ' landing-review; without it, hand those '
    'back instead of adapting or excluding them. When the bytes were already landed or the lane changed nothing, set record.kind "already_landed" '
    'and name the commit that actually contains them. Never merge or pull with -X ours/theirs or -s ours, reset --hard, '
    'clean -f, checkout --ours/--theirs or <ref> -- <path>, restore, or force-push in maintained worktrees.')


def git(repo, *args, stdin=None, codes=(0,), timeout=TIMEOUT, env=None):
    """(exit code, stdout bytes) of one bounded, non-fetching git call; anything else refuses.

    env adds variables after the inherited redirects are removed (shipping points merge-tree's
    object writes at a scratch directory)."""
    environment = {k: v for k, v in os.environ.items() if k not in _REDIRECTS}
    environment.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0', GIT_NO_REPLACE_OBJECTS='1',
                       **(env or {}))
    command = ['git', '--no-replace-objects', '-c', 'protocol.allow=never', '-C', str(repo), *args]
    try:
        p = subprocess.run(command, input=stdin, capture_output=True, timeout=timeout, env=environment,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise Rejected(f"Landing git call failed ({' '.join(args[:2])} in {repo}): {str(exc) or type(exc).__name__}")
    if p.returncode not in codes:
        raise Rejected(f"Landing git call failed ({' '.join(args[:2])} in {repo}): "
                       + p.stderr.decode('utf-8', 'replace').strip()[:300])
    return p.returncode, p.stdout


def lines(root):
    """Declared {root|native: {repo, ref}} from the controller config; {} when none is declared."""
    path = Path(root) / CONFIG
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise Rejected('Controller config unreadable for integration_lines: ' + str(exc))
    declared = data.get('integration_lines') if isinstance(data, dict) else None
    if declared is None:
        return {}
    require(isinstance(declared, dict) and set(declared) <= set(DEFAULT_REPOS) and all(
        isinstance(v, dict) and nonempty(v.get('repo')) and nonempty(v.get('ref')) and not v['ref'].startswith('-')
        for v in declared.values()), 'integration_lines must map root/native to {repo, ref}')
    return declared


def repository(root, name, declared):
    """The working tree whose objects prove this side; a nested non-repo never falls back to its parent."""
    path = local_path(root, (declared.get(name) or {}).get('repo') or DEFAULT_REPOS[name])
    require(path.is_dir(), f'{name} repository missing: {path}')
    top = git(path, 'rev-parse', '--show-toplevel')[1].decode('utf-8', 'replace').strip()
    require(top and Path(top).resolve() == path, f'{name} repository {path} is not a git working tree root')
    return path


def objects(repo, names):
    """{name: (objectname, type) or None} through one cat-file batch; names never contain newlines."""
    if not names:
        return {}
    require(all('\n' not in n and '\r' not in n for n in names), 'Path with a line break cannot be verified')
    out = git(repo, 'cat-file', '--batch-check=%(objectname) %(objecttype)',
              stdin=''.join(n + '\n' for n in names).encode('utf-8', 'surrogateescape')  # Git's own path bytes.
              )[1].decode('utf-8', 'surrogateescape').splitlines()
    require(len(out) == len(names), 'Unexpected cat-file output in ' + str(repo))
    result = {}
    for name, line in zip(names, out):
        if line == name + ' missing':
            result[name] = None
            continue
        parts = line.split(' ')
        require(len(parts) == 2 and re.fullmatch(r'[0-9a-f]{40,64}', parts[0]), f'Cannot resolve {name}: {line}')
        result[name] = tuple(parts)
    return result


def changes(repo, base, head):
    """[(status, path)] the lane changed base..head, renames split into delete plus add."""
    raw = git(repo, 'diff', '--no-renames', '--no-ext-diff', '--no-textconv', '--name-status', '-z',
              base, head, '--')[1].decode('utf-8', 'surrogateescape').split('\0')
    fields = [f for f in raw if f]
    require(len(fields) % 2 == 0, 'Unexpected diff output in ' + str(repo))
    return list(zip(fields[0::2], fields[1::2]))


def shared_file(name, path, shared):
    """Routed through #186 / shared_reviews, or an engine path."""
    candidates = {path, 'native/' + path} if name == 'native' else {path}
    return bool(candidates & set(shared)) or any(path == p or (p.endswith('/') and path.startswith(p))
                                                 for p in ENGINE[name])


def require_landing_review(name, port, shared, review=None):
    """None for a non-shared port; else the id of the approved landing review covering it at these exact pins.

    review is {lane, head, commit, interdiff, lander, ledger}; lander is the authenticated
    integrate caller and never the reviewer."""
    if not shared_file(name, port['file'], shared):
        return None
    where = f"{name}:{port['file']}"
    require(review and review.get('lander'), 'shared-file port requires a landing review and an authenticated lander '
            '(run integrate from your own live launch session): ' + where)
    from .approvals import landing_approval
    row = landing_approval(review['ledger'], review['lane'], name, review['head'], review['commit'], port['file'],
                           review['interdiff'])
    require(row, f"shared-file port requires a landing review approved at {review['head'][:12]}..{review['commit'][:12]} "
            f"with interdiff {review['interdiff']}: " + where)
    require(row['reviewer']['lane'] != review['lander']['lane'], 'shared-file port reviewed by its own lander: ' + where)
    return row['id']


def recheck(ledger, key, attestation):
    """In the writer transaction: every landing review a port relied on is still the latest approved row."""
    from .approvals import landing_approval
    for name in ('root', 'native'):
        report = attestation.get(name) or {}
        for path, (identity, interdiff) in (report.get('port_reviews') or {}).items():
            row = landing_approval(ledger, key, name, report['head'], report['commit'], path, interdiff)
            require(row and row['id'] == identity, f'Landing review for {name}:{path} changed while proving the landing')


def check_ports(root, ports):
    """Validated {(repo, file): declaration}; the declaration itself is stored unchanged on the receipt."""
    require(isinstance(ports, list), 'record.ports must be a list')
    result = {}
    for port in ports:
        require(isinstance(port, dict) and set(port) == PORT_FIELDS,
                'Port declaration needs exactly: ' + ', '.join(sorted(PORT_FIELDS)))
        require(isinstance(port['repo'], str) and port['repo'] in DEFAULT_REPOS and nonempty(port['file']) and
                nonempty(port['reason']), 'Port needs repo root|native, file and reason')
        for field in ('reviewed_blob', 'landed_blob'):
            require(port[field] is None or (isinstance(port[field], str) and SHA.fullmatch(port[field])),
                    f"Port {field} must be a full blob id or null: {port['file']}")
        require(isinstance(port['interdiff_sha256'], str) and HEX64.fullmatch(port['interdiff_sha256']),
                'Port interdiff_sha256 required: ' + port['file'])
        evidence = port['evidence']
        require(isinstance(evidence, dict) and nonempty(evidence.get('path')) and
                local_path(root, evidence['path']).is_file() and
                digest(local_path(root, evidence['path'])) == evidence.get('sha256'),
                'Port evidence missing or changed: ' + port['file'])
        key = (port['repo'], port['file'])
        require(key not in result, 'Duplicate port declaration: ' + ':'.join(key))
        result[key] = port
    return result


def side(root, name, source, commit, declared, ports=None, shared=(), review=None):
    """(report, problems) for one repository; problems are precise per-file strings."""
    ports = ports or {}
    repo = repository(root, name, declared)
    base, head = source['base'], source['head']
    found = objects(repo, [c + '^{commit}' for c in (commit, base, head)])
    report = dict(repo=str(repo), commit=commit, base=base, head=head, files=[])
    if found[commit + '^{commit}'] is None:
        return report, [dict(kind='missing_commit', repo=name, commit=commit,
                             detail=f'{name}: {name}_commit {commit} does not exist in {repo}')]
    for label, sha in (('base', base), ('head', head)):
        require(found[sha + '^{commit}'], f'{name}: reviewed {label} {sha} missing from {repo}')
    changed = changes(repo, base, head)
    report['head_is_ancestor'] = git(repo, 'merge-base', '--is-ancestor', head, commit, codes=(0, 1))[0] == 0
    blobs = objects(repo, [c + ':' + p for _, p in changed for c in (head, commit)])
    files, problems = [], []
    for status, path in changed:
        reviewed, landed = ((blobs[c + ':' + path] or (None,))[0] for c in (head, commit))
        port = ports.pop((name, path), None)
        if port is not None:
            require(reviewed != landed and not report['head_is_ancestor'],
                    f'{name}:{path} needs no port: the reviewed bytes are landed')
            require((port['reviewed_blob'], port['landed_blob']) == (reviewed, landed),
                    f"{name}:{path} port blobs differ from git (reviewed {reviewed}, landed {landed})")
            actual = hashlib.sha256(git(repo, '--literal-pathspecs', *INTERDIFF, head, commit, '--', path)[1]).hexdigest()
            require(port['interdiff_sha256'] == actual, f'{name}:{path} port interdiff_sha256 must be {actual} '
                    f"(sha256 of git --literal-pathspecs {' '.join(INTERDIFF)} {head} {commit} -- {path})")
            identity = require_landing_review(name, port, shared, review and dict(
                review, head=head, commit=commit, interdiff=actual))
            if identity:
                report.setdefault('port_reviews', {})[path] = [identity, actual]
            via = 'port'
        elif reviewed == landed:
            via = 'blob' if reviewed else 'absent'
        elif report['head_is_ancestor']:
            via = 'ancestor'
        else:
            kind = 'absent' if landed is None else 'present' if reviewed is None else 'different'
            problems.append(dict(kind=kind, repo=name, file=path, reviewed=reviewed, landed=landed, detail=(
                f'{name}:{path} ' + {'absent': 'is absent', 'present': 'was deleted by the lane but is present',
                                     'different': 'differs'}[kind] +
                f' at {commit[:12]} (reviewed {reviewed or "deleted"}, landed {landed or "absent"})')))
            via = None
        files.append([path, status, reviewed, landed, via])
    report['files'] = files
    line = declared.get(name)
    if line:
        tip = git(repo, 'rev-parse', '--verify', '--end-of-options', line['ref'] + '^{commit}')[1].decode().strip()
        reachable = git(repo, 'merge-base', '--is-ancestor', commit, tip, codes=(0, 1))[0] == 0
        report['line_check'] = dict(ref=line['ref'], tip=tip, reachable=reachable)
        if not reachable:
            problems.append(dict(kind='not_on_line', repo=name, commit=commit, detail=(
                f"{name}: {commit[:12]} is not reachable from declared line {line['ref']} ({tip[:12]})")))
    else:
        # Undeclared: lines are never guessed, but the lane's own worktree branch is not a landing.
        report['line_check'] = 'undeclared'
        own = _norm(Path(root, source['worktree'])) if nonempty(source.get('worktree')) else None
        own = None if own == _norm(repo) else own  # A lane working in the maintained checkout lands on its branch.
        out = git(repo, 'for-each-ref', '--contains', commit, '--format=%(refname)%00%(worktreepath)',
                  'refs/heads', 'refs/remotes')[1].decode('utf-8', 'surrogateescape').splitlines()
        refs = [r for r, _, tree in (o.partition('\0') for o in out) if not own or not tree or _norm(tree) != own]
        report['landed_refs'] = refs[:5]
        if not refs:
            problems.append(dict(kind='not_landed', repo=name, commit=commit, detail=(
                f"{name}: {commit[:12]} is on no branch outside the lane's own worktree; land it on a maintained "
                'branch (declare integration_lines to name it)')))
    return report, problems


def _norm(path):
    return os.path.normcase(str(Path(path).resolve()))


def shared_files(root, lane):
    """Files this lane routed through shared review, read from its submitted (hash-pinned) handoff."""
    handoff = lane.get('handoff')
    if not handoff:
        return []
    path = local_path(root, handoff['path'])
    require(path.is_file() and digest(path) == handoff['sha256'], 'Handoff changed after submission')
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    return [r['file'] for r in data.get('shared_reviews', []) if isinstance(r, dict) and nonempty(r.get('file'))]


def inspect(root, lane, record, declared=None, ports=None, shared=(), review=None):
    """(attestation, problems) for a receipt without raising on content mismatches."""
    root = Path(root).resolve()
    declared = lines(root) if declared is None else declared
    ports = dict(ports or {})
    kind = record.get('kind', 'landed')
    require(kind in KINDS, 'record.kind must be landed or already_landed')
    require(isinstance(record.get('root_commit'), str) and SHA.fullmatch(record['root_commit']),
            'Full integrated root commit required')
    reports, problems = {}, []
    for name, commit in (('root', record['root_commit']), ('native', record.get('native_commit'))):
        source = lane.get(name)
        if source is None:
            require(name == 'root' or commit is None, 'Lane has no native source; native_commit must be absent')
            reports[name] = None
            continue
        require(isinstance(source, dict) and all(SHA.fullmatch(str(source.get(k, ''))) for k in ('base', 'head')),
                f'Lane {name} source record lacks base/head')
        if commit is None or not SHA.fullmatch(str(commit)):
            problems.append(dict(kind='missing_commit', repo=name, commit=commit,
                                 detail=f'{name}: full {name}_commit required for a lane with {name} source'))
            reports[name] = None
            continue
        reports[name], found = side(root, name, source, commit, declared, ports, shared, review)
        problems += found
    missing = {p['repo'] for p in problems if p['kind'] == 'missing_commit'}  # Their ports were never examined.
    ports = {k: v for k, v in ports.items() if k[0] not in missing}
    require(not ports, 'Port declared for a file the lane did not change: ' +
            ', '.join(':'.join(k) for k in ports))
    return dict(schema=1, kind=kind, root=reports['root'], native=reports['native'],
                files_changed=sum(len(r['files']) for r in reports.values() if r)), problems


def prove(root, lane, record, lander=None, ledger=None):
    """Attestation for integrate(); refuses with every per-file problem otherwise.

    lander is the authenticated integrate caller (approvals.session) or None; ledger holds
    the approvals rows a shared-file port's landing review is read from."""
    root = Path(root).resolve()
    ports = check_ports(root, record.get('ports', []))
    require(not ports or record.get('kind', 'landed') == 'landed', 'already_landed receipts cannot carry ports')
    shared = shared_files(root, lane) if ports else []
    attestation, problems = inspect(root, lane, record, ports=ports, shared=shared,
                                    review=dict(lane=lane['lane'], lander=lander, ledger=ledger or {}))
    require(attestation['kind'] == 'already_landed' or attestation['files_changed'] or problems,
            "Lane changed no files between base and head; record kind 'already_landed' naming the commit "
            "that contains its bytes")
    if problems:
        details = [p['detail'] for p in problems]
        raise Rejected('Receipt does not contain the reviewed bytes: ' + '; '.join(details[:20]) +
                       (f' (+{len(details) - 20} more)' if len(details) > 20 else '') +
                       '. Land the reviewed bytes, name the commit that contains them, or declare a port.')
    attestation.update(ports=list(record.get('ports', [])), lander=lander)
    return attestation
