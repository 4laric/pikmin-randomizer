"""Controller adapter for authorized pool jobs and provisional QA.

All execution still uses the existing fenced runner. This adapter never invents
an issue, changes admission, or starts a second integration writer.
"""
import hashlib
import json
import math
import time
from pathlib import Path

from .handoff import Rejected, digest, local_path
from .runner import write


def capture_costs(controller):
    """Ingest provider-reported estimates once; absent prices stay unknown."""
    reg = controller.reg
    paths = []
    for key, entry in controller.config.get('lanes', {}).copy().items():
        try:
            directory = local_path(reg.root, entry['output'])
            paths.extend((key, p) for p in directory.glob('run-*.jsonl'))
        except (KeyError, Rejected, OSError, ValueError) as exc:
            reg.notice(key, 'cost_source_unavailable', {'error': str(exc)})
    for launch in reg.control_status()['launches'].values():
        path = controller.launch_directory(launch['id']) / 'events.jsonl'
        if path.is_file():
            paths.append((launch['lane'], path))
    with reg.transaction() as state:
        offsets = dict(state.setdefault('throughput_runtime', {}).setdefault('cost_offsets', {}))
        known = dict(state.get('throughput', {}).get('costs', {}))
    for key, path in paths:
        identity = str(path.resolve())
        offset = offsets.get(identity, 0)
        try:
            if path.stat().st_size < offset:
                continue  # Rotated source: preserve original attribution.
            with path.open('rb') as stream:
                stream.seek(offset)
                data = stream.read(2 * 1024 * 1024)
        except OSError as exc:
            reg.notice(key, 'cost_source_unavailable', {'path': identity, 'error': str(exc)})
            continue
        complete = data.rfind(b'\n') + 1
        if not complete:
            continue
        records = []
        for line in data[:complete].splitlines():
            try:
                event = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(event, dict) or event.get('type') != 'step_finish':
                continue
            part = event.get('part', {})
            amount = part.get('cost') if isinstance(part, dict) else None
            if type(amount) not in (int, float) or not math.isfinite(amount) or amount <= 0:
                continue  # Zero often means the provider has no pricing metadata.
            timestamp = event.get('timestamp')
            if type(timestamp) not in (int, float) or not math.isfinite(timestamp) or timestamp <= 0:
                continue
            session = event.get('sessionID') or part.get('sessionID')
            fingerprint = (str(session) + ':' + str(part['id'])).encode() if session and part.get('id') else identity.encode() + line
            event_id = hashlib.sha256(fingerprint).hexdigest()
            if event_id in known:
                prior = known[event_id]
                if prior['amount'] != amount:
                    reg.notice(key, 'cost_event_conflict', {'event_id': event_id, 'path': identity})
                # Reused sessions can replay history in a new slice. Keep its
                # original attribution, never charge that same event twice.
                continue
            records.append(dict(event_id=event_id, lane=key, amount=amount, currency='USD',
                                at=timestamp / 1000))
            known[event_id] = {'amount': amount, 'at': timestamp / 1000}
        if records:
            reg.report_cost_batch(records)
        with reg.transaction() as state:
            state.setdefault('throughput_runtime', {}).setdefault('cost_offsets', {})[identity] = offset + complete



def completion_evidence(reg, lane):
    """Prefer the applied disposition; never repair or rehash stale evidence."""
    candidates = []
    integration = lane.get('integration')
    if isinstance(integration, dict):
        candidates.append(('integration', {'path': integration.get('validation_path'),
                                           'sha256': integration.get('validation_sha256')}))
    disposition = lane.get('review_disposition')
    if isinstance(disposition, dict):
        candidates.append(('review_disposition', disposition.get('evidence')))
        candidates.append(('archived_review_disposition', disposition.get('archived_evidence')))
    handoff = lane.get('handoff')
    if isinstance(handoff, dict):
        candidates.append(('handoff', {key: handoff.get(key) for key in ('path', 'sha256')}))
    candidates.append(('progress', lane.get('progress_evidence')))
    outcome = lane.get('outcome')
    if isinstance(outcome, dict):
        candidates.append(('outcome', outcome.get('evidence')))
    failures = []
    for label, evidence in candidates:
        if evidence is None:
            continue
        try:
            reg.evidence(evidence)
        except (Rejected, OSError, ValueError, TypeError) as exc:
            failures.append(label + ': ' + str(exc))
            continue
        return evidence
    raise Rejected('No valid completion evidence' + (': ' + '; '.join(failures) if failures else ' recorded'))


