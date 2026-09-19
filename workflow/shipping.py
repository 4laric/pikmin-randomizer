"""Where done work is: on an integration line, pushed off-disk, or shipped to the release target (read-only).

The release target is declared beside integration_lines, in the canonical controller config only
(<root>/output/workflow/controller/config.json, never written here):
  "release_target": {"root": {"repo": ".", "ref": "origin/main"}, "native": {"repo": "native", "ref": "fork/main"}}
An entry may add "remote", the off-disk push remote (default: root origin, native fork).

reconcile() classifies each repository side of every done lane's receipt (lanes whose history
registry_archive moved keep their receipts in the lanes section and are included, marked archived):
  shipped             the receipt commit is an ancestor of the release target
  pushed              reachable from a remote-tracking ref of the off-disk push remote
  integrated-on-line  reachable from the declared integration line only
  off-line            on none of those
  missing             not a commit of that repository
  undeclared          release_target (or, for an unpushed commit, integration_lines) is not declared
  truncated / unverifiable  over the commit or walk cap / git failed for that repository
Done lanes without a receipt count as done-no-code. A remote whose URL is a local path never counts as
pushed. Only local refs are read: git never fetches or pushes, reachability is one rev-list walk per
repository with a cap, every call has a timeout, and merge-tree writes its objects to a scratch
directory, never the repository. suggest() is the evidence for choosing integration_lines and
release_target (it prints a snippet, never writes the config); plan() proposes bounded promotion
batches and creates no branch, commit or PR. CLI: workflow.inspect delivery | delivery-suggest |
promotion-plan.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import time

from .handoff import Rejected, local_path, nonempty, require
from .landing import CONFIG, DEFAULT_REPOS, SHA, lines

TIMEOUT = 60  # Seconds per git call.
COMMITS, WALK, REFS, FILES, LANE_DIFFS = 2000, 200000, 5000, 20000, 500  # Caps; over a cap the result says truncated.
PUSH_REMOTES = {'root': 'origin', 'native': 'fork'}
CLASSES = ('shipped', 'pushed', 'integrated-on-line', 'off-line', 'missing', 'undeclared', 'truncated', 'unverifiable')
UNSHIPPED = ('pushed', 'integrated-on-line', 'off-line')
REF = re.compile(r'[A-Za-z0-9._/-]+')
NETWORK = re.compile(r'(?:https?|ssh|git|git\+ssh|ssh\+git)://[^/\s]+/\S+|[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:(?![\\/])\S+', re.I)
SHARED = {'root': ('engine/', 'include/', 'src/', 'pc_port/'),
          'native': ('pc_port/', 'src/', 'include/', 'cmake/', 'CMakeLists.txt')}
LIMITS = {'modify-shared': (12, 8), 'modify': (40, 20), 'additive': (200, 40)}  # (files, receipts) per batch, in order.
TIP_SECONDS = 60  # The dashboard re-reads line/target/remote tips at most this often.


def _git(repo, *args, stdin=None, codes=(0,), env=None):
    from .landing import git
    return git(repo, *args, stdin=stdin, codes=codes, timeout=TIMEOUT, env=env)


def _out(repo, *args, **kw):
    return _git(repo, *args, **kw)[1].decode('utf-8', 'surrogateescape')


def targets(root):
    """Declared {root|native: {repo, ref[, remote]}} from the canonical controller config; {} when none."""
    path = Path(root) / CONFIG
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise Rejected('Controller config unreadable for release_target: ' + str(exc))
    declared = data.get('release_target') if isinstance(data, dict) else None
    if declared is None:
        return {}
    require(isinstance(declared, dict) and set(declared) <= set(DEFAULT_REPOS) and all(
        isinstance(v, dict) and set(v) <= {'repo', 'ref', 'remote'} and nonempty(v.get('repo')) and ref_ok(v.get('ref'))
        and (v.get('remote') is None or (nonempty(v['remote']) and REF.fullmatch(v['remote'])))
        for v in declared.values()), 'release_target must map root/native to {repo, ref[, remote]}')
    return declared


def ref_ok(ref):
    return isinstance(ref, str) and bool(REF.fullmatch(ref)) and not ref.startswith('-') and '..' not in ref


def off_disk(url):
    """A network URL; file://, bare paths and drive letters are on this machine and never count as pushed."""
    return isinstance(url, str) and bool(NETWORK.fullmatch(url.strip()))


