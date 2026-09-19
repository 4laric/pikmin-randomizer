"""Read-only throughput metrics. Missing observations remain unknown."""
import math

from .handoff import require


def finite_number(value, name, minimum=None):
    require(type(value) in (int, float) and math.isfinite(value), name + ' must be finite numeric')
    require(minimum is None or value >= minimum, name + ' below minimum')
    return value


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _heavy(resource):
    return isinstance(resource, str) and (resource.startswith('build:') or resource == 'maintained-build-export')


def _build_utilization(state, now, start):
    # A renewal/expiry is not release. Live leases remain counted until release/reap.
    events = sorted((e for e in state.get('events', []) if _number(e.get('at')) and e['at'] <= now), key=lambda e: e['at'])
    opened, intervals = {}, []
    for event in events:
        resource = event.get('resource')
        if not _heavy(resource):
            continue
        kind = event.get('kind')
        if kind == 'lease_acquired':
            if resource in opened:
                intervals.append((opened[resource], event['at']))
            opened[resource] = event['at']
        elif kind in ('lease_released', 'lease_reaped'):
            acquired = opened.pop(resource, None)
            if acquired is not None:
                intervals.append((acquired, event['at']))
    # Sparse event history can still account for actual current lease starts.
    for resource, lease in state.get('leases', {}).items():
        if _heavy(resource) and resource not in opened and _number(lease.get('acquired_at')):
            opened[resource] = lease['acquired_at']
    intervals.extend((begin, now) for begin in opened.values())
    seconds = sum(max(0, min(end, now) - max(begin, start)) for begin, end in intervals)
    cap = state.get('settings', {}).get('max_heavy_builds')
    denominator = (now - start) * cap if _number(cap) and cap > 0 else None
    changes = [e for e in events if e.get('kind') == 'build_capacity_changed']
    if changes:
        current, cursor, denominator = changes[0]['previous'], start, 0
        for event in changes:
            if event['at'] > start:
                denominator += (event['at'] - cursor) * current
                cursor = event['at']
            current = event['capacity']
        denominator += (now - cursor) * current
    return dict(leased_seconds=seconds, capacity_slots=cap,
                utilization_percent=100 * seconds / denominator if denominator else None,
                basis='recorded lease intervals; reservation time, not CPU use')


def throughput_metrics(state, now, window_seconds=3600):
    from .batching import handoff_repairs
    finite_number(now, 'now', minimum=0)
    finite_number(window_seconds, 'window_seconds', minimum=1)
    start = now - window_seconds
    lanes = state.get('lanes', {})
    repairs = handoff_repairs(state, now)
    repair_keys = {r['lane'] for r in repairs}
    # A review acknowledgement is not an accepted implementation slice.
    accepted = {key for key, lane in lanes.items() if lane.get('integration') and
                _number(lane.get('integrated_at')) and start < lane['integrated_at'] <= now}
    accepted.update(e['lane'] for e in state.get('events', []) if e.get('kind') == 'integrated' and
                    isinstance(e.get('lane'), str) and _number(e.get('at')) and start < e['at'] <= now)
    owners = {s.get('owner_lane') for s in state.get('throughput', {}).get('workstreams', {}).values()}
    parked_reports = [key for key in owners if lanes.get(key, {}).get('state') == 'review_ready'
                      and not lanes[key].get('handoff')]
    handoffs = [dict(lane=key, age_seconds=max(0, now - lane['handoff_at'])) for key, lane in lanes.items()
                if key not in parked_reports and key not in repair_keys and lane.get('state') in ('handoff_ready', 'review_ready', 'integrating')
                and _number(lane.get('handoff_at'))]
    dependency_waits = []
    for key, lane in lanes.items():
        if lane.get('state') not in ('ready', 'blocked', 'waiting_resource'):
            continue
        ready_at = lane.get('dependency_ready_at')
        dependencies = lane.get('dependencies', [])
        if not _number(ready_at) and dependencies and all(
                d in lanes and lanes[d].get('state') == 'done' and _number(lanes[d].get('integrated_at')) for d in dependencies):
            ready_at = max(lanes[d]['integrated_at'] for d in dependencies)
        if _number(ready_at) and ready_at <= now:
            dependency_waits.append(dict(lane=key, ready_at=ready_at, wait_seconds=max(0, now-ready_at)))
    costs = state.get('throughput', {}).get('costs', {})
    values = costs.values() if isinstance(costs, dict) else costs
    recorded, coverage = {}, set()
    for item in values:
        if not isinstance(item, dict) or not _number(item.get('amount')) or item['amount'] < 0:
            continue
        if not _number(item.get('at')) or not start < item['at'] <= now:
            continue
        currency = item.get('currency')
        if not isinstance(currency, str):
            continue
        recorded[currency] = recorded.get(currency, 0) + item['amount']
        if item.get('lane') in accepted:
            coverage.add(item['lane'])
    missing = sorted(accepted - coverage)
    from .consumer_verification import metrics as consumer_metrics
    from .stage_timing import metrics as stage_metrics
    from .recurring_failures import groups as recurring_groups
    from .no_progress import parked
    return dict(window_seconds=window_seconds, accepted_slices=len(accepted),
                no_progress_parked=parked(state, now),
                stage_timing=stage_metrics(state, now),
                recurring_failures=recurring_groups(state),
                consumer_verification=consumer_metrics(state,now,window_seconds),
                accepted_slices_per_hour=len(accepted)*3600/window_seconds,
                oldest_handoff=max(handoffs, key=lambda x:x['age_seconds']) if handoffs else None,
                parked_integration_reports=parked_reports,
                blocked_handoff_repairs=repairs,
                dependency_ready_waits=sorted(dependency_waits, key=lambda x:x['wait_seconds'], reverse=True),
                heavy_build=_build_utilization(state, now, start),
                costs=dict(recorded_by_currency=recorded, accepted_lanes_missing_cost=missing,
                           cost_per_accepted_slice={c: amount/len(accepted) for c, amount in recorded.items()} if accepted and not missing else None,
                           coverage='partial' if missing else 'recorded' if recorded else 'unknown',
                           basis='reported spend in window / integrated implementation slices; unreported spend unknown'))