def assign_pending(controller):
    reg = controller.reg
    settings = controller.config.get('throughput', {})
    if not settings.get('enabled', False): return
    pool = reg.scheduling_status()
    if controller.capacity():
        from .scheduling import job_priority
        assigned = 0
        assignment_limit = min(4, max(1, int(settings.get('assignments_per_tick', 1))))
        def priority(worker):
            return min((job_priority(j) for j in pool['jobs'].values()
                        if j['status'] in ('queued', 'assigned') and j['worker_id'] == worker['worker_id']),
                       default=(99, 99, 99, 0, worker['worker_id']))
        # Workers without queued/assigned work cannot produce an assignment.
        # Avoid a registry transaction and fresh RAM probe for every idle slot.
        dispatched={a['worker_id'] for a in pool['assignments'].values() if a['status']=='dispatched'}
        demanded={j['worker_id'] for j in pool['jobs'].values() if j['status'] in ('queued','assigned')}-dispatched
        for worker in sorted((w for w in pool['workers'].values() if w['worker_id'] in demanded), key=priority):
            try:
                assignment = reg.assign_job(worker['worker_id'], controller.memory())
                if not assignment or assignment['status'] != 'assigned':
                    continue
                if assignment['lane'] not in controller.config['lanes'] or not controller.available(assignment['lane']):
                    reg.release_assignment(assignment['id'], 'Launch configuration or legacy owner unavailable')
                    reg.notice(assignment['lane'], 'pool_launch_config_needed',
                               {'reason': 'Prepared launch spec or stopped legacy supervisor required'})
                    continue
                reg.plan_assignment(assignment['id'], controller.config['models'], controller.memory(),
                                    fresh_session=settings.get('fresh_session_per_lane', True))
                assigned += 1
                if assigned >= assignment_limit or not controller.capacity(): break
            except Rejected as exc:
                reg.notice(worker['worker_id'], 'pool_dispatch_blocked', {'error': str(exc)})


def complete_pool_assignments(controller):
    reg = controller.reg
    # Completion releases a persistent pool worker only after accepted output.
    snapshot = reg.snapshot()
    pool = reg.scheduling(snapshot)
    lanes = snapshot['lanes']
    for assignment in pool['assignments'].values():
        if assignment['status'] != 'dispatched':
            continue
        lane = lanes.get(assignment['lane'], {})
        if lane.get('state') != 'done':
            continue
        try:
            if lane.get('target_level') == 'planning-only' and not lane.get('integration') and not lane.get('review_disposition'):
                child_path = controller.launch_directory(assignment['launch_id']) / 'child.json'
                if child_path.is_file():
                    reg.supersede_planning_assignment(assignment['id'], json.loads(child_path.read_text()))
                    continue
            evidence = completion_evidence(reg, lane)
            reg.complete_assignment(assignment['id'], evidence)
        except (Rejected, OSError, ValueError, TypeError) as exc:
            reg.notice(assignment['lane'], 'pool_completion_blocked', {'error': str(exc)})