def checkout(root, name, entry=None):
    """The working tree for one side: the declared entry's repo, else the default ('.' or 'native')."""
    from .landing import repository
    return repository(root, name, {name: entry} if entry else {})


def common(repo):
    return os.path.normcase(str((Path(repo) / _out(repo, 'rev-parse', '--git-common-dir').strip()).resolve()))


def remotes(repo):
    """{remote name: url} from the repository config."""
    result = {}
    for row in _out(repo, 'config', '--get-regexp', r'^remote\..*\.url$', codes=(0, 1)).splitlines():
        key, _, url = row.partition(' ')
        result[key[len('remote.'):-len('.url')]] = url
    return result


def refs(repo, *patterns):
    """[{ref, sha, symref, worktree}] of for-each-ref over patterns; symbolic refs keep their target."""
    rows = []
    out = _out(repo, 'for-each-ref', '--format=%(objectname)%00%(refname)%00%(symref)%00%(worktreepath)', *patterns)
    for row in out.splitlines():
        parts = row.split('\0')
        if len(parts) == 4:
            rows.append(dict(sha=parts[0], ref=parts[1], symref=parts[2] or None, worktree=parts[3] or None))
    return rows


def tip(repo, ref):
    code, out = _git(repo, 'rev-parse', '--verify', '--quiet', '--end-of-options', ref + '^{commit}', codes=(0, 1))
    sha = out.decode().strip()
    return sha if code == 0 and SHA.fullmatch(sha) else None


def present(repo, commits):
    """The commits (in order) that are commit objects of repo; one cat-file batch."""
    from .landing import objects
    valid = [c for c in dict.fromkeys(commits) if isinstance(c, str) and SHA.fullmatch(c)]
    found = objects(repo, [c + '^{commit}' for c in valid])
    return [c for c in valid if found[c + '^{commit}'] and found[c + '^{commit}'][1] == 'commit']


def reach(repo, tips, commits, cap=None):
    """({tip name: bitmask over commits}, walked, truncated) from one rev-list walk of every tip.

    Bits propagate from parents to children in reverse topological order, so each tip's mask is
    exactly the listed commits it reaches. A walk over the cap answers nothing (truncated)."""
    shas, cap = sorted(set(tips.values())), WALK if cap is None else cap
    if not shas or not commits:
        return {n: 0 for n in tips}, 0, False
    rows = _out(repo, 'rev-list', '--topo-order', '--parents', '--max-count=%d' % (cap + 1), '--stdin',
                stdin=''.join(s + '\n' for s in shas).encode()).splitlines()
    if len(rows) > cap:
        return None, len(rows), True
    bit = {c: 1 << i for i, c in enumerate(commits)}
    mask = {}
    for row in reversed(rows):  # Parents before children.
        c, *parents = row.split()
        m = bit.get(c, 0)
        for p in parents:
            m |= mask.get(p, 0)
        mask[c] = m
    return {n: mask.get(s, 0) for n, s in tips.items()}, len(rows), False


def members(mask, commits):
    return {c for i, c in enumerate(commits) if mask >> i & 1}


def divergence(repo, ours, theirs, conflicts=True):
    """{ahead, behind[, conflicts, conflict_paths | conflicts_skipped]} of ours against theirs."""
    ahead, behind = (int(n) for n in _out(repo, 'rev-list', '--left-right', '--count', ours + '...' + theirs).split())
    result = dict(ahead=ahead, behind=behind)
    if conflicts:
        result.update(merge_conflicts(repo, ours, theirs))
    return result


