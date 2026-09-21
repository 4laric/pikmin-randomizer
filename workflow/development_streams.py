"""Operator-reviewed development streams layered on the shared registry.

An isolated ``development_streams`` section tracks stream provisioning, explicit
live-owner binding, stream-local candidate receipts and read-only references to
real canonical maintained integration records.  Stream-local status is never
canonical ``done``/``integrated``: the module never calls ``Registry.integrate``,
never dispatches and never wakes a maintained consumer.  Final merges,
maintained builds/exports and admission stay with the existing sole integration
owner.

Fail-closed rules:
* every owner operation names an existing, live, unfinished lane at its current
  recorded ownership generation; a stored owner label alone is not authority;
* a stream-local candidate must pin the stream's current maintained base *and*
  the real Git HEAD observed from the configured maintained worktrees, so a
  moved maintained HEAD makes the stream stale until an explicit refresh;
* at most one ``ready`` batch exists per stream;
* a ready batch is retired only through an explicit fenced operation: either a
  reasoned abandon (releases the slot without claiming delivery) or a read-only
  reference to an existing canonical ``lane.integration`` record.  No caller
  supplies maintained hashes.
"""
import argparse
import copy
import json
import re
import subprocess
from pathlib import Path

from .handoff import Rejected, digest, local_path, nonempty, require

SCHEMA = 1
STREAM_ID = r'[a-z0-9][a-z0-9_-]*'
COMMIT = r'[0-9a-f]{40}'
CANDIDATE_STATES = ('draft', 'ready', 'stale')
CLOSED_STATES = ('abandoned', 'maintained')
INTEGRATOR_LEVEL = 'integration ownership'
CONFIG_PATH = 'output/workflow/controller/config.json'
MISSING_GIT = 'git-unavailable'


def _commit(value, name):
    require(isinstance(value, str) and re.fullmatch(COMMIT, value), name + ': full commit required')
    return value


def _base(value):
    require(isinstance(value, dict), 'maintained base record required')
    return {kind: _commit((value.get(kind) or {}).get('commit'), kind) if isinstance(value.get(kind), dict)
            else _commit(value.get(kind), kind) for kind in ('root', 'native')}


def _observed_commits(observed):
    require(isinstance(observed, dict), 'Observed maintained sources required')
    return {kind: _commit((observed.get(kind) or {}).get('commit'), kind) for kind in ('root', 'native')}


def _git(tree, *args):
    try:
        proc = subprocess.run(['git', '-C', str(tree), *args], capture_output=True, text=True)
    except OSError as error:
        raise Rejected('Git unavailable: ' + str(error))
    require(proc.returncode == 0, 'Git verification failed: ' + proc.stderr.strip())
    return proc.stdout.strip()


def _is_ancestor(tree, ancestor, descendant):
    try:
        proc = subprocess.run(['git', '-C', str(tree), 'merge-base', '--is-ancestor', ancestor, descendant],
                              capture_output=True, text=True)
    except OSError:
        return True  # Git unavailable: skip ancestry, never fail open on a missing tool
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return True


def observe_maintained_sources(reg, controller_config=CONFIG_PATH):
    """Read real Git HEADs of the configured maintained lines; never under a lock."""
    path = local_path(reg.root, controller_config)
    require(path.is_file(), 'Controller config missing: ' + str(controller_config))
    lines = (json.loads(path.read_text(encoding='utf-8-sig')) or {}).get('integration_lines') or {}
    observed = {}
    for kind in ('root', 'native'):
        spec = lines.get(kind) or {}
        repo, ref = spec.get('repo'), spec.get('ref')
        require(nonempty(repo) and nonempty(ref), 'Maintained ' + kind + ' line not configured')
        tree = local_path(reg.root, repo)
        require(tree.is_dir(), 'Maintained ' + kind + ' worktree missing: ' + repo)
        observed[kind] = dict(repo=repo, ref=ref, commit=_commit(_git(tree, 'rev-parse', ref), kind),
                              dirty=_git(tree, 'status', '--porcelain'))
    return observed


def _validate_stream_worktrees(reg, record):
    """Confirm provisioned stream worktrees descend from the recorded maintained base."""
    for kind, worktree in (record.get('worktrees') or {}).items():
        if kind not in ('root', 'native') or not nonempty(worktree):
            continue
        tree = local_path(reg.root, worktree)
        if not tree.is_dir() or not (tree / '.git').exists():
            continue  # Worktree not present on this host; nothing to fence.
        head = _git(tree, 'rev-parse', 'HEAD')
        require(_is_ancestor(tree, record['maintained_base'][kind], head),
                'Stream ' + kind + ' worktree does not descend from the maintained base')


