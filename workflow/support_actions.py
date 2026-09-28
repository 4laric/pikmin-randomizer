"""Pinned actionable outcomes for delegated integration/repair workers."""
import copy
import json
import re
from .control import fingerprint
from .provenance import cli
from .handoff import require
from .batching import isolated_handoff

FIELDS=('lane','generation','root','native','handoff')


def same(target,lane):
    return all(target.get(k)==lane.get(k) for k in FIELDS)


def assignment(state,reviewer):
    return next((r for r in state.get('throughput_runtime',{}).get('autofill',{}).get('planner_pool',{}).get('scopes',{}).values()
                 if r.get('spec',{}).get('lane',{}).get('lane')==reviewer and 'completed_at' not in r),{})


def extra_targets(reg,state):
    result=[];batches=state.get('throughput',{}).get('batches',{})
    from .batching import handoff_repairs
    exports = {r['lane']:r for r in handoff_repairs(state,reg.clock())
               if re.search(r'\bexport\b', r.get('reason',''), re.I)}
    for key,lane in state['lanes'].items():
        from .shared_decisions import requested
        if key.startswith(('planning-','publication-','integration-support-')):continue
        text=lane.get('next_action','')+' '+str(lane.get('dependencies',[]))
        isolation=isolated_handoff(batches,key,lane)
        export = exports.get(key)
        kind=('export_preparation' if export and lane['state'] in ('blocked','handoff_ready') else
              'handoff_diagnosis' if lane['state']=='handoff_ready' and isolation else
              'blocked_review' if lane['state']=='blocked' and requested(text) else None)
        if kind=='blocked_review':
            from .shared_decisions import approved_scope
            if approved_scope(state,lane):continue
        if not kind or not reg.recovery_safe(state,lane):continue
        if any(b.get('state')=='claimed' and key in b.get('candidates',{}) and key not in b.get('isolated',{}) for b in batches.values()):continue
        result.append(dict({k:copy.deepcopy(lane.get(k)) for k in FIELDS},issue=lane['issue'],
            kind=kind,downstream=0,request=text,outcome=copy.deepcopy(lane.get('outcome')),isolation=isolation,
            **({'export_blocker':export['reason']} if kind=='export_preparation' else {})))
        if kind=='export_preparation':
            packets=[a for a in state.get('support_actions',{}).values() if a['key']==key and
                     a['action']=='integration_packet' and a['target'].get('kind')==kind and same(a['target'],lane)]
            if packets:
                from .export_packet import error
                latest=max(packets,key=lambda a:a['at']);problem=error(reg,latest)
                if problem:result[-1]['export_packet_repair']=dict(packet=latest['id'],reason=problem)
                else:
                    from .export_feedback import stalled
                    feedback=stalled(state,latest)
                    if feedback:result[-1]['export_packet_repair']=feedback
    return result


INSTRUCTION=(' ACTIONABLE OUTCOME REQUIRED before finish review-ready: prose referrals do not count. '
 'For blocked_review use '+cli('shared_decisions')+' --root <root> --request <json>; fields '
 'key,generation (producer),source_pins:{root:<head>,native:<head or null>},file (producer-owned),'
 'status:approved|rejected,reviewer (your lane),reviewer_generation (your current generation),reason,evidence:{path,sha256}; '
 'run it from inside your own live launch session (the CLI authenticates the calling process). '
 'Review actual scoped changes only, not future unimplemented wiring. For other outcomes use '
 +cli('support_actions')+' --root <root> --request <json> with reviewer,generation (yours),'
 'key (target lane),action:repair|integration_packet|producer|proposal|external|stale,reason,evidence:{path,sha256},details. '
 'Planning recovery may record proposal with details.proposal {path,sha256}, details.proposal_id and '
 'details.consumer equal to the target lane; the artifact must contain a complete valid executable spec. '
 'This records staged work only; publication, admission and consumer verification remain required. '
 'producer requires details.lane naming an actual queued or live implementation producer, with hashed '
 'evidence explaining how its scope supplies the blocked input. Staging a proposal alone is insufficient; '
 'wait for publication/admission or record the concrete remaining blocker. '
 'repair requires details.instruction with exact reproducible correction within producer-owned files; it '
 'queues one independently diagnosed retry per unchanged source heads. integration_packet requires '
 'details.destination:{root:<40-char commit>,native:<40-char commit or null>} and hashed preparation '
 'evidence naming private resolution commits, tests and exact remaining final-owner commands; it wakes '
 'the sole integrator. external requires details.owner=user, details.kind=user_asset|user_decision and '
 'details.required naming the precise missing input. stale is only valid when producer pins/state changed. '
 'Never manufacture an external dependency or approval to finish. If unable to resolve, finish BLOCKED '
 'with concrete evidence; that is unresolved work, not successful review completion. ')