def merge_conflicts(repo, ours, theirs):
    """Conflicting paths of a trial merge; merge-tree's objects go to a scratch directory that is deleted.
    Skipped (never guessed) when this git has no merge-tree --write-tree or the call fails."""
    objects = (Path(repo) / _out(repo, 'rev-parse', '--git-path', 'objects').strip()).resolve()
    try:
        with tempfile.TemporaryDirectory(prefix='shipping-merge-tree-') as scratch:
            code, out = _git(repo, 'merge-tree', '--write-tree', '--name-only', '--no-messages', '-z', ours, theirs,
                             codes=(0, 1), env=dict(GIT_OBJECT_DIRECTORY=scratch,
                                                    GIT_ALTERNATE_OBJECT_DIRECTORIES=str(objects)))
    except (Rejected, OSError) as exc:
        return dict(conflicts=None, conflicts_skipped=str(exc)[:300])
    paths = sorted({p for p in out.decode('utf-8', 'surrogateescape').split('\0')[1:] if p}) if code == 1 else []
    return dict(conflicts=len(paths), conflict_paths=paths[:20])


def receipts(state):
    """(done lanes with an integration receipt as [(key, lane, {side: commit})] newest first, done lanes without one)."""
    done, bare = [], []
    for key, lane in state.get('lanes', {}).items():
        if lane.get('state') != 'done':
            continue
        record = lane.get('integration')
        if not isinstance(record, dict) or not record.get('root_commit'):
            bare.append(key)
            continue
        sides = {'root': record.get('root_commit')}
        if record.get('native_commit') or lane.get('native'):
            sides['native'] = record.get('native_commit')
        done.append((key, lane, sides))
    done.sort(key=lambda r: (-(r[1].get('integrated_at') or 0), r[0]))
    return done, sorted(bare)


def commits_of(rows):
    """{side: [commit, ...]} newest receipt first, each commit once."""
    result = {}
    for _, _, sides in rows:
        for name, commit in sides.items():
            if isinstance(commit, str):
                result.setdefault(name, []).append(commit)
    return {k: list(dict.fromkeys(v)) for k, v in result.items()}


def facts(root, name, commits, line=None, target=None, conflicts=True):
    """Git facts for one side: which receipt commits exist, lie on the line, are pushed and are shipped."""
    result = dict(exists=set(), on_line=set(), pushed=set(), shipped=set(), truncated=set(), line=None, target=None)
    repo = checkout(root, name, line or target)
    other = checkout(root, name, target) if target else repo
    require(common(other) == common(repo), f'{name}: release_target repo and integration line repo are different repositories')
    remote = (target or {}).get('remote') or PUSH_REMOTES[name]
    url = remotes(repo).get(remote)
    result['repo'], result['remote'] = str(repo), dict(name=remote, url=url, off_disk=off_disk(url))
    heads = [r for r in refs(repo, 'refs/remotes/%s/' % remote) if not r['symref']] if result['remote']['off_disk'] else []
    result['remote']['refs'] = len(heads)
    tips = {'push:' + r['ref']: r['sha'] for r in heads}
    for label, entry, where in (('line', line, repo), ('target', target, other)):
        if entry:
            sha = tip(where, entry['ref'])
            require(sha, f"{name}: declared {'integration line' if label == 'line' else 'release target'} {entry['ref']} "
                    f'is not a commit in {where}')
            result[label] = dict(ref=entry['ref'], repo=entry['repo'], tip=sha)
            tips[label] = sha
    found = present(repo, commits)
    result['exists'] = set(found)
    evaluated, over = found[:COMMITS], found[COMMITS:]
    masks, result['walked'], cut = reach(repo, tips, evaluated)
    if cut:
        result['truncated'] = set(found)
    else:
        result['truncated'] = set(over)
        result['pushed'] = members(sum_or(masks[k] for k in masks if k.startswith('push:')), evaluated)
        if line: result['on_line'] = members(masks['line'], evaluated)
        if target: result['shipped'] = members(masks['target'], evaluated)
    if line and target:
        result['divergence'] = divergence(repo, result['line']['tip'], result['target']['tip'], conflicts)
    if line:
        pushed = [r['sha'] for r in heads]
        result['line']['unpushed_commits'] = int(_out(repo, 'rev-list', '--count', '--stdin', stdin=(
            result['line']['tip'] + '\n' + ''.join('^' + s + '\n' for s in pushed)).encode()).strip()) if heads else None
    return result


def sum_or(masks):
    total = 0
    for m in masks:
        total |= m
    return total


