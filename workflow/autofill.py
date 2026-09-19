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
from .provenance import cli
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
    require(required <= set(spec) <= required | {'producer_contract'}, 'Autofill spec fields must be explicit')
    from .producer_contract import validate as validate_contract
    validate_contract(spec)
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
    lane_fields = {'lane', 'issue', 'scope', 'target_level', 'next_action', 'milestone',
                   'owned_files', 'acceptance', 'root', 'native'}
    require(lane_fields <= set(lane) <= lane_fields | {'closes_gates'}, 'Explicit slice fields required')
    for field in ('lane', 'scope', 'target_level', 'next_action', 'milestone'):
        require(isinstance(lane[field], str) and lane[field].strip(), field + ' required')
    require(isinstance(lane['acceptance'], list) and lane['acceptance'] and
            all(isinstance(v, str) and v.strip() for v in lane['acceptance']), 'acceptance required')
    require(isinstance(lane.get('owned_files'), list) and lane['owned_files'] and
            all(isinstance(f, str) and f for f in lane['owned_files']), 'Explicit owned file strings required')
    require(type(lane.get('issue')) is int and lane['issue'] > 0, 'Explicit issue required')
    require(isinstance(lane.get('lane'), str) and lane['lane'].strip(), 'Explicit lane name required')
    require(lane.get('target_level') != 'runtime' or lane.get('native') is not None,
            'Runtime acceptance requires a prepared private native source worktree')
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
        from .managed_config import pinned_config_matches
        return (digest(_private(reg, entry['brief'])) == entry['autofill_proof']['brief'] and
                pinned_config_matches(_private(reg, entry['config']), entry['autofill_proof']['config']))
    except (Rejected, OSError, ValueError, KeyError, TypeError):
        return False


def _workers(reg, state, spec=None, eligible=None):
    from .worker_capacity import reusable
    pool = reg.scheduling(state)
    delivery_workers={row['worker_id'] for key,row in state.get('handoff_resume_reservations',{}).items()
        if row.get('expires_at',0)>reg.clock() and
        state['lanes'].get(key,{}).get('state')=='blocked' and
        state['lanes'][key]['generation']==row['generation'] and
        not any(x['lane']==key and x['reason']==row['reason']
                for x in state.get('control',{}).get('launches',{}).values())}
    candidates = []
    for worker in pool['workers'].values():
        if worker['worker_id'] in delivery_workers:continue
        if eligible is not None and worker['worker_id'] not in eligible:
            continue
        if spec and (spec['role'] not in worker['roles'] or not set(spec['capabilities']) <= set(worker['capabilities'])):
            continue
        lanes = [l for l in state['lanes'].values() if l['worker_id'] == worker['worker_id']]
        if not lanes or any((l['state'] != 'done' and not reusable(reg, state, l)) or not reg.recovery_safe(state, l) for l in lanes):
            continue
        if any(a['worker_id'] == worker['worker_id'] and a['status'] in ('assigned', 'dispatched') for a in pool['assignments'].values()):
            continue
        if any(a['lane'] in {l['lane'] for l in lanes} and a['status'] in ('intent', 'spawned', 'running', 'exiting')
               for a in state.get('control', {}).get('launches', {}).values()):
            continue
        latest = max(lanes, key=lambda l: (l['created_at'], l['lane']))
        if reusable(reg, state, latest) or latest.get('integration') or latest.get('review_disposition') or latest.get('cancelled_before_start') or latest.get('superseded_planning'):
            candidates.append(latest)
    return sorted(candidates, key=lambda l: (l['worker_id'], l['lane']))


