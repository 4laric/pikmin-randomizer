"""Bounded, partitioned planning turns on the existing approved worker pool."""
import copy
import json
import math
from contextlib import nullcontext
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
        from .producer_contract import validate as validate_contract
        validate_contract(spec, required=True)
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


def review_pending(reg, settings, helper):
    """Review demand comes from unpublished immutable inbox items, not idle time."""
    from .autofill import _private
    from .input_cache import read
    manifest, _ = read(_private(reg, settings['manifest']))
    known = {s['id']: s for s in manifest['items']}
    observation = reg.snapshot()
    for directory in helper.get('review_inboxes', []):
        for path in _private(reg, directory).glob('proposals-*.json'):
            from .proposal_feedback import feedback
            try:
                proposal, sha = read(path)
                if feedback(reg, path, state=observation, observed_sha=sha): continue
                items = proposal['items']
                if any(known.get(s.get('id')) != s for s in items): return True
            except (ValueError, KeyError, TypeError, AttributeError):
                return True  # A reviewer must disposition malformed input too.
    return False


def integration_backed_up(config, integration):
    integration = integration if isinstance(integration, dict) else {}
    return (integration.get('depth', 0) >= max(1, int(config.get('pause_integration_depth', 4))) or
            integration.get('oldest_seconds', 0) >= max(300, int(config.get('pause_integration_age_seconds', 3600))))


def helper_target(config, *, helper_count, ready, unclaimed_ready, idle, active, integration):
    """Return safe helper concurrency without consuming delivery capacity."""
    reserve_workers = max(0, int(config.get('reserve_workers', 2)))
    # The configured limit is the ceiling, not a second fixed three-worker cap.
    # Idle-capacity mode may use every spare worker, while unclaimed execution
    # work and the configured reserve retain first call on the pool.
    limit = config.get('max_active', 3)
    helper_limit = helper_count if limit is None else max(0, int(limit))
    deficit = max(0, int(config.get('low_watermark', 8)) - ready)
    planning_demand = (helper_count if config.get('use_idle_capacity') else
                       math.ceil(deficit / max(1, int(config.get('items_per_helper', 4)))))
    backed_up = integration_backed_up(config, integration)
    if backed_up:
        reserve_workers = max(2, reserve_workers)
    target = min(helper_limit, helper_count, planning_demand,
                 max(0, idle + active - unclaimed_ready - reserve_workers))
    if backed_up:
        # Preserve a bounded path to repair/discovery instead of deadlocking
        # every planner behind work that itself needs a new prerequisite.
        limit = config.get('backpressure_planning_limit', 0)
        if limit is not None:
            target = min(target, max(0, int(limit)))
    if ready and config.get('use_idle_capacity') and idle <= 1:
        return 0
    return target


def support_target(config, *, demanded, idle, active, unclaimed_ready):
    """Integration drain capacity is independent of discovery backpressure."""
    limit = config.get('integration_support_max_active', 2)
    return min(demanded if limit is None else max(0, int(limit)), demanded,
               max(0, idle + active - unclaimed_ready - max(0, int(config.get('reserve_workers', 2)))))


def accept_helper_report(reg, lane):
    try:
        return reg.accept_review(lane['lane'], lane['generation'],
            'Planning report received; coordinator validation still required; no gameplay acceptance',
            lane['review']['evidence']['review'])
    except Rejected:
        current = reg.snapshot()['lanes'][lane['lane']]
        receipt = current.get('review_disposition') or {}
        if (current['generation'] != lane['generation'] or current['state'] != 'done' or not receipt):
            raise
        reg.evidence(receipt.get('archived_evidence') or receipt.get('evidence'))
        return current  # Another authorized acceptor won; preserve its immutable receipt.