def classify(fact, commit, has_line, has_target):
    """One side's class; undeclared config is its own class, never a guess."""
    if fact.get('error'): return 'unverifiable'
    if commit not in fact['exists']: return 'missing'
    if commit in fact['truncated']: return 'truncated'
    if not has_target: return 'undeclared'
    if commit in fact['shipped']: return 'shipped'
    if commit in fact['pushed']: return 'pushed'
    if not has_line: return 'undeclared'
    return 'integrated-on-line' if commit in fact['on_line'] else 'off-line'


def gather(root, state, conflicts=True):
    """{side: facts} for every side that has receipt commits; a failing side records its error."""
    rows, _ = receipts(state)
    declared_lines, declared_targets = lines(root), targets(root)
    result = {}
    for name, commits in commits_of(rows).items():
        try:
            result[name] = facts(root, name, commits, declared_lines.get(name), declared_targets.get(name), conflicts)
        except (Rejected, OSError, ValueError) as exc:
            result[name] = dict(error=str(exc) or type(exc).__name__, exists=set(), truncated=set())
    return result


def reconcile(root, state, now=None, *, conflicts=True, known=None, detail=True):
    """Delivery classes of every done lane per side, unpushed receipts, oldest unshipped and line divergence."""
    now = time.time() if now is None else now
    declared_lines, declared_targets = lines(root), targets(root)
    known = gather(root, state, conflicts) if known is None else known
    rows, bare = receipts(state)
    repos, lanes = {}, {}
    for name in DEFAULT_REPOS:
        fact = known.get(name) or {}
        repos[name] = dict(counts={}, line=fact.get('line') or ('undeclared' if name not in declared_lines else None),
                           target=fact.get('target') or ('undeclared' if name not in declared_targets else None),
                           remote=fact.get('remote'), divergence=fact.get('divergence'), error=fact.get('error'),
                           walked=fact.get('walked'), truncated=len(fact.get('truncated') or ()),
                           unpushed=dict(count=0, oldest=None, lanes=[]), oldest_unshipped=None)
    for key, lane, sides in rows:
        at = lane.get('integrated_at')
        entry = lanes[key] = dict(integrated_at=at, archived=bool(lane.get('archived')))
        for name, commit in sides.items():
            fact, repo = known.get(name) or dict(error='not evaluated', exists=set(), truncated=set()), repos[name]
            kind = classify(fact, commit, name in declared_lines, name in declared_targets)
            evaluated = kind not in ('missing', 'truncated', 'unverifiable')
            pushed = commit in fact.get('pushed', ()) if evaluated else None
            entry[name] = dict(commit=commit, cls=kind, pushed=pushed)
            repo['counts'][kind] = repo['counts'].get(kind, 0) + 1
            if pushed is False:
                bucket = repo['unpushed']
                bucket['count'] += 1
                if len(bucket['lanes']) < 10: bucket['lanes'].append(key)
                if type(at) in (int, float) and (bucket['oldest'] is None or at < bucket['oldest']['integrated_at']):
                    bucket['oldest'] = dict(lane=key, integrated_at=at, age_seconds=max(0, now - at))
            if kind in UNSHIPPED and type(at) in (int, float) and (
                    repo['oldest_unshipped'] is None or at < repo['oldest_unshipped']['integrated_at']):
                repo['oldest_unshipped'] = dict(lane=key, integrated_at=at, age_seconds=max(0, now - at), cls=kind)
    for name, repo in repos.items():
        if name not in declared_targets:
            repo['oldest_unshipped'] = 'undeclared'
    archived = sum(bool(l.get('archived')) for k, l in state.get('lanes', {}).items() if l.get('state') == 'done')
    report = dict(at=now, declared=dict(integration_lines=sorted(declared_lines), release_target=sorted(declared_targets)),
                  lanes=dict(done=len(rows) + len(bare), **{'done-no-code': len(bare)}, receipts=len(rows), archived=archived),
                  repos=repos)
    if detail:
        report['receipts'] = lanes
    return report


