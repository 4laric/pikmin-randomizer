"""Observed queue pressure, not a claim of CPU use or forecast certainty."""
import copy
import hashlib
import json
from .control import fingerprint


def dependents(lanes, key, issue):
    return sum(v.get('state')!='done' and (key in v.get('dependencies',[]) or
               '#'+str(issue) in v.get('dependencies',[])) for v in lanes.values())


def integration_items(lanes, bucket=None, buckets=2, batches=None):
    from .batching import isolated_handoff
    result=[]
    for key,v in lanes.items():
        if v.get('state') not in ('handoff_ready','integrating'):continue
        if isolated_handoff(batches or {}, key, v):continue
        if bucket is not None and int(hashlib.sha256(key.encode()).hexdigest(),16)%buckets!=bucket:continue
        result.append(dict(lane=key,generation=v.get('generation'),issue=v.get('issue'),handoff=v.get('handoff'),
                           root=v.get('root'),native=v.get('native'),
                           downstream=dependents(lanes,key,v.get('issue'))))
    return sorted(result,key=lambda x:(-x['downstream'],x['lane']))


def support_work(reg, helper):
    with reg.transaction() as s:
        lanes=copy.deepcopy(s['lanes'])
        seen=s.get('integration_support_reviewed',{})
        return [x for x in integration_items(lanes,helper['bucket'],helper.get('buckets',2),
                    s.get('throughput',{}).get('batches',{}))
                if fingerprint(x) not in seen or
                (helper.get('mode') == 'preparation' and seen[fingerprint(x)].get('mode') != 'preparation')][:3]


def support_allocations(reg, helpers, records, dynamic=False, actionable=False):
    """One distinct candidate per free slot; retain in-flight ownership unchanged."""
    slots=[h for h in helpers if h.get('kind')=='integration_support']
    if not dynamic:return {h['scope']:support_work(reg,h) for h in slots}
    state=reg.snapshot();seen=state.get('integration_support_reviewed',{})
    result={h['scope']:[] for h in slots};reserved=set()
    for h in slots:
        record=records.get(h['scope'],{})
        if record and 'completed_at' not in record:
            result[h['scope']]=record.get('support_targets',[])
            reserved.update(t['lane'] for t in result[h['scope']])
    candidates=integration_items(state['lanes'],batches=state.get('throughput',{}).get('batches',{}))
    if actionable:
        from .support_actions import extra_targets
        candidates += extra_targets(reg,state)
        # Legacy preparation reports do not satisfy the new action contract.
        for target in candidates:target['action_contract']=1
    candidates.sort(key=lambda t:(0 if t.get('kind')=='export_preparation' else 1,
        -t['downstream'],state['lanes'][t['lane']].get('handoff_at') or float('inf'),t['lane']))
    for h in sorted(slots,key=lambda h:records.get(h['scope'],{}).get('started_at',0)):
        if result[h['scope']]:continue
        record=records.get(h['scope'],{})
        if record and 'completed_at' not in record:continue
        for target in candidates:
            if target.get('kind')=='export_preparation' and h.get('mode')!='preparation':continue
            if target['lane'] in reserved:continue
            prior=seen.get(fingerprint(target))
            if prior and (h.get('mode')!='preparation' or prior.get('mode')=='preparation'):continue
            if record.get('support_snapshot')==fingerprint([target]):continue
            result[h['scope']]=[target];reserved.add(target['lane']);break
    return result


