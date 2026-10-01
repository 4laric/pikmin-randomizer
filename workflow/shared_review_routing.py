"""Deliver owner decision tasks; only an authenticated ledger decision satisfies the queue.

A routed owner must pass approvals.authorize for the producer (own its workstream or hold its
exact delegation); otherwise no packet is sent and an owner notice names the misrouting."""
import copy
import json
from .control import fingerprint
from .handoff import local_path,require,Rejected
from .runner import write
from .review_decisions import INSTRUCTION
from .approvals import authorize,decision


def tick(controller):
    cfg=controller.config.get('shared_review_routing',{})
    if not cfg.get('enabled'):return
    reg=controller.reg;now=reg.clock();routes=cfg.get('files',{})
    with reg.transaction() as s:
        lanes=copy.deepcopy(s['lanes']);ledger=copy.deepcopy(s.get('shared_review_routes',{}))
        rows=copy.deepcopy(s.get('approvals',{}))
        # Authority inputs only: the routed owner must be able to record the decision it is sent.
        auth=dict(throughput={k:copy.deepcopy(s.get('throughput',{}).get(k,{})) for k in ('workstreams','dispositions')},
                  throughput_runtime=dict(autofill=dict(planner_pool=dict(scopes=copy.deepcopy(
                      s.get('throughput_runtime',{}).get('autofill',{}).get('planner_pool',{}).get('scopes',{}))))))
    active=set()
    for key,lane in lanes.items():
        if lane['state'] not in ('handoff_ready','integrating'):continue
        handoff=lane.get('handoff')
        if not handoff:continue
        reg.evidence({k:handoff[k] for k in ('path','sha256')})
        data=json.loads(local_path(reg.root,handoff['path']).read_text(encoding='utf-8-sig'))
        for review in data.get('shared_reviews',[]):
            if decision(rows,lane,review['file']) is not None:continue  # Only a ledger decision resolves; handoff statuses never do.
            owner=routes.get(review['file'])
            if not owner:continue
            require(owner in lanes,'Shared-review owner not registered')
            identity=fingerprint([key,lane['generation'],review['file'],lane.get('root'),lane.get('native')])
            active.add(identity);old=ledger.get(identity,{})
            target=lanes[owner]
            if reg.probe(target.get('process'))!='alive':
                # A stopped owner the controller can wake still gets the packet; one nothing supervises does not.
                supervised=owner in controller.config.get('lanes',{}) and target['state']!='done'
                reg.notice(owner,'shared_review_target_dead',dict(state=target['state'],supervised=supervised,
                    error='Routed shared-review owner is not running'+('' if supervised else
                          ' and has no controller launch config; routing held until it is supervised or rerouted')),
                    status='info' if supervised else 'pending')
                if not supervised:
                    # A delivered packet keeps its record (and the protocol-2 resend throttle); only an
                    # undelivered route is held.
                    delivered=old.get('protocol')==2
                    if (old.get('owner_state')!='unsupervised_stopped') if delivered else (old.get('status')!='owner_unsupervised'):
                        with reg.transaction(sections=()) as s:  # shared_review_routes lives in the meta row.
                            s.setdefault('shared_review_routes',{})[identity]=(dict(old,owner_state='unsupervised_stopped',held_at=now)
                                if delivered else dict(producer=key,generation=lane['generation'],file=review['file'],owner=owner,
                                status='owner_unsupervised',at=now,attempts=old.get('attempts',0)))
                    continue
            try:authorize(auth,owner,lane)
            except Rejected as exc:
                # Never send a packet the owner cannot decide; surface the misrouted config instead.
                detail=dict(producer=key,generation=lane['generation'],file=review['file'],
                            error='routed owner cannot record authenticated decisions: '+str(exc))
                reg.notice(owner,'shared_review_owner_cannot_decide',detail)
                if old.get('status')!='owner_cannot_decide':
                    with reg.transaction() as s:
                        s.setdefault('shared_review_routes',{})[identity]=dict(detail,owner=owner,status='owner_cannot_decide',at=now,
                            attempts=old.get('attempts',0))
                continue
            inbox=local_path(reg.root,controller.config['integrator_inbox'])
            require(inbox.is_relative_to(reg.root/'output'),'Review inbox must be private')
            inbox.mkdir(parents=True,exist_ok=True)
            packet=inbox/('shared-review-'+identity+'.md')
            if old.get('protocol')==2 and (packet.exists() or now-old['delivered_at']<max(300,cfg.get('retry_seconds',600))):
                if old.get('owner_state'):  # The owner runs again: drop the stopped marker, keep the delivery.
                    with reg.transaction(sections=()) as s:
                        s.setdefault('shared_review_routes',{})[identity]={k:v for k,v in old.items() if k not in ('owner_state','held_at')}
                continue
            payload=dict(owner=owner,producer=key,generation=lane['generation'],revision=lane['revision'],
                issue=lane['issue'],file=review['file'],review_request=review,handoff=handoff,
                root=lane.get('root'),native=lane.get('native'))
            packet.write_text('# ACTION REQUIRED: shared-code owner decision\n\n'+json.dumps(payload,indent=2)+
                '\n\nDelegated focused review under #186/#629 to the existing integration lead, Codex through shared 4laric. '
                'Inspect exact pinned diffs and tests; decide APPROVED or REQUEST CHANGES with file-specific reasoning. '
                'An advisory packet or missing separate historical worker is not a reason to wait: you own this focused decision. '
                'Do not infer approval from age or these instructions. Post actual decision/evidence to #186 and child issue. '
                'Record an immutable hashed decision report. Re-read current lane revision/handoff hash before using canonical '
                'Registry.dispose_review (CLI dispose-review, run from inside your own live launch session) with key,generation,'
                'revision,unique version,handoff_sha256,file,status approved/rejected,reviewer (your registered lane),'
                'reviewer_generation (your generation),evidence={path,sha256}; free-text reviewers are refused. '
                'Its stopped-producer/child fences must pass; if producer still live, retain decision and apply after stop. '
                'Prefer review_decisions (every file in one call); separate dispositions apply sequentially using the '
                'refreshed hash/revision. Approval then follows normal '
                'integration/receipt checks; rejection needs explicit owner repair instructions. No ADMIT or semantic approval '
                'outside this named file. Task remains outstanding until an authenticated approvals-ledger decision '
                'exists at these pins, even if inbox consumed.\n'+INSTRUCTION,encoding='utf-8')
            with reg.transaction() as s:
                s.setdefault('shared_review_routes',{})[identity]=dict(**payload,path=str(packet),
                    delivered_at=now,attempts=old.get('attempts',0)+1,status='awaiting_owner_decision',protocol=2)
                reg.event(s,'shared_review_routed',key,file=review['file'],owner=owner,task=identity)
    with reg.transaction() as s:
        for identity,record in s.setdefault('shared_review_routes',{}).items():
            if identity not in active:record.update(status='resolved_or_superseded',resolved_at=record.get('resolved_at',now))