def dashboard(root, state, now, *, clock=time.monotonic, cache=None):
    """The reconcile summary for the dashboard; git runs only when a line, target or push-remote tip
    or the receipt set changed (tips re-read at most every TIP_SECONDS)."""
    cache = _CACHE if cache is None else cache
    rows, _ = receipts(state)
    commits = {k: tuple(v) for k, v in commits_of(rows).items()}
    config = (json.dumps(lines(root), sort_keys=True), json.dumps(targets(root), sort_keys=True))
    entry = cache.get(str(root))
    fresh = entry and entry['commits'] == commits and entry['config'] == config
    if not (fresh and clock() - entry['checked'] < TIP_SECONDS):
        key = tips_key(root, commits)
        if not (fresh and entry['key'] == key):
            entry = dict(commits=commits, config=config, key=key, known=gather(root, state))
        entry['checked'] = clock()
        cache[str(root)] = entry
    return reconcile(root, state, now, known=entry['known'], detail=False)


_CACHE = {}


def tips_key(root, commits):
    """Line, target and push-remote tips of each side with receipts: what a recompute depends on in git."""
    declared_lines, declared_targets = lines(root), targets(root)
    key = []
    for name in sorted(commits):
        line, target = declared_lines.get(name), declared_targets.get(name)
        try:
            repo = checkout(root, name, line or target)
            remote = (target or {}).get('remote') or PUSH_REMOTES[name]
            heads = sorted((r['ref'], r['sha']) for r in refs(repo, 'refs/remotes/%s/' % remote))
            key.append((name, tip(repo, line['ref']) if line else None,
                        tip(checkout(root, name, target), target['ref']) if target else None,
                        remotes(repo).get(remote), hashlib.sha256(json.dumps(heads).encode()).hexdigest()))
        except (Rejected, OSError, ValueError) as exc:
            key.append((name, 'error', str(exc)))
    return tuple(key)


def short(ref):
    for prefix in ('refs/heads/', 'refs/remotes/'):
        if ref.startswith(prefix):
            return ref[len(prefix):]
    return ref


def relative(root, path):
    """A worktree path as the config names it (posix, relative to root), or None outside the workspace."""
    if not path:
        return None
    try:
        rel = Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return None
    return rel or '.'


