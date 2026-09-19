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


SECTIONS = [('lanes',), ('leases',), ('queue',), ('control', 'launches'), ('throughput', 'workstreams'),
            ('throughput', 'workers'), ('throughput', 'assignments'), ('throughput', 'jobs')]


def parkable(reg, state, keys=None, hashed=None):
    """(lane key, dispatched/assigned rows) that may release their worker. Evidence is hashed
    only when hashed is None; otherwise it must equal the evidence hashed before the lock."""
    pool = reg.scheduling(state)
    owners = {s['owner_lane'] for s in pool['workstreams'].values()}
    launches = state.get('control', {}).get('launches', {})
    for key, lane in state['lanes'].items():
        if keys is not None and key not in keys: continue
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
        if hashed is None:
            try:
                reg.evidence(outcome.get('evidence'))
            except (Rejected, OSError, ValueError, TypeError):
                continue
        elif hashed.get(key) != outcome.get('evidence'):
            continue
        assignments = [a for a in pool['assignments'].values()
                       if a['lane'] == key and a['status'] in ('assigned', 'dispatched')]
        if any((launches.get(a.get('launch_id'), {}).get('bound_generation')
                if a['status'] == 'dispatched' else a.get('generation')) != lane['generation']
               for a in assignments):
            continue
        yield key, assignments


def park_blocked(reg):
    """Candidates and evidence hashes come from a committed read; the writer only rechecks them."""
    seen = reg.snapshot(sections=SECTIONS)
    hashed = {key: seen['lanes'][key]['outcome']['evidence'] for key, _ in parkable(reg, seen)}
    if not hashed:
        return []
    result = []
    with reg.transaction(sections=SECTIONS, append=[('events',)]) as state:
        pool = reg.scheduling(state)
        for key, assignments in list(parkable(reg, state, set(hashed), hashed)):
            lane = state['lanes'][key]
            evidence = lane['outcome']['evidence']
            lane['capacity_parked'] = dict(generation=lane['generation'], at=reg.clock(), evidence=evidence)
            for a in assignments:
                a.update(status='parked', parked_at=reg.clock(), evidence=evidence)
                pool['jobs'][a['job']]['status'] = 'parked'
            reg.event(state, 'worker_capacity_parked', key, generation=lane['generation'], evidence=evidence)
            result.append(key)
    return result
