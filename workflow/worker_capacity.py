"""Release execution capacity without completing or abandoning blocked work."""
from .handoff import Rejected

IN_FLIGHT = ('intent', 'spawned', 'running', 'exiting')


def parked(lane):
    marker = lane.get('capacity_parked') or {}
    return lane.get('state') == 'blocked' and marker.get('generation') == lane.get('generation')


def reusable(reg, state, lane):
    return (parked(lane) and reg.recovery_safe(state, lane) and
            not any(x['lane'] == lane['lane'] and x['status'] in IN_FLIGHT
                    for x in state.get('control', {}).get('launches', {}).values()))


def park_blocked(reg):
    result = []
    with reg.transaction() as state:
        pool = reg.scheduling(state)
        owners = {s['owner_lane'] for s in pool['workstreams'].values()}
        launches = state.get('control', {}).get('launches', {})
        for key, lane in state['lanes'].items():
            if (lane['state'] != 'blocked' or parked(lane) or lane.get('handoff') or
                    key in owners or key == 'acceptance-backlog-planner' or
                    lane['worker_id'] not in pool['workers']):
                continue
            if not reg.recovery_safe(state, lane) or any(
                    x['lane'] == key and x['status'] in IN_FLIGHT for x in launches.values()):
                continue
            outcome = lane.get('outcome') or {}
            if outcome.get('outcome') != 'blocked' or not lane.get('dependencies'):
                continue
            try:
                reg.evidence(outcome.get('evidence'))
            except (Rejected, OSError, ValueError, TypeError):
                continue
            assignments = [a for a in pool['assignments'].values()
                           if a['lane'] == key and a['status'] in ('assigned', 'dispatched')]
            if any((launches.get(a.get('launch_id'), {}).get('bound_generation')
                    if a['status'] == 'dispatched' else a.get('generation')) != lane['generation']
                   for a in assignments):
                continue
            marker = dict(generation=lane['generation'], at=reg.clock(), evidence=outcome['evidence'])
            lane['capacity_parked'] = marker
            for a in assignments:
                a.update(status='parked', parked_at=reg.clock(), evidence=outcome['evidence'])
                pool['jobs'][a['job']]['status'] = 'parked'
            reg.event(state, 'worker_capacity_parked', key, generation=lane['generation'], evidence=outcome['evidence'])
            result.append(key)
    return result
