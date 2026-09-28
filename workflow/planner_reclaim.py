"""Yield only never-launched helper reservations, under the sole controller."""
from .autofill import _state, _workers, _check_conflicts
from .control import fingerprint


def reclaim_for(controller, spec):
    reg = controller.reg
    with reg.transaction() as state:
        data = _state(state)
        item = data['items'].get(spec['id'], {})
        if (not item.get('ready') or item.get('planner_helper') or
                item.get('spec_hash') != fingerprint(spec) or
                item.get('previous_lane') or spec['lane']['lane'] in state['lanes'] or
                _workers(reg, state, spec)):
            return None
        _check_conflicts(controller, state, spec)
        pool = reg.scheduling(state)
        stream = pool['workstreams'].get(spec['workstream'], {})
        owner = state['lanes'].get(stream.get('owner_lane'), {})
        if not owner or owner['state'] == 'done' or reg.probe(owner['process']) != 'alive': return None
        for scope, record in data.get('planner_pool', {}).get('scopes', {}).items():
            if 'completed_at' in record: continue
            helper = data['items'].get(record['spec']['id'], {})
            lane = state['lanes'].get(helper.get('lane'))
            if (not helper.get('planner_helper') or not lane or lane['state'] != 'ready' or
                    lane['generation'] != 1 or lane.get('started_at') or lane.get('progress_evidence') or
                    not reg.recovery_safe(state, lane)):
                continue
            key = lane['lane']
            worker = pool['workers'].get(lane['worker_id'], {})
            if (spec['role'] not in worker.get('roles', []) or
                    not set(spec['capabilities']) <= set(worker.get('capabilities', []))): continue
            if any(l['worker_id'] == lane['worker_id'] and l['lane'] != key and
                   (l['state'] != 'done' or not reg.recovery_safe(state, l)) for l in state['lanes'].values()): continue
            if any(v['lane'] == key for v in state.get('planning_claims', {}).values()): continue
            if any(v['lane'] == key for v in state['leases'].values()): continue
            launches = [l for l in state.get('control', {}).get('launches', {}).values() if l['lane'] == key]
            # Even a dead unbound runner is outside this operation's authority.
            # Any dispatch artifact leaves uncertain startup to normal recovery.
            if any(l['status'] != 'intent' or l.get('process') or l.get('bound_generation') or
                   l.get('attempts', 0) or controller.launch_directory(l['id']).exists() for l in launches): continue
            assignments = [a for a in pool['assignments'].values() if a['worker_id'] == lane['worker_id'] and
                           a['status'] in ('assigned', 'dispatched')]
            if any(a['lane'] != key or a['generation'] != lane['generation'] for a in assignments): continue
            reason = dict(at=reg.clock(), for_spec=spec['id'], summary='Cancelled before execution to yield capacity to prepared implementation')
            for launch in launches: launch.update(status='cancelled', cancellation=reason)
            for assignment in assignments: assignment.update(status='cancelled', cancellation=reason)
            for job in pool['jobs'].values():
                if job['lane'] == key: job.update(status='cancelled', cancellation=reason)
            lane.update(state='done', cancelled_before_start=reason, next_action=reason['summary'], revision=lane['revision']+1)
            helper.update(status='cancelled', ready=False, awaiting_worker=False, cancellation=reason)
            record.update(completed_at=reg.clock(), cancelled_before_start=reason)
            reg.event(state, 'planner_reservation_cancelled', key, for_spec=spec['id'])
            return key
    return None
