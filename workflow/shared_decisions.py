"""Pinned shared-file decisions for producers that cannot yet submit a handoff."""
import argparse
import copy
import json
import re
from pathlib import Path
from .control import fingerprint
from .handoff import require, Rejected
from .no_progress import Parked


def requested(text):
    return bool(re.search(r'#186\b', text) and
                re.search(r'review|shared|landing decision|approval', text, re.I))


def pins(lane):
    return {k:(lane.get(k) or {}).get('head') for k in ('root','native')}


def semantic(decision):
    """An identical approved source diff does not become new work with a new turn."""
    return fingerprint([decision['lane'],decision['source_pins'],decision['file'],decision['status'],
                        decision.get('reason') if decision['status']=='rejected' else None])


def backed(state,decision):
    """Only a decision with an authenticated approvals-ledger row counts; older rows are unauthenticated-legacy."""
    return decision.get('approval') is not None and decision['approval'] in state.get('approvals',{})


def approved_scope(state,lane):
    files=set(lane.get('owned_files',[]))
    if not files or any((lane.get(k) or {}).get('dirty') for k in ('root','native')):return False
    latest={}
    for decision in state.get('shared_preflight_decisions',{}).values():
        if decision['lane']!=lane['lane'] or decision['source_pins']!=pins(lane) or not backed(state,decision):continue
        old=latest.get(decision['file'])
        if old is None or decision.get('at',0)>=old.get('at',0):latest[decision['file']]=decision
    return all(latest.get(file,{}).get('status')=='approved' for file in files)


def record(reg, key, generation, source_pins, file, status, reviewer, reason, evidence, reviewer_generation=None):
    """Always authenticated: reviewer is a live registered lane, called from inside its own launch session."""
    from . import approvals
    from .provenance import stamp
    from .storage import read_record
    require(status in ('approved','rejected'), 'Explicit approved/rejected decision required')
    require(isinstance(reason,str) and reason.strip(), 'Scoped reasoning required')
    require(isinstance(reviewer,str) and reviewer.strip() and type(reviewer_generation) is int,
            'reviewer (your registered lane) and reviewer_generation required; free-text reviewers are refused')
    reg.evidence(evidence)
    code=stamp();chain=approvals.ancestry()
    before=read_record(reg,('lanes',),key)
    require(isinstance(before,dict) and pins(before)==source_pins, 'Source pins changed')
    require(file in before['owned_files'], 'Decision file must belong to producer scope')
    digest=approvals.diff(reg.root,before,file)
    with reg.transaction() as state:
        lane=reg.lane(state,key,generation)
        identity=approvals.authenticate(reg,state,reviewer,reviewer_generation,chain)
        approvals.authorize(state,reviewer,lane)
        require(pins(lane)==source_pins and approvals.pins(lane)==approvals.pins(before), 'Source pins changed')
        require(file in lane['owned_files'], 'Decision file must belong to producer scope')
        require(lane['state']=='blocked' and reg.recovery_safe(state,lane), 'Safely stopped blocked producer required')
        decision=dict(lane=key,generation=generation,source_pins=source_pins,file=file,status=status,
                      reviewer=reviewer,reason=reason,evidence=evidence)
        identity_key=fingerprint(decision)
        rows=state.setdefault('shared_preflight_decisions',{})
        # The ledger row replays only while it is the latest decision on this file; otherwise it is recorded afresh.
        approval=approvals.review_row(reg,state,'shared_decisions',lane,file,digest,status,evidence,identity,code,reason=reason)['id']
        if identity_key in rows and rows[identity_key].get('approval')!=approval:
            identity_key=fingerprint(dict(decision,approval=approval))
        if identity_key not in rows:
            rows[identity_key]=dict(decision,at=reg.clock(),code_revision=code,reviewer_generation=reviewer_generation,
                                    reviewer_identity=identity,approval=approval)
        row=rows[identity_key]
        return dict(id=identity_key,**decision,code_revision=row.get('code_revision'),approval=row.get('approval'))


def completer(state, lane):
    """The approval that most recently completed the owned-file set at the lane's pins, while it is complete."""
    if not approved_scope(state,lane):return None
    files=set(lane.get('owned_files',[]))
    rows=sorted(((k,d) for k,d in state.get('shared_preflight_decisions',{}).items() if d['lane']==lane['lane']
                 and d['source_pins']==pins(lane) and backed(state,d)),key=lambda item:item[1].get('at',0))
    latest,complete,result={},False,None
    for identity,d in rows:
        latest[d['file']]=d['status']
        now=all(latest.get(f)=='approved' for f in files)
        if now and not complete:result=identity
        complete=now
    return result


def tick(controller):
    """Launch for a rejection, or for the approval that first completes the owned-file set at these pins.

    Every other decision stays a recorded ledger fact and launches nothing."""
    reg=controller.reg
    with reg.transaction() as state: state=copy.deepcopy(state)
    launches=list(state.get('control',{}).get('launches',{}).values())
    decisions=state.get('shared_preflight_decisions',{})
    consumed={}
    for x in launches:
        identity=x.get('reason','').removeprefix('shared-preflight-decision:')
        if (x.get('bound_generation') is not None and x.get('reason','').startswith('shared-preflight-decision:')
                and identity in decisions):
            d=decisions[identity];key=semantic(d)
            consumed[key]=max(consumed.get(key,0),d.get('at',0))
    completing={}
    for identity,d in decisions.items():
        key=d['lane'];lane=state['lanes'].get(key,{})
        if (key not in controller.config['lanes'] or not backed(state,d) or lane.get('state')!='blocked' or
                lane.get('generation')!=d['generation'] or pins(lane)!=d['source_pins']):continue
        token='shared-preflight-decision:'+identity
        if d['status']=='approved':
            if key not in completing:completing[key]=completer(state,lane)
            if completing[key]!=identity:continue  # Recorded without a launch: it does not complete the set.
            prior=consumed.get(semantic(d))
            if prior is not None and not any(x['lane']==key and x['file']==d['file'] and x['status']=='rejected' and
                    x['source_pins']==d['source_pins'] and x.get('at',0)>prior for x in decisions.values()):
                continue  # This identical approved diff was already delivered at these pins.
        elif semantic(d) in consumed:continue  # The same rejection was already delivered at these pins.
        if any(x['lane']==key and (x['reason']==token or x['status'] in ('intent','spawned','running','exiting')) for x in launches):continue
        if not reg.recovery_safe(state,lane) or not controller.available(key):continue
        try:
            reg.evidence(d['evidence'])
            reg.plan_launch(key,token,
                'A substantive pinned shared-file review decision is available. Read its hashed evidence '
                'and apply only its exact scope to your existing private work. Approved does not mean '
                'source integration, runtime acceptance or ADMIT; preserve every unrelated blocker. '
                'For rejection implement the requested correction within owned files. Update dependencies '
                'through normal checkpoints only where this decision actually resolves them. Submit a '
                'validated handoff when appropriate; final integration remains with the existing owner. '
                'Decision: '+json.dumps(d),controller.config['models'],inputs=['decision:'+semantic(d)])
        except (Rejected,OSError,ValueError) as exc:
            if not isinstance(exc,Parked):reg.notice(key,'shared_preflight_decision_blocked',dict(id=identity,error=str(exc)))


def main():
    from .registry import Registry
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--request',type=Path,required=True)
    args=parser.parse_args();reg=Registry(args.root/'output/workflow/registry.sqlite3',args.root)
    print(json.dumps(record(reg,**json.loads(args.request.read_text(encoding='utf-8-sig'))),indent=2))

if __name__=='__main__':main()
