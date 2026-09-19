"""Action-specific routing for classified internal blockers."""
import json
import re
from .control import fingerprint
from .handoff import Rejected
from .delivery_contracts import owners, source_pins


def routes(state, request):
    result=[]
    for finding in request['findings']:
        kind=finding['kind'];owner=finding.get('owner_lane')
        landing=(kind=='missing_producer' and re.search(r'\b(landed|landing|lands)\b',finding['missing']+' '+finding['next_action'],re.I)
                 and any(state['lanes'].get(k,{}).get('native') and state['lanes'][k].get('state')=='done'
                         for k in finding['inspected_lanes']))
        if kind=='integration_review' or landing:
            for integrator in owners(state,request['consumer']):
                result.append(dict(kind='integration',owner=integrator,finding=finding))
            if not owners(state,request['consumer']):result.append(dict(kind='planning',owner=None,finding=finding))
        elif kind=='owner_blocked':result.append(dict(kind='resume',owner=owner,finding=finding))
        else:result.append(dict(kind='planning',owner=None,finding=finding))
    return result


def integration_work(state, owner):
    from .internal_followup import requests
    work=[]
    for request in requests(state).values():
        findings=[r['finding'] for r in routes(state,request) if r['kind']=='integration' and r['owner']==owner]
        if findings:
            work.append(dict(delivery_contract=request['id'],internal_owner_action='integration',
                consumer=request['consumer'],snapshot=request['snapshot'],findings=findings,report=request['report'],
                instruction='Perform the pinned review/landing through existing integration gates. Inspect actual source and '
                    'handoff evidence; if no eligible handoff exists, record the exact required owner repair. '
                    'Do not replace landing with another planning referral or infer approval.'))
    return work


def owner_work(state):
    from .internal_followup import requests
    groups={}
    for request in requests(state).values():
        for route in routes(state,request):
            if route['kind']=='resume':groups.setdefault(route['owner'],[]).append(dict(
                consumer=request['consumer'],snapshot=request['snapshot'],finding=route['finding'],report=request['report']))
    return groups


def owner_token(state, owner, work):
    return 'internal-owner-resume:'+fingerprint([owner,source_pins(state['lanes'][owner]),sorted(
        (r['consumer'],r['snapshot'],r['finding']['requirement']) for r in work)])


def validate_resume(state, owner, reason):
    from .handoff import require
    work=owner_work(state).get(owner)
    require(work and state['lanes'][owner]['state']=='blocked' and owner_token(state,owner,work)==reason,
            'Owner action inputs changed; reassess before resumption')
    require(not any(x['lane']==owner and x['reason']==reason for x in state.get('control',{}).get('launches',{}).values()),
            'Owner action already attempted for these inputs')


def tick(controller):
    reg=controller.reg;state=reg.snapshot();groups=owner_work(state)
    for owner,work in groups.items():
        lane=state['lanes'].get(owner,{})
        if lane.get('state')!='blocked' or owner not in controller.config['lanes']:continue
        if not reg.recovery_safe(state,lane) or not controller.available(owner):continue
        # Stable per-owner source/requirement set: no generation or heartbeat retry resets.
        token=owner_token(state,owner,work)
        launches=state.get('control',{}).get('launches',{}).values()
        if any(x['lane']==owner and (x['reason']==token or x['status'] in ('intent','spawned','running','exiting')) for x in launches):continue
        try:
            for row in work:reg.evidence(row['report'])
            reg.plan_launch(owner,token,'CLASSIFIED OWNER ACTION: resume your existing private implementation scope. '
                'Inspect the attached evidence and perform the concrete remaining owner action where authorized. '
                'Do not create duplicate lanes, expand owned files, or assume dependencies are satisfied. '
                'Preserve all source pins, leases, required shared reviews, integration and ADMIT gates. '
                'Runtime work requires current fixture baseline, leased private builds and bounded game runs. '
                'Record actual results and a valid handoff; if still blocked, state the precise remaining input '
                'and stop. This is one bounded execution attempt, not another planning assignment. Findings: '+json.dumps(work),controller.config['models'])
        except (Rejected,OSError,ValueError) as exc:reg.notice(owner,'internal_owner_resume_blocked',dict(error=str(exc)))