def update(controller):
    if not controller.config.get('queue_pressure',{}).get('enabled'):return
    reg=controller.reg;now=reg.clock()
    s=reg.snapshot(sections=[('lanes',),('throughput','batches')])
    lanes=s['lanes']
    prior=s.get('queue_pressure',{})
    batches=s.get('throughput',{}).get('batches',{})
    from .batching import isolated_handoff, handoff_repairs
    stages={'integration':{},'runtime':{},'publication':{},'repair':{}}
    stages['repair'] = {r['lane']:now-r['age_seconds'] for r in
                        handoff_repairs({'lanes':lanes,'throughput':{'batches':batches}},now)}
    for k,v in lanes.items():
        if v.get('state') in ('handoff_ready','integrating'):
            stage='repair' if isolated_handoff(batches,k,v) else 'integration'
            stages[stage][k]=v.get('handoff_at') or v.get('progress_at') or now
        if v.get('target_level')=='runtime' and v.get('state') in ('ready','running','waiting_resource','blocked'):
            stages['runtime'][k]=v.get('created_at') or now
    settings=controller.config.get('throughput',{}).get('autofill',{})
    if settings.get('manifest'):
        from .autofill import _private
        from .proposal_feedback import feedback
        published={x['id']:x for x in json.loads(_private(reg,settings['manifest']).read_text(encoding='utf-8-sig'))['items']}
        for path in (reg.root/'output/workflow/autofill/planning-shards').glob('*/proposals-*.json'):
            if feedback(reg,path,state=s):continue
            try:pending=any(published.get(x.get('id'))!=x for x in json.loads(path.read_text(encoding='utf-8-sig'))['items'])
            except (ValueError,KeyError,TypeError,AttributeError):pending=True
            if pending:stages['publication'][str(path)]=path.stat().st_mtime
    history=prior.get('history',[])
    last=history[-1] if history else None
    if not last or now-last['at']>=60:
        events={}
        for stage,items in stages.items():
            old=set(last['keys'].get(stage,[])) if last else set(items)
            gone=old-set(items)
            events[stage]=dict(arrivals=len(set(items)-old),departures=len(gone),
                completions=sum(lanes.get(k,{}).get('state')=='done' for k in gone) if stage!='publication' else 0)
        history.append(dict(at=now,keys={k:list(v) for k,v in stages.items()},events=events))
    history=[h for h in history if h['at']>=now-3600][-62:]
    duration=max(60,now-history[0]['at']);metrics={}
    for stage,items in stages.items():
        counts={kind:sum(h['events'].get(stage,{}).get(kind,0) for h in history[1:]) for kind in ('arrivals','departures','completions')}
        age=max((max(0,now-t) for t in items.values()),default=0)
        fanout=sum(dependents(lanes,k,lanes[k].get('issue')) for k in items if k in lanes)
        metrics[stage]=dict(depth=len(items),oldest_seconds=age,downstream=fanout,
            **{k+'_per_hour':v*3600/duration for k,v in counts.items()},
            pressure=len(items)+min(age/300,12)+fanout+2*max(0,counts['arrivals']-counts['departures']))
    result=dict(at=now,observed_seconds=duration,warming_up=duration<300,stages=metrics,history=history)
    # Meta row only; an observation never replaces a newer one.
    with reg.transaction(sections=()) as s:
        if s.get('queue_pressure',{}).get('at',0)>now:return
        s['queue_pressure']=result
    from .runner import write
    write(controller.base/'queue-pressure.json',{k:v for k,v in result.items() if k!='history'},durable=False)

def start_monitor(controller):
    """Single pressure sampler independent of the main reconciliation pass."""
    import threading
    import time
    from .runner import write
    existing=getattr(controller,'_pressure_monitor',None)
    if existing is not None:return existing
    stop=threading.Event();controller._pressure_monitor=stop
    def monitor():
        while not stop.is_set():
            started=time.monotonic()
            try:
                update(controller)
                write(controller.base/'queue-pressure-monitor.json',dict(at=controller.reg.clock(),elapsed_seconds=time.monotonic()-started),durable=False)
            except Exception as exc:
                write(controller.base/'queue-pressure-error.json',dict(at=controller.reg.clock(),error=str(exc)))
            stop.wait(max(1,30-(time.monotonic()-started)))
    threading.Thread(target=monitor,name='queue-pressure',daemon=True).start()
    return stop
