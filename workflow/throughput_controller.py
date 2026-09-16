"""Controller adapter for authorized pool jobs and provisional QA.

All execution still uses the existing fenced runner. This adapter never invents
an issue, changes admission, or starts a second integration writer.
"""
import hashlib
import json
import math
from pathlib import Path

from .handoff import Rejected, digest, local_path
from .runner import write


def capture_costs(controller):
    """Ingest provider-reported estimates once; absent prices stay unknown."""
    reg = controller.reg
    paths = []
    for key, entry in controller.config.get('lanes', {}).items():
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


def pool_tick(controller):
    reg = controller.reg
    settings = controller.config.get('throughput', {})
    with reg.transaction() as state:
        specs = dict(state.get('throughput_runtime', {}).get('launch_specs', {}))
    controller.config['lanes'].update(specs)
    if not settings.get('enabled', False):
        return
    # Completion releases a persistent pool worker only after accepted output.
    pool = reg.scheduling_status()
    lanes = reg.status()['lanes']
    for assignment in pool['assignments'].values():
        if assignment['status'] != 'dispatched':
            continue
        lane = lanes.get(assignment['lane'], {})
        if lane.get('state') != 'done':
            continue
        try:
            evidence = completion_evidence(reg, lane)
            reg.complete_assignment(assignment['id'], evidence)
        except (Rejected, OSError, ValueError, TypeError) as exc:
            reg.notice(assignment['lane'], 'pool_completion_blocked', {'error': str(exc)})
    from .autofill import autofill_tick, autofill_status
    autofill_tick(controller)
    pool = reg.scheduling_status()
    if controller.capacity():
        from .scheduling import job_priority
        def priority(worker):
            return min((job_priority(j) for j in pool['jobs'].values()
                        if j['status'] in ('queued', 'assigned') and j['worker_id'] == worker['worker_id']),
                       default=(99, 99, 99, 0, worker['worker_id']))
        for worker in sorted(pool['workers'].values(), key=priority):
            try:
                assignment = reg.assign_job(worker['worker_id'], controller.memory())
                if not assignment or assignment['status'] != 'assigned':
                    continue
                if assignment['lane'] not in controller.config['lanes'] or not controller.available(assignment['lane']):
                    reg.release_assignment(assignment['id'], 'Launch configuration or legacy owner unavailable')
                    reg.notice(assignment['lane'], 'pool_launch_config_needed',
                               {'reason': 'Prepared launch spec or stopped legacy supervisor required'})
                    continue
                reg.plan_assignment(assignment['id'], controller.config['models'], controller.memory())
                break  # Existing dispatcher still starts at most one runner per tick.
            except Rejected as exc:
                reg.notice(worker['worker_id'], 'pool_dispatch_blocked', {'error': str(exc)})
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
    status = reg.throughput_status(ram_percent=controller.memory())
    status['autofill'] = autofill_status(reg)
    write(controller.base / 'throughput.json', status)
    from .dashboard import render_dashboard
    target = controller.base / 'throughput.html'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(render_dashboard(status), encoding='utf-8')
    temporary.replace(target)