def section(state, create=False):
    data = state.get('development_streams')
    if data is None:
        require(create, 'development_streams section not configured')
        data = state['development_streams'] = dict(schema=SCHEMA, streams={})
    require(data.get('schema') == SCHEMA, 'Unsupported development_streams schema')
    data.setdefault('streams', {})
    return data


def _stream(data, stream):
    require(isinstance(stream, str) and stream in data['streams'], 'Unknown development stream: ' + str(stream))
    return data['streams'][stream]


def _stale(stream, base):
    return base != stream['maintained_base']


def _owner_for(data, lane):
    return next((s for s in data['streams'].values()
                 if (s.get('owner') or {}).get('lane') == lane), None)


def _require_live_owner(reg, state, record):
    """A stored owner label is not authority; require a live lane at generation."""
    owner = record.get('owner')
    require(owner, 'Stream has no bound owner')
    lane = state.get('lanes', {}).get(owner['lane'])
    require(lane, 'Bound owner lane is not registered: ' + owner['lane'])
    require(lane['generation'] == owner['generation'], 'Stream owner ownership generation is stale')
    require(lane.get('state') != 'done', 'Stream owner lane is terminal')
    require(reg.probe(lane['process']) == 'alive', 'Stream owner process is not live')
    return lane


def configure(reg, streams, *, supersede=False):
    """Register or refresh stream definitions; never touches lanes or consumers."""
    require(isinstance(streams, list) and streams, 'A list of stream definitions is required')
    with reg.transaction() as state:
        data = section(state, create=True)
        now = reg.clock()
        recorded = []
        for item in streams:
            require(isinstance(item, dict), 'Stream definition must be an object')
            stream = item.get('id')
            require(isinstance(stream, str) and stream and all(
                part not in stream for part in ('/', '\\', '..')), 'Stable lowercase stream ID required')
            require(re.fullmatch(STREAM_ID, stream), 'Stable lowercase stream ID required')
            require(nonempty(item.get('name')) and nonempty(item.get('scope')), 'Name and scope required')
            hooks = item.get('shared_hooks', [])
            require(isinstance(hooks, list) and all(nonempty(h) for h in hooks),
                    'shared_hooks must be repository-relative paths')
            base = _base(item.get('maintained_base'))
            existing = data['streams'].get(stream)
            if existing and existing['maintained_base'] != base and not supersede:
                raise Rejected('Maintained base changed for ' + stream + '; pass supersede=true explicitly')
            previous_base = existing['maintained_base'] if existing else None
            record = existing or dict(id=stream, candidates={}, maintained_receipts={},
                                      owner=None, ready_batch=None, status='provisioned',
                                      created_at=now)
            record.update(name=item['name'], scope=item['scope'], shared_hooks=hooks,
                          maintained_base=base, worktrees=copy.deepcopy(item.get('worktrees') or {}),
                          repository=item.get('repository') or 'paired', updated_at=now)
            if record.get('owner') is None:
                record['status'] = 'awaiting-owner'
            if previous_base is not None and previous_base != base:
                for candidate in record['candidates'].values():
                    if candidate['state'] in ('draft', 'ready') and candidate['base'] != base:
                        candidate.update(state='stale', stale_at=now)
                if record.get('ready_batch') and record['candidates'][record['ready_batch']]['state'] != 'ready':
                    record['ready_batch'] = None
            data['streams'][stream] = record
            recorded.append(stream)
        data['configured_at'] = now
        return copy.deepcopy([data['streams'][s] for s in recorded])


def bind_owner(reg, stream, lane, generation, *, replace=False):
    """Bind exactly one live existing lane at its current generation; conflicts fail closed."""
    require(type(generation) is int, 'Current owner generation is mandatory')
    with reg.transaction() as state:
        data = section(state)
        record = _stream(data, stream)
        require(lane in state.get('lanes', {}), 'Owner lane is not registered: ' + str(lane))
        owner_lane = state['lanes'][lane]
        require(owner_lane['generation'] == generation, 'Stale owner generation; read current status first')
        require(owner_lane.get('state') != 'done', 'A completed lane cannot own a development stream')
        require(reg.probe(owner_lane['process']) == 'alive', 'Owner lane process must be live')
        other = _owner_for(data, lane)
        if other is not None and other['id'] != stream:
            raise Rejected('Lane already owns stream ' + other['id'])
        current = record.get('owner')
        if current and current['lane'] != lane:
            require(replace, 'Stream already owned by ' + current['lane'] + '; pass replace=true explicitly')
        now = reg.clock()
        record['owner'] = dict(lane=lane, worker_id=owner_lane.get('worker_id'),
                               generation=owner_lane['generation'], bound_at=now)
        record['status'] = 'active'
        record['updated_at'] = now
        return copy.deepcopy(record['owner'])


