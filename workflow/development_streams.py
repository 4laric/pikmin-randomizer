"""Operator-reviewed development streams layered on the shared registry.

An isolated ``development_streams`` section tracks stream provisioning, explicit
owner binding, stream-local candidate receipts and final maintained receipt
*references*.  Stream-local status is never canonical ``done``/``integrated``: the
module never calls ``Registry.integrate``, never dispatches and never wakes a
maintained consumer.  Final merges, maintained builds/exports and admission stay
with the existing sole integration owner.

Fail-closed rules:
* a stream owner must be an existing, live, unfinished lane and own no other stream;
* a stream-local candidate must pin the stream's current maintained base, so a
  moved maintained base makes the candidate stale and unpromotable;
* at most one ``ready`` batch exists per stream;
* maintained receipt references may only be recorded by an integration owner lane.
"""
import argparse
import copy
import json
import re
from pathlib import Path

from .handoff import Rejected, digest, nonempty, require

SCHEMA = 1
STREAM_ID = r'[a-z0-9][a-z0-9_-]*'
COMMIT = r'[0-9a-f]{40}'
STREAM_STATES = ('provisioned', 'awaiting-owner', 'active')
CANDIDATE_STATES = ('draft', 'ready', 'stale')
INTEGRATOR_LEVEL = 'integration ownership'


def _commit(value, name):
    require(isinstance(value, str) and re.fullmatch(COMMIT, value), name + ': full commit required')
    return value


def _base(value):
    require(isinstance(value, dict), 'maintained base record required')
    return {kind: _commit((value.get(kind) or {}).get('commit'), kind) if isinstance(value.get(kind), dict)
            else _commit(value.get(kind), kind) for kind in ('root', 'native')}


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
                    if candidate['base'] != base and candidate['state'] != 'stale':
                        candidate.update(state='stale', stale_at=now)
                if record.get('ready_batch') and record['candidates'][record['ready_batch']]['state'] == 'stale':
                    record['ready_batch'] = None
            data['streams'][stream] = record
            recorded.append(stream)
        data['configured_at'] = now
        return copy.deepcopy([data['streams'][s] for s in recorded])


def bind_owner(reg, stream, lane, generation=None, *, replace=False):
    """Bind exactly one existing lane to one stream; conflicts fail closed."""
    with reg.transaction() as state:
        data = section(state)
        record = _stream(data, stream)
        require(lane in state.get('lanes', {}), 'Owner lane is not registered: ' + str(lane))
        owner_lane = state['lanes'][lane]
        require(generation is None or owner_lane['generation'] == generation, 'Stale owner generation')
        require(owner_lane.get('state') != 'done', 'A completed lane cannot own a development stream')
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


def submit_candidate(reg, stream, candidate):
    """Record a stream-local candidate; stale pins and a second ready batch fail."""
    require(isinstance(candidate, dict), 'Candidate must be an object')
    for key in ('id', 'title', 'summary'):
        require(nonempty(candidate.get(key)), key + ' required')
    references = candidate.get('references', [])
    require(isinstance(references, list) and all(nonempty(r) for r in references),
            'references must name existing lanes or issues, not duplicate work')
    state_value = candidate.get('state', 'draft')
    require(state_value in CANDIDATE_STATES, 'Unknown candidate state')
    with reg.transaction() as state:
        data = section(state)
        record = _stream(data, stream)
        require(record.get('owner'), 'Stream has no bound owner; candidate cannot be promoted')
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
                     created_at=entry.get('created_at', now), updated_at=now)
        record['candidates'][candidate['id']] = entry
        if state_value == 'ready':
            record['ready_batch'] = candidate['id']
        record['updated_at'] = now
        return copy.deepcopy(entry)


def record_maintained_receipt(reg, stream, receipt):
    """Store a *reference* to an integrator's maintained receipt; grants no authority."""
    require(isinstance(receipt, dict), 'Receipt must be an object')
    require(nonempty(receipt.get('id')) and nonempty(receipt.get('recorded_by')),
            'Receipt id and recorded_by required')
    with reg.transaction() as state:
        data = section(state)
        record = _stream(data, stream)
        author = state.get('lanes', {}).get(receipt['recorded_by'])
        require(author, 'Recording lane is not registered')
        require(author.get('target_level') == INTEGRATOR_LEVEL,
                'Only an integration owner can record a maintained receipt reference')
        root_commit = _commit(receipt.get('root_commit'), 'root_commit')
        native_commit = _commit(receipt.get('native_commit'), 'native_commit')
        evidence = receipt.get('export_evidence')
        path = reg.evidence(evidence)
        candidate = receipt.get('candidate')
        require(candidate is None or candidate in record['candidates'],
                'Receipt candidate is not recorded in this stream')
        now = reg.clock()
        entry = dict(id=receipt['id'], stream=stream, candidate=candidate,
                     recorded_by=author['lane'], recorded_generation=author['generation'],
                     root_commit=root_commit, native_commit=native_commit,
                     export_evidence={'path': evidence['path'], 'sha256': digest(path)},
                     reference_only=True, at=now)
        record['maintained_receipts'][receipt['id']] = entry
        record['updated_at'] = now
        return copy.deepcopy(entry)


def validate_sources(reg, stream, observed):
    """Fail closed when an observed source no longer matches the maintained base."""
    stored = reg.snapshot().get('development_streams') or {}
    data = section({'development_streams': stored})
    record = _stream(data, stream)
    observed_base = _base(observed)
    require(not _stale(record, observed_base),
            'Observed source is stale against the maintained base for ' + stream)
    return copy.deepcopy(record['maintained_base'])


def status(reg, stream=None):
    """Report configured streams, explicit owners and unstaffed roles honestly."""
    stored = reg.snapshot().get('development_streams') or {}
    if not stored.get('streams'):
        return []
    data = section({'development_streams': stored})
    records = [data['streams'][stream]] if stream else list(data['streams'].values())
    report = []
    for record in records:
        candidates = record['candidates']
        ready = record.get('ready_batch')
        report.append(dict(
            id=record['id'], name=record['name'], scope=record['scope'],
            status=record['status'], maintained_base=record['maintained_base'],
            shared_hooks=record['shared_hooks'], worktrees=record['worktrees'],
            owner=record.get('owner') or None,
            owner_state='assigned' if record.get('owner') else 'awaiting-controller-assignment',
            ready_batch=ready if ready and candidates.get(ready, {}).get('state') == 'ready' else None,
            candidate_count=len(candidates),
            stale_candidates=[c['id'] for c in candidates.values() if c['state'] == 'stale'],
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
        return {'owner': bind_owner(reg, request['stream'], request['lane'],
                                    request.get('generation'), replace=request.get('replace', False))}
    if operation == 'submit-candidate':
        return {'candidate': submit_candidate(reg, request['stream'], request['candidate'])}
    if operation == 'record-receipt':
        return {'receipt': record_maintained_receipt(reg, request['stream'], request['receipt'])}
    if operation == 'validate-sources':
        return {'maintained_base': validate_sources(reg, request['stream'], request['observed'])}
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
