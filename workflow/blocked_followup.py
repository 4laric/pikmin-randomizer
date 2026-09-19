"""Turn evidence-backed blocked consumers into concrete preparation demand."""
import copy
from .control import fingerprint
from .handoff import Rejected, require
from .planner_demand import is_helper


def tick(controller):
    reg = controller.reg
    settings = controller.config.get('throughput', {}).get('autofill', {})
    key = settings.get('planner_lane')
    if not settings.get('enabled') or not key or key not in controller.config['lanes']: return
    with reg.transaction() as state: state = copy.deepcopy(state)
    owner = state['lanes'].get(key, {})
    if owner.get('state') not in ('blocked', 'ready', 'reconciling'): return
    launches = list(state.get('control', {}).get('launches', {}).values())
    active = [x for x in launches if x['lane'] == key and x['status'] in ('intent','spawned','running','exiting')]
    pending = active[0] if len(active) == 1 and active[0]['status'] == 'intent' else None
    if active and (not pending or pending.get('process') or pending.get('blocked_followup_ids') or
                   controller.launch_directory(pending['id']).exists()): return
    if not reg.recovery_safe(state, owner) or not controller.available(key): return
    candidates = []
    from .recurring_failures import groups as recurring_groups
    recurring_consumers = set()
    for group in recurring_groups(state):
        names = [c['lane'] for c in group['consumers']]
        if any(not reg.recovery_safe(state,state['lanes'][n]) or
               any(x['lane']==n and x['status'] in ('intent','spawned','running','exiting') for x in launches)
               for n in names): continue
        if any(state['lanes'].get(p,{}).get('state') in ('ready','running','waiting_resource','handoff_ready','integrating')
               for n in names for p in state.get('blocked_producer_links',{}).get(n,{}).get('producers',[])): continue
        try:
            for consumer in group['consumers']: reg.evidence(consumer['evidence'])
        except (Rejected,OSError,ValueError): continue
        recurring_consumers.update(names)
        attempts = sum(group['id'] in x.get('blocked_followup_ids',[]) for x in launches)
        if attempts < 2: candidates.append(dict(group,attempt=attempts+1))
    from .consumer_verification import repairs
    groups = repairs(state)
    grouped_consumers=set()
    for group in groups:
        names=[c['lane'] for c in group['consumers']]
        if set(names) & recurring_consumers: continue
        if any(not reg.recovery_safe(state,state['lanes'][n]) or
               any(x['lane']==n and x['status'] in ('intent','spawned','running','exiting') for x in launches) for n in names): continue
        # Preserve real active replacement owners and their source claims.
        if any(state['lanes'].get(p,{}).get('state') in ('ready','running','waiting_resource','handoff_ready','integrating')
               for n in names for p in state.get('blocked_producer_links',{}).get(n,{}).get('producers',[])): continue
        grouped_consumers.update(names)
        attempts=sum(group['id'] in x.get('blocked_followup_ids',[]) for x in launches)
        if attempts>=2: continue
        try:
            for c in group['consumers']: reg.evidence(c['evidence'])
        except (Rejected,OSError,ValueError): continue
        candidates.append(dict(group,attempt=attempts+1,
            summary='Integrated prerequisite has no verified consumer unblock. Reproduce these checks; '
            'reuse/reopen the existing producer scope through a private repair job after ownership checks. '
            'Do not rewrite historical integration receipts or create another contract-only provider.'))
    for name, lane in sorted(state['lanes'].items(), key=lambda x:x[1].get('progress_at',0)):
        if name in grouped_consumers or name in recurring_consumers: continue
        if name == key or lane['state'] != 'blocked' or is_helper(name) or lane.get('handoff'): continue
        if reg.clock() - lane.get('progress_at', reg.clock()) < 300: continue
        if any(x['lane'] == name and x['status'] in ('intent','spawned','running','exiting') for x in launches): continue
        if not reg.recovery_safe(state,lane): continue
        evidence = (lane.get('outcome') or {}).get('evidence')
        if not evidence: continue
        dependencies = lane.get('dependencies', [])
        linked=state.get('blocked_producer_links', {}).get(name, {})
        if linked.get('source_pins') == {k:(lane.get(k) or {}).get('head') for k in ('root','native')}:
            dependencies = dependencies + linked.get('producers', [])
        if any(state['lanes'].get(d, {}).get('state') in ('ready','running','waiting_resource','handoff_ready','integrating') for d in dependencies): continue
        identity = fingerprint([name, (lane.get('root') or {}).get('head'),
                                (lane.get('native') or {}).get('head'), evidence] +
                               (['game-runtime-proof-v1'] if lane.get('target_level')=='runtime' else []))
        attempts = sum(identity in x.get('blocked_followup_ids', []) for x in launches)
        if attempts >= 2: continue
        try: reg.evidence(evidence)
        except (Rejected,OSError,ValueError): continue
        candidates.append(dict(id=identity,attempt=attempts+1,lane=name,issue=lane.get('issue'),
            summary=lane.get('next_action'),dependencies=dependencies,evidence=evidence))
    # Give every stranded consumer a first attempt before retrying old referrals.
    candidates = sorted(candidates, key=lambda item:item['attempt'])[:3]
    if not candidates: return
    try:
        instruction = ('BLOCKED PRODUCER FOLLOW-UP: these stopped consumers have verified blocker evidence but '
            'no directly recorded active input producer. This demand is independent of planner no-work '
            'reports. For each, inspect the evidence and canonical source/ownership. Reuse actual live '
            'producers and record exact lane links. Otherwise prepare and publish a bounded executable '
            'issue-backed proposal for the missing implementation, shared-file integration, conversion, '
            'or engine diagnosis. You are authorized to prepare private worktrees and immutable launch '
            'proofs under output using the existing planner preparation tools; do not implement or '
            'launch directly. An open issue, completed report, referral to #186, or another blocked '
            'consumer is not an active input producer. Missing raw assets require verification against '
            'output/workflow/asset-inputs.json and exact failed reads; derived-data work is engineering. '
            'Do not repeat previously completed pin-discovery if its concrete patch is already present. '
            'Shared CMake/preview work needs a private scoped candidate, substantive owner decision and '
            'normal integration validation. Reserve the ACTUAL native implementation files in that '
            'job and require native commits plus compiled evidence. Owning only documentation and a '
            'Python patch generator prepares an input but does not implement or land native changes. '
            'Private native source candidates are authorized; the single-writer restriction protects '
            'the maintained checkout. Serialize overlapping source claims instead of substituting more packets. '
            'Runtime recovery acceptance now requires hashed actual consumer executable, native pin, log and '
            'bounded supervisor result. A completed module, fixture-only call, landing packet, diagnostic '
            'or review request is not completion of engine wiring. If source exists but is never invoked, '
            'prepare an implementation job owning the real engine call site AND required build membership '
            '(including a private CMake candidate when needed), with shared review and integration followed '
            'by a real consumer run. If only staging/rerun remains within the consumer ownership, prepare '
            'a fenced resumption of that existing owner instead of another diagnosis or duplicate scope. '
            'Preserve source claims, final single-writer integration, '
            'runtime safety and ADMIT gates. Record proposal IDs, producer lane IDs, or precise external '
            'user-owned input evidence for every consumer in your final checkpoint. After publication, '
            'record executable producer links with python -m workflow.blocked_followup --root <canonical> '
            '--request <json>: coordinator, generation, consumer, consumer_generation, producers (lane IDs), '
            'reason, acceptance_check (the exact consumer command and expected outcome), evidence {path,sha256}. '
            'This creates automatic consumer wakeup after verified integration; delivery is not a verified '
            'unblock until the consumer reports its independent check through workflow.consumer_verification. '
            'Demand: '+str(candidates))
        if pending:
            with reg.transaction() as current:
                launch = current['control']['launches'][pending['id']]
                if (launch['status'] != 'intent' or launch.get('process') or launch.get('blocked_followup_ids') or
                        controller.launch_directory(launch['id']).exists()): return
                launch['instruction'] += '\n\n' + instruction
                launch['blocked_followup_ids'] = [x['id'] for x in candidates]
                reg.event(current,'blocked_followup_attached',key,action=launch['id'])
            return
        launch = reg.plan_launch(key,'blocked-producer-followup:'+fingerprint(candidates),
                                 instruction,controller.config['models'])
        with reg.transaction() as current:
            current['control']['launches'][launch['id']]['blocked_followup_ids']=[x['id'] for x in candidates]
    except Rejected as exc:
        reg.notice(key,'blocked_followup_deferred',dict(error=str(exc)))