def _adapt_worker(controller, state, spec, reserved, eligible=None):
    """Apply an operator-authorized capability profile during reservation only."""
    reg = controller.reg
    policy = controller.config.get('throughput', {}).get('autofill', {}).get('worker_adaptation', {})
    if not policy.get('enabled') or not policy.get('authorized_by'):
        return []
    pool = reg.scheduling(state)
    owners = {stream['owner_lane'] for stream in pool['workstreams'].values()}
    for lane in _workers(reg, state, eligible=eligible):
        worker_id = lane['worker_id']
        worker = pool['workers'][worker_id]
        if worker_id in reserved or spec['role'] not in worker['roles']:
            continue
        if any(l['lane'] in owners for l in state['lanes'].values() if l['worker_id'] == worker_id):
            continue
        current = set(worker['capabilities'])
        missing = set(spec['capabilities']) - current
        for profile in policy.get('profiles', []):
            if (not profile.get('name') or profile.get('role') != spec['role'] or
                    profile.get('workstream') != spec['workstream'] or
                    not set(profile.get('requires', [])) <= current or
                    not missing or not missing <= set(profile.get('grants', []))):
                continue
            # Caller has validated the spec and checked admission/conflicts.
            # This mutation and the caller's worker reservation share one transaction.
            worker['capabilities'] = sorted(current | missing)
            reg.event(state, 'pool_worker_adapted', lane['lane'], worker_id=worker_id,
                      target_lane=spec['lane']['lane'], spec_hash=fingerprint(spec),
                      profile=profile['name'], authorized_by=policy['authorized_by'],
                      added_capabilities=sorted(missing))
            return [lane]
    return []


def autofill_status(reg, state=None):
    from contextlib import nullcontext
    with nullcontext(reg.snapshot() if state is None else state) as state:
        data = copy.deepcopy(_state(state))
        data['idle_workers_count'] = len(_workers(reg, state))
        data['ready_count'] = sum(i.get('ready', False) and
            (i['lane'] not in state['lanes'] or (state['lanes'][i['lane']]['state'] == 'ready' and
             reg.recovery_safe(state, state['lanes'][i['lane']]))) for i in data['items'].values())
        data['awaiting_worker_count'] = sum(bool(i.get('ready') and i.get('awaiting_worker')) for i in data['items'].values())
        idle = _workers(reg, state)
        pool = reg.scheduling(state)
        idle_by_id = {lane['worker_id']: lane for lane in idle}
        compatible_ids = set()
        unmatched = []
        reassignment_options = []
        compatibility = []
        for item in data['items'].values():
            if not item.get('ready') or item.get('planner_helper'):
                continue
            role = item.get('role')
            capabilities = set(item.get('capabilities', []))
            matches = []
            near_matches = []
            if role:
                for worker_id, lane in idle_by_id.items():
                    worker = pool.get('workers', {}).get(worker_id, {})
                    if role in worker.get('roles', []) and capabilities <= set(worker.get('capabilities', [])):
                        matches.append(worker_id)
                    elif role in worker.get('roles', []):
                        missing = sorted(capabilities - set(worker.get('capabilities', [])))
                        if missing:
                            near_matches.append(dict(worker_id=worker_id, missing_capabilities=missing))
            compatible_ids.update(matches)
            detail = dict(lane=item.get('lane'), role=role, capabilities=sorted(capabilities),
                          compatible_workers=sorted(matches), reason=None if matches else
                          'No idle compatible worker' if role else 'Worker requirements unavailable')
            compatibility.append(detail)
            if not matches:
                unmatched.append(detail)
                if near_matches:
                    reassignment_options.append(dict(lane=item.get('lane'), role=role,
                        capabilities=sorted(capabilities), options=near_matches,
                        action='explicitly reassign an idle worker, then refresh readiness'))
        data['ready_compatibility'] = compatibility
        data['compatible_idle_workers'] = len(compatible_ids)
        data['unmatched_ready_items'] = unmatched
        data['reassignment_options'] = reassignment_options
        helpers = dict(running=0, queued=0, prepared=0, report_ready=0, recovery=0)
        integration_helpers = dict(running=0,queued=0,prepared=0,report_ready=0,recovery=0,workers=[])
        exhausted = {v['lane'] for v in state.get('control', {}).get('launches', {}).values()
                     if v.get('status') == 'intent' and v.get('registration_recovery_exhausted')}
        for record in data.get('planner_pool', {}).get('scopes', {}).values():
            if 'completed_at' in record: continue
            lane = state['lanes'].get(record['spec']['lane']['lane'], {})
            if lane.get('state') == 'done': continue
            if not lane: bucket = 'prepared'
            elif lane.get('state') == 'review_ready': bucket = 'report_ready'
            elif lane.get('state') == 'ready': bucket = 'recovery' if lane.get('lane') in exhausted else 'queued'
            elif lane.get('state') == 'running' and reg.probe(lane['process']) == 'alive': bucket = 'running'
            else: bucket = 'recovery'
            helpers[bucket] += 1
            if 'support_targets' in record:
                integration_helpers[bucket] += 1
                integration_helpers['workers'].append(dict(lane=record['spec']['lane']['lane'],
                    worker=lane.get('worker_id'),status=bucket,
                    targets=[t['lane'] for t in record['support_targets']]))
        data.setdefault('planner_pool', {}).update(helpers, active=sum(helpers.values()))
        integration_helpers.update(active=sum(integration_helpers[k] for k in helpers),
            target=data['planner_pool'].get('integration_support_target',0),
            limit=data['planner_pool'].get('integration_support_limit',2))
        data['planner_pool']['integration_helpers']=integration_helpers
        data['planner_pool']['integration_support_active']=integration_helpers['active']
        data['pending_count'] = sum(i.get('phase') == 'pending' for i in data['items'].values())
        data['active_enemy_lanes'] = active_enemy_lanes(state, data['items'])
        data['active_enemy_count'] = len(data['active_enemy_lanes'])
        since = data.get('needs_refill_since')
        data['starvation_seconds'] = max(0, reg.clock() - since) if since is not None else 0
        return data


