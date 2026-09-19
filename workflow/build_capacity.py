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


def refresh_observation(controller):
    """Short independent heartbeat: no scheduling, process probes or dispatch."""
    if not controller.config.get('build_capacity', {}).get('enabled'): return
    high, low, growth, ceiling = thresholds(controller)
    ram = controller.memory()
    require(type(ram) in (int, float) and math.isfinite(ram) and 0 <= ram <= 100,
            'Fresh RAM observation required')
    observed_at = controller.reg.clock()
    with controller.reg.transaction() as state:
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
    config = controller.config.get('build_capacity', {})
    if not config.get('enabled'):
        return
    high, low, growth, ceiling = thresholds(controller)
    base, maximum = config.get('base', 2), config.get('maximum', 4)
    require(type(base) is int and type(maximum) is int and 1 <= base <= maximum <= 8,
            'Invalid build capacity bounds')
    ram = controller.memory()
    require(type(ram) in (int, float) and math.isfinite(ram) and 0 <= ram <= 100,
            'Fresh RAM observation required')
    reg = controller.reg
    with reg.transaction() as state:
        now = reg.clock()
        reg.reap_dead_build_leases(state)
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