def submit_candidate(reg, stream, candidate, *, observed=None):
    """Record a stream-local candidate; stale maintained HEAD and slot conflicts fail."""
    require(isinstance(candidate, dict), 'Candidate must be an object')
    for key in ('id', 'title', 'summary'):
        require(nonempty(candidate.get(key)), key + ' required')
    references = candidate.get('references', [])
    require(isinstance(references, list) and all(nonempty(r) for r in references),
            'references must name existing lanes or issues, not duplicate work')
    state_value = candidate.get('state', 'draft')
    require(state_value in CANDIDATE_STATES, 'Unknown candidate state')
    observed = observed or observe_maintained_sources(reg)
    observed_base = _observed_commits(observed)
    with reg.transaction() as state:
        data = section(state)
        record = _stream(data, stream)
        _require_live_owner(reg, state, record)
        require(observed_base == record['maintained_base'],
                'Maintained source moved; refresh the stream base explicitly before submitting')
        base = _base(candidate.get('base'))
        require(not _stale(record, base), 'Candidate pins a stale maintained base')
        evidence = candidate.get('evidence')
        path = reg.evidence(evidence)
        commits = candidate.get('commits') or {}
        for kind in ('root', 'native'):
            values = commits.get(kind, [])
            require(isinstance(values, list) and all(isinstance(v, str) and _is_commit(v) for v in values),
                    kind + ': ordered full commits required')
        if state_value == 'ready':
            ready = record.get('ready_batch')
            if ready and record['candidates'].get(ready, {}).get('state') == 'ready':
                raise Rejected('Stream already has a ready batch: ' + ready)
        now = reg.clock()
        entry = record['candidates'].get(candidate['id'], {})
        entry.update(id=candidate['id'], title=candidate['title'], summary=candidate['summary'],
                     references=list(references), base=base, commits=copy.deepcopy(commits),
                     owner_lane=record['owner']['lane'], owner_generation=record['owner']['generation'],
                     state=state_value, evidence={'path': evidence['path'], 'sha256': digest(path)},
                     observed=copy.deepcopy(observed),
                     created_at=entry.get('created_at', now), updated_at=now)
        record['candidates'][candidate['id']] = entry
        if state_value == 'ready':
            record['ready_batch'] = candidate['id']
        record['updated_at'] = now
        return copy.deepcopy(entry)


def retire_ready(reg, stream, candidate, lane, generation, disposition, *, reason=None, integration_lane=None):
    """Fenced close of the ready batch: abandon or reference a canonical integration.

    Never writes maintained hashes and never marks the lane done.  Replay is
    idempotent for the exact disposition/reason; a conflicting replay is refused.
    """
    require(disposition in CLOSED_STATES, 'Disposition must be one of ' + ', '.join(CLOSED_STATES))
    require(nonempty(candidate), 'Ready candidate ID required')
    require(type(generation) is int, 'Current owner generation is mandatory')
    if disposition == 'abandoned':
        require(nonempty(reason), 'Abandoned batch requires a reason')
    with reg.transaction() as state:
        data = section(state)
        record = _stream(data, stream)
        owner = _require_live_owner(reg, state, record)
        require(lane == owner['lane'] and owner['generation'] == generation,
                'Only the bound owner at its current generation can retire the ready batch')
        require(candidate in record['candidates'], 'Unknown candidate: ' + str(candidate))
        entry = record['candidates'][candidate]
        if entry['state'] in CLOSED_STATES:
            expected = dict(disposition=entry.get('disposition'), reason=entry.get('reason'))
            require(expected == dict(disposition=disposition, reason=reason), 'Conflicting batch replay')
            return copy.deepcopy(entry)
        require(record.get('ready_batch') == candidate, 'Only the current ready batch can be retired')
        now = reg.clock()
        reference = None
        if disposition == 'maintained':
            require(nonempty(integration_lane), 'Canonical integration lane required')
            integrated = state.get('lanes', {}).get(integration_lane)
            require(integrated, 'Integration lane is not registered: ' + str(integration_lane))
            receipt = integrated.get('integration')
            require(isinstance(receipt, dict), 'Integration lane has no canonical integration record')
            root_commit = _commit(receipt.get('root_commit'), 'integration root_commit')
            reg.evidence(dict(path=receipt.get('validation_path'), sha256=receipt.get('validation_sha256')))
            native = integrated.get('native') is not None
            native_commit = _commit(receipt.get('native_commit'), 'integration native_commit') if native else None
            if native:
                require(isinstance(receipt.get('native_dirty'), str) and nonempty(receipt.get('export_evidence')),
                        'Canonical native integration requires dirty state and export evidence')
                reg.evidence(dict(path=receipt.get('export_evidence'), sha256=receipt.get('export_sha256')))
            reference = dict(lane=integrated['lane'], generation=integrated['generation'],
                             root_commit=root_commit, native_commit=native_commit,
                             integrated_at=integrated.get('integrated_at'), reference_only=True)
        entry.update(state=disposition, disposition=disposition, reason=reason or None,
                     closed_at=now, closed_by=lane, maintained_reference=reference, ready=False)
        record['ready_batch'] = None
        record['updated_at'] = now
        if reference:
            record['maintained_receipts'][candidate] = reference
        return copy.deepcopy(entry)