def link(reg, coordinator, generation, consumer, consumer_generation, producers, reason, evidence, acceptance_check=None):
    require(isinstance(producers,list) and producers and all(isinstance(k,str) and k for k in producers),
            'Executable producer lane IDs required')
    require(isinstance(reason,str) and reason.strip(), 'Evidence-backed linkage reason required')
    reg.evidence(evidence)
    with reg.transaction() as state:
        data=state.get('throughput_runtime',{}).get('autofill',{})
        require(coordinator==data.get('prerequisite_coordinator'), 'Registered coordinator required')
        owner=reg.lane(state,coordinator,generation)
        require(owner['state']=='running' and reg.probe(owner['process'])=='alive', 'Live coordinator required')
        target=reg.lane(state,consumer,consumer_generation)
        require(target['state']=='blocked' and not is_helper(consumer) and consumer!=coordinator,
                'Blocked implementation consumer required')
        require(reg.recovery_safe(state,target), 'Consumer still active or uncertain')
        items=data.get('items',{}).values()
        for producer in producers:
            require(producer not in (consumer,coordinator) and not is_helper(producer), 'Not an executable producer')
            lane=state['lanes'].get(producer)
            if lane:
                require(lane['state'] in ('ready','running','waiting_resource','handoff_ready','integrating') or
                        (lane['state']=='done' and lane.get('integration')),
                        'Producer must be executable or integrated, not another blocked/review-only owner')
            else:
                require(any(x.get('lane')==producer and x.get('ready') and x.get('status')!='blocked' for x in items),
                        'Producer needs a validated ready published spec')
            pending=[producer];seen=set()
            while pending:
                node=pending.pop()
                require(node!=consumer, 'Circular producer dependency')
                if node in seen: continue
                seen.add(node)
                pending.extend(state.get('blocked_producer_links',{}).get(node,{}).get('producers',[]))
                pending.extend(d for d in state['lanes'].get(node,{}).get('dependencies',[]) if d in state['lanes'])
        result=dict(consumer=consumer,consumer_generation=consumer_generation,producers=sorted(set(producers)),
                    source_pins={k:(target.get(k) or {}).get('head') for k in ('root','native')},
                    reason=reason,evidence=evidence,at=reg.clock(), acceptance_check=acceptance_check or reason)
        state.setdefault('blocked_producer_links',{})[consumer]=result
        reg.event(state,'blocked_producers_linked',coordinator,consumer=consumer,producers=result['producers'])
        return copy.deepcopy(result)


def main():
    import argparse
    import json
    from pathlib import Path
    from .registry import Registry
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--request',type=Path,required=True)
    args=parser.parse_args();reg=Registry(args.root/'output/workflow/registry.sqlite3',args.root)
    print(json.dumps(link(reg,**json.loads(args.request.read_text(encoding='utf-8-sig'))),indent=2))


if __name__=='__main__':main()
