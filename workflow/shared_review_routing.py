"""Deliver owner decision tasks; only recorded dispositions satisfy the queue."""
import copy
import json
from .control import fingerprint
from .handoff import local_path,require
from .runner import write


def tick(controller):
    cfg=controller.config.get('shared_review_routing',{})
    if not cfg.get('enabled'):return
    reg=controller.reg;now=reg.clock();routes=cfg.get('files',{})
    with reg.transaction() as s:
        lanes=copy.deepcopy(s['lanes']);ledger=copy.deepcopy(s.get('shared_review_routes',{}))
    active=set()
    for key,lane in lanes.items():
        if lane['state'] not in ('handoff_ready','integrating'):continue
        handoff=lane.get('handoff')
        if not handoff:continue
        reg.evidence({k:handoff[k] for k in ('path','sha256')})
        data=json.loads(local_path(reg.root,handoff['path']).read_text(encoding='utf-8-sig'))
        for review in data.get('shared_reviews',[]):
            if review['status']!='requested':continue
            owner=routes.get(review['file'])
            if not owner:continue
            require(owner in lanes,'Shared-review owner not registered')
            identity=fingerprint([key,lane['generation'],review['file'],lane.get('root'),lane.get('native')])
            active.add(identity);old=ledger.get(identity,{})
            inbox=local_path(reg.root,controller.config['integrator_inbox'])
            require(inbox.is_relative_to(reg.root/'output'),'Review inbox must be private')
            inbox.mkdir(parents=True,exist_ok=True)
            packet=inbox/('shared-review-'+identity+'.md')
            if old and (packet.exists() or now-old['delivered_at']<max(300,cfg.get('retry_seconds',600))):continue
            payload=dict(owner=owner,producer=key,generation=lane['generation'],revision=lane['revision'],
                issue=lane['issue'],file=review['file'],review_request=review,handoff=handoff,
                root=lane.get('root'),native=lane.get('native'))
            packet.write_text('# ACTION REQUIRED: shared-code owner decision\n\n'+json.dumps(payload,indent=2)+
                '\n\nDelegated focused review under #186/#629 to the existing integration lead, Codex through shared 4laric. '
                'Inspect exact pinned diffs and tests; decide APPROVED or REQUEST CHANGES with file-specific reasoning. '
                'An advisory packet or missing separate historical worker is not a reason to wait: you own this focused decision. '
                'Do not infer approval from age or these instructions. Post actual decision/evidence to #186 and child issue. '
                'Record an immutable hashed decision report. Re-read current lane revision/handoff hash before using canonical '
                'Registry.dispose_review (CLI dispose-review) with key,generation,revision,unique version,handoff_sha256,file,'
                'status approved/rejected,reviewer identifying yourself,evidence={path,sha256}. '
                'Its stopped-producer/child fences must pass; if producer still live, retain decision and apply after stop. '
                'Apply separate dispositions sequentially using the refreshed hash/revision. Approval then follows normal '
                'integration/receipt checks; rejection needs explicit owner repair instructions. No ADMIT or semantic approval '
                'outside this named file. Task remains outstanding until shared_reviews status changes, even if inbox consumed.\n',encoding='utf-8')
            with reg.transaction() as s:
                s.setdefault('shared_review_routes',{})[identity]=dict(**payload,path=str(packet),
                    delivered_at=now,attempts=old.get('attempts',0)+1,status='awaiting_owner_decision')
                reg.event(s,'shared_review_routed',key,file=review['file'],owner=owner,task=identity)
    with reg.transaction() as s:
        for identity,record in s.setdefault('shared_review_routes',{}).items():
            if identity not in active:record.update(status='resolved_or_superseded',resolved_at=record.get('resolved_at',now))