def suggest(root, state, *, candidates=3, shown=10, conflicts=True):
    """Which refs hold how many receipt commits per side, and how the top candidates diverge from the
    push remote's default branch; the snippet is for the operator to paste, never written here."""
    rows, _ = receipts(state)
    report, snippet = dict(repos={}), dict(integration_lines={}, release_target={})
    for name, commits in commits_of(rows).items():
        side = report['repos'][name] = dict(receipts=len(commits))
        try:
            repo = checkout(root, name)
            found = present(repo, commits)
            evaluated = found[:COMMITS]
            all_refs = refs(repo, 'refs/heads', 'refs/remotes')
            real = [r for r in all_refs if not r['symref']][:REFS]
            side.update(repo=str(repo), missing=len(commits) - len(found), truncated=dict(
                commits=len(found) > COMMITS, refs=len([r for r in all_refs if not r['symref']]) > REFS))
            masks, side['walked'], cut = reach(repo, {r['ref']: r['sha'] for r in real}, evaluated)
            if cut:
                side['truncated']['walk'] = True
                continue
            remote = PUSH_REMOTES[name]
            url = remotes(repo).get(remote)
            side['remote'] = dict(name=remote, url=url, off_disk=off_disk(url))
            count = {r['ref']: bin(masks[r['ref']]).count('1') for r in real}
            anywhere = sum_or(masks.values())
            side['on_no_ref'] = len(evaluated) - bin(anywhere).count('1')
            pushed = sum_or(masks[r['ref']] for r in real if r['ref'].startswith('refs/remotes/%s/' % remote)) \
                if side['remote']['off_disk'] else 0
            side['unpushed'] = len(evaluated) - bin(pushed).count('1')
            def listing(prefix):
                rows_ = sorted((r for r in real if r['ref'].startswith(prefix) and count[r['ref']]),
                               key=lambda r: (-count[r['ref']], r['ref']))
                return rows_, [dict(ref=short(r['ref']), receipts=count[r['ref']], tip=r['sha'],
                                    worktree=relative(root, r['worktree']) if r['worktree'] else None) for r in rows_[:shown]]
            local, side['branches'] = listing('refs/heads/')
            _, side['remote_refs'] = listing('refs/remotes/')
            side['branches_with_receipts'] = len(local)
            head = next((r for r in all_refs if r['ref'] == 'refs/remotes/%s/HEAD' % remote and r['symref']), None)
            default = head['symref'] if head else next((r['ref'] for r in real if r['ref'] == 'refs/remotes/%s/main' % remote), None)
            target = next((r for r in real if r['ref'] == default), None) if default else None
            side['default_target'] = dict(ref=short(target['ref']), tip=target['sha'],
                                          receipts=count[target['ref']]) if target else None
            side['candidates'], chosen = [], []  # Distinct lines: a branch whose receipts an earlier one holds is a copy.
            for r in local:
                if len(chosen) == candidates: break
                if any(masks[r['ref']] & ~masks[c['ref']] == 0 for c in chosen): continue
                row = dict(ref=short(r['ref']), receipts=count[r['ref']], worktree=relative(root, r['worktree']))
                if chosen:
                    row['beyond_top'] = bin(masks[r['ref']] & ~masks[chosen[0]['ref']]).count('1')
                if target:
                    row['vs_target'] = divergence(repo, r['sha'], target['sha'], conflicts)
                side['candidates'].append(row)
                chosen.append(r)
            if len(chosen) > 1:
                side['between'] = dict(ours=short(chosen[0]['ref']), theirs=short(chosen[1]['ref']),
                                       **divergence(repo, chosen[0]['sha'], chosen[1]['sha'], conflicts))
            side['candidates_hold'] = bin(sum_or(masks[c['ref']] for c in chosen)).count('1')
            if local:
                top = side['candidates'][0]
                snippet['integration_lines'][name] = dict(repo=top['worktree'] or DEFAULT_REPOS[name], ref=top['ref'])
                if not top['worktree']:
                    side['warning'] = (f"{top['ref']} is not checked out in a worktree under the root; review packets need "
                                       'the line checked out, so create or name one before declaring it')
            if target:
                snippet['release_target'][name] = dict(repo=DEFAULT_REPOS[name], ref=short(target['ref']))
        except (Rejected, OSError, ValueError) as exc:
            side['error'] = str(exc) or type(exc).__name__
    report['declared'] = dict(integration_lines=lines(root), release_target=targets(root))
    report['snippet'] = {k: v for k, v in snippet.items() if v}
    return report


def kind_of(name, status, path):
    shared = any(path == p or (p.endswith('/') and path.startswith(p)) for p in SHARED[name])
    return 'additive' if status == 'A' else 'modify-shared' if shared else 'modify'


def slug(prefix, path):
    body = re.sub(r'[^a-z0-9._-]+', '-', path.lower()).strip('-.')[:96] or 'file'
    return f"{prefix}-{body}-{hashlib.sha1(path.encode('utf-8', 'surrogateescape')).hexdigest()[:8]}"


def packet_inputs(name, files, line, target, tip_):
    """review-packet-v1 inputs for the batch's shared-path files: the line's bytes as candidates, the
    release target as the maintained side (it must be checked out in a worktree before a packet uses it)."""
    inputs, skipped = {}, []
    for f in files:
        path = f['path']
        if not any(path == p or (p.endswith('/') and path.startswith(p)) for p in SHARED[name]):
            continue
        if '\\' in path or ':' in path or path.startswith('-') or '..' in PurePosixPath(path).parts:
            skipped.append(path)
            continue
        if f['status'] != 'D':
            inputs[slug('c', path)] = dict(role='candidate', repo=line['repo'], commit=tip_, path=path)
        maintained = dict(role='maintained', line=dict(repo=target['repo'], ref=target['ref']), path=path)
        if f['status'] == 'A':
            maintained['optional'] = True
        inputs[slug('m', path)] = maintained
    return inputs, skipped