def tick(controller, settings, issue_reader):
    from .autofill import _private, _workers, _state, _prepare
    reg = controller.reg
    config = settings.get('planner_pool', {})
    if not config.get('enabled'): return
    def stage(name):
        if getattr(controller,'base',None):
            from .runner import write
            write(controller.base/'helper-refill-progress.json',dict(at=reg.clock(),stage=name))
    stage('worker_eligibility')
    # Expensive historical process inspection must happen before taking a writer lock.
    eligible_workers = {l['worker_id'] for l in _workers(reg, reg.snapshot())}
    from .helper_retirement import tick as retire_helpers
    stage('helper_retirement')
    retire_helpers(reg)
    launches = reg.control_status()['launches']
    waiting = [key for key in config.get('wait_for_launches', [])
               if launches.get(key, {}).get('status') != 'exited']
    with reg.transaction() as state:
        pool = _state(state).setdefault('planner_pool', {})
        pool['waiting_for_coordinator'] = waiting
        pool.setdefault('scopes', {})
    if waiting: return
    from .planner_claims import reconcile_topics
    stage('topic_reconciliation')
    reconcile_topics(reg)
    from .planner_demand import no_work_observation, demand, prerequisites
    helpers = config.get('helpers', [])
    from .prerequisite_queue import links, recovery_demand, recovery_instruction
    with nullcontext(reg.snapshot()) as state:
        helpers = [dict(h, prerequisite_lanes=links(state, h)) for h in helpers]
    require(len({h['scope'] for h in helpers}) == len(helpers), 'Duplicate planner partition')
    with nullcontext(reg.snapshot()) as state:
        records = copy.deepcopy(_state(state).setdefault('planner_pool', {}).setdefault('scopes', {}))
        pressure=copy.deepcopy(state.get('queue_pressure',{}).get('stages',{}))
    from .queue_pressure import support_allocations
    stage('support_discovery')
    support=support_allocations(reg,helpers,records,config.get('integration_support_dynamic',False),config.get('actionable_support',False))
    def fresh_support(h):
        record=records.get(h['scope'],{})
        return (h.get('kind')=='integration_support' and bool(support.get(h['scope'])) and
                fingerprint(support[h['scope']])!=record.get('support_snapshot'))
    review_cache = {}
    def review_demand(h):
        key = tuple(h.get('review_inboxes', []))
        if key not in review_cache:
            review_cache[key] = review_pending(reg, settings, h)
        return review_cache[key]
    def demanded(h):
        if h.get('kind')=='integration_support':
            work=support[h['scope']]
            prior = records.get(h['scope'], {})
            return bool(work) and (fingerprint(work) != prior.get('support_snapshot') or
                                  h.get('mode', 'review') != prior.get('support_mode', 'review'))
        return (review_demand(h) if h.get('kind')=='publication' else
                not (h.get('defer_for_review') and review_demand({'review_inboxes':h['defer_for_review']})))
    # An old unpublished planning report must not suppress distinct, concrete
    # delivery recovery. Publication still validates every resulting proposal.
    from .delivery_recovery import allocations as delivery_allocations
    stage('delivery_and_publication_demand')
    from .dependency_classification import allocations as classifications
    demand_state = reg.snapshot()
    from .internal_followup import allocations as internal_allocations
    delivery_requested = classifications(demand_state,helpers,records,internal_allocations(demand_state,helpers,records,delivery_allocations(demand_state,helpers,records)))
    helpers = [h for h in helpers if h['scope'] in delivery_requested or
               (h['scope'] in records and 'completed_at' not in records[h['scope']]) or
               demanded(h)]
    # Receiving a report accepts no proposed implementation or gameplay gate.
    observed_lanes = reg.snapshot()['lanes']
    stage('report_completion')
    for scope, record in records.items():
        if record.get('cancelled_before_start') or ('completed_at' in record and 'no_work_checked' in record): continue
        lane = observed_lanes.get(record['spec']['lane']['lane'])
        if lane and lane['state']=='blocked' and record.get('actionable_support'):
            with reg.transaction() as state:
                if reg.recovery_safe(state,state['lanes'][lane['lane']]):
                    live=_state(state)['planner_pool']['scopes'][scope]
                    live.update(completed_at=reg.clock(),no_work_checked=True,no_work=None,
                                unresolved_outcome=copy.deepcopy(lane.get('outcome')))
                    _state(state)['items'][record['spec']['id']].update(status='needs_attention',ready=False)
                    reg.event(state,'support_action_unresolved',lane['lane'],scope=scope)
            continue
        if lane and lane['state'] == 'review_ready':
            with nullcontext(reg.snapshot()) as state:
                safe = reg.recovery_safe(state, state['lanes'][lane['lane']])
            if safe:
                lane = accept_helper_report(reg, lane)
        if lane and lane['state'] == 'done':
            with reg.transaction() as state:
                live = _state(state)['planner_pool']['scopes'][scope]
                live.setdefault('completed_at', reg.clock())
                if 'no_work_checked' not in live:
                    live['no_work'] = no_work_observation(reg, state, live)
                    live['no_work_checked'] = True
                for target in live.get('support_targets',[]):
                    state.setdefault('integration_support_reviewed',{})[fingerprint(target)]={
                        'reviewer':lane['lane'],'at':reg.clock(), 'mode':live.get('support_mode', 'review')}
                _state(state)['items'][record['spec']['id']].update(status='completed', ready=False)
    stage('recovery_allocation')
    with reg.transaction() as state:
        data = _state(state)
        pool = data['planner_pool']
        records = copy.deepcopy(pool['scopes'])
        from .blocked_recovery import allocations as blocked_allocations
        blocked = (blocked_allocations(state,helpers,records,reg.clock(),config.get('prerequisite_recovery_seconds',900),classify=True)
                   if config.get('cross_partition_recovery',False) else {})
        sleeping = {}
        eligible = []
        recovery_chains = set()
        recovery_targets = {k for r in blocked.values() for k in r['request']['lanes']}
        for helper in helpers:
            record = records.get(helper['scope'])
            recovery = blocked.get(helper['scope']) or (recovery_demand(state, helper, reg.clock(), config.get('prerequisite_recovery_seconds', 900))
                        if record and 'completed_at' in record else None)
            if recovery:
                if helper['scope'] not in blocked and recovery_targets.intersection(recovery['request']['lanes']):
                    sleeping[helper['scope']]=dict(reason='Blocked input already assigned to a repair planner')
                    continue
                if recovery['key'] in recovery_chains:
                    sleeping[helper['scope']] = dict(reason='Same blocked chain already assigned to a repair planner')
                    continue
                try:
                    reg.recovery_evidence(recovery['request']['report'])
                except (Rejected,OSError,ValueError) as exc:
                    sleeping[helper['scope']]=dict(reason='Repair evidence unavailable',error=str(exc))
                    continue
                recovery_chains.add(recovery['key'])
                recovery_targets.update(recovery['request']['lanes'])
                eligible.append(dict(helper, prerequisite_recovery=recovery))
                continue
            linked = helper.get('prerequisite_lanes', [])
            if linked and (not record or 'completed_at' in record):
                complete, signature, blockers = prerequisites(state, linked)
                if not complete:
                    sleeping[helper['scope']] = dict(reason='Waiting for assigned prerequisite jobs', prerequisites=blockers)
                    continue
                if not record or record.get('prerequisite_snapshot') != signature:
                    eligible.append(helper)
                    continue
            if not helper.get('kind') and record and 'completed_at' in record:
                wanted, reason = demand(reg, state, record, config.get('no_work_recheck_seconds', 3600))
                if not wanted:
                    sleeping[helper['scope']] = dict(reason=reason,
                        issues=record['no_work']['issues'], lanes=record['no_work']['lanes'],
                        recheck_at=record['completed_at'] + max(300, config.get('no_work_recheck_seconds', 3600)))
                    continue
            eligible.append(helper)
        cooling = {h['scope']: records[h['scope']]['completed_at'] + max(300, config.get('cooldown_seconds', 900))
                   for h in eligible if h['scope'] in records and 'completed_at' in records[h['scope']]
                   and not fresh_support(h)
                   and not h.get('prerequisite_recovery')
                   and reg.clock() < records[h['scope']]['completed_at'] + max(300, config.get('cooldown_seconds', 900))}
        helpers = [h for h in eligible if h['scope'] not in cooling]
        pool['cooling_scopes'] = cooling
        pool['sleeping_scopes'] = sleeping
        active = sum('completed_at' not in record for record in records.values())
        ready = sum(bool(i.get('ready')) and not i.get('planner_helper') for i in data['items'].values())
        unclaimed_ready = sum(bool(i.get('ready')) and not i.get('planner_helper') and
                              i.get('lane') not in state['lanes'] for i in data['items'].values())
        idle = len(_workers(reg, state, eligible=eligible_workers))
        integration = state.get('queue_pressure', {}).get('stages', {}).get('integration', {})
        support_scopes = {h['scope'] for h in helpers if h.get('kind') == 'integration_support'}
        support_active = sum(scope in support_scopes and 'completed_at' not in record
                             for scope, record in records.items())
        support_limit = support_target(config, demanded=len(support_scopes), idle=idle,
                                       active=support_active, unclaimed_ready=unclaimed_ready)
        planning_active = active - support_active
        planning_limit = helper_target(dict(config, low_watermark=settings.get('low_watermark', 8)),
                               helper_count=len(helpers) - len(support_scopes), ready=ready,
                               unclaimed_ready=unclaimed_ready,
                               idle=max(0, idle - max(0, support_limit - support_active)),
                               active=planning_active, integration=integration)
        target = planning_limit + support_limit
        if target:
            target_reason = ('Bounded planning and integration assistance during integration backlog'
                             if integration_backed_up(config, integration) else
                             'Planning and integration assistance with available worker capacity')
        elif integration_backed_up(config, integration):
            target_reason = 'Paused: integration queue reached depth or age threshold'
        elif ready and config.get('use_idle_capacity') and idle <= 1:
            target_reason = 'Paused: remaining idle capacity reserved for ready work'
        elif idle + active <= unclaimed_ready + max(0, int(config.get('reserve_workers', 2))):
            target_reason = 'Paused: workers reserved for execution'
        else:
            target_reason = ('Waiting for dependency changes in exhausted planning scopes' if sleeping else
                             'No helper demand within configured limits')
        # A target of zero is a drain instruction, not an instruction to kill
        # live model turns. Make the excess explicit so the dashboard explains
        # why active reservations can temporarily exceed the target.
        reclaimable = 0
        for record in records.values():
            if 'completed_at' in record: continue
            helper = data['items'].get(record['spec']['id'], {})
            lane = state['lanes'].get(helper.get('lane'), {})
            if lane.get('state') == 'ready' and reg.recovery_safe(state, lane):
                reclaimable += 1
        pool.update(enabled=True, active=active, target=target, target_reason=target_reason,
                    recovery_active=sum(bool(r.get('prerequisite_recovery')) and 'completed_at' not in r for r in records.values()),
                    recovery_candidates=len(blocked),
                    integration_support_active=support_active, integration_support_target=support_limit,
                    integration_support_limit=('uncapped' if config.get('integration_support_max_active',2) is None
                                               else config.get('integration_support_max_active',2)),
                    discovery_active=planning_active, discovery_target=planning_limit,
                    draining=active > target, excess=max(0, active-target),
                    reclaimable=reclaimable, ready_backlog=ready, updated_at=reg.clock())
    if not controller.capacity() or not 0 <= controller.memory() < controller.config.get('ram_high', 90): return
    # Never-used shards precede repeated turns, so fast no-work reports cannot
    # continually reclaim workers ahead of untouched backlog partitions.
    def staffing_priority(h):
        return preparation_priority(h,records,pressure,reg.clock())
    work = []
    provision_limit = min(4, max(1, int(config.get('provisions_per_tick', 1))))
    for helper in sorted(helpers, key=staffing_priority):
        scope = helper['scope']
        record = records.get(scope)
        pending = record and 'completed_at' not in record
        if pending:
            with nullcontext(reg.snapshot()) as state:
                if _state(state)['items'][record['spec']['id']]['phase'] == 'enqueued': continue
            spec = record['spec']
        else:
            is_support = helper.get('kind') == 'integration_support'
            if (support_active >= support_limit if is_support else planning_active >= planning_limit): continue
            if record and not fresh_support(helper) and not helper.get('prerequisite_recovery') and reg.clock() - record['completed_at'] < max(300, config.get('cooldown_seconds', 900)): continue
            path = _private(reg, helper['template'])
            require(digest(path) == helper['sha256'], 'Planner template bytes changed')
            spec = json.loads(path.read_text(encoding='utf-8-sig'))
            require(spec['role'] == 'review' and spec['heavy'] is False and spec['lane']['native'] is None,
                    'Planner template must be non-build review work')
            cycle = (record or {}).get('cycle', 0) + 1
            spec['id'] += '-cycle-' + str(cycle)
            spec['lane']['lane'] += '-cycle-' + str(cycle)
            if helper.get('kind') == 'integration_support':
                if config.get('actionable_support',False):
                    from .support_actions import INSTRUCTION as ACTION_INSTRUCTION
                    spec['instruction'] += ACTION_INSTRUCTION
                spec['instruction'] += (' Integration support: inspect this frozen queue snapshot: '+
                    json.dumps(support[scope])+'. Verify current handoff pins before reviewing. '
                    'Prepare a hashed packet for the existing integrator. Finish review-ready. '
                    'Existing owner retains final integration and gameplay acceptance; no ADMIT. ')
                if any(t.get('kind')=='export_preparation' for t in support[scope]):
                    spec['instruction'] += (' EXPORT PREPARATION ASSIGNMENT: the target is blocked on export delivery, '
                        'not a request to send the producer through another unchanged repair. Use an exclusive private '
                        'root worktree under your output directory. Identify the actual maintained root/native '
                        'destination from current integrator evidence, verify both HEADs, and pin the assigned '
                        'producer native head. Prepare a minimal engine/ patch for the candidate native delta '
                        '(native base..head), preserving unrelated curated engine differences. Rehearse apply/check '
                        'only in your private destination worktree; inspect every changed path and demonstrate that '
                        'unrelated curated files are byte-identical. If candidate bytes already landed, prove that '
                        'fact and prepare the remaining export delta without repeating source cherry-picks. '
                        'Emit the patch as UTF-8 unified Git diff bytes (prefer Python subprocess stdout bytes); '
                        'PowerShell redirection can produce UTF-16, which is rejected. If export_packet_repair '
                        'is present, inspect its reason and recorded integrator generations. For unconsumed packets, '
                        'read those owner reports and actual destination pins; resolve wrong prefixes, stale bases, '
                        'missing handoff prerequisites or other concrete blockers in private preparation. '
                        'A packet can be syntactically valid yet unusable. Do not resubmit identical bytes with '
                        'new prose; produce corrected application evidence or finish blocked with the exact '
                        'remaining correction and responsible scope. Re-run private git apply --check. '
                        'Do not run a full export over the maintained engine tree, touch shared source, or manufacture '
                        'an export receipt. Record action integration_packet with details.destination {root,native}, '
                        'source_native (assigned native head), export_patch {path,sha256}, export_validation '
                        '{path,sha256}, and apply_commands (exact commands for final-owner apply, verification and '
                        'receipt). Include the source/destination pins, per-path before/after hashes, rehearsal '
                        'results and remaining owner steps in the validation artifact. Recheck pins before submission; '
                        'changed producer pins require stale disposition, changed destination requires revalidation. '
                        'A prose referral to the maintained lead is not a deliverable. If genuinely unable to '
                        'produce a safe patch, finish blocked with the concrete conflicting hunks and evidence. ')
                if config.get('delegate_shared_reviews',False):
                    from .review_decisions import INSTRUCTION as REVIEW_INSTRUCTION
                    spec['instruction'] += ('Controller authorization under #635 supersedes older template restrictions '
                        'on shared-file approval: you may approve or reject shared files ONLY for your frozen '
                        'support_targets assignment. Inspect actual diffs and hashed evidence, submit all file '
                        'decisions in one request before finishing review-ready. Missing evidence is a blocker, '
                        'never approval. Source merges, exports, final integration receipts and ADMIT remain '
                        'with the integration owner. '+REVIEW_INSTRUCTION)
                else:
                    spec['instruction'] += 'Shared-file decisions remain with the integration owner. '
                if helper.get('mode') == 'preparation':
                    spec['instruction'] += ('Use exclusive private worktrees and codex branches beneath your owned output directory '
                        'to rehearse candidate integration, resolve merge conflicts and run relevant tests. '
                        'Read the current registered integrator batch/build/receipt evidence to determine the actual destination '
                        'worktree and commit; do not assume the integrator lane source record is the destination. '
                        'If destination is ambiguous, report the exact missing pin rather than guess. '
                        'Pin producer and destination commits before work, preserve original candidate commits, and report '
                        'resolution commits, patch hashes, build/test evidence and remaining decisions. '
                        'Before handing off, recheck both pins; mark changed destinations stale and requiring revalidation. '
                        'Heavy builds require canonical registry leases and an exclusive private build directory; '
                        'record commit, executable SHA256 and ninja dry-run. No edits to producer/shared worktrees, '
                        'maintained builds/exports, runtime acceptance, shared merges or worker launches. '
                        'Preparation evidence never replaces the integrator final validation or receipt.')
                else:
                    spec['instruction'] += 'Read-only review only: no source edits, merges or builds.'
            elif helper.get('kind') == 'publication':
                spec['instruction'] += (' Publication review partition: ' + scope +
                    '. Review existing immutable proposals only. Publish solely through canonical '
                    'workflow.planner_pool.merge_proposals; retry manifest-change conflicts from fresh state. '
                    'No raw manifest writes, implementation, launches or ADMIT. Finish review-ready with hashed decisions.')
            else:
                if integration_backed_up(config, integration):
                    spec['instruction'] += (' Integration backlog mode: prioritize concrete prerequisites, '
                        'repair proposals and publication of existing work that unblock current consumers. '
                        'Inspect current blocked outcomes and missing integration receipts before proposing '
                        'expansion. Reuse existing owners; do not duplicate their active work. A linked '
                        'producer that remains blocked is not a resolved dependency. Stage bounded '
                        'issue-backed proposals with the original failing consumer check as acceptance. ')
                from .proposal_feedback import feedback
                observation = reg.snapshot()
                for directory in helper.get('defer_for_review', []):
                    for proposal in _private(reg, directory).glob('proposals-*.json'):
                        decision = feedback(reg, proposal, state=observation)
                        if decision:
                            spec['instruction'] += (' PRIOR REVIEW FEEDBACK: ' + json.dumps(decision) +
                                '. For repair, prioritize a corrected uniquely named immutable proposal '
                                'and validate the full schema; do not alter old bytes. For dependency, '
                                'advance the existing named dependency through its owner; do not create '
                                'a duplicate scope or re-review the unchanged proposal. Read the hashed report.')
                spec['instruction'] += (' Planning partition: ' + scope +
                '. Stage proposals only in your configured partition; never write the shared manifest. '
                'Finish review-ready with a hashed planning report even when no actionable scope exists. '
                'No implementation, builds, worker launches or ADMIT. Respect coordinator ownership partition.')
                if helper.get('prerequisite_recovery'):
                    spec['instruction'] += recovery_instruction(helper['prerequisite_recovery'])
                    if not helper['prerequisite_recovery']['request'].get('classification') and (config.get('actionable_support',False) or helper['prerequisite_recovery']['request'].get('internal_followup')):
                        from .support_actions import INSTRUCTION as ACTION_INSTRUCTION
                        spec['instruction'] += ACTION_INSTRUCTION
            from .producer_contract import INSTRUCTION
            spec['instruction'] += INSTRUCTION
            with reg.transaction() as state:
                data = _state(state)
                data['planner_pool']['scopes'][scope] = dict(spec=spec, cycle=cycle, started_at=reg.clock())
                if helper.get('prerequisite_recovery'):
                    recovery = helper['prerequisite_recovery']
                    data.setdefault('prerequisite_recovery', {})[recovery['key']] = dict(
                        scope=scope, request_id=recovery['request']['id'], input_snapshot=recovery['input_snapshot'],
                        lane=spec['lane']['lane'], created_at=reg.clock())
                    data['planner_pool']['scopes'][scope]['prerequisite_recovery'] = recovery['key']
                    data['planner_pool']['scopes'][scope]['recovery_targets'] = recovery['request']['lanes']
                    data['planner_pool']['scopes'][scope]['followup_owner_lanes'] = recovery['request'].get('followup_owner_lanes',[])
                    if recovery['request'].get('classification'):
                        data['planner_pool']['scopes'][scope]['classification_target'] = copy.deepcopy(recovery['request']['classification'])
                    if config.get('actionable_support',False) or recovery['request'].get('classification') or recovery['request'].get('internal_followup'):
                        from .support_actions import FIELDS
                        row=data['planner_pool']['scopes'][scope]
                        row['actionable_support']=True
                        row['recovery_action_targets']=[{f:copy.deepcopy(state['lanes'][k].get(f)) for f in FIELDS}
                                                       for k in recovery['request']['lanes'] if k in state['lanes']]
                    reg.event(state, 'prerequisite_recovery_prepared', spec['lane']['lane'],
                              scope=scope, request_id=recovery['request']['id'])
                if helper.get('prerequisite_lanes'):
                    data['planner_pool']['scopes'][scope]['prerequisite_snapshot'] = prerequisites(
                        state, helper['prerequisite_lanes'])[1]
                if helper.get('kind')=='integration_support':
                    data['planner_pool']['scopes'][scope]['actionable_support']=config.get('actionable_support',False)
                    data['planner_pool']['scopes'][scope]['support_mode']=helper.get('mode', 'review')
                    data['planner_pool']['scopes'][scope]['support_snapshot']=fingerprint(support[scope])
                    data['planner_pool']['scopes'][scope]['support_targets']=support[scope]
                    if config.get('delegate_shared_reviews',False):
                        data['planner_pool']['scopes'][scope]['review_authority']='shared-files-v1'
                data['items'][spec['id']] = dict(spec_hash=fingerprint(spec), priority=spec['priority'],
                    lane=spec['lane']['lane'], phase='pending', status='pending', ready=False, planner_helper=True)
            active += 1
            if is_support: support_active += 1
            else: planning_active += 1
        work.append((scope,copy.deepcopy(spec)))
        if len(work)>=provision_limit:break
    from .helper_preparation import prepare_batch
    prepare_batch(controller,work,issue_reader,config,prepare=_prepare)


def preparation_priority(helper, records, pressure, now):
    stage={'publication':'publication','integration_support':'integration'}.get(helper.get('kind'))
    old=records.get(helper['scope'],{})
    aged=bool(old and 'completed_at' not in old and now-old.get('started_at',now)>=300)
    return (0 if stage or aged else 1 if helper.get('prerequisite_recovery') or old.get('prerequisite_recovery') else 2,
            -pressure.get(stage,{}).get('pressure',0),old.get('started_at',0))