def record(reg,reviewer,generation,key,action,reason,evidence,details):
    require(action in ('repair','integration_packet','producer','proposal','external','stale') and isinstance(reason,str) and reason.strip(),'Explicit action and reason required')
    archived=reg.archive_evidence(evidence)
    details=copy.deepcopy(details)
    if action=='proposal':
        from .autofill import validate_spec
        require(details.get('consumer')==key, 'Proposal must identify its blocked consumer')
        artifact=details.get('proposal')
        require(artifact, 'Hashed staged proposal required')
        path=reg.evidence(artifact)
        # evidence validates the hash; parse the exact archived bytes outside the writer lock.
        details['proposal']=reg.archive_evidence(artifact)
        from .handoff import local_path
        body=json.loads(local_path(reg.root,details['proposal']['path']).read_text(encoding='utf-8-sig'))
        specs=[v for v in body.get('items',[]) if v.get('id')==details.get('proposal_id')]
        require(len(specs)==1, 'Exact executable proposal ID required')
        require(specs[0]['lane']['lane'] not in (key,reviewer), 'Independent scoped proposal required')
        validate_spec(reg,specs[0])
    if action=='integration_packet':
        for field in ('export_patch','export_validation'):
            if details.get(field):details[field]=reg.archive_evidence(details[field])
    with reg.transaction() as state:
        owner=reg.lane(state,reviewer,generation)
        require(owner['state']=='running' and reg.probe(owner['process'])=='alive','Live reviewer required')
        row=assignment(state,reviewer)
        require(row.get('actionable_support'),'Actionable support assignment required')
        if action=='proposal':require(row.get('recovery_action_targets'), 'Planning recovery assignment required')
        target=next((t for t in row.get('support_targets',row.get('recovery_action_targets',[])) if t['lane']==key),None)
        require(target is not None and key!=reviewer,'Exact assigned target required')
        lane=state['lanes'][key]
        current=same(target,lane) and lane['state'] in ('blocked','handoff_ready','integrating')
        require(not current if action=='stale' else current,'Target changed; record stale disposition')
        if action=='producer':
            producer=state['lanes'].get(details.get('lane'),{})
            from .planner_demand import is_helper
            require(producer and not is_helper(details['lane']) and details['lane'] not in (key,reviewer),
                    'Independent implementation producer required')
            queued=any(j['lane']==details['lane'] and j['status'] in ('queued','assigned') for j in
                       state.get('throughput',{}).get('jobs',{}).values())
            require(queued or (producer['state']=='running' and reg.probe(producer['process'])=='alive'),
                    'Producer must be actually queued or live, not merely a blocked owner or proposal')
        if action=='external':
            require(details.get('owner')=='user' and details.get('kind') in ('user_asset','user_decision') and
                    isinstance(details.get('required'),str) and details['required'].strip(),'Specific user-owned input required')
        if action=='integration_packet':
            dest=details.get('destination',{})
            require(set(dest)=={'root','native'} and re.fullmatch('[0-9a-f]{40}',dest.get('root','')) and
                    (dest.get('native') is None or re.fullmatch('[0-9a-f]{40}',dest['native'])),'Pinned integration destination required')
            if target.get('kind') == 'export_preparation':
                require(dest.get('native') is not None, 'Native export requires native destination pin')
                require(details.get('source_native') == (lane.get('native') or {}).get('head'),
                        'Export source must match assigned native head')
                for field in ('export_patch','export_validation'):
                    require(details.get(field), 'Concrete hashed '+field+' required; referral is not export preparation')
                    reg.evidence(details[field])
                from .export_packet import validate
                validate(reg,details)
                require(isinstance(details.get('apply_commands'),list) and details['apply_commands'] and
                        all(isinstance(c,str) and c.strip() for c in details['apply_commands']),
                        'Exact final-owner application and validation commands required')
        if action=='repair':
            require(lane['state']=='handoff_ready' and reg.recovery_safe(state,lane),'Stopped handoff required for repair action')
            require(isolated_handoff(state.get('throughput',{}).get('batches',{}),key,lane),'Existing handoff isolation required')
            require(isinstance(details.get('instruction'),str) and details['instruction'].strip(),'Concrete repair instruction required')
            source_key=fingerprint([key,(lane.get('root') or {}).get('head'),(lane.get('native') or {}).get('head')])
            prior=state.setdefault('independent_repair_sources',{}).get(source_key)
            require(not prior or prior.get('reviewer')==reviewer,'Independent retry already granted for these source heads')
        if target.get('kind') == 'export_preparation':
            require(action in ('integration_packet','stale','external'),
                    'Export preparation needs a packet, not a producer repair/referral')
        value=dict(reviewer=reviewer,generation=generation,key=key,target=target,action=action,
                   reason=reason,evidence=archived,details=details)
        identity=fingerprint(value)
        ledger=state.setdefault('support_actions',{})
        if identity not in ledger:
            ledger[identity]=dict(value,id=identity,at=reg.clock())
            if action=='repair':
                require(not prior,'Independent repair action already recorded')
                state['independent_repair_sources'][source_key]=dict(reviewer=reviewer,action=identity)
                candidate={k:copy.deepcopy(lane.get(k)) for k in ('generation','revision','root','native','handoff')}
                lane['review_repair']=dict(candidate=candidate,pin=dict(batch_id=None,generation=lane['generation'],
                    revision=lane['revision'],reason=reason,instruction=details['instruction'],independent_action=identity,evidence=archived))
            reg.event(state,'support_action_recorded',key,action=identity,outcome=action)
        return copy.deepcopy(ledger[identity])