def active_enemy_lanes(state, items):
    """Acceptance domain can differ from immutable scheduling priority."""
    classified=set(state.get('settings',{}).get('enemy_acceptance_lanes',[]))
    return sorted({item['lane'] for item in items.values()
        if (item.get('priority')=='enemy_acceptance' or item.get('lane') in classified)
        and not item.get('planner_helper')
        and item.get('phase') in ('provisioned','configured','enqueued')
        and state['lanes'].get(item.get('lane'),{}).get('state') in ('running','waiting_resource')})


def _blocker_signature(lane):
    """Normalized text identifying why a lane is blocked, or None if nothing usable.

    Structured `dependencies` entries (plain lane names or '#issue' strings) are
    preferred since they are exact data, not prose. Free-text `progress_detail`/
    `next_action` is used only as a fallback, normalized by casefolding and
    collapsing whitespace. This is intentionally a byte-exact-after-normalization
    match, not fuzzy/keyword extraction: two lanes describing the same missing
    capability in slightly different wording will NOT cluster unless their
    recorded text normalizes identically.
    """
    deps = lane.get('dependencies') or []
    text = ' '.join(sorted(d.strip() for d in deps if isinstance(d, str) and d.strip()))
    if text:
        return ' '.join(text.casefold().split())
    detail = lane.get('progress_detail') or lane.get('next_action') or ''
    if isinstance(detail, str) and detail.strip():
        return ' '.join(detail.casefold().split())
    return None


def clustered_blockers(state):
    """Surface 2+ blocked/waiting_resource lanes sharing one normalized blocker signature.

    Propose-only, mirroring every other human-gated notice in this module: this
    never creates a lane, dispatches work or mutates any lane. It only reports a
    signature, its lane count and the affected lane names for an operator/planner
    to act on. A cluster is suppressed if any lane's `scope` text already contains
    the signature, on the assumption that scope text is human-authored and would
    reference a fix already underway.
    """
    groups = {}
    for name, lane in state['lanes'].items():
        if lane.get('state') not in ('blocked', 'waiting_resource'):
            continue
        signature = _blocker_signature(lane)
        if not signature:
            continue
        groups.setdefault(signature, []).append(name)
    all_scopes = ' '.join((lane.get('scope') or '').casefold() for lane in state['lanes'].values())
    clusters = [dict(signature=signature, count=len(lanes), lanes=sorted(lanes))
                for signature, lanes in groups.items() if len(lanes) >= 2 and signature not in all_scopes]
    return sorted(clusters, key=lambda c: c['signature'])


