"""RAM-aware build admission; preparation never consumes an execution lease."""
import math
import threading

from .handoff import require


def thresholds(controller):
    config = controller.config.get('build_capacity', {})
    high = config.get('ram_high', 87)
    low = config.get('ram_low', 82)
    growth = config.get('ram_growth', 80)
    ceiling = controller.config.get('ram_high', 90)
    require(all(type(v) in (int, float) and math.isfinite(v)
                for v in (growth, low, high, ceiling)) and
            0 < growth <= low < high <= 100 and 0 < ceiling <= 100,
            'Invalid RAM capacity thresholds')
    return high, low, growth, ceiling


def admission_paused(state, now):
    policy = state.get('build_capacity', {})
    return bool(policy.get('enabled') and (policy.get('paused', True) or
        now - policy.get('observed_at', 0) > policy.get('sample_ttl', 60)))


def sample(controller):
    ram = controller.memory()
    require(type(ram) in (int, float) and math.isfinite(ram) and 0 <= ram <= 100,
            'Fresh RAM observation required')
    return ram


def refresh_observation(controller):
    """Short independent heartbeat: no scheduling, process probes or dispatch; meta row only."""
    if not controller.config.get('build_capacity', {}).get('enabled'): return
    high, low, growth, ceiling = thresholds(controller)
    with controller.reg.transaction(sections=()) as state:
        ram = sample(controller)  # Sampled under the writer lock, so commits are in sample order.
        observed_at = controller.reg.clock()
        policy = state.setdefault('build_capacity', {})
        if policy.get('observed_at', 0) > observed_at: return
        paused = policy.get('paused', False)
        if ram >= high: paused = True
        elif ram <= low: paused = False
        policy.update(enabled=True, lease_only=True, observed_at=observed_at,
                      sample_ttl=60, ram_percent=ram, paused=paused,
                      ram_high=high, ram_low=low, ram_growth=growth)
        state['settings']['ram_ceiling_percent'] = ceiling


def start_monitor(controller):
    """Adjust capacity independently of slow scheduling and provider operations.

    update() serializes the ramp timestamp with the main tick in the registry;
    this monitor never grants leases, launches workers, or runs a scheduler tick.
    """
    stop = threading.Event()
    def monitor():
        while not stop.is_set():
            try:
                update(controller)
            except Exception:
                # Failed measurements do not refresh the timestamp: admission fails closed.
                pass
            stop.wait(15)
    thread = threading.Thread(target=monitor, name='build-capacity-monitor', daemon=True)
    thread.start()
    return stop


def update(controller):
    """Pool occupancy is read outside the writer; RAM is sampled and leases/queue reread under it."""
    config = controller.config.get('build_capacity', {})
    if not config.get('enabled'):
        return
    high, low, growth, ceiling = thresholds(controller)
    base, maximum = config.get('base', 2), config.get('maximum', 4)
    require(type(base) is int and type(maximum) is int and 1 <= base <= maximum <= 8,
            'Invalid build capacity bounds')
    sample(controller)  # Fail before any registry work when RAM cannot be read.
    reg = controller.reg
    seen = reg.snapshot(sections=[('lanes',), ('leases',), ('queue',), ('throughput', 'assignments'),
                                  ('throughput', 'workers')])
    pool = seen.get('throughput', {})
    assignments = [a for a in pool.get('assignments', {}).values()
                   if a['status'] in ('assigned', 'dispatched')]
    busy = {a['worker_id'] for a in assignments}
    idle = any(w not in busy for w in pool.get('workers', {}))
    preparing = sum(a.get('heavy', False) and
                    seen['lanes'][a['lane']]['state'] not in ('blocked', 'done', 'handoff_ready', 'review_ready')
                    for a in assignments)
    def waiters(queue):
        return any(reg.heavy(q['resource']) and reg.probe(q['process']) != 'dead' for q in queue.values())
    waiting = waiters(seen['queue'])
    dead = any(reg.heavy(r) and reg.probe(l['process']) == 'dead' for r, l in seen['leases'].items())
    with reg.transaction(sections=[('leases',), ('queue',)], append=[('events',)]) as state:
        # Sampled under the writer lock: a slower writer can never commit an older sample.
        ram = sample(controller)
        now = reg.clock()
        policy = state.setdefault('build_capacity', {})
        if policy.get('observed_at', 0) > now: return
        if dead or state['leases'] != seen['leases']:
            reg.reap_dead_build_leases(state)
        else:
            state['build_lease_recovery'] = dict(at=now, released=[],
                remaining=sum(reg.heavy(k) for k in state['leases']))
        if state['queue'] != seen['queue']:
            waiting = waiters(state['queue'])
        old = state['settings']['max_heavy_builds']
        paused = policy.get('paused', False)
        if ram >= high: paused = True
        elif ram <= low: paused = False
        target = min(maximum, max(base, old))
        if paused:
            target = base
        elif now - policy.get('changed_at', 0) >= config.get('ramp_seconds', 60):
            if ram < growth and (waiting or (idle and preparing >= old)):
                target = min(maximum, target + 1)
            elif not waiting and preparing + int(idle) < old:
                target = max(base, preparing + int(idle))
        if target != old:
            reg.event(state, 'build_capacity_changed', None, previous=old, capacity=target, ram_percent=ram)
            policy['changed_at'] = now
        state['settings']['max_heavy_builds'] = target
        policy.update(enabled=True, lease_only=True, base=base, maximum=maximum,
                      observed_at=now, sample_ttl=60, ram_percent=ram, paused=paused,
                      ram_high=high, ram_low=low, ram_growth=growth)
        state['settings']['ram_ceiling_percent'] = ceiling