def staffing_recommendations(state, now, ram_percent=None, ram_ceiling_percent=None, *, process_probe=None):
    if ram_ceiling_percent is None:
        ram_ceiling_percent = state.get('settings', {}).get('ram_ceiling_percent', 90)
    finite_number(now, 'now', minimum=0)
    finite_number(ram_ceiling_percent, 'ram_ceiling_percent', minimum=0)
    require(ram_ceiling_percent <= 100, 'RAM ceiling exceeds 100')
    if ram_percent is not None:
        finite_number(ram_percent, 'ram_percent', minimum=0)
        require(ram_percent <= 100, 'RAM percentage exceeds 100')
    jobs = state.get('throughput', {}).get('jobs', {})
    jobs = jobs.values() if isinstance(jobs, dict) else jobs
    if process_probe is None:
        from .processes import probe as process_probe
    ready, roles, heavy_ready = {}, {}, {}
    ready_jobs = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        role = job.get('role', 'implementation')
        lane = state.get('lanes', {}).get(job.get('lane'), {})
        status = job.get('status', job.get('state'))
        if status in ('queued', 'ready') and not lane.get('dependencies') and not job.get('dependencies'):
            ready[role] = ready.get(role, 0) + 1
            heavy_ready[role] = heavy_ready.get(role, 0) + int(job.get('heavy', False))
            ready_jobs.append(job)
        elif status in ('assigned', 'dispatched', 'claimed', 'running'):
            roles[role] = roles.get(role, 0) + 1
    heavy_leases = [lease for resource, lease in state.get('leases', {}).items() if _heavy(resource)]
    leased_lanes = {lease.get('lane') for lease in heavy_leases}
    from .scheduling import pending_heavy_lanes
    reservations = pending_heavy_lanes(state, state.get('throughput', {}), process_probe)
    lease_only = state.get('build_capacity', {}).get('lease_only', False)
    occupied = len(heavy_leases) + (0 if lease_only else len(reservations - leased_lanes))
    cap = state.get('settings', {}).get('max_heavy_builds', 0)
    slots = max(0, cap - occupied) if _number(cap) else None
    from .build_capacity import admission_paused
    paused = admission_paused(state, now)
    policy = state.get('build_capacity', {})
    pause_reason = ('RAM pressure' if policy.get('paused') else 'RAM observation expired') if paused else None
    unoccupied = slots
    if paused: slots = 0
    recommendations = []
    for role, count in sorted(ready.items()):
        action = 'staff'
        reason = 'Ready bounded assignments can use additional workers'
        if ram_percent is None:
            action, reason = 'measure', 'RAM observation required before automatic dispatch'
        elif ram_percent >= ram_ceiling_percent:
            action, reason = 'wait_ram', 'RAM is at or above dispatch ceiling'
        elif not lease_only and heavy_ready.get(role, 0) == count and slots == 0:
            action, reason = 'prepare', 'Heavy slots occupied; prepare work while builds finish'
        recommendations.append(dict(role=role, ready_jobs=count, ready_heavy_jobs=heavy_ready.get(role, 0),
                                    active_jobs=roles.get(role, 0), action=action, reason=reason))
    workers = state.get('throughput', {}).get('workers', {})
    workers = workers.values() if isinstance(workers, dict) else workers
    assignments = state.get('throughput', {}).get('assignments', {})
    assignments = assignments.values() if isinstance(assignments, dict) else assignments
    busy = {a.get('worker_id') for a in assignments if a.get('status') in ('assigned', 'dispatched')}
    idle_workers = []
    for worker in workers:
        worker_id = worker.get('worker_id')
        if worker_id in busy:
            continue
        owned = [lane for lane in state.get('lanes', {}).values() if lane.get('worker_id') == worker_id]
        if owned and any(lane.get('state') != 'done' or process_probe(lane.get('process', {})) != 'dead'
                         for lane in owned):
            continue
        idle_workers.append(worker)
    idle_roles = {}
    for worker in idle_workers:
        for role in worker.get('roles', []):
            idle_roles[role] = idle_roles.get(role, 0) + 1
    unmatched = []
    compatible_ids = set()
    for job in ready_jobs:
        compatible = [w for w in idle_workers if job.get('role') in w.get('roles', []) and
                      set(job.get('capabilities', [])) <= set(w.get('capabilities', [])) and
                      (not job.get('worker_id') or job.get('worker_id') == w.get('worker_id'))]
        compatible_ids.update(w.get('worker_id') for w in compatible)
        if not compatible:
            unmatched.append(dict(job=job.get('id'), lane=job.get('lane'), role=job.get('role'),
                                  capabilities=job.get('capabilities', []), reason='No idle compatible worker'))
    return dict(ram_percent=ram_percent, ram_ceiling_percent=ram_ceiling_percent, heavy_slots_available=slots,
                heavy_leases=len(heavy_leases), heavy_capacity=cap,
                heavy_preparing_lanes=len(reservations - leased_lanes), build_admission_paused=paused,
                heavy_slots_unoccupied=unoccupied, build_admission_pause_reason=pause_reason,
                idle_workers=len(idle_workers), idle_worker_roles=idle_roles,
                compatible_idle_workers=len(compatible_ids),
                unmatched_ready_jobs=unmatched,
                recommendations=recommendations)