def pool_tick(controller, *, publish=True):
    reg = controller.reg
    settings = controller.config.get('throughput', {})
    state = reg.snapshot(sections=[('throughput_runtime', 'launch_specs')])
    specs = dict(state.get('throughput_runtime', {}).get('launch_specs', {}))
    controller.config['lanes'].update(specs)
    if not settings.get('enabled', False):
        return
    if not getattr(controller, '_dispatch_monitor', None):
        complete_pool_assignments(controller)
    from .autofill import autofill_tick, autofill_status
    from .worker_capacity import park_blocked
    park_blocked(reg)
    autofill_tick(controller)
    if settings.get('auto_batch_claim', False):
        try:
            claimed = reg.auto_claim_batches(max_candidates=settings.get('auto_batch_max_candidates', 16))
            for batch in claimed:
                reg.notice(batch['integrator'], 'integration_batch_claimed', {
                    'batch_id': batch['id'], 'workstream': batch['workstream'],
                    'candidates': list(batch['candidates']),
                    'next_action': 'record validated build evidence or isolate a candidate'})
        except (Rejected, OSError, ValueError, TypeError, KeyError) as exc:
            reg.notice('integration', 'auto_batch_claim_blocked', {'error': str(exc)})
    # A live owner is not sufficient: claimed batches must show execution
    # progress. Escalate stalled owners by age bucket without changing pins or
    # killing a live process; reassignment remains a fenced owner operation.
    try:
        batch_sla = max(300, int(settings.get('batch_stall_seconds', 900)))
        sched = reg.scheduling_status()
        lanes = reg.status()['lanes']
        now = reg.clock()
        for batch in sched.get('batches', {}).values():
            if batch.get('state') != 'claimed':
                continue
            owner = lanes.get(batch.get('integrator'), {})
            progress = owner.get('progress_at') or batch.get('created_at') or now
            age = max(0, now - progress)
            if age < batch_sla:
                continue
            bucket = int(age // batch_sla)
            reg.notice(batch['integrator'], 'integration_batch_stalled', {
                'batch_id': batch['id'], 'workstream': batch.get('workstream'),
                'stall_bucket': bucket,
                'candidates': list(batch.get('candidates', {})),
                'action': 'record build progress or fenced reassignment before the next SLA bucket'})
    except (Rejected, OSError, ValueError, TypeError, KeyError):
        pass
    if not getattr(controller, '_dispatch_monitor', None):
        assign_pending(controller)
    if controller.capacity():
        if settings.get('provisional_qa', True):
            for job in reg.candidate_qa_ready():
                key = job['key']
                if key not in controller.config['lanes'] or not controller.available(key):
                    continue
                try:
                    instruction = (
                        'Run independent PROVISIONAL QA on this exact frozen candidate. '
                        'Preserve your same session and private worktree. Do not change '
                        'integration dependencies, grant ADMIT, or report this as accepted integration. '
                        'Any runtime needs a private leased build and fresh current fixture baseline. '
                        'Record candidate QA result with the current bound generation and candidate pin: '
                        + json.dumps(job))
                    reg.queue_candidate_qa(key, job['generation'], job['revision'], job['pin'],
                                           instruction, controller.config['models'])
                    break
                except Rejected as exc:
                    reg.notice(key, 'candidate_qa_blocked', {'error': str(exc), 'pin': job['pin']})
    if settings.get('capture_costs', True):
        try:
            capture_costs(controller)
        except (Rejected, OSError, ValueError) as exc:
            write(controller.base / 'cost-error.json', {'at': reg.clock(), 'error': str(exc)})
    if publish and not getattr(controller, '_dashboard_monitor', None):
        publish_status(controller)


def publish_status(controller):
    """Publish after dispatch so the dashboard includes this tick's starts.

    One committed snapshot feeds every section; historical maps are bounded before writing."""
    reg = controller.reg
    observed = reg.clock()  # Before the read: orders concurrent publishers' stage observations.
    state = reg.snapshot()
    from .stage_timing import observe, alert
    observe(reg, state, now=observed)
    alert(reg, state)
    from .autofill import autofill_status
    status = reg.throughput_status(ram_percent=controller.memory(), state=state)
    status['autofill'] = autofill_status(reg, state=state)
    error_path = controller.base / 'error.json'
    if error_path.is_file():
        try:
            error = json.loads(error_path.read_text(encoding='utf-8-sig'))
            age = status['at'] - error.get('at', status['at']) if isinstance(error, dict) else 0
            status['controller_health'] = dict(status='degraded' if age < 2 * controller.config.get('interval', 15) else 'healthy',
                                               last_error=error, age_seconds=max(0, age))
        except (OSError, ValueError, TypeError):
            status['controller_health'] = {'status': 'error record unreadable'}
    else:
        status['controller_health'] = {'status': 'healthy'}
    status['queue_pressure']={k:v for k,v in state.get('queue_pressure',{}).items() if k!='history'}
    from .activity_health import snapshot
    status['worker_activity'] = snapshot(controller, state=state)
    from .worker_roster import roster
    from .spend import hourly_spend
    from .autofill import _workers
    from .delivery_contracts import audit as delivery_audit
    status['delivery_audit'] = delivery_audit(state)
    status['worker_roster'] = roster(state, {w['worker_id'] for w in _workers(reg, state)},
                                     status['worker_activity'])
    from .inspect import stuck, bounded as bounded_stuck
    try:  # A view only: a malformed record must not stop the dashboard publishing.
        status['stuck'] = bounded_stuck(dict(stuck(state, status['at'], cfg=controller.config, base=controller.base,
            probe=reg.probe), available_workers=status['worker_roster']['available_workers']))
    except (Rejected, KeyError, TypeError, ValueError, AttributeError) as exc:
        status['stuck'] = dict(error='Stuck view unavailable: %s' % (str(exc) or type(exc).__name__))
    spend_state = dict(lanes={k:dict(task_id=v.get('task_id', '')) for k,v in state['lanes'].items()},
                       control=dict(launches={k:dict(session=v.get('session')) for k,v in state.get('control', {}).get('launches', {}).items()}))
    status['hourly_spend'] = hourly_spend(spend_state, status['at'])
    from .admission_progress import snapshot as admission_snapshot
    status['monster_admission'] = admission_snapshot(reg.root, controller.config.get('monster_admission', {}))
    from .admission_reconciliation import audit as admission_audit
    status['admission_reconciliation'] = admission_audit(reg, status['monster_admission'],
        controller.config.get('monster_admission', {}), snapshot=state)
    from .export_preparation import status as export_status
    status['export_preparation'] = export_status(reg, state=state)
    from .dashboard import render_dashboard, publishable
    status = publishable(status)
    write(controller.base / 'throughput.json', status, durable=False)
    target = controller.base / 'throughput.html'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(render_dashboard(status), encoding='utf-8')
    publish_dashboard(temporary, target, controller.reg.clock())


def publish_dashboard(temporary, target, now, *, pause=time.sleep):
    """An open Windows reader must not abort controller maintenance."""
    for attempt in range(6):
        try:
            temporary.replace(target)
            return True
        except PermissionError as exc:
            if attempt < 5:
                pause(.05 * 2**attempt)
                continue
            write(target.parent / 'dashboard-publish-error.json',
                  dict(at=now, error=str(exc), status='retry_next_tick', target=str(target)))
            return False