def _blocked(reg, identity, reason):
    with reg.transaction() as state:
        item = _state(state)['items'][identity]
        now = reg.clock()
        if item.get('status') != 'blocked' or not item.get('blocked_at'):
            item['blocked_at'] = now
        text = str(reason)
        lowered = text.casefold()
        if 'integration owner' in lowered:
            dependency_kind = 'integration_owner'
        elif 'provider' in lowered or 'api absent' in lowered or 'staging' in lowered:
            dependency_kind = 'provider'
        elif 'worker' in lowered or 'capacity' in lowered:
            dependency_kind = 'worker_capacity'
        else:
            dependency_kind = 'workflow'
        item.update(status='blocked', reason=text, dependency_kind=dependency_kind,
                    updated_at=now, ready=False)
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
    from contextlib import nullcontext
    with nullcontext(reg.snapshot()) as state:
        data = _state(state)
        item = data['items'].get(identity)
        require(item is not None and item['spec_hash'] == spec_hash, 'Spec changed after publication')
        if item.get('phase') == 'enqueued':
            if state['lanes'].get(item['lane'], {}).get('state') == 'done':
                with reg.transaction() as current:
                    live = _state(current)['items'][identity]
                    if (live['spec_hash'] == spec_hash and live.get('phase') == 'enqueued' and
                            current['lanes'].get(live['lane'], {}).get('state') == 'done'):
                        live.update(status='completed', updated_at=reg.clock())
            return False
        pinned = item.get('previous_lane')
        verified = item.get('issue_verified_at') is not None and reg.clock() - item['issue_verified_at'] <= 86400
    # After provisioning a worker may already have edited its worktree. Replay
    # checks the recorded identity, not a falsely required clean implementation.
    if not pinned or item.get('phase') == 'intent':
        validate_spec(reg, spec, issue_reader, verified=False)
    # Discovery happens outside the lock. Reservation rechecks the selected pool
    # against current lanes, leases and assignments, so a stale snapshot cannot
    # double-book a worker. Newly freed workers can be discovered next pass.
    eligible = {l['worker_id'] for l in _workers(reg, reg.snapshot())} if not pinned else set()
    with reg.transaction() as state:
        data = _state(state)
        item = data['items'][identity]
        pool = reg.scheduling(state)
        stream = pool['workstreams'].get(spec['workstream'])
        require(stream is not None, 'Workstream integration owner is missing')
        owner = reg.lane(state, stream['owner_lane'])
        require(reg.integration_assistance(state, spec['lane'], spec['role']) or
                reg.integration_owner_available(state, owner), 'Integration owner unavailable')
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
            candidates = _workers(reg, state, spec, eligible=eligible)
            reserved = {i.get('worker_id') for i in data['items'].values()
                        if i.get('phase') in ('intent', 'provisioned', 'configured') and i.get('previous_lane')}
            candidates = [l for l in candidates if l['worker_id'] not in reserved]
            if item.get('planner_helper'):
                # The outside preflight is advisory; parallel preparation needs
                # the reserve enforced at the same fence as worker selection.
                available={l['worker_id'] for l in _workers(reg,state,eligible=eligible)}-reserved
                execution=sum(bool(i.get('ready')) and not i.get('planner_helper') and
                              i.get('lane') not in state['lanes'] for i in data['items'].values())
                helper_config=controller.config.get('throughput',{}).get('autofill',{}).get('planner_pool',{})
                require(len(available)>execution+max(0,int(helper_config.get('reserve_workers',2))),
                        'Idle workers reserved for execution')
            if not candidates:
                candidates = _adapt_worker(controller, state, spec, reserved, eligible=eligible)
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
        require(reg.integration_assistance(state, spec['lane'], spec['role']) or
                reg.integration_owner_available(state, owner), 'Integration owner changed')
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
    observed = _state(reg.snapshot())['items']
    items = [spec for spec in items if not (observed.get(spec['id'], {}).get('status') == 'completed'
             and observed[spec['id']].get('spec_hash') == fingerprint(spec))]
    snapshot = reg.snapshot()
    def unchanged_execution(spec):
        item = observed.get(spec['id'], {})
        lane = snapshot['lanes'].get(item.get('lane'), {})
        status = lane.get('state')
        reason = lane.get('next_action') if status in ('blocked','reconciling') else None
        return (status in ('running','blocked','waiting_resource','handoff_ready','review_ready','integrating')
                and item.get('spec_hash') == fingerprint(spec) and item.get('status') == status
                and item.get('reason') == reason and not item.get('ready') and not item.get('awaiting_worker'))
    items = [spec for spec in items if not unchanged_execution(spec)]
    eligible = {l['worker_id'] for l in _workers(reg, snapshot)} if items else set()
    for spec in items:
        identity = spec['id']
        try:
            with reg.transaction() as state:
                item = _state(state)['items'][identity]
                item['ready'] = False
                item['awaiting_worker'] = False
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
                require(reg.integration_assistance(state, spec['lane'], spec['role']) or
                        reg.integration_owner_available(state, owner), 'Integration owner unavailable')
                lane = state['lanes'].get(item['lane'])
                if lane is not None:
                    if lane['state'] != 'ready' or not reg.recovery_safe(state, lane) or lane.get('dependencies'):
                        continue
                    require(item.get('previous_lane') == lane.get('previous_lane'), 'Lane is not this refill item')
                    require(launch_files_unchanged(reg, _launch(spec)), 'Launch files changed')
                else:
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
                item.update(role=spec.get('role'), capabilities=list(spec.get('capabilities', [])),
                            workstream=spec.get('workstream'))
                waiting = lane is None and not _workers(reg, state, spec, eligible=eligible)
                item.update(ready=True, awaiting_worker=waiting, reason='Awaiting compatible worker' if waiting else None,
                            status='queued' if lane else 'pending', updated_at=reg.clock())
                if lane is None and not verified:
                    item['readiness_verified_at'] = reg.clock()
        except (Rejected, OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
            _blocked(reg, identity, exc)


def _planner_tick(controller, settings, manifest_hash):
    reg = controller.reg
    key = settings.get('planner_lane')
    if not key or not controller.capacity() or not 0 <= controller.memory() < controller.config.get('ram_high', 90):
        return False
    from .prerequisite_queue import collect, dispatched
    promotion = collect(reg, settings)
    parallel_config = settings.get('planner_pool', {})
    inboxes = sorted({p for h in parallel_config.get('helpers', [])
                      for p in h.get('review_inboxes', []) + h.get('defer_for_review', [])})
    if parallel_config.get('enabled') and inboxes:
        with reg.transaction() as state:
            malformed = bool(_state(state).get('last_manifest_error'))
        if not malformed and not promotion:
            from .planner_pool import review_pending
            if not review_pending(reg, settings, {'review_inboxes': inboxes}):
                with reg.transaction() as state:
                    active_requests = _state(state).get('prerequisite_requests', {}).values()
                    _state(state)['coordinator_wait_reason'] = (
                        'Handling prerequisite requests' if any(r['status'] == 'dispatched' for r in active_requests)
                        else 'Waiting for new unpublished proposals')
                return False
    with reg.transaction() as state:
        data = _state(state)
        if (data.get('last_planner_request') or {}).get('status') != 'parked':  # A park keeps its reason.
            data['coordinator_wait_reason'] = None
    cooldown = max(300, settings.get('planner_cooldown_seconds', 900))
    staged = []
    for directory in inboxes:
        for path in sorted(_private(reg, directory).glob('proposals-*.json')):
            try: staged.append((str(path), digest(path)))
            except OSError: staged.append((str(path), None))
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
        if not promotion and not data.get('last_manifest_error') and backlog >= max(1, settings.get('low_watermark', 4)) and enemies:
            return False
        lane = reg.lane(state, key)
        require(lane['state'] in ('ready', 'blocked', 'reconciling', 'running'), 'Backlog planner is not resumable')
        health = reg.probe(lane['process'])
        require(health in ('alive', 'dead'), 'Backlog planner process identity is unknown')
        in_flight = any(a['lane'] == key and a['status'] in ('intent', 'spawned', 'running', 'exiting')
                        for a in state.get('control', {}).get('launches', {}).values())
        if health == 'alive' or in_flight:
            data['last_planner_error'] = None
            return False  # Expected ongoing work; never a recovery error.
        require(reg.recovery_safe(state, lane), 'Backlog planner protected child is live or unknown')
        previous = data.get('last_planner_request')
        resolution_version = max((r.get('resolution_version', 1) for r in promotion), default=1)
        # What a cycle is offered: the manifest, staged proposals and the open requests at their input
        # snapshots (not their pending/dispatched churn). Re-offering the same set is an empty cycle.
        planner_inputs = fingerprint([manifest_hash, staged, bool(data.get('last_manifest_error')),
            sorted((r['id'], r.get('input_snapshot')) for r in data.get('prerequisite_requests', {}).values()
                   if r['status'] in ('pending', 'dispatched'))])
        same = bool(previous and previous.get('inputs') == planner_inputs)
        empty = previous.get('empty_cycles', 0) + 1 if same else 0
        wait = max(cooldown, min(3600, cooldown * 2 ** empty)) if same else cooldown
        if (previous and previous.get('status') == 'planned' and reg.clock() - previous['at'] < wait
                and previous.get('resolution_version', 1) >= resolution_version):
            return False
        due = lane.get('wake_after')
        if (previous and previous.get('status') == 'parked' and same and
                type(due) in (int, float) and reg.clock() < due):
            return False  # Parked on these inputs: only a changed input or the lane's recheck relaunches.
        if previous and previous.get('status') == 'intent' and previous.get('inputs') != planner_inputs:
            previous['inputs'] = planner_inputs  # A reused intent offers what this cycle actually sees.
        if not previous or previous.get('status') in ('planned', 'parked'):
            if previous and previous['status'] == 'parked':
                data['coordinator_wait_reason'] = None  # Re-offered: a new input or the due recheck.
            previous = dict(at=reg.clock(), id=fingerprint([manifest_hash, lane['generation'], int(reg.clock())]),
                            status='intent', resolution_version=resolution_version,
                            inputs=planner_inputs, empty_cycles=empty)
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
    if promotion:
        packet = reg.root/'output/workflow/autofill/prerequisite-requests.json'
        packet.parent.mkdir(parents=True, exist_ok=True)
        from .runner import write
        with reg.transaction() as state:
            blocked_consumers = [dict(lane=k, issue=l['issue'], next_action=l.get('next_action'),
                dependencies=l.get('dependencies', []), evidence=l.get('progress_evidence'),
                owned_files=l.get('owned_files', [])) for k, l in state['lanes'].items()
                if l['state'] == 'blocked' and not k.startswith(('planning-', 'publication-review-', 'integration-support-'))
                and k != key]
        write(packet, dict(requests=promotion, blocked_consumers=blocked_consumers))
        partition_directive += (
            'PREREQUISITE PROMOTION EXCEPTION to older publication-only briefs: the user authorizes you '
            'to turn these verified unmet prerequisite requests into bounded executable jobs. Read ' + str(packet) + '. '
            'For each request inspect the hashed report and live ownership. Reuse an existing producer or '
            'already-published job whenever it covers the gap; never duplicate owned issues/files. Otherwise '
            'create/assign a suitable GitHub issue to 4laric with Codex as implementation owner, define '
            'scope/acceptance first, prepare isolated codex worktrees and pinned launch/issue proofs under '
            'output/workflow/autofill/prerequisites/, and publish an immutable spec through '
            'workflow.planner_pool.merge_proposals. Prefer the smallest actual provider implementation '
            'when its contract is known; use a contract slice only when necessary. Do not return no-work '
            'merely because a missing provider is outside the requesting content partition. You own '
            'cross-partition prerequisite preparation for this request, not its implementation. '
            'RESOLUTION CONTRACT v3: linking only completed historical producers is rejected. '
            'Read blocked_consumers in the packet, including consumers outside the reporting partition. '
            'A completed schema/contract/P0 packet is not the missing runtime implementation or its landing. '
            'For every residual actionable gap, publish a bounded producer job or link an outstanding producer '
            'that actually owns that deliverable. A vague referral to provider business/controller business '
            'does not assign the missing work. For an existing blocked consumer, preserve its owned files '
            'and prepare a disjoint shared provider/fixture prerequisite; never duplicate the consumer. '
            'In particular inspect guarded game-linked cave boot fixtures and coherent runtime consumer pins '
            'for forest1 #154 and yakushima4 #161, and the Challenge host-mode implementation behind #136. '
            'An existing captain-guard header does not establish that a game-linked boot fixture exists. '
            'No known consumer pins is a bounded source-pin discovery/compatibility job, not an external '
            'decision. If implementation cannot yet be scoped, publish that concrete discovery deliverable '
            'with exact consumer pin files and acceptance; do not close the request as no_action. '
            'For reports referencing blocked consumers, no_action is rejected unless external_input is '
            'supplied as {kind:user_asset or user_decision, owner:user, detail:exact needed input}. '
            'Internal provider/controller/integrator work does not qualify as a user-owned external input. '
            'A request may include stranded_producers: these are already-linked owners that are all blocked. '
            'Linking the blocked consumer back to itself does not assign its missing input and is rejected. '
            'Prepare the missing producer or a bounded source/ownership discovery job; avoid a circular wait. '
            'If the existing consumer already owns the entire missing step, give a concrete evidenced '
            'owner/action disposition explaining whether it can resume without new inputs; do not invent '
            'a dependency or new job. External asset/decision blockers must identify the exact needed input. '
            'Then resolve each request using canonical workflow.prerequisite_queue.resolve, or run from '
            'the pinned workflow checkout: ' + cli('prerequisite_queue') + ' --root ' + str(reg.root) +
            ' --request <private-json>. JSON fields: coordinator (your lane), generation (session-ready), '
            'request_id, outcome (linked or no_action), lanes (published/existing producer IDs for linked; '
            'empty for no_action), reason, evidence ({path,sha256} of your disposition report). '
            'Link shared producers to every affected request. no_action requires concrete evidence that '
            'no unmet prerequisite exists or a decision outside your authority is required, with exact '
            'owner/action; a vague outside-my-partition answer is not a disposition. No raw registry or '
            'manifest writes, implementation, builds, independent dispatch or ADMIT. Handle at most the '
            'three supplied requests this turn; normal controller admission starts published jobs. ')
    from .no_progress import Parked
    try:
        launch = _planner_launch(reg, key, previous, partition_directive, brief, parallel, settings, controller)
    except Parked as exc:  # A parked coordinator waits for a changed input; that is not a planner error.
        with reg.transaction() as state:  # Once per park: later ticks return before any write.
            data = _state(state)
            data['last_planner_request'].update(status='parked', parked_at=reg.clock())
            data.update(coordinator_wait_reason=str(exc), last_planner_error=None)
        return False
    with reg.transaction() as state:
        _state(state)['last_planner_request'].update(status='planned', launch_id=launch['id'])
        _state(state)['last_planner_error'] = None
    if promotion: dispatched(reg, promotion, launch['id'])
    return True


def _planner_launch(reg, key, previous, partition_directive, brief, parallel, settings, controller):
    return reg.plan_launch(key, 'autofill-planner:' + previous['id'],
        partition_directive + 'Read your configured backlog-planner brief at ' + str(brief) + '. Capacity needs explicit prepared next-gate scopes. '
        'For an unclaimed prepared job with a wrong role/instruction/proof, use '
        'workflow.prepared_repair.repair or ' + cli('prepared_repair') + ' --root <canonical-root> '
        '--request <json>; request fields manifest_path,replacement,expected_hash,evidence. '
        'It validates fresh issue/launch proofs, archives the original and preserves issue/lane/owned files/source pins. '
        'Registered or launched lanes cannot use this repair tool. Private candidate preparation uses '
        'implementation/review roles; never request a second integration writer merely to prepare a candidate. '
        'Inspect autofill last_manifest_error first; if malformed/unreadable, diagnose and repair the manifest from '
        'immutable recorded specs without changing accepted scopes. '
        'Prioritize uncompleted enemy acceptance gates, then existing content, then expansion. Inspect live ownership; ' +
        ('validate helper-prepared issue-first bounded specs with exact private git pins and immutable issue proofs, ' if parallel else
         'create assigned issue-first bounded specs with exact prepared private git pins and immutable issue proofs, ') +
        'then atomically append fresh IDs to ' + str(_private(reg, settings['manifest'])) + '. '
        'Do not grant ADMIT, duplicate active owners, enqueue workers, or alter existing immutable specs. '
        'Record evidence and finish BLOCKED awaiting the next controller refill demand. '
        'If no eligible work remains, record that exact blocker; never invent scopes.', controller.config['models'],
        inputs=['planner:' + previous.get('inputs', previous['id'])])


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
                        role=spec.get('role'), capabilities=list(spec.get('capabilities', [])),
                        workstream=spec.get('workstream'), ready=False, updated_at=reg.clock())
                else:
                    old.update(role=spec.get('role'), capabilities=list(spec.get('capabilities', [])),
                               workstream=spec.get('workstream'))
                if data['items'][identity]['phase'] == 'enqueued' and state['lanes'].get(spec.get('lane', {}).get('lane'), {}).get('state') == 'done':
                    data['items'][identity].update(status='completed', ready=False, updated_at=reg.clock())
        if not controller.capacity() or not 0 <= controller.memory() < controller.config.get('ram_high', 90):
            return
        _refresh_readiness(controller, items, issue_reader)
        admitted = False
        from .queue_pressure import dependents
        lanes=reg.status()['lanes']
        if not getattr(controller, '_admission_monitor', None):
            for spec in sorted(items, key=lambda i: (PRIORITIES.get(i.get('priority'), 99),
                    -dependents(lanes,i['lane']['lane'],i['lane']['issue']),i['id'])):
                try:
                    from .planner_reclaim import reclaim_for
                    reclaim_for(controller, spec)
                    if _prepare(controller, spec, issue_reader):
                        admitted = True
                        break  # At most one newly provisioned slice per tick.
                except (Rejected, OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
                    _blocked(reg, spec['id'], exc)
        _refresh_readiness(controller, items, issue_reader)
        try:
            from .planner_pool import tick as planner_pool_tick
            if not getattr(controller, '_helper_monitor', None):
                planner_pool_tick(controller, settings, issue_reader)
        except (Rejected, OSError, ValueError, KeyError, TypeError) as exc:
            with reg.transaction() as state:
                _state(state).setdefault('planner_pool', {})['error'] = str(exc)
        eligible = {l['worker_id'] for l in _workers(reg, reg.snapshot())}
        with reg.transaction() as state:
            data = _state(state)
            data['clustered_blockers'] = clustered_blockers(state)
            idle = bool(_workers(reg, state, eligible=eligible))
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
