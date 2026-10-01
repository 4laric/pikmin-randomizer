"""Assign distinct blocked inputs to spare planning partitions, once per input."""
import copy
import re
from .control import fingerprint
from .planner_demand import inputs, is_helper


def allocations(state, helpers, records, now, age_seconds=900, classify=False):
    from .delivery_recovery import allocations as delivery_allocations
    from .dependency_classification import allocations as classifications
    delivery = delivery_allocations(state, helpers, records)
    if classify:
        from .internal_followup import allocations as internal_allocations
        delivery = classifications(state, helpers, records, internal_allocations(state, helpers, records, delivery))
    data=state.get('throughput_runtime',{}).get('autofill',{})
    attempts=data.get('prerequisite_recovery',{})
    reserved=set()
    for entry in delivery.values():
        reserved.update(entry['request']['lanes'])
        reserved.update(entry['request'].get('followup_owner_lanes',[]))
    for helper in helpers:
        row=records.get(helper['scope'],{})
        if row and 'completed_at' not in row:
            reserved.update(row.get('recovery_targets',helper.get('prerequisite_lanes',[])))
            reserved.update(row.get('followup_owner_lanes',[]))
            reserved.update(t['lane'] for t in row.get('support_targets',[]))
    candidates=[]
    for key,lane in state['lanes'].items():
        outcome=lane.get('outcome') or {}
        if (lane['state']!='blocked' or is_helper(key) or key=='acceptance-backlog-planner' or
                key in reserved or outcome.get('outcome')!='blocked' or not outcome.get('evidence')):continue
        if now-max(lane.get('progress_at') or 0,lane.get('started_at') or 0)<max(300,age_seconds):continue
        deps=lane.get('dependencies',[])
        issues=sorted({int(n) for dep in deps for n in re.findall(r'#(\d+)\b',dep)})
        producers=[k for k,v in state['lanes'].items() if k!=key and not is_helper(k) and
                   (k in deps or v.get('issue') in issues)]
        if any(state['lanes'][k]['state'] in ('ready','running','waiting_resource','reconciling','handoff_ready','integrating')
               for k in producers):continue
        # The substantive signal alone: a new evidence file per no-op generation is not a new input.
        signal=inputs(state,issues,[key]+producers)
        identity=fingerprint(['blocked-recovery-v1',key,signal])
        raw=inputs(state,issues,[key]+producers,raw=True)  # Identities written before gen-marker normalization.
        for legacy in (fingerprint(['blocked-recovery-v1',key,raw]),
                       fingerprint(['blocked-recovery-v1',key,fingerprint([raw,outcome['evidence']])])):
            if identity not in attempts and legacy in attempts:identity=legacy
        match=re.match(r'shard-(enemies-\d+|caves-[a-z]+)-',key)
        affinity=match.group(1) if match and any(h['scope']==match.group(1) for h in helpers) else None
        previous=None
        if identity in attempts:
            previous=state['lanes'].get(attempts[identity].get('lane'),{})
            failed=previous.get('outcome') or {}
            if previous.get('state')!='done' or not failed.get('evidence'):continue
            actions=[a for a in state.get('support_actions',{}).values()
                     if a['reviewer']==attempts[identity].get('lane') and a['key']==key]
            if any(a['action'] in ('proposal','integration_packet','external') for a in actions):continue
            if any(a['action']=='producer' and state['lanes'].get(a['details'].get('lane'),{}).get('state')
                   in ('ready','running','waiting_resource','reconciling','handoff_ready','integrating') for a in actions):continue
            # One contract-corrected proposal turn, not a reset of the old budget.
            identity=fingerprint(['blocked-proposal-followup-v1',identity]+(['owner-partition',affinity] if affinity else []))
            if identity in attempts:continue
        downstream=sum(key in v.get('dependencies',[]) or any(
            re.search(r'#'+str(lane['issue'])+r'\b',d) for d in v.get('dependencies',[]))
            for v in state['lanes'].values() if v['state']!='done')
        request=dict(id=identity,status='blocked-recovery',report=copy.deepcopy(outcome['evidence']),
            lanes=[key],issues=[lane['issue']],blockers=[dict(lane=key,dependencies=deps,outcome=copy.deepcopy(outcome))])
        if previous:
            request['previous_recovery']=dict(lane=previous.get('lane'),outcome=copy.deepcopy(previous['outcome']))
        candidates.append((-downstream,lane.get('progress_at') or 0,key,
                           dict(key=identity,input_snapshot=signal,request=request,affinity=affinity)))
    candidates.sort(key=lambda x:x[:3])
    result=dict(delivery)
    for helper in sorted(helpers,key=lambda h:records.get(h['scope'],{}).get('started_at',0)):
        row=records.get(helper['scope'],{})
        if helper['scope'] in result:continue
        if helper.get('kind') or (row and 'completed_at' not in row):continue
        if not candidates:break
        eligible=[(i,c) for i,c in enumerate(candidates) if c[3]['affinity'] in (None,helper['scope'])]
        if not eligible:continue
        index=min(eligible,key=lambda pair:(pair[1][3]['affinity']!=helper['scope'],pair[1][:3]))[0]
        target=candidates.pop(index)[3];target['request']['scope']=helper['scope']
        result[helper['scope']]=target
    return result
