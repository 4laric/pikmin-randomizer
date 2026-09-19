"""Observed pipeline transitions. Ages are lower bounds, never invented history."""
from .control import fingerprint


def stages(state):
    result = {}
    launches = {l['lane']: l for l in state.get('control', {}).get('launches', {}).values()
                if l.get('status') in ('intent', 'spawned', 'running', 'exiting')}
    building = {l.get('lane') for r,l in state.get('leases', {}).items()
                if r.startswith('build:') or r == 'maintained-build-export'}
    verifying = {v['consumer'] for v in state.get('consumer_verifications', {}).values()
                 if v['status'] == 'pending'}
    for key, lane in state.get('lanes', {}).items():
        status = lane.get('state')
        if status is None or status == 'done': continue
        if key in building: stage = 'build'
        elif status == 'waiting_resource': stage = 'resource wait'
        elif status == 'blocked': stage = 'dependency'
        elif status == 'integrating': stage = 'integration'
        elif status in ('handoff_ready', 'review_ready'): stage = 'review'
        elif key in launches and launches[key]['status'] in ('intent', 'spawned'): stage = 'launch'
        elif status == 'running': stage = 'consumer verification' if key in verifying else 'execution'
        else: stage = 'assignment'
        result[key] = dict(stage=stage, generation=lane.get('generation'), reason=lane.get('next_action'))
    for item in state.get('throughput_runtime', {}).get('autofill', {}).get('items', {}).values():
        key = item.get('lane')
        if key and key not in state.get('lanes', {}) and item.get('status') != 'completed':
            result[key] = dict(stage='assignment' if item.get('ready') else 'preparation',
                               generation=None, reason=item.get('reason'))
    return result


def observe(reg):
    snapshot = reg.snapshot()
    current = stages(snapshot)
    signature = fingerprint(current)
    if snapshot.get('stage_timing', {}).get('signature') == signature: return
    with reg.transaction() as state:
        current = stages(state)
        ledger = state.setdefault('stage_timing', dict(current={}, history=[]))
        now = reg.clock()
        for key, old in list(ledger['current'].items()):
            new = current.get(key)
            if new is None or (new['stage'],new['generation']) != (old['stage'],old['generation']):
                ledger['history'].append(dict(lane=key, **old, ended_at=now,
                    duration_seconds=max(0, now-old['observed_since'])))
                del ledger['current'][key]
        for key, value in current.items():
            ledger['current'].setdefault(key, dict(value, observed_since=now)).update(value)
        ledger['history'] = [h for h in ledger['history'] if h['ended_at'] >= now-86400]
        ledger.update(signature=fingerprint(current), observed_at=now)


def metrics(state, now):
    ledger = state.get('stage_timing', {})
    rows = []
    # Suppress stale stage observations rather than showing a completed lane as stuck.
    current = stages(state)
    for key, item in ledger.get('current', {}).items():
        live = current.get(key)
        if not live or (live['stage'],live['generation']) != (item['stage'],item['generation']): continue
        age = max(0, now-item['observed_since'])
        budget = 120 if item['stage'] in ('assignment','launch') else 900
        rows.append(dict(lane=key, **item, age_seconds=age, needs_attention=age >= budget))
    durations = {}
    for h in ledger.get('history', []):
        if h['ended_at'] < now-3600: continue
        durations.setdefault(h['stage'], []).append(h['duration_seconds'])
    return dict(basis='Observed stage residence; initial ages are lower bounds. Age alone never authorizes restart.',
                current=sorted(rows, key=lambda r:r['age_seconds'], reverse=True),
                completed_last_hour={k:dict(count=len(v), mean_seconds=sum(v)/len(v), max_seconds=max(v))
                                     for k,v in durations.items()})


def alert(reg):
    sent = getattr(reg, '_stage_alerts', set())
    reg._stage_alerts = sent
    for row in metrics(reg.snapshot(), reg.clock())['current']:
        if not row['needs_attention'] or row['stage'] in ('execution','build','dependency','resource wait'): continue
        identity = (row['lane'],row['generation'],row['stage'],row['observed_since'])
        if identity in sent: continue
        reg.notice(row['lane'], 'stage_wait_exceeded', dict(stage=row['stage'],generation=row['generation'],
            observed_since=row['observed_since'],instruction='Inspect concrete queue/review/consumer evidence; age alone does not authorize restart.'))
        sent.add(identity)