def require_outcomes(state,reviewer):
    from .dependency_classification import require_outcomes as require_classification
    require_classification(state,reviewer)
    row=assignment(state,reviewer)
    if row.get("classification_target"):return
    if not row.get('actionable_support'):return
    actions=list(state.get('support_actions',{}).values())
    decisions=list(state.get('shared_preflight_decisions',{}).values())+list(state.get('shared_review_decisions',{}).values())
    for target in row.get('support_targets',row.get('recovery_action_targets',[])):
        if target.get('kind')=='export_preparation':
            require(any(a['reviewer']==reviewer and a['target']==target and
                        a['action'] in ('integration_packet','stale','external') for a in actions),
                    'Record a concrete export preparation outcome for '+target['lane'])
            continue
        require(any(a['reviewer']==reviewer and a['target']==target for a in actions) or
                any(d.get('reviewer')==reviewer and d.get('lane',d.get('key'))==target['lane'] and
                    d.get('generation')==target['generation'] for d in decisions),'Record an actionable outcome for '+target['lane']+' before finishing review-ready')


def main():
    import argparse
    from pathlib import Path
    from .registry import Registry
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--request',type=Path,required=True)
    a=p.parse_args();print(json.dumps(record(Registry(a.root/'output/workflow/registry.sqlite3',a.root),
                    **json.loads(a.request.read_text(encoding='utf-8-sig'))),indent=2))

if __name__=='__main__':main()