def plan(root, state, name, *, line=None, target=None, max_batches=40, limits=None):
    """Bounded promotion batches from the integration line to the release target (read-only).

    line/target name refs explicitly (the operator's choice); otherwise the declared config is used,
    and an undeclared one refuses. Files are what the line changed since its merge base with the
    target; each is attributed to the carried receipts whose lanes changed it."""
    require(name in DEFAULT_REPOS, 'promotion-plan needs root or native')
    limits = dict(LIMITS, **(limits or {}))
    declared_line, declared_target = lines(root).get(name), targets(root).get(name)
    source = dict(line='argument' if line else 'config', target='argument' if target else 'config')
    if line: require(ref_ok(line), 'line must be a ref name')
    if target: require(ref_ok(target), 'target must be a ref name')
    line = dict(repo=(declared_line or {}).get('repo') or DEFAULT_REPOS[name], ref=line) if line else declared_line
    target = dict(repo=(declared_target or {}).get('repo') or DEFAULT_REPOS[name], ref=target) if target else declared_target
    require(line, f'integration_lines.{name} is undeclared; declare it or pass --line <ref>')
    require(target, f'release_target.{name} is undeclared; declare it or pass --target <ref>')
    repo, other = checkout(root, name, line), checkout(root, name, target)
    require(common(repo) == common(other), f'{name}: line and target are in different repositories')
    ltip, ttip = tip(repo, line['ref']), tip(other, target['ref'])
    require(ltip and ttip, f"{name}: {line['ref'] if not ltip else target['ref']} is not a commit")
    code, out = _git(repo, 'merge-base', ltip, ttip, codes=(0, 1))
    base = out.decode().strip()
    require(code == 0 and SHA.fullmatch(base), f"{name}: {line['ref']} and {target['ref']} share no history")
    from .landing import changes
    changed = changes(repo, base, ltip)
    truncated = dict(files=len(changed) > FILES)
    changed = changed[:FILES]
    rows, _ = receipts(state)
    mine = [(k, l, s[name]) for k, l, s in rows if isinstance(s.get(name), str)]
    found = present(repo, [c for _, _, c in mine])[:COMMITS]
    masks, _, cut = reach(repo, dict(line=ltip, target=ttip), found)
    require(not cut, f'{name}: history walk over {WALK} commits; plan refused rather than guessed')
    on_line, shipped = members(masks['line'], found), members(masks['target'], found)
    carried = [(k, l, c) for k, l, c in mine if c in on_line and c not in shipped]
    truncated['lanes'] = len(carried) > LANE_DIFFS
    by_path, unattributed = {}, []
    for key, lane, commit in carried[:LANE_DIFFS]:
        paths = lane_paths(repo, name, lane)
        if paths is None:
            unattributed.append(key)
            continue
        for p in paths:
            by_path.setdefault(p, set()).add(key)
    info = {k: dict(lane=k, commit=c, integrated_at=l.get('integrated_at')) for k, l, c in carried}
    known, exists = set(info), set(found)
    batches, counts = [], {}
    for kind in LIMITS:
        files = sorted(((s, p) for s, p in changed if kind_of(name, s, p) == kind),
                       key=lambda sp: (str(PurePosixPath(sp[1]).parent), sp[1]))
        counts[kind] = len(files)
        most_files, most_receipts = limits[kind]
        current = None
        for status, path in files:
            owners = by_path.get(path, set()) & known
            if current is None or len(current['files']) >= most_files or (
                    current['files'] and len(current['lanes'] | owners) > most_receipts):
                current = dict(kind=kind, files=[], lanes=set())
                batches.append(current)
            current['files'].append(dict(path=path, status=status))
            current['lanes'] |= owners
    spread = {}
    for b in batches:
        for k in b['lanes']: spread[k] = spread.get(k, 0) + 1
    result = []
    for n, b in enumerate(batches[:max_batches], 1):
        inputs, skipped = packet_inputs(name, b['files'], line, target, ltip)
        result.append(dict(id='%s-%s-%02d' % (name, b['kind'], n), kind=b['kind'], files=b['files'],
                           receipts=[dict(info[k], partial=spread[k] > 1) for k in sorted(b['lanes'])],
                           unattributed_files=sum(not (by_path.get(f['path'], set()) & known) for f in b['files']),
                           packet_inputs=inputs, packet_inputs_skipped=skipped,
                           review=f"git diff {base} {ltip} -- <files>"))
    return dict(repo=name, line=dict(line, tip=ltip), target=dict(target, tip=ttip), merge_base=base, source=source,
                files=len(changed), classes=counts, limits={k: dict(files=v[0], receipts=v[1]) for k, v in limits.items()},
                receipts=dict(carried=len(carried), shipped=len(shipped & {c for _, _, c in mine}),
                              off_line=len({c for _, _, c in mine if c in exists and c not in on_line}),
                              missing=len({c for _, _, c in mine} - exists), unattributed=unattributed[:50],
                              unattributed_count=len(unattributed)),
                batches=result, omitted_batches=max(0, len(batches) - max_batches), truncated=truncated,
                note='Proposal only: no branch, commit or PR was created. Batches go first to last; each shared-path batch '
                     'needs its own #186 review packet.')