def validate_sources(reg, stream, observed=None):
    """Fail closed when the real maintained HEAD no longer matches the recorded base."""
    observed = observed or observe_maintained_sources(reg)
    observed_base = _observed_commits(observed)
    state = reg.snapshot()
    stored = state.get('development_streams') or {}
    data = section({'development_streams': stored})
    record = _stream(data, stream)
    require(observed_base == record['maintained_base'],
            'Observed maintained source is stale against the recorded base for ' + stream)
    _validate_stream_worktrees(reg, record)
    return dict(maintained_base=copy.deepcopy(record['maintained_base']), observed=copy.deepcopy(observed))


def receipt_references(reg, stream):
    """Read-only maintained receipt references for a stream; never grants authority."""
    data = section({'development_streams': (reg.snapshot().get('development_streams') or {})})
    return copy.deepcopy(list(_stream(data, stream)['maintained_receipts'].values()))


def status(reg, stream=None):
    """Report configured streams, live owners and unstaffed roles honestly."""
    state = reg.snapshot()
    stored = state.get('development_streams') or {}
    if not stored.get('streams'):
        return []
    data = section({'development_streams': stored})
    lanes = state.get('lanes', {})
    records = [data['streams'][stream]] if stream else list(data['streams'].values())
    report = []
    for record in records:
        candidates = record['candidates']
        ready = record.get('ready_batch')
        owner = record.get('owner')
        lane = lanes.get(owner['lane']) if owner else None
        if not owner:
            owner_state = 'awaiting-controller-assignment'
        elif not lane or lane['generation'] != owner['generation']:
            owner_state = 'assigned-stale-generation'
        elif lane.get('state') == 'done':
            owner_state = 'assigned-terminal'
        elif reg.probe(lane['process']) != 'alive':
            owner_state = 'assigned-not-live'
        else:
            owner_state = 'assigned-live'
        report.append(dict(
            id=record['id'], name=record['name'], scope=record['scope'],
            status=record['status'], maintained_base=record['maintained_base'],
            shared_hooks=record['shared_hooks'], worktrees=record['worktrees'],
            owner=owner, owner_state=owner_state,
            ready_batch=ready if ready and candidates.get(ready, {}).get('state') == 'ready' else None,
            candidate_count=len(candidates),
            stale_candidates=[c['id'] for c in candidates.values() if c['state'] == 'stale'],
            closed_candidates=[c['id'] for c in candidates.values() if c['state'] in CLOSED_STATES],
            maintained_receipts=sorted(record['maintained_receipts'])))
    return report


def _is_commit(value):
    return isinstance(value, str) and bool(re.fullmatch(COMMIT, value))


def manifest(reg, **_):
    """Current inventory/routing view; never fabricates owners or assignments."""
    streams = status(reg)
    return dict(schema=SCHEMA, streams=streams,
                maintained_base={s['id']: s['maintained_base'] for s in streams})


def dispatch(reg, request):
    operation = request.get('operation')
    if operation == 'configure':
        return {'streams': [s['id'] for s in configure(reg, request['streams'],
                                                       supersede=request.get('supersede', False))]}
    if operation == 'bind-owner':
        return {'owner': bind_owner(reg, request['stream'], request['lane'], request['generation'],
                                    replace=request.get('replace', False))}
    if operation == 'submit-candidate':
        return {'candidate': submit_candidate(reg, request['stream'], request['candidate'],
                                              observed=request.get('observed'))}
    if operation == 'retire-ready':
        return {'candidate': retire_ready(reg, request['stream'], request['candidate'], request['lane'],
                                          request['generation'], request['disposition'],
                                          reason=request.get('reason'),
                                          integration_lane=request.get('integration_lane'))}
    if operation == 'validate-sources':
        return validate_sources(reg, request['stream'], request.get('observed'))
    if operation == 'receipts':
        return {'maintained_receipts': receipt_references(reg, request['stream'])}
    if operation == 'status':
        return {'streams': status(reg, request.get('stream'))}
    if operation == 'manifest':
        return manifest(reg)
    raise Rejected('Unknown operation: ' + str(operation))


def main():
    from .registry import Registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    reg = Registry(args.root / 'output/workflow/registry.sqlite3', args.root)
    request = json.loads(args.request.read_text(encoding='utf-8-sig'))
    print(json.dumps(dispatch(reg, request), indent=2))


if __name__ == '__main__':
    main()
