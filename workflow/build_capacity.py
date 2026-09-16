"""RAM-aware build admission; preparation never consumes an execution lease."""
import math

from .handoff import require


def admission_paused(state, now):
    policy = state.get('build_capacity', {})
    return bool(policy.get('enabled') and (policy.get('paused', True) or
        now - policy.get('observed_at', 0) > policy.get('sample_ttl', 60)))


def update(controller):
    config = controller.config.get('build_capacity', {})
    if not config.get('enabled'):
        return
    base, maximum = config.get('base', 2), config.get('maximum', 4)
    require(type(base) is int and type(maximum) is int and 1 <= base <= maximum <= 8,
            'Invalid build capacity bounds')
    ram = controller.memory()
    require(type(ram) in (int, float) and math.isfinite(ram) and 0 <= ram <= 100,
            'Fresh RAM observation required')
    reg = controller.reg
    with reg.transaction() as state:
        now = reg.clock()
        policy = state.setdefault('build_capacity', {})
        old = state['settings']['max_heavy_builds']
        pool = state.get('throughput', {})
        assignments = [a for a in pool.get('assignments', {}).values()
                       if a['status'] in ('assigned', 'dispatched')]
        busy = {a['worker_id'] for a in assignments}
        idle = any(w not in busy for w in pool.get('workers', {}))
        waiting = any(reg.heavy(q['resource']) and reg.probe(q['process']) != 'dead'
                      for q in state['queue'].values())
        preparing = sum(a.get('heavy', False) and
                        state['lanes'][a['lane']]['state'] not in ('blocked', 'done', 'handoff_ready', 'review_ready')
                        for a in assignments)
        paused = policy.get('paused', False)
        if ram >= 87: paused = True
        elif ram <= 82: paused = False
        target = min(maximum, max(base, old))
        if paused:
            target = base
        elif now - policy.get('changed_at', 0) >= config.get('ramp_seconds', 60):
            if ram < 80 and (waiting or (idle and preparing >= old)):
                target = min(maximum, target + 1)
            elif not waiting and preparing + int(idle) < old:
                target = max(base, preparing + int(idle))
        if target != old:
            reg.event(state, 'build_capacity_changed', None, previous=old, capacity=target, ram_percent=ram)
            policy['changed_at'] = now
        state['settings']['max_heavy_builds'] = target
        policy.update(enabled=True, lease_only=True, base=base, maximum=maximum,
                      observed_at=now, sample_ttl=60, ram_percent=ram, paused=paused)
