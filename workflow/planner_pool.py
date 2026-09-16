"""Bounded, partitioned planning turns on the existing approved worker pool."""
import copy
import json
import math
from types import SimpleNamespace
from .control import fingerprint
from .handoff import require, digest, Rejected


def merge_proposals(reg, manifest_path, proposal_path, issue_reader=None):
    """Coordinator publication: validate new specs, then serialize append/replay."""
    from .autofill import _private, validate_spec, github_issue, _check_conflicts
    from .runner import write
    manifest_path, proposal_path = _private(reg, str(manifest_path)), _private(reg, str(proposal_path))
    proposals = json.loads(proposal_path.read_text(encoding='utf-8-sig'))['items']
    require(isinstance(proposals, list) and proposals, 'Nonempty proposal items required')
    before = manifest_path.read_bytes()
    manifest = json.loads(before)
    require(manifest.get('schema') == 1 and manifest.get('repository') == '4laric/pikmin-randomizer'
            and manifest.get('assignee') == '4laric', 'Invalid coordinator manifest')
    known = {s['id']: s for s in manifest['items']}
    require(len(known) == len(manifest['items']), 'Duplicate manifest IDs')
    added = []
    for spec in proposals:
        if spec['id'] in known:
            require(known[spec['id']] == spec, 'Published spec cannot change')
            continue
        validate_spec(reg, spec, issue_reader or github_issue)
        known[spec['id']] = spec
        added.append(spec)
    with reg.transaction() as state:
        require(manifest_path.read_bytes() == before, 'Manifest changed; reread and retry publication')
        controller = SimpleNamespace(reg=reg, config={'lanes': {}})
        for spec in added:
            _check_conflicts(controller, state, spec)
            for other in known.values():
                if other['id'] == spec['id'] or state['lanes'].get(other['lane']['lane'], {}).get('state') == 'done': continue
                require(spec['lane']['issue'] != other['lane']['issue'] and spec['lane']['lane'] != other['lane']['lane'],
                        'Proposal duplicates an outstanding issue/lane')
                require(not ({f.casefold() for f in spec['lane']['owned_files']} &
                             {f.casefold() for f in other['lane']['owned_files']}), 'Proposal files overlap outstanding scope')
                require(_private(reg, spec['launch']['output']) != _private(reg, other['launch']['output']), 'Proposal output overlaps')
                trees = {_private(reg, spec['lane'][k]['worktree']) for k in ('root','native') if spec['lane'].get(k)}
                require(not trees & {_private(reg, other['lane'][k]['worktree']) for k in ('root','native') if other['lane'].get(k)},
                        'Proposal worktree overlaps')
        if added:
            backup = manifest_path.parent / 'coordinator-backups' / (fingerprint(manifest) + '.json')
            backup.parent.mkdir(exist_ok=True)
            if not backup.exists(): backup.write_bytes(before)
            manifest['items'].extend(added)
            write(manifest_path, manifest)
    return [s['id'] for s in added]


def tick(controller, settings, issue_reader):
    from .autofill import _private, _workers, _state, _prepare
    reg = controller.reg
    config = settings.get('planner_pool', {})
    if not config.get('enabled'): return
    launches = reg.control_status()['launches']
    waiting = [key for key in config.get('wait_for_launches', [])
               if launches.get(key, {}).get('status') != 'exited']
    with reg.transaction() as state:
        _state(state).setdefault('planner_pool', {})['waiting_for_coordinator'] = waiting
    if waiting: return
    helpers = config.get('helpers', [])
    require(len({h['scope'] for h in helpers}) == len(helpers), 'Duplicate planner partition')
    with reg.transaction() as state:
        records = copy.deepcopy(_state(state).setdefault('planner_pool', {}).setdefault('scopes', {}))
    # Receiving a report accepts no proposed implementation or gameplay gate.
    for scope, record in records.items():
        lane = reg.status()['lanes'].get(record['spec']['lane']['lane'])
        if lane and lane['state'] == 'review_ready':
            with reg.transaction() as state:
                safe = reg.recovery_safe(state, state['lanes'][lane['lane']])
            if safe:
                reg.accept_review(lane['lane'], lane['generation'],
                    'Planning report received; coordinator validation still required; no gameplay acceptance',
                    lane['review']['evidence']['review'])
        if lane and reg.status()['lanes'][lane['lane']]['state'] == 'done':
            with reg.transaction() as state:
                live = _state(state)['planner_pool']['scopes'][scope]
                live.setdefault('completed_at', reg.clock())
                _state(state)['items'][record['spec']['id']].update(status='completed', ready=False)
    with reg.transaction() as state:
        data = _state(state)
        pool = data['planner_pool']
        records = copy.deepcopy(pool['scopes'])
        active = sum('completed_at' not in record for record in records.values())
        ready = sum(bool(i.get('ready')) and not i.get('planner_helper') for i in data['items'].values())
        idle = len(_workers(reg, state))
        deficit = max(0, settings.get('low_watermark', 8) - ready)
        target = min(config.get('max_active', 3), len(helpers),
                     math.ceil(deficit / max(1, config.get('items_per_helper', 4))),
                     max(0, idle + active - ready - config.get('reserve_workers', 2)))
        pool.update(enabled=True, active=active, target=target, ready_backlog=ready, updated_at=reg.clock())
    if not controller.capacity() or not 0 <= controller.memory() < 90: return
    for helper in helpers:
        scope = helper['scope']
        record = records.get(scope)
        pending = record and 'completed_at' not in record
        if pending:
            with reg.transaction() as state:
                if _state(state)['items'][record['spec']['id']]['phase'] == 'enqueued': continue
            spec = record['spec']
        else:
            if active >= target: continue
            if record and reg.clock() - record['completed_at'] < max(300, config.get('cooldown_seconds', 900)): continue
            path = _private(reg, helper['template'])
            require(digest(path) == helper['sha256'], 'Planner template bytes changed')
            spec = json.loads(path.read_text(encoding='utf-8-sig'))
            require(spec['role'] == 'review' and spec['heavy'] is False and spec['lane']['native'] is None,
                    'Planner template must be non-build review work')
            cycle = (record or {}).get('cycle', 0) + 1
            spec['id'] += '-cycle-' + str(cycle)
            spec['lane']['lane'] += '-cycle-' + str(cycle)
            spec['instruction'] += (' Planning partition: ' + scope +
                '. Stage proposals only in your configured partition; never write the shared manifest. '
                'Finish review-ready with a hashed planning report even when no actionable scope exists. '
                'No implementation, builds, worker launches or ADMIT. Respect coordinator ownership partition.')
            with reg.transaction() as state:
                data = _state(state)
                data['planner_pool']['scopes'][scope] = dict(spec=spec, cycle=cycle, started_at=reg.clock())
                data['items'][spec['id']] = dict(spec_hash=fingerprint(spec), priority=spec['priority'],
                    lane=spec['lane']['lane'], phase='pending', status='pending', ready=False, planner_helper=True)
            active += 1
        try:
            if _prepare(controller, spec, issue_reader): return
        except (Rejected, OSError, ValueError, KeyError) as exc:
            with reg.transaction() as state:
                _state(state)['planner_pool']['scopes'][scope]['error'] = str(exc)
