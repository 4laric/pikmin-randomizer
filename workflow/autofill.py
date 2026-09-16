"""Deterministic refill from operator-prepared, issue-backed local slice specs.

This module never creates worktrees, issues, workers or admission decisions. Every
mutation is replayable; actual execution remains the sole controller's pool path.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

from .control import fingerprint
from .handoff import Rejected, digest, local_path, require, source_record
from .runner import write
from .scheduling import pending_heavy_lanes

PRIORITIES = {'enemy_acceptance': 0, 'existing_content': 1, 'expansion': 2}


def _state(state):
    return state.setdefault('throughput_runtime', {}).setdefault('autofill', {'items': {}})


def _private(reg, value):
    path = local_path(reg.root, value)
    require(path.is_relative_to(reg.root / 'output'), 'Autofill paths must be private under output/')
    return path


def _git(tree, *args):
    result = subprocess.run(['git', '-C', str(tree), *args], capture_output=True, text=True, timeout=30)
    require(result.returncode == 0, 'Prepared worktree git verification failed: ' + result.stderr.strip())
    return result.stdout.strip()


def github_issue(number):
    result = subprocess.run(['gh', 'issue', 'view', str(number), '--repo', '4laric/pikmin-randomizer',
                             '--json', 'number,state,assignees,url,body,updatedAt'],
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    require(result.returncode == 0, 'Cannot verify GitHub issue assignment')
    return json.loads(result.stdout)


def _issue(record, number, body_hash):
    require(record.get('number') == number and record.get('state') == 'OPEN', 'Issue must be open and match slice')
    require(record.get('url') == f'https://github.com/4laric/pikmin-randomizer/issues/{number}', 'Wrong issue repository')
    require(any(a.get('login') == '4laric' for a in record.get('assignees', [])), 'Issue must be assigned to 4laric')
    body = record.get('body')
    require(isinstance(body, str) and body.strip() and hashlib.sha256(body.encode()).hexdigest() == body_hash,
            'Issue scope/body differs from prepared spec')


def validate_spec(reg, spec, issue_reader=github_issue, *, verified=False):
    required = {'id', 'priority', 'workstream', 'role', 'capabilities', 'heavy', 'instruction',
                'lane', 'launch', 'launch_hashes', 'issue_proof', 'issue_body_sha256'}
    require(set(spec) == required, 'Autofill spec fields must be explicit')
    require(isinstance(spec['id'], str) and spec['id'] and len(spec['id']) <= 120, 'Bounded spec ID required')
    require(isinstance(spec['priority'], str) and spec['priority'] in PRIORITIES, 'Unknown autofill priority')
    from .scheduling import ROLES
    require(isinstance(spec['role'], str) and spec['role'] in ROLES, 'Known role required')
    require(isinstance(spec['capabilities'], list) and all(isinstance(v, str) and v for v in spec['capabilities']), 'Explicit capabilities required')
    require(type(spec['heavy']) is bool, 'Heavy flag must be boolean')
    require(isinstance(spec['instruction'], str) and spec['instruction'].strip(), 'Bounded instruction required')
    require(set(spec['launch_hashes']) == {'brief', 'config'}, 'Exact launch byte hashes required')
    lane = spec['lane']
    require(isinstance(lane, dict) and 'owner' not in lane and 'worker_id' not in lane and 'task_id' not in lane,
            'Worker identity must be inherited, not invented')
    require(isinstance(lane.get('owned_files'), list) and lane['owned_files'] and
            all(isinstance(f, str) and f for f in lane['owned_files']), 'Explicit owned file strings required')
    require(type(lane.get('issue')) is int and lane['issue'] > 0, 'Explicit issue required')
    for label in ('root', 'native'):
        source = lane.get(label)
        if source is None and label == 'native':
            continue
        source_record(source, label)
        tree = _private(reg, source['worktree'])
        require(Path(_git(tree, 'rev-parse', '--show-toplevel')).resolve() == tree, 'Prepared worktree root mismatch')
        require(_git(tree, 'rev-parse', 'HEAD') == source['head'], 'Prepared source head changed')
        require(not source['dirty'] and not _git(tree, 'status', '--porcelain'), 'Prepared source must be clean')
    launch = spec['launch']
    require(set(launch) == {'root', 'output', 'brief', 'config'}, 'Prepared launch fields required')
    require(_private(reg, launch['root']) == _private(reg, lane['root']['worktree']), 'Launch/source root mismatch')
    require(_private(reg, launch['output']).is_dir(), 'Prepared output directory missing')
    for label in ('brief', 'config'):
        require(_private(reg, launch[label]).is_file(), 'Prepared ' + label + ' missing')
        require(digest(_private(reg, launch[label])) == spec['launch_hashes'][label], 'Prepared ' + label + ' bytes changed')
    proof = spec['issue_proof']
    path = _private(reg, proof['path'])
    require(path.is_file() and digest(path) == proof['sha256'], 'Issue proof missing or changed')
    _issue(json.loads(path.read_text(encoding='utf-8-sig')), lane['issue'], spec['issue_body_sha256'])
    if not verified:
        _issue(issue_reader(lane['issue']), lane['issue'], spec['issue_body_sha256'])


def _launch(spec):
    return dict(copy.deepcopy(spec['launch']), autofill_proof=dict(spec_hash=fingerprint(spec), **spec['launch_hashes']))


def launch_files_unchanged(reg, entry):
    try:
        return all(digest(_private(reg, entry[k])) == entry['autofill_proof'][k] for k in ('brief', 'config'))
    except (Rejected, OSError, ValueError, KeyError, TypeError):
        return False


def _workers(reg, state, spec=None):
    pool = reg.scheduling(state)
    candidates = []
    for worker in pool['workers'].values():
        if spec and (spec['role'] not in worker['roles'] or not set(spec['capabilities']) <= set(worker['capabilities'])):
            continue
        lanes = [l for l in state['lanes'].values() if l['worker_id'] == worker['worker_id']]
        if not lanes or any(l['state'] != 'done' or not reg.recovery_safe(state, l) for l in lanes):
            continue
        if any(a['worker_id'] == worker['worker_id'] and a['status'] in ('assigned', 'dispatched') for a in pool['assignments'].values()):
            continue
        if any(a['lane'] in {l['lane'] for l in lanes} and a['status'] in ('intent', 'spawned', 'running')
               for a in state.get('control', {}).get('launches', {}).values()):
            continue
        latest = max(lanes, key=lambda l: (l['created_at'], l['lane']))
        if latest.get('integration') or latest.get('review_disposition'):
            candidates.append(latest)
    return sorted(candidates, key=lambda l: (l['worker_id'], l['lane']))


def autofill_status(reg):
    with reg.transaction() as state:
        data = copy.deepcopy(_state(state))
        data['idle_workers_count'] = len(_workers(reg, state))
        data['ready_count'] = sum(i.get('ready', False) and
            (i['lane'] not in state['lanes'] or (state['lanes'][i['lane']]['state'] == 'ready' and
             reg.recovery_safe(state, state['lanes'][i['lane']]))) for i in data['items'].values())
        data['pending_count'] = sum(i.get('phase') == 'pending' for i in data['items'].values())
        data['active_enemy_count'] = sum(item.get('priority') == 'enemy_acceptance' and
            not item.get('planner_helper') and
            item.get('phase') in ('provisioned', 'configured', 'enqueued') and
            state['lanes'].get(item.get('lane'), {}).get('state') in ('running', 'waiting_resource') for item in data['items'].values())
        since = data.get('needs_refill_since')
        data['starvation_seconds'] = max(0, reg.clock() - since) if since is not None else 0
        return data


def _blocked(reg, identity, reason):
    with reg.transaction() as state:
        item = _state(state)['items'][identity]
        item.update(status='blocked', reason=str(reason), updated_at=reg.clock(), ready=False)
        if item.get('phase') == 'intent' and item.get('lane') not in state['lanes']:
            for key in ('previous_lane', 'worker_id', 'owner', 'issue_verified_at'):
                item.pop(key, None)
            item['phase'] = 'pending'


def _check_conflicts(controller, state, spec):
    reg = controller.reg
    from .remote import check_remote_ownership
    check_remote_ownership(state, spec['lane']['issue'], spec['lane']['owned_files'])
    requested = {_private(reg, spec['lane'][k]['worktree']) for k in ('root','native') if spec['lane'].get(k)}
    launches = state.get('throughput_runtime', {}).get('launch_specs', {})
    for other in state['lanes'].values():
        if other['state'] == 'done':
            continue
        require(other['issue'] != spec['lane']['issue'], 'Issue has unfinished lane')
        require(not ({f.casefold() for f in other['owned_files']} &
                     {f.casefold() for f in spec['lane']['owned_files']}), 'Owned files overlap')
        occupied = {local_path(reg.root, other[k]['worktree']) for k in ('root','native') if other.get(k)}
        require(not requested & occupied, 'Prepared worktree is already owned by an unfinished lane')
        launch = launches.get(other['lane']) or controller.config['lanes'].get(other['lane'])
        if launch:
            require(_private(reg, launch['output']) != _private(reg, spec['launch']['output']), 'Launch output is already owned by an unfinished lane')


def _prepare(controller, spec, issue_reader):
    reg = controller.reg
    identity, spec_hash = spec['id'], fingerprint(spec)
    with reg.transaction() as state:
        data = _state(state)
        item = data['items'].get(identity)
        require(item is not None and item['spec_hash'] == spec_hash, 'Spec changed after publication')
        if item.get('phase') == 'enqueued':
            if state['lanes'].get(item['lane'], {}).get('state') == 'done':
                item.update(status='completed', updated_at=reg.clock())
            return False
        pinned = item.get('previous_lane')
        verified = item.get('issue_verified_at') is not None and reg.clock() - item['issue_verified_at'] <= 86400
    # After provisioning a worker may already have edited its worktree. Replay
    # checks the recorded identity, not a falsely required clean implementation.
    if not pinned or item.get('phase') == 'intent':
        validate_spec(reg, spec, issue_reader, verified=False)
    with reg.transaction() as state:
        data = _state(state)
        item = data['items'][identity]
        pool = reg.scheduling(state)
        stream = pool['workstreams'].get(spec['workstream'])
        require(stream is not None, 'Workstream integration owner is missing')
        owner = reg.lane(state, stream['owner_lane'])
        require(owner['state'] != 'done' and reg.probe(owner['process']) == 'alive', 'Integration owner unavailable')
        if spec['heavy'] and not state.get('build_capacity', {}).get('lease_only'):
            held = [v for r, v in state['leases'].items() if reg.heavy(r)]
            pending = pending_heavy_lanes(state, pool, reg.probe)
            pending.difference_update(v['lane'] for v in held)
            own = spec['lane']['lane'] in (pending | {v['lane'] for v in held})
            required = len(held) + len(pending) + (0 if own else 1)
            require(required <= state['settings']['max_heavy_builds'], 'Heavy build slots full')
        if not item.get('previous_lane'):
            require(spec['lane']['lane'] not in state['lanes'], 'Lane already exists outside this refill')
            _check_conflicts(controller, state, spec)
            candidates = _workers(reg, state, spec)
            reserved = {i.get('worker_id') for i in data['items'].values()
                        if i.get('phase') in ('intent', 'provisioned', 'configured') and i.get('previous_lane')}
            candidates = [l for l in candidates if l['worker_id'] not in reserved]
            require(candidates, 'No authorized stopped worker with required role/capabilities')
            prior = candidates[0]
            item.update(previous_lane=prior['lane'], worker_id=prior['worker_id'], owner=prior['owner'],
                        phase='intent', status='provisioning', issue_verified_at=reg.clock())
        prior = reg.lane(state, item['previous_lane'])
        record = dict(spec['lane'], owner=item['owner'])
        existing = state['lanes'].get(record['lane'])
        if existing:
            require(existing.get('previous_lane') == prior['lane'] and existing['worker_id'] == prior['worker_id'] and
                    all(existing.get(k) == v for k, v in record.items()), 'Existing lane conflicts with immutable refill spec')
    if not existing:
        reg.provision_pool_lane(record, prior['lane'])
    with reg.transaction() as state:
        item = _state(state)['items'][identity]
        item.update(phase='provisioned', status='provisioning', updated_at=reg.clock())
        specs = state.setdefault('throughput_runtime', {}).setdefault('launch_specs', {})
        require(item['lane'] not in specs or specs[item['lane']] == _launch(spec), 'Conflicting launch configuration')
        specs[item['lane']] = _launch(spec)
        stream = reg.scheduling(state)['workstreams'][spec['workstream']]
        owner = reg.lane(state, stream['owner_lane'])
        require(owner['state'] != 'done' and reg.probe(owner['process']) == 'alive', 'Integration owner changed')
        stream['lanes'] = sorted(set(stream.get('lanes', [])) | {item['lane']})
        item['phase'] = 'configured'
    reg.enqueue_job(dict(id='autofill:' + identity, lane=record['lane'], issue=record['issue'],
                        workstream=spec['workstream'], role=spec['role'], capabilities=spec['capabilities'],
                        instruction=spec['instruction'], heavy=spec['heavy'],
                        work_class='expansion' if spec['priority'] == 'expansion' else 'existing', focus=spec['priority']))
    with reg.transaction() as state:
        _state(state)['items'][identity].update(phase='enqueued', status='queued', reason=None, updated_at=reg.clock())
    controller.config['lanes'][record['lane']] = _launch(spec)
    return True


def _request_refill(controller, manifest_hash, cooldown):
    reg = controller.reg
    inbox = controller.config.get('integrator_inbox')
    if not inbox:
        return
    directory = _private(reg, inbox)
    require(directory.is_dir(), 'Integrator inbox must already exist')
    with reg.transaction() as state:
        data = _state(state)
        previous = data.get('last_refill_request')
        if previous and reg.clock() - previous['at'] < cooldown and previous.get('status') == 'written':
            return
        if not previous or previous.get('status') == 'written':
            path = directory / ('autofill-next-gates-' + fingerprint([manifest_hash, int(reg.clock())])[:20] + '.md')
            previous = dict(at=reg.clock(), manifest_hash=manifest_hash, path=str(path), status='intent')
            data['last_refill_request'] = previous
        path = Path(previous['path'])
    if not path.exists():
        temporary = path.with_suffix('.tmp')
        temporary.write_text('Autonomous worker pool needs explicit prepared next-gate scopes.\n\n'
            'Prioritize remaining enemy acceptance gates, then existing content, then new content. '
            'Append assigned issue-backed immutable specs to the configured autofill manifest, with exact private '
            'source pins, launch files, acceptance, capabilities and fresh issue proof. Reuse existing owners; '
            'do not duplicate active scopes or grant ADMIT. Blocked specs remain visible in autofill status.\n', encoding='utf-8')
        temporary.replace(path)
    with reg.transaction() as state:
        _state(state)['last_refill_request']['status'] = 'written'


def _refresh_readiness(controller, items, issue_reader):
    reg = controller.reg
    for spec in items:
        identity = spec['id']
        try:
            with reg.transaction() as state:
                item = _state(state)['items'][identity]
                item['ready'] = False
                require(item['spec_hash'] == fingerprint(spec), 'Previously published spec changed')
                if item['status'] == 'completed':
                    continue
                lane = state['lanes'].get(item['lane'])
                if lane is not None and item.get('previous_lane') == lane.get('previous_lane') and lane['state'] != 'ready':
                    item.update(status={'done': 'completed'}.get(lane['state'], lane['state']),
                                reason=lane.get('next_action') if lane['state'] in ('blocked', 'reconciling') else None,
                                updated_at=reg.clock())
                    continue
                stream = reg.scheduling(state)['workstreams'].get(spec.get('workstream'))
                require(stream is not None, 'No integration owner')
                owner = reg.lane(state, stream['owner_lane'])
                require(owner['state'] != 'done' and reg.probe(owner['process']) == 'alive', 'Integration owner unavailable')
                lane = state['lanes'].get(item['lane'])
                if lane is not None:
                    if lane['state'] != 'ready' or not reg.recovery_safe(state, lane) or lane.get('dependencies'):
                        continue
                    require(item.get('previous_lane') == lane.get('previous_lane'), 'Lane is not this refill item')
                    require(launch_files_unchanged(reg, _launch(spec)), 'Launch files changed')
                else:
                    require(_workers(reg, state, spec), 'No eligible authorized stopped worker')
                    _check_conflicts(controller, state, spec)
                if spec.get('heavy') and not state.get('build_capacity', {}).get('lease_only'):
                    held = [v for r,v in state['leases'].items() if reg.heavy(r)]
                    pending = pending_heavy_lanes(state, reg.scheduling(state), reg.probe)
                    pending.difference_update(v['lane'] for v in held)
                    own = lane is not None and lane['lane'] in (pending | {v['lane'] for v in held})
                    required = len(held) + len(pending) + (0 if own else 1)
                    require(required <= state['settings']['max_heavy_builds'], 'Heavy build slots full')
                verified = item['status'] != 'blocked' and item.get('readiness_verified_at') is not None and reg.clock()-item['readiness_verified_at'] < 86400
            if lane is None:
                validate_spec(reg, spec, issue_reader, verified=verified)
            with reg.transaction() as state:
                item = _state(state)['items'][identity]
                item.update(ready=True, reason=None, status='queued' if lane else 'pending', updated_at=reg.clock())
                if lane is None and not verified:
                    item['readiness_verified_at'] = reg.clock()
        except (Rejected, OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
            _blocked(reg, identity, exc)


def _planner_tick(controller, settings, manifest_hash):
    reg = controller.reg
    key = settings.get('planner_lane')
    if not key or not controller.capacity() or not 0 <= controller.memory() < 90:
        return False
    cooldown = max(300, settings.get('planner_cooldown_seconds', 900))
    with reg.transaction() as state:
        data = _state(state)
        pool = reg.scheduling(state)
        def ready(item):
            lane = state['lanes'].get(item['lane'])
            if item['status'] in ('completed', 'blocked'):
                return False
            if not item.get('ready', False):
                return False
            if lane is None:
                return True
            return lane['state'] == 'ready' and reg.recovery_safe(state, lane)
        backlog = sum(ready(i) for i in data['items'].values())
        enemies = sum(not i.get('planner_helper') and i['priority'] == 'enemy_acceptance' and
                      (ready(i) or (i.get('phase') in ('provisioned', 'configured', 'enqueued') and
                       state['lanes'].get(i['lane'], {}).get('state') in ('running', 'handoff_ready', 'review_ready', 'integrating')))
                      for i in data['items'].values())
        if not data.get('last_manifest_error') and backlog >= max(1, settings.get('low_watermark', 4)) and enemies:
            return False
        lane = reg.lane(state, key)
        require(lane['state'] in ('ready', 'blocked', 'reconciling', 'running'), 'Backlog planner is not resumable')
        health = reg.probe(lane['process'])
        require(health in ('alive', 'dead'), 'Backlog planner process identity is unknown')
        in_flight = any(a['lane'] == key and a['status'] in ('intent', 'spawned', 'running')
                        for a in state.get('control', {}).get('launches', {}).values())
        if health == 'alive' or in_flight:
            data['last_planner_error'] = None
            return False  # Expected ongoing work; never a recovery error.
        require(reg.recovery_safe(state, lane), 'Backlog planner protected child is live or unknown')
        previous = data.get('last_planner_request')
        if previous and previous.get('status') == 'planned' and reg.clock() - previous['at'] < cooldown:
            return False
        if not previous or previous.get('status') == 'planned':
            previous = dict(at=reg.clock(), id=fingerprint([manifest_hash, lane['generation'], int(reg.clock())]), status='intent')
            data['last_planner_request'] = previous
    require(key in controller.config['lanes'] and controller.available(key), 'Prepared planner launch configuration unavailable')
    brief = _private(reg, controller.config['lanes'][key]['brief'])
    require(brief.is_file(), 'Planner brief missing')
    parallel = settings.get('planner_pool', {}).get('enabled')
    partition_directive = (
        'PARALLEL PLANNING MODE: you coordinate manifest publication and claim disposition. Read your updated brief first. '
        'Helpers exclusively own discovery/issue creation in enemy acceptance, dungeons, and overworld/challenge. '
        'Do not independently prepare scopes in those partitions. Consume their staged proposals using '
        'canonical workflow.planner_pool.merge_proposals; validate issue scope, ownership and source proofs. '
        'Record accepted/rejected proposal paths in your cycle report. Never overwrite helper inboxes. '
        if parallel else '')
    launch = reg.plan_launch(key, 'autofill-planner:' + previous['id'],
        partition_directive + 'Read your configured backlog-planner brief at ' + str(brief) + '. Capacity needs explicit prepared next-gate scopes. '
        'Inspect autofill last_manifest_error first; if malformed/unreadable, diagnose and repair the manifest from '
        'immutable recorded specs without changing accepted scopes. '
        'Prioritize uncompleted enemy acceptance gates, then existing content, then expansion. Inspect live ownership; ' +
        ('validate helper-prepared issue-first bounded specs with exact private git pins and immutable issue proofs, ' if parallel else
         'create assigned issue-first bounded specs with exact prepared private git pins and immutable issue proofs, ') +
        'then atomically append fresh IDs to ' + str(_private(reg, settings['manifest'])) + '. '
        'Do not grant ADMIT, duplicate active owners, enqueue workers, or alter existing immutable specs. '
        'Record evidence and finish BLOCKED awaiting the next controller refill demand. '
        'If no eligible work remains, record that exact blocker; never invent scopes.', controller.config['models'])
    with reg.transaction() as state:
        _state(state)['last_planner_request'].update(status='planned', launch_id=launch['id'])
        _state(state)['last_planner_error'] = None
    return True


def autofill_tick(controller, *, issue_reader=github_issue):
    reg = controller.reg
    settings = controller.config.get('throughput', {}).get('autofill', {})
    with reg.transaction() as state:
        data = _state(state)
        data.update(enabled=bool(settings.get('enabled')), updated_at=reg.clock(), ready_count=0)
    if not settings.get('enabled'):
        return
    try:
        path = _private(reg, settings['manifest'])
        manifest = json.loads(path.read_text(encoding='utf-8-sig'))
        require(isinstance(manifest, dict) and manifest.get('schema') == 1 and manifest.get('repository') == '4laric/pikmin-randomizer' and
                manifest.get('assignee') == '4laric' and isinstance(manifest.get('items'), list), 'Invalid autofill manifest')
        def minimal(i):
            return (isinstance(i, dict) and isinstance(i.get('id'), str) and bool(i['id']) and
                    isinstance(i.get('lane'), dict) and isinstance(i['lane'].get('lane'), str) and bool(i['lane']['lane']) and
                    isinstance(i.get('priority'), str))
        invalid = [i for i in manifest['items'] if not minimal(i)]
        items = [i for i in manifest['items'] if minimal(i)]
        require(len({i['id'] for i in items}) == len(items), 'Duplicate manifest IDs')
        with reg.transaction() as state:
            data = _state(state)
            data['last_manifest_error'] = None
            data['invalid_items'] = [{'hash': fingerprint(i), 'reason': 'Nonempty immutable spec ID required'} for i in invalid]
            for invalid_spec in invalid:
                if isinstance(invalid_spec, dict) and isinstance(invalid_spec.get('id'), str) and invalid_spec['id']:
                    old = data['items'].setdefault(invalid_spec['id'], dict(spec_hash=fingerprint(invalid_spec),
                        priority=None, lane=None, phase='pending'))
                    old.update(status='blocked', ready=False, reason='Malformed lane or priority shape', updated_at=reg.clock())
            for spec in items:
                identity = spec['id']
                old = data['items'].get(identity)
                if old and old['spec_hash'] != fingerprint(spec):
                    old.update(status='blocked', ready=False, reason='Previously published spec changed')
                    continue
                if not old:
                    data['items'][identity] = dict(spec_hash=fingerprint(spec), priority=spec.get('priority'),
                        lane=spec.get('lane', {}).get('lane'), phase='pending', status='pending', reason=None,
                        ready=False, updated_at=reg.clock())
                if data['items'][identity]['phase'] == 'enqueued' and state['lanes'].get(spec.get('lane', {}).get('lane'), {}).get('state') == 'done':
                    data['items'][identity].update(status='completed', ready=False, updated_at=reg.clock())
        if not controller.capacity() or not 0 <= controller.memory() < 90:
            return
        admitted = False
        for spec in sorted(items, key=lambda i: (PRIORITIES.get(i.get('priority'), 99), i['id'])):
            try:
                if _prepare(controller, spec, issue_reader):
                    admitted = True
                    break  # At most one newly provisioned slice per tick.
            except (Rejected, OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
                _blocked(reg, spec['id'], exc)
        _refresh_readiness(controller, items, issue_reader)
        try:
            from .planner_pool import tick as planner_pool_tick
            planner_pool_tick(controller, settings, issue_reader)
        except (Rejected, OSError, ValueError, KeyError, TypeError) as exc:
            with reg.transaction() as state:
                _state(state).setdefault('planner_pool', {})['error'] = str(exc)
        with reg.transaction() as state:
            data = _state(state)
            idle = bool(_workers(reg, state))
            has_ready = any(i.get('ready') for i in data['items'].values())
            if admitted or not idle or has_ready:
                data['needs_refill_since'] = None
            else:
                data.setdefault('needs_refill_since', reg.clock())
                if data['needs_refill_since'] is None:
                    data['needs_refill_since'] = reg.clock()
        try:
            planner = _planner_tick(controller, settings, fingerprint(manifest))
        except (Rejected, OSError, ValueError, KeyError, TypeError) as exc:
            planner = False
            with reg.transaction() as state:
                _state(state)['last_planner_error'] = str(exc)
        if idle and not admitted and not has_ready and not settings.get('planner_lane'):
            _request_refill(controller, fingerprint(manifest), max(60, settings.get('refill_cooldown_seconds', 900)))
    except (Rejected, OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
        with reg.transaction() as state:
            _state(state)['last_manifest_error'] = str(exc)
        try:
            _planner_tick(controller, settings, fingerprint(['manifest-error', settings.get('manifest'), str(exc)]))
        except (Rejected, OSError, ValueError, KeyError, TypeError) as planner_error:
            with reg.transaction() as state:
                _state(state)['last_planner_error'] = str(planner_error)
