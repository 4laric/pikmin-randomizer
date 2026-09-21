"""One row per authorized persistent pool worker, independent of lane history."""
from collections import Counter
from .worker_capacity import parked


def roster(state, idle_ids, activity):
    launches = {}
    for item in state.get('control', {}).get('launches', {}).values():
        if item.get('status') in ('intent', 'spawned', 'running', 'exiting'):
            if item.get('created_at', 0) >= launches.get(item['lane'], {}).get('created_at', 0):
                launches[item['lane']] = item
    owners = {s.get('owner_lane') for s in state.get('throughput', {}).get('workstreams', {}).values()}
    rows = []
    for worker_id in sorted(state.get('throughput', {}).get('workers', {})):
        lanes = [l for l in state.get('lanes', {}).values() if l.get('worker_id') == worker_id]
        unfinished = [l for l in lanes if l.get('state') != 'done']
        candidates = [l for l in unfinished if not parked(l)] or unfinished or lanes
        lane = max(candidates, key=lambda l: (l.get('lane') in launches,
                   l.get('created_at', 0), l.get('generation', 0)), default={})
        key = lane.get('lane', '')
        launch = launches.get(key, {})
        state_name = lane.get('state')
        if worker_id in idle_ids:
            status = 'Idle'
        elif state_name == 'done':
            status = 'Releasing / inspect'
        elif (key == 'acceptance-backlog-planner' and state_name == 'blocked'
              and lane.get('dependencies') == ['#581']
              and str(lane.get('next_action', '')).startswith('Awaiting helper proposals')):
            status = 'Waiting for proposals'
        elif state_name in ('blocked', 'reconciling'):
            status = 'Unavailable / recovery'
        elif state_name == 'waiting_resource':
            status = 'Waiting for resource'
        elif state_name in ('handoff_ready', 'review_ready', 'integrating'):
            status = 'Awaiting integration / review'
        elif launch.get('registration_recovery_exhausted'):
            status = 'Needs inspection'
        elif launch.get('status') in ('intent', 'spawned') or state_name == 'ready':
            status = 'Queued'
        elif launch.get('status') == 'running':
            status = 'Running'
        else:
            status = 'Needs inspection'
        role = ('Integration' if key in owners else
                'Integration preparation' if key.startswith('integration-support-') else
                'Planning' if key.startswith('planning-') or key == 'acceptance-backlog-planner' else
                'Publication review' if key.startswith('publication-review-') else
                'Implementation / QA')
        observed = activity.get(key, {})
        rows.append(dict(worker=worker_id, status=status,
            role=role if status != 'Idle' else 'Available', lane=key if status != 'Idle' else '',
            issue=lane.get('issue') if status != 'Idle' else None,
            detail=('Available for compatible work' if status == 'Idle' else
                    str(lane.get('progress_detail') or lane.get('next_action') or 'No update recorded'))[:260],
            activity=observed.get('status', 'No current session observation'),
            activity_age_seconds=observed.get('activity_age_seconds'),
            other_unfinished_lanes=max(0, len(unfinished)-1)))
    return dict(blocked_lanes=sum(l.get('state') == 'blocked' for l in state.get('lanes', {}).values()),
                parked_lanes=sum(parked(l) for l in state.get('lanes', {}).values()),
                available_workers=len(idle_ids),
                unavailable_workers=sum(r['status'] == 'Unavailable / recovery' for r in rows), total=len(rows), counts=dict(Counter(r['status'] for r in rows)), workers=rows)
