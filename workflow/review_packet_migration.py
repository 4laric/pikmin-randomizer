"""Read-only report: what a legacy working-copy review packet's inputs return under workflow.review_packet rules.

  <python> <checkout>/scripts/workflow_module.py review_packet_migration --root <root> --legacy <packet.py>
      [--maintained native=native] [--line native=<worktree>@<branch>] [--out <json>]

The legacy module (INPUTS / ABSENT_OKINPUTS / REVIEW_ITEMS, paths under CANONICAL_ROOT) is parsed,
never imported or executed: only literal assignments (strings joined with +, dicts, lists,
tuples) are read. For every input it reports the repository chain, nested untracked
repositories, working-copy state, and whether a pin names committed bytes; for every item what
the new rules return at the maintained checkout (--maintained, its current branch) and on the
consuming line (--line), and what porting would need. Git runs with optional locks off.
"""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import sys

from .handoff import Rejected, require
from .landing import objects
from .review_packet import DriftError, MANIFEST, _git, _text, blob_at, content, listed, observe, working


def literals(path):
    """{name: value} of the module's literal top-level assignments; nothing is executed."""
    env = {}

    def value(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name) and node.id in env:
            return env[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = value(node.left), value(node.right)
            if isinstance(left, str) and isinstance(right, str):
                return left + right
        if isinstance(node, (ast.Tuple, ast.List)):
            return [value(e) for e in node.elts]
        if isinstance(node, ast.Dict) and None not in node.keys:
            return {value(k): value(v) for k, v in zip(node.keys, node.values)}
        raise ValueError('not a literal')

    for node in ast.parse(Path(path).read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                env[node.targets[0].id] = value(node.value)
            except (ValueError, TypeError):
                pass
    require(all(k in env for k in ('SCHEMA', 'INPUTS', 'REVIEW_ITEMS', 'CANONICAL_ROOT')),
            'Legacy packet lacks literal SCHEMA, INPUTS, REVIEW_ITEMS or CANONICAL_ROOT')
    return env


def locate(root, canonical, raw):
    """The legacy path, with its CANONICAL_ROOT prefix moved to root."""
    text, canonical = raw.replace('\\', '/'), canonical.replace('\\', '/').rstrip('/')
    if text.startswith(canonical + '/'):
        text = text[len(canonical) + 1:]
    path = Path(text)
    return path if path.is_absolute() else Path(root) / text


def chain(root, path):
    """Git working trees containing path, innermost first, up to root."""
    found, folder = [], path.parent
    while True:
        if (folder / '.git').exists():
            found.append(folder)
        if folder == root or folder.parent == folder or not folder.is_relative_to(root):
            return found
        folder = folder.parent


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect(root, path, commit=None, pin=None):
    """How the legacy packet reads one file, and what the working-copy bytes it pinned are."""
    repos = chain(root, path)
    result = dict(path=str(path), exists=path.is_file(), problems=[])
    if not repos:
        result['problems'].append('not inside a git repository')
        return result
    inner = repos[0]
    rel = path.relative_to(inner).as_posix()
    result.update(repository=str(inner), relative=rel, repositories=[str(r) for r in repos])
    for child, parent in zip(repos, repos[1:]):
        if parent == root:
            continue  # native and output/ worktrees are separate repositories of the workspace by design.
        name = 'HEAD:' + child.relative_to(parent).as_posix()
        if (objects(parent, [name])[name] or (None, None))[1] != 'commit':
            result['problems'].append(f'{child} is a nested repository that {parent} does not track')
    dirty = working(inner, rel)
    result['problems'] += dirty
    try:
        head = blob_at(inner, 'HEAD', rel)
    except DriftError as exc:
        head, result['problems'] = None, result['problems'] + [str(exc)]
    result['head_blob'] = head
    result['head_sha256'] = head and _sha(content(inner, head))
    result['working_sha256'] = _sha(path.read_bytes()) if path.is_file() else None
    if pin:
        result['pinned_sha256'] = pin
    if commit:
        found = _git(inner, 'cat-file', '-e', commit + '^{commit}', codes=(0, 1, 128))[0] == 0
        blob = found and blob_at(inner, commit, rel)
        result.update(claimed_commit=commit, commit_blob=blob or None,
                      commit_sha256=_sha(content(inner, blob)) if blob else None)
    if pin:
        result['pin_is'] = ('the claimed commit\'s blob' if pin == result.get('commit_sha256') else
                            'the HEAD blob' if pin == result['head_sha256'] else
                            ('uncommitted working-copy bytes' if dirty else 'checkout-converted working-copy bytes (e.g. CRLF), '
                             'not the blob') if pin == result['working_sha256'] else 'no known bytes')
    return result


def _pair(value, what):
    require(value and '=' in value, what + ' must be name=value')
    return value.split('=', 1)


SOURCES = ('.c', '.cc', '.cpp', '.cxx')


def at_line(root, line, rel, candidate=None):
    """(facts, text) of a maintained path as review_packet observes it on a line, with build membership."""
    now = observe(root, dict(line=line, path=rel, optional=True), strict=False)
    pin = now['pin']
    manifest = blob_at(now['repo'], pin['commit'], MANIFEST)
    text = now['text'] or ''
    result = dict(line=line, commit=pin['commit'], path=rel, blob=pin['blob'], problems=now['problems'],
                  built=bool(manifest) and listed(_text(content(now['repo'], manifest)), rel, MANIFEST),
                  lines=len(text.splitlines()) if now['text'] is not None else None)
    if pin['blob']:
        out = _git(now['repo'], 'log', '-1', '--format=%H %s', '--diff-filter=A', pin['commit'], '--', rel)[1]
        result['introduced_by'] = _text(out).strip() or None
    if candidate and candidate.get('commit_blob') and pin['blob']:
        result['same_as_candidate_commit'] = pin['blob'] == candidate['commit_blob']
        if not result['same_as_candidate_commit'] and objects(now['repo'], [candidate['commit_blob']])[candidate['commit_blob']]:
            other = _text(content(now['repo'], candidate['commit_blob']))
            diff = list(difflib.unified_diff(other.splitlines(), text.splitlines(), lineterm='', n=0))
            result['diff_vs_candidate'] = dict(added=sum(1 for d in diff if d.startswith('+') and not d.startswith('+++')),
                                               removed=sum(1 for d in diff if d.startswith('-') and not d.startswith('---')))
    return result, text


def _branch(repo):
    code, out = _git(repo, 'symbolic-ref', '--quiet', '--short', 'HEAD', codes=(0, 1))
    return _text(out).strip() if code == 0 else None


def report(root, legacy, maintained=None, lines=None):
    """The whole read-only migration report."""
    root = Path(root).resolve()
    env = literals(legacy)
    inputs, absent = env['INPUTS'], env.get('ABSENT_OKINPUTS', {})
    maintained, lines = maintained or {}, lines or {}
    reads = {}
    for key, spec in inputs.items():
        reads[key] = inspect(root, locate(root, env['CANONICAL_ROOT'], spec['path']), spec.get('commit'), spec.get('sha256'))
    for key, raw in absent.items():
        reads[key] = inspect(root, locate(root, env['CANONICAL_ROOT'], raw))
    items = []
    for item in env['REVIEW_ITEMS']:
        keys = ([item['maintained_input']] if item.get('maintained_input') else []) + list(item.get('maintained_absent_inputs', []))
        tokens = list(item.get('maintained_required_tokens', [])) + list(item.get('integration_tokens', []))
        cands = {}
        for k in item.get('candidate_inputs', []):
            commit = inputs[k].get('commit') or item.get('candidate_commit')
            cands[k] = inspect(root, Path(reads[k]['path']), commit, inputs[k].get('sha256'))
        reasons, here, there, need, texts = [], {}, {}, [], {}
        for key in keys:
            raw = inputs[key]['path'] if key in inputs else absent[key]
            reasons += [f'{key}: {p}' for p in reads[key]['problems']]
            repo_name, _, rel = raw.partition('/')
            source = next((c for c in cands.values() if c.get('relative') == rel), None)
            branch = repo_name in maintained and _branch(root / maintained[repo_name])
            if branch:
                here[key] = at_line(root, dict(repo=maintained[repo_name], ref=branch), rel)[0]
                if rel.endswith(SOURCES) and not here[key]['built']:
                    reasons.append(f"{key}: {rel} is not built by {maintained[repo_name]}/{MANIFEST} at {branch} "
                                   f"({here[key]['commit'][:12]})")
            if repo_name not in lines:
                continue
            got, texts[key] = at_line(root, lines[repo_name], rel, source)
            there[key], ref = got, lines[repo_name]['ref']
            if got['problems']:
                need.append(f"{key}: fix the line worktree first: {'; '.join(got['problems'])}")
            if not got['blob']:
                need.append(f'{key}: land {rel} on {ref}')
                continue
            if rel.endswith(SOURCES) and not got['built']:
                need.append(f'{key}: list {rel} in {MANIFEST} on {ref}')
            if got.get('diff_vs_candidate'):
                need.append(f"{key}: the line's {got['lines']}-line {rel} ({got['introduced_by'] or got['blob'][:12]}) "
                            f"differs from the reviewed candidate {source['claimed_commit'][:12]} blob by "
                            f"+{got['diff_vs_candidate']['added']}/-{got['diff_vs_candidate']['removed']} lines; "
                            'review the line version, not the candidate')
        if there:
            joined = '\n'.join(texts.values())
            missing = [t for t in tokens if t not in joined]
            if missing:
                need.append(f"line files lack {', '.join(missing)} (legacy maintained/integration tokens)")
            need.append('port: declare each maintained input on ' + ', '.join(sorted({str(v['line']) for v in there.values()})) +
                        ' with region anchors (built_by for engine sources), commit the packet under tools/review_packets/, '
                        'then record first audited pins (review_packet repin --show-diff, approve:true by a reviewer that is '
                        'neither consumer nor lander)')
        for k, c in cands.items():
            if c.get('pin_is') and c['pin_is'] != "the claimed commit's blob":
                need.append(f"{k}: pin blob {c.get('commit_blob')} at {str(c.get('claimed_commit'))[:12]} (file sha256 "
                            f"{c.get('commit_sha256')}) instead of {c['pin_is']} ({c.get('pinned_sha256')})")
        items.append(dict(id=item['id'], gate=item['gate'], new_rules='REFUSED' if reasons else 'EVALUABLE',
                          reasons=reasons, maintained_checkout=here, integration_line=there, would_need=need,
                          candidates={k: {f: c.get(f) for f in ('claimed_commit', 'commit_blob', 'commit_sha256',
                                                                 'pinned_sha256', 'pin_is', 'problems')} for k, c in cands.items()}))
    return dict(legacy=str(legacy), schema=env['SCHEMA'], inputs=reads, items=items,
                summary={i['id']: i['new_rules'] for i in items})


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--legacy', type=Path, required=True)
    parser.add_argument('--maintained', action='append', default=[], help='name=<worktree> read at its current branch')
    parser.add_argument('--line', action='append', default=[], help='name=<worktree>@<branch> consuming line')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        maintained = dict(_pair(v, '--maintained') for v in args.maintained)
        lines = {}
        for value in args.line:
            name, spec = _pair(value, '--line')
            require('@' in spec, '--line needs <worktree>@<branch>')
            repo, ref = spec.rsplit('@', 1)
            lines[name] = dict(repo=repo, ref=ref)
        result = report(args.root, args.legacy, maintained, lines)
    except (Rejected, OSError, ValueError, SyntaxError) as exc:
        print(json.dumps({'error': str(exc) or type(exc).__name__}), file=sys.stderr)
        return 2
    text = json.dumps(result, indent=1)
    if args.out:
        args.out.write_text(text, encoding='utf-8')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