def lane_paths(repo, name, lane):
    """Paths the lane changed on this side: its landing proof when recorded, else its base..head diff; None if unknown."""
    proof = ((lane.get('integration_landing') or {}).get(name) or {}) if isinstance(lane.get('integration_landing'), dict) else {}
    if isinstance(proof.get('files'), list) and proof['files']:
        return [f[0] for f in proof['files'] if isinstance(f, list) and f and isinstance(f[0], str)]
    source = lane.get(name) if isinstance(lane.get(name), dict) else {}
    base, head = source.get('base'), source.get('head')
    if not (isinstance(base, str) and SHA.fullmatch(base) and isinstance(head, str) and SHA.fullmatch(head)):
        return None
    if len(present(repo, [base, head])) != len({base, head}):
        return None
    from .landing import changes
    try:
        return [p for _, p in changes(repo, base, head)]
    except Rejected:
        return None


def markdown(data):
    """The promotion plan as markdown for a PR description or a reviewer."""
    out = ['# Promotion plan: %s %s -> %s' % (data['repo'], data['line']['ref'], data['target']['ref']), '',
           '%s (%s) onto %s (%s); merge base %s. %d files; %d carried receipts, %d already shipped, %d not on the line, '
           '%d unattributed receipts.' % (data['line']['ref'], data['line']['tip'][:12], data['target']['ref'],
           data['target']['tip'][:12], data['merge_base'][:12], data['files'], data['receipts']['carried'],
           data['receipts']['shipped'], data['receipts']['off_line'], data['receipts']['unattributed_count']), '',
           data['note'], '']
    if any(data['truncated'].values()):
        out += ['**Truncated:** ' + ', '.join(k for k, v in data['truncated'].items() if v), '']
    for b in data['batches']:
        out += ['## %s (%s): %d files, %d receipts' % (b['id'], b['kind'], len(b['files']), len(b['receipts'])), '']
        out += ['- receipt %s at %s%s' % (r['lane'], r['commit'][:12], ' (split across batches)' if r['partial'] else '')
                for r in b['receipts']]
        if b['unattributed_files']:
            out.append('- %d files carry no receipt (tooling, merges or unrecorded work)' % b['unattributed_files'])
        out += ['', '```'] + ['%s %s' % (f['status'], f['path']) for f in b['files']] + ['```', '']
        if b['packet_inputs']:
            out += ['#186 packet inputs (stub, `tools/review_packets/template.json` format):', '', '```json',
                    json.dumps(b['packet_inputs'], indent=2), '```', '']
    if data['omitted_batches']:
        out.append('%d more batches omitted; rerun after the first ones land.' % data['omitted_batches'])
    return '\n'.join(out)


def write_plan(root, data, out):
    """Write <out>.json and <out>.md; out must lie under <root>/output/."""
    target = local_path(root, str(out))
    require(target.is_relative_to((Path(root) / 'output').resolve()), 'promotion-plan --out must be under output/')
    stem = target.with_suffix('') if target.suffix in ('.json', '.md') else target
    stem.parent.mkdir(parents=True, exist_ok=True)
    paths = (stem.with_name(stem.name + '.json'), stem.with_name(stem.name + '.md'))
    paths[0].write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    paths[1].write_text(markdown(data) + '\n', encoding='utf-8')
    return [str(p) for p in paths]
