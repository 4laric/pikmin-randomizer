"""Observed queue pressure, not a claim of CPU use or forecast certainty."""
import copy
import hashlib
import json
from .control import fingerprint


def dependents(lanes, key, issue):
    return sum(v.get('state')!='done' and (key in v.get('dependencies',[]) or
               '#'+str(issue) in v.get('dependencies',[])) for v in lanes.values())


def integration_items(lanes, bucket=None, buckets=2):
    result=[]
    for key,v in lanes.items():
        if v.get('state') not in ('handoff_ready','integrating'):continue
        if bucket is not None and int(hashlib.sha256(key.encode()).hexdigest(),16)%buckets!=bucket:continue
        result.append(dict(lane=key,issue=v.get('issue'),handoff=v.get('handoff'),
                           root=v.get('root'),native=v.get('native'),
                           downstream=dependents(lanes,key,v.get('issue'))))
    return sorted(result,key=lambda x:(-x['downstream'],x['lane']))


def support_work(reg, helper):
    with reg.transaction() as s:
        lanes=copy.deepcopy(s['lanes'])
        seen=s.get('integration_support_reviewed',{})
        return [x for x in integration_items(lanes,helper['bucket'],helper.get('buckets',2))
                if fingerprint(x) not in seen][:3]


def update(controller):
    if not controller.config.get('queue_pressure',{}).get('enabled'):return
    reg=controller.reg;now=reg.clock()
    with reg.transaction() as s:
        lanes=copy.deepcopy(s['lanes'])
        prior=copy.deepcopy(s.get('queue_pressure',{}))
    stages={'integration':{},'runtime':{},'publication':{}}
    for k,v in lanes.items():
        if v.get('state') in ('handoff_ready','integrating'):
            stages['integration'][k]=v.get('handoff_at') or v.get('progress_at') or now
        if v.get('target_level')=='runtime' and v.get('state') in ('ready','running','waiting_resource','blocked'):
            stages['runtime'][k]=v.get('created_at') or now
    settings=controller.config.get('throughput',{}).get('autofill',{})
    if settings.get('manifest'):
        from .autofill import _private
        from .proposal_feedback import feedback
        published={x['id']:x for x in json.loads(_private(reg,settings['manifest']).read_text(encoding='utf-8-sig'))['items']}
        for path in (reg.root/'output/workflow/autofill/planning-shards').glob('*/proposals-*.json'):
            if feedback(reg,path):continue
            try:pending=any(published.get(x.get('id'))!=x for x in json.loads(path.read_text(encoding='utf-8-sig'))['items'])
            except (ValueError,KeyError,TypeError,AttributeError):pending=True
            if pending:stages['publication'][str(path)]=path.stat().st_mtime
    history=prior.get('history',[])
    last=history[-1] if history else None
    if not last or now-last['at']>=60:
        events={}
        for stage,items in stages.items():
            old=set(last['keys'][stage]) if last else set(items)
            gone=old-set(items)
            events[stage]=dict(arrivals=len(set(items)-old),departures=len(gone),
                completions=sum(lanes.get(k,{}).get('state')=='done' for k in gone) if stage!='publication' else 0)
        history.append(dict(at=now,keys={k:list(v) for k,v in stages.items()},events=events))
    history=[h for h in history if h['at']>=now-3600][-62:]
    duration=max(60,now-history[0]['at']);metrics={}
    for stage,items in stages.items():
        counts={kind:sum(h['events'][stage][kind] for h in history[1:]) for kind in ('arrivals','departures','completions')}
        age=max((max(0,now-t) for t in items.values()),default=0)
        fanout=sum(dependents(lanes,k,lanes[k].get('issue')) for k in items if k in lanes)
        metrics[stage]=dict(depth=len(items),oldest_seconds=age,downstream=fanout,
            **{k+'_per_hour':v*3600/duration for k,v in counts.items()},
            pressure=len(items)+min(age/300,12)+fanout+2*max(0,counts['arrivals']-counts['departures']))
    result=dict(at=now,observed_seconds=duration,warming_up=duration<300,stages=metrics,history=history)
    with reg.transaction() as s:s['queue_pressure']=result
    from .runner import write
    write(controller.base/'queue-pressure.json',{k:v for k,v in result.items() if k!='history'})
