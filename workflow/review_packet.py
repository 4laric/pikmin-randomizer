"""Declarative #186 review packets over committed git blobs, audited re-pins and controller-verified decisions.

A packet is JSON committed under tools/review_packets/ (docs/PIKMIN2_REVIEW_PACKETS.md) and is
read from a commit, never from the working copy. Candidate inputs are (repo, commit, path) pinned
by blob id. Maintained inputs name the consuming line (a worktree that has branch `ref` checked
out) and pin {commit, blob, region_sha256}: the observed line commit, the whole-file blob and the
sha256 of an anchor-delimited normalized region. A dirty or untracked maintained path, a path in a
nested repository and a line worktree on another branch refuse (DriftError); nothing is hashed from
disk. Maintained pins live only in the registry's packet_pins records, written by `repin`; a packet
evaluates only while each maintained input still has the blob and region of its latest record.

  <python> <checkout>/scripts/workflow_module.py review_packet verify --root <root> --packet <path> [--commit <sha>]
  <python> <checkout>/scripts/workflow_module.py review_packet repin --root <root> --request <json> [--show-diff] [--dry-run]
  <python> <checkout>/scripts/workflow_module.py review_packet request --root <root> --request <json>

verify writes nothing. repin records {packet, input, old_pin, new_pin, commit, region_diff_sha256,
actor, evidence}: always allowed to an authenticated lane when the reviewed region is unchanged;
a changed region (or a first pin) needs approve:true from an authenticated lane that is not a
declared consumer or lander and did not author or land the commits that touched the path.
request asks the controller to evaluate a packet for lanes holding a structured shared_hook; only
the controller (approvals.packet_decision) records the resulting ledger decision.
"""
import copy
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

from .control import fingerprint
from .handoff import Rejected, local_path, nonempty, require

FORMAT = 'review-packet-v1'
DIRECTORY = 'tools/review_packets/'
MANIFEST = 'CMakeLists.txt'
HEX = re.compile(r'[0-9a-f]{40}([0-9a-f]{24})?')
NAME = re.compile(r'[a-z0-9][a-z0-9._-]{0,127}')
TOUCHING = 500  # rev-list bound when finding the commits that changed a re-pinned path.
POLL_SECONDS, RETRY_SECONDS = 30, 300
DECISIONS = {'APPROVED': 'approved', 'CHANGES_REQUIRED': 'rejected'}


class DriftError(Rejected):
    """Fail-closed refusal: an input is unpinned, moved, dirty, untracked or outside a tracked tree."""


def drift(condition, message):
    if not condition:
        raise DriftError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _git(repo, *args, codes=(0,)):
    from .landing import git
    return git(repo, *args, codes=codes)


def _text(data):
    return data.decode('utf-8', 'surrogateescape')


def _path(value, what):
    require(isinstance(value, str) and nonempty(value) and '\\' not in value and not value.startswith(('/', '-'))
            and str(PurePosixPath(value)) == value and '..' not in PurePosixPath(value).parts
            and not re.search(r'[\r\n:]', value), what + ' must be a repository-relative posix path')
    return value


def _strings(value, what, empty=True):
    require(isinstance(value, list) and (empty or value) and all(nonempty(v) for v in value), what + ' must be a list of strings')
    return value


def normalize(text):
    """LF line ends, no trailing whitespace, no leading/trailing blank lines."""
    return '\n'.join(line.rstrip() for line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n')).strip('\n')


def region(text, spec):
    """The normalized region from the unique begin anchor through the next end anchor (whole file without spec)."""
    body = normalize(text)
    if not spec:
        return body
    begin, end = spec['begin'], spec['end']
    first = body.find(begin)
    drift(first >= 0, 'Region begin anchor not found: ' + repr(begin))
    drift(body.find(begin, first + 1) < 0, 'Region begin anchor is not unique: ' + repr(begin))
    stop = body.find(end, first + len(begin))
    drift(stop >= 0, 'Region end anchor not found after the begin anchor: ' + repr(end))
    return body[first:stop + len(end)]


def region_sha256(text):
    return None if text is None else _sha(text.encode('utf-8', 'surrogateescape'))


def validate(packet):
    """The packet itself, refused unless it is a well-formed review-packet-v1 declaration."""
    require(isinstance(packet, dict) and packet.get('format') == FORMAT, 'Packet format must be ' + FORMAT)
    require(isinstance(packet.get('schema'), str) and NAME.fullmatch(packet['schema']), 'Packet schema name required')
    require(type(packet.get('issue')) is int and packet['issue'] > 0, 'Packet issue number required')
    for field in ('consumers', 'landers'):
        _strings(packet.get(field, []), field)
    inputs = packet.get('inputs')
    require(isinstance(inputs, dict) and inputs, 'Packet inputs required')
    for key, item in inputs.items():
        require(NAME.fullmatch(key) and isinstance(item, dict), 'Input keys must be short names: ' + str(key))
        if item.get('role') == 'candidate':
            require(set(item) <= {'role', 'repo', 'commit', 'path', 'blob'} and isinstance(item.get('commit'), str) and
                    re.fullmatch(r'[0-9a-f]{40}', item['commit']) and (item.get('blob') is None or HEX.fullmatch(str(item['blob']))),
                    f'Candidate {key} needs repo, full commit, path and optional blob')
            _path(item.get('path'), key + '.path'); require(nonempty(item.get('repo')), key + '.repo required')
        else:
            require(item.get('role') == 'maintained' and set(item) <= {'role', 'line', 'path', 'region', 'optional', 'manifest'},
                    f'Input {key} role must be candidate or maintained')
            line = item.get('line')
            require(isinstance(line, dict) and set(line) == {'repo', 'ref'} and nonempty(line['repo']) and nonempty(line['ref'])
                    and re.fullmatch(r'[A-Za-z0-9._/-]+', line['ref']) and not line['ref'].startswith('-') and '..' not in line['ref'],
                    f'Maintained {key} needs line {{repo, ref}} with a branch name')
            _path(item.get('path'), key + '.path'); _path(item.get('manifest', MANIFEST), key + '.manifest')
            require(isinstance(item.get('optional', False), bool), key + '.optional must be a boolean')
            spec = item.get('region')
            require(spec is None or (isinstance(spec, dict) and set(spec) == {'begin', 'end'} and all(
                nonempty(spec[k]) and '\r' not in spec[k] and all(r == r.rstrip() for r in spec[k].split('\n'))
                for k in ('begin', 'end'))),
                f'{key}.region must be {{begin, end}} anchors without trailing whitespace')
    items = packet.get('items')
    require(isinstance(items, list) and items and len({i.get('id') for i in items if isinstance(i, dict)}) == len(items),
            'Packet items need distinct ids')
    for item in items:
        require(set(item) <= {'id', 'gate', 'candidates', 'candidate_tokens', 'maintained', 'required_tokens',
                              'integration_tokens', 'built_by', 'missing_change', 'downstream'} and
                NAME.fullmatch(str(item.get('id'))) and nonempty(item.get('gate')) and nonempty(item.get('missing_change')),
                'Item needs id, gate and missing_change (known fields only)')
        for field, role in (('candidates', 'candidate'), ('maintained', 'maintained')):
            require(all(inputs.get(k, {}).get('role') == role for k in _strings(item.get(field, []), field)),
                    f"Item {item['id']} {field} must name {role} inputs")
        for field in ('candidate_tokens', 'required_tokens', 'downstream'):
            _strings(item.get(field, []), field)
        _strings(item.get('integration_tokens'), 'integration_tokens', empty=False)
        require(item.get('maintained'), f"Item {item['id']} needs maintained inputs")
        require(isinstance(item.get('built_by', False), bool), 'built_by must be a boolean')
    return packet


def repository(root, value):
    """A git working tree root inside the workspace; a nested non-repo never falls back to its parent."""
    path = local_path(root, value)
    require(path.is_dir(), 'Repository missing: ' + str(path))
    top = _text(_git(path, 'rev-parse', '--show-toplevel')[1]).strip()
    require(top and Path(top).resolve() == path, f'{path} is not a git working tree root')
    return path


def commit_of(repo, ref):
    code, out = _git(repo, 'rev-parse', '--verify', '--quiet', '--end-of-options', ref + '^{commit}', codes=(0, 1))
    sha = _text(out).strip()
    drift(code == 0 and re.fullmatch(r'[0-9a-f]{40}', sha), f'{ref} is not a commit in {repo}')
    return sha


def blob_at(repo, commit, path):
    """Blob id of commit:path, None when absent; a gitlink (nested repository) or directory refuses."""
    from .landing import objects
    parts = PurePosixPath(path).parts
    names = [commit + ':' + '/'.join(parts[:i]) for i in range(1, len(parts) + 1)]
    found = objects(repo, names)
    for name in names[:-1]:
        kind = found[name] and found[name][1]
        drift(kind in (None, 'tree'), f'{name} is a nested repository, not tracked content' if kind == 'commit'
              else f'{name} is a {kind}, not a directory')
    last = found[names[-1]]
    drift(not last or last[1] == 'blob', f'{names[-1]} is a {last and last[1]}, not a file')
    return last and last[0]


def content(repo, blob):
    return _git(repo, 'cat-file', 'blob', blob)[1]


def working(repo, path):
    """Problems that make the working copy of path unlike its committed line: nested repositories, edits, untracked."""
    problems = []
    parts = PurePosixPath(path).parts
    for i in range(1, len(parts)):
        prefix = '/'.join(parts[:i])
        if (repo / prefix / '.git').exists():
            problems.append(f'{prefix} is a nested repository that {repo} does not track')
    out = _git(repo, '--literal-pathspecs', 'status', '--porcelain=v1', '-z', '--untracked-files=all',
               '--ignored=matching', '--', path)[1]
    for entry in filter(None, _text(out).split('\0')):
        code = entry[:2]
        kind = 'untracked' if code == '??' else 'ignored and untracked' if code == '!!' else 'dirty (' + code.strip() + ')'
        if len(entry) > 3 and entry[2] == ' ':
            problems.append(f'{entry[3:]} is {kind} in the working copy of {repo}')
    return problems


def line_repo(root, line):
    """(repository, observed commit, problems) for a line whose worktree must have branch ref checked out."""
    repo = repository(root, line['repo'])
    code, out = _git(repo, 'symbolic-ref', '--quiet', '--short', 'HEAD', codes=(0, 1))
    branch = _text(out).strip() if code == 0 else None
    problems = [] if branch == line['ref'] else [
        f"{repo} has {branch or 'a detached HEAD'} checked out, not the declared line {line['ref']}; "
        'declare the worktree that maintains the line']
    return repo, commit_of(repo, line['ref']), problems


def listed(text, path, manifest):
    """path (or its path relative to the manifest's directory) is named outside comments in the manifest."""
    body = '\n'.join(row.split('#', 1)[0] for row in text.replace('\r\n', '\n').split('\n'))
    folder = str(PurePosixPath(manifest).parent)
    names = {path} | ({path[len(folder) + 1:]} if folder != '.' and path.startswith(folder + '/') else set())
    return any(re.search(r'(?:^|(?<=[\s"\'(])|(?<=\}/))' + re.escape(n) + r'(?=[\s"\')]|$)', body, re.M) for n in names)


def observe(root, item, strict=True):
    """{pin, text, region, problems, repo} of a maintained input at its line's current commit."""
    repo, commit, problems = line_repo(root, item['line'])
    problems += working(repo, item['path'])
    try:
        blob = blob_at(repo, commit, item['path'])
    except DriftError as exc:
        blob, problems = None, problems + [str(exc)]
    if blob is None and not item.get('optional') and not problems:
        problems.append(f"{item['path']} is not tracked at {item['line']['ref']} ({commit[:12]})")
    text = _text(content(repo, blob)) if blob else None
    part = region(text, item.get('region')) if text is not None else None
    if strict:
        drift(not problems, 'Maintained input refused: ' + '; '.join(problems))
    return dict(pin=dict(commit=commit, blob=blob, region_sha256=region_sha256(part)), text=text, region=part,
                problems=problems, repo=repo)


def same(pin, observed):
    return bool(pin) and pin.get('blob') == observed.get('blob') and pin.get('region_sha256') == observed.get('region_sha256')


def load(root, path, commit=None):
    """(packet, blob id, commit) from the root repository; without commit, HEAD, refused while the path is uncommitted."""
    repo = repository(root, '.')
    _path(path, 'packet'); require(path.startswith(DIRECTORY) and path.endswith('.json'), 'Packets live in ' + DIRECTORY)
    if commit is None:
        drift(not working(repo, path), f'{path} differs from HEAD in the working copy; commit the packet first')
        commit = 'HEAD'
    else:
        require(isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{40}', commit), 'Full packet commit required')
    commit = commit_of(repo, commit)
    blob = blob_at(repo, commit, path)
    drift(blob is not None, f'{path} is not committed at {commit[:12]}')
    try:
        packet = json.loads(content(repo, blob).decode('utf-8'))
    except ValueError as exc:
        raise Rejected(f'{path} at {commit[:12]} is not UTF-8 JSON: {exc}')
    return validate(packet), blob, commit


def declaration(packet, key):
    return fingerprint(packet['inputs'][key])


def latest(rows, packet, key):
    """Latest audited pin record of this packet input at its current declaration, else None."""
    want = declaration(packet, key)
    found = [r for r in (rows or {}).values() if r.get('packet') == packet['schema'] and r.get('input') == key
             and r.get('declaration') == want]
    return max(found, key=lambda r: (r.get('at', 0), r.get('seq', 0), r['id']), default=None)


def audited(rows, packet):
    """{maintained input: latest record}."""
    return {k: latest(rows, packet, k) for k, v in packet['inputs'].items() if v['role'] == 'maintained'}


def candidate(root, key, item):
    repo = repository(root, item['repo'])
    blob = blob_at(repo, item['commit'], item['path'])
    drift(blob is not None, f"Candidate {key}: {item['path']} is not in commit {item['commit'][:12]}")
    drift(item.get('blob') in (None, blob), f"Candidate {key}: blob {blob} != pinned {item.get('blob')}")
    return dict(pin=dict(commit=item['commit'], blob=blob), text=_text(content(repo, blob)), repo=repo)


def evaluate(root, packet, blob, records):
    """Side-effect-free verdicts; DriftError unless every maintained input matches its latest audited record."""
    seen = {}
    for key, item in packet['inputs'].items():
        if item['role'] == 'candidate':
            seen[key] = candidate(root, key, item)
            continue
        record = records.get(key)
        drift(record, f'Maintained input {key} has no audited pin; record one with review_packet repin')
        now = observe(root, item)
        pin = record['new_pin']
        drift(same(pin, now['pin']), f"Maintained input {key} moved from its audited pin ({pin.get('blob')}, region "
              f"{pin.get('region_sha256')}) to ({now['pin']['blob']}, region {now['pin']['region_sha256']}) at "
              f"{now['pin']['commit'][:12]}; review_packet repin --show-diff records the change")
        code = _git(now['repo'], 'merge-base', '--is-ancestor', pin['commit'], now['pin']['commit'], codes=(0, 1))[0]
        drift(code == 0, f"Maintained input {key}: audited commit {pin['commit'][:12]} is not on {item['line']['ref']}")
        seen[key] = dict(now, record=record['id'])
    items = [verdict(root, packet, item, seen) for item in packet['items']]
    decision = 'APPROVED' if all(i['status'] == 'APPROVED' for i in items) else 'CHANGES_REQUIRED'
    pins = {k: dict(v['pin'], **({'record': v['record']} if 'record' in v else {})) for k, v in seen.items()}
    return dict(format=FORMAT, schema=packet['schema'], issue=packet['issue'], packet_blob=blob,
                decided_by=f"packet:{packet['schema']}@{blob}", pins=pins, items=items, decision=decision)


def verdict(root, packet, item, seen):
    problems = []
    joined = '\n'.join(seen[k]['text'] for k in item.get('candidates', []))
    problems += [f'candidate inputs lack {t!r}' for t in item.get('candidate_tokens', []) if t not in joined]
    regions = '\n'.join(seen[k]['region'] or '' for k in item['maintained'])
    problems += [f'maintained regions lack required {t!r}' for t in item.get('required_tokens', []) if t not in regions]
    evidence = [dict(token=t, present_on_maintained=t in regions) for t in item['integration_tokens']]
    built = {}
    if item.get('built_by'):
        for key in item['maintained']:
            spec, now = packet['inputs'][key], seen[key]
            if not now['pin']['blob']:
                continue
            manifest = spec.get('manifest', MANIFEST)
            dirt = working(now['repo'], manifest)
            drift(not dirt, 'Build manifest refused: ' + '; '.join(dirt))
            data = blob_at(now['repo'], now['pin']['commit'], manifest)
            listed_here = bool(data) and listed(_text(content(now['repo'], data)), spec['path'], manifest)
            built[key] = dict(manifest=manifest, commit=now['pin']['commit'], listed=listed_here)
            if not listed_here:
                problems.append(f"{spec['path']} is not built by {manifest} at {spec['line']['ref']} ({now['pin']['commit'][:12]})")
    status = 'APPROVED' if all(e['present_on_maintained'] for e in evidence) and not problems else 'CHANGES_REQUIRED'
    return dict(id=item['id'], gate=item['gate'], status=status, integration_evidence=evidence, built_by=built,
                problems=problems, missing_change=None if status == 'APPROVED' else item['missing_change'],
                downstream=list(item.get('downstream', [])))


def verify(root, path, commit=None, rows=None):
    """Load a committed packet and evaluate it at the audited pins in rows (packet_pins records)."""
    packet, blob, commit = load(root, path, commit)
    return dict(evaluate(root, packet, blob, audited(rows, packet)), packet=dict(path=path, commit=commit))


def region_diff(old, new, key, old_commit, new_commit):
    lines = difflib.unified_diff((old or '').split('\n') if old else [], (new or '').split('\n') if new else [],
                                 f"{key}@{(old_commit or 'unpinned')[:12]}", f'{key}@{new_commit[:12]}', lineterm='', n=3)
    return '\n'.join(lines) + '\n'


def touching(repo, old, new, path):
    """Commits that changed path on the way from the old pin to the new one (bounded)."""
    spec = [old + '..' + new] if old else [new]
    out = _git(repo, '--literal-pathspecs', 'rev-list', f'--max-count={TOUCHING}', *spec, '--', path)[1]
    return set(_text(out).split())


def excluded(state, packet, commits):
    """Lanes that may not approve a changed region: declared consumers/landers, and authors/landers of those commits."""
    result = set(packet.get('consumers', [])) | set(packet.get('landers', []))
    for key, lane in state.get('lanes', {}).items():
        mine = {c for n in ('root', 'native') for c in ((lane.get(n) or {}).get('commits') or []) + [(lane.get(n) or {}).get('head')]}
        landed = {(lane.get('integration') or {}).get(k) for k in ('root_commit', 'native_commit')}
        if commits & (mine | landed):
            result.add(key)
            if commits & landed:
                result.add(((lane.get('integration_landing') or {}).get('lander') or {}).get('lane'))
    return result - {None}


def prepare(root, packet, blob, commit, key, rows):
    """Everything a re-pin records except the actor, computed from git before any registry lock."""
    item = packet['inputs'].get(key)
    require(item and item['role'] == 'maintained', 'repin applies to a maintained input of the packet: ' + str(key))
    now = observe(root, item)
    old = latest(rows, packet, key)
    old_pin = old and old['new_pin']
    before = None
    if old_pin and old_pin.get('blob'):
        before = region(_text(content(now['repo'], old_pin['blob'])), item.get('region'))
    changed = not old_pin or old_pin.get('region_sha256') != now['pin']['region_sha256']
    diff = region_diff(before, now['region'], key, old_pin and old_pin['commit'], now['pin']['commit'])
    commits = touching(now['repo'], old_pin and old_pin['commit'], now['pin']['commit'], item['path']) if changed else set()
    value = dict(packet=packet['schema'], packet_blob=blob, packet_commit=commit, input=key,
                 declaration=declaration(packet, key), line=item['line'], path=item['path'], old_pin=old_pin,
                 new_pin=now['pin'], commit=now['pin']['commit'], region_changed=changed,
                 region_diff_sha256=_sha(diff.encode('utf-8', 'surrogateescape')), supersedes=old and old['id'])
    return dict(value=value, diff=diff, previous=old and old['id'], commits=commits,
                unchanged=same(old_pin, now['pin']))


def repin(reg, packet, input, actor, actor_generation, evidence, approve=False, commit=None, show=None, dry_run=False):
    """Record an audited re-pin of one maintained input (see module docstring for who may approve)."""
    from .approvals import ancestry, authenticate
    from .provenance import stamp
    require(isinstance(approve, bool), 'approve must be true or false')
    definition, blob, commit = load(reg.root, packet, commit)
    plan = prepare(reg.root, definition, blob, commit, input, reg.snapshot(section=('packet_pins',)))
    if show:
        show(plan['diff'])
    if dry_run or plan['unchanged']:
        return dict(plan['value'], dry_run=dry_run, unchanged=plan['unchanged'], recorded=plan['previous'] if plan['unchanged'] else None)
    reg.evidence(evidence)
    chain = ancestry()
    code = stamp()
    with reg.transaction() as state:
        identity = authenticate(reg, state, actor, actor_generation, chain)
        rows = state.setdefault('packet_pins', {})
        current = latest(rows, definition, input)
        require((current and current['id']) == plan['previous'], 'Audited pin changed while diffing; rerun repin')
        value = plan['value']
        if value['region_changed']:
            require(approve, 'The reviewed region changed (or has never been pinned): read the diff (--show-diff) and '
                    'record approve:true as an authenticated reviewer who is not a consumer or lander')
            refused = excluded(state, definition, plan['commits'])
            require(actor not in refused, f'Self re-pin refused: {actor} consumes, lands or authored this change; '
                    'another authenticated reviewer must approve it')
        value = dict(value, approval='reviewer' if value['region_changed'] else 'region-unchanged', actor=identity,
                     evidence=evidence)
        identity_id = fingerprint(value)
        require(identity_id not in rows, 'Identical re-pin already recorded')
        rows[identity_id] = dict(copy.deepcopy(value), id=identity_id, at=reg.clock(), seq=len(rows) + 1, code_revision=code)
        reg.event(state, 'packet_repinned', actor, record=identity_id, packet=definition['schema'], input=input,
                  region_changed=value['region_changed'])
        return copy.deepcopy(rows[identity_id])


def request(reg, requester, requester_generation, packet, lanes, hook, commit=None):
    """An authenticated lane asks the controller to evaluate a packet for lanes holding this shared_hook."""
    from .approvals import ancestry, authenticate, hooks
    definition, blob, commit = load(reg.root, packet, commit)
    spec = hooks([hook])[0]
    require(spec['issue'] == definition['issue'], f"Hook issue {spec['issue']} is not the packet's issue {definition['issue']}")
    require(isinstance(lanes, list) and lanes and all(isinstance(t, dict) and set(t) == {'key', 'generation'} for t in lanes)
            and len({t['key'] for t in lanes}) == len(lanes), 'lanes [{key, generation}] required')
    chain = ancestry()
    with reg.transaction() as state:
        identity = authenticate(reg, state, requester, requester_generation, chain)
        for target in lanes:
            lane = reg.lane(state, target['key'], target['generation'])
            require(spec['id'] in [h.get('id') for h in lane.get('shared_hooks') or []],
                    target['key'] + ' holds no matching shared_hook dependency')
        rows = state.setdefault('packet_requests', {})
        value = dict(packet=packet, commit=commit, blob=blob, schema=definition['schema'], hook_id=spec['id'], hook=spec,
                     lanes=sorted(lanes, key=lambda t: t['key']))
        for row in rows.values():
            if row['status'] == 'requested' and {k: row.get(k) for k in value} == value:
                return copy.deepcopy(row)
        identity_id = fingerprint(dict(value, at=reg.clock(), seq=len(rows) + 1))
        rows[identity_id] = dict(value, id=identity_id, status='requested', requested_by=identity, at=reg.clock(),
                                 seq=len(rows) + 1)
        reg.event(state, 'packet_evaluation_requested', requester, request=identity_id, packet=definition['schema'])
        return copy.deepcopy(rows[identity_id])


def tick(controller):
    """Evaluate the oldest requested packet, at most one per tick and one meta read per POLL_SECONDS."""
    from .approvals import packet_decision
    reg, now = controller.reg, controller.reg.clock()
    if getattr(controller, '_packet_poll', 0) > now:
        return None
    controller._packet_poll = now + POLL_SECONDS
    retry = getattr(controller, '_packet_retry', None)
    if retry is None:
        retry = {}; controller._packet_retry = retry
    rows = [r for r in reg.snapshot(section=('packet_requests',)).values()
            if r.get('status') == 'requested' and retry.get(r['id'], 0) <= now]
    for row in sorted(rows, key=lambda r: (r.get('at', 0), r.get('seq', 0)))[:1]:
        try:
            return packet_decision(reg, row['id'], getattr(controller, 'base', None))
        except (Rejected, OSError, ValueError) as exc:
            retry[row['id']] = now + RETRY_SECONDS
            reg.notice(None, 'packet_evaluation_deferred', dict(request=row['id'], error=str(exc)))
    return None


def _registry(root, db=None):
    from .registry import Registry
    return Registry(db or root / 'output/workflow/registry.sqlite3', root)


def main(argv=None):
    import argparse
    import sqlite3
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('verify', 'repin', 'request'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--db', type=Path, help='registry (default <root>/output/workflow/registry.sqlite3)')
    parser.add_argument('--packet', help='verify: packet path under ' + DIRECTORY)
    parser.add_argument('--commit', help='verify: full commit of the packet (default HEAD, which must match the working copy)')
    parser.add_argument('--request', type=Path, help='repin/request: UTF-8 JSON arguments')
    parser.add_argument('--show-diff', action='store_true', help='repin: print the region diff to stderr')
    parser.add_argument('--dry-run', action='store_true', help='repin: compute and print, record nothing')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == 'verify':
            require(args.packet, '--packet required')
            reg = _registry(root, args.db)
            rows = reg.snapshot(section=('packet_pins',)) if reg.path.is_file() else {}
            result = verify(root, args.packet, args.commit, rows)
        else:
            require(args.request, '--request required')
            body = json.loads(args.request.read_text(encoding='utf-8-sig'))
            require(isinstance(body, dict), 'Request must be a JSON object')
            reg = _registry(root, args.db)
            if args.command == 'repin':
                show = (lambda text: print(text, file=sys.stderr, end='')) if args.show_diff else None
                result = repin(reg, **body, show=show, dry_run=args.dry_run)
            else:
                result = request(reg, **body)
    except (Rejected, OSError, ValueError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({'error': str(exc) or type(exc).__name__, 'drift': isinstance(exc, DriftError)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
