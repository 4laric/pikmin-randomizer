"""Durable integrator-authored decisions; controller applies without producer handback."""
import copy
import json
from .control import fingerprint
from .provenance import cli
from .handoff import require, Rejected
from . import approvals
from .approvals import INSTRUCTION as APPROVALS, delegated  # noqa: F401 (delegated is re-exported)


INSTRUCTION = (' For handoff shared reviews, record your actual decision through '
    + cli('review_decisions') + ' --root <canonical-root> --request <json>, run from inside your own live launch '
    'session. Fields: reviewer (your registered lane), generation (your generation), '
    'key (producer lane), producer_generation, handoff_sha256, decisions '
    '[{file,status:approved|rejected,evidence:{path,sha256}}]. Each decision becomes an authenticated '
    'approvals-ledger row pinned to the producer root/native pins and that file diff; integrate reads only '
    'the ledger. The controller also applies each decision to a new immutable handoff once the producer is '
    'safely stopped. Do not hand approved status changes back to a stopped producer. Issue comments '
    'and prose approval alone do not complete the decision. Read the returned queue receipt.' + APPROVALS)


def record(reg, reviewer, generation, key, producer_generation, handoff_sha256, decisions):
    require(isinstance(decisions,list) and decisions, 'Nonempty file decisions required')
    require(all(isinstance(d,dict) for d in decisions) and len({d.get('file') for d in decisions}) == len(decisions),
            'One decision per file required')
    for d in decisions:
        require(set(d)=={'file','status','evidence'} and d['status'] in ('approved','rejected'), 'Explicit scoped review required')
        reg.evidence(d['evidence'])
    from .provenance import stamp
    from .storage import read_record
    code=stamp();chain=approvals.ancestry()
    before=read_record(reg,('lanes',),key)
    require(isinstance(before,dict),'Unknown lane: '+str(key))
    digests={d['file']:approvals.diff(reg.root,before,d['file']) for d in decisions}
    with reg.transaction() as state:
        identity=approvals.authenticate(reg,state,reviewer,generation,chain)
        lane=reg.lane(state,key,producer_generation)
        approvals.authorize(state,reviewer,lane)
        require(lane['state'] in ('handoff_ready','integrating') and lane['handoff']['sha256']==handoff_sha256,
                'Exact current handoff required')
        require(approvals.pins(lane)==approvals.pins(before),'Producer pins changed while hashing the reviewed diff')
        data=reg._delivery_read_handoff(lane)
        require({d['file'] for d in decisions}<={r['file'] for r in data['shared_reviews']}, 'Unknown shared file')
        value=dict(reviewer=reviewer,reviewer_generation=generation,key=key,generation=producer_generation,
                   handoff_sha256=handoff_sha256,root=lane['root'],native=lane.get('native'),decisions=copy.deepcopy(decisions))
        identity_key=fingerprint(value)
        ledger=state.setdefault('shared_review_decisions',{})
        # Ledger rows replay only while each is still the latest decision on its file; otherwise they are new rows.
        rows=[approvals.review_row(reg,state,'review_decisions',lane,d['file'],digests[d['file']],d['status'],
                                   d['evidence'],identity,code,handoff_sha256=handoff_sha256)['id'] for d in decisions]
        if identity_key in ledger and ledger[identity_key].get('approvals')!=rows:
            identity_key=fingerprint(dict(value,approvals=rows))
        if identity_key not in ledger:
            ledger[identity_key]=dict(value,id=identity_key,status='pending',applied=0,current_handoff=handoff_sha256,at=reg.clock(),
                                      code_revision=code,approvals=rows,reviewer_identity=identity)
            reg.event(state,'shared_review_decision_queued',key,decision=identity_key)
        return copy.deepcopy(ledger[identity_key])


def tick(controller):
    reg=controller.reg
    pending=[v for v in reg.snapshot().get('shared_review_decisions',{}).values() if v['status']=='pending']
    budget=4
    for item in sorted(pending,key=lambda d:d['at']):
        if budget<=0:break
        try:
            with reg.transaction() as state:
                row=state['shared_review_decisions'][item['id']]
                if row['status']!='pending':continue
                lane=state['lanes'][row['key']]
                if (lane['generation']!=row['generation'] or lane.get('root')!=row['root'] or lane.get('native')!=row['native'] or
                        (lane.get('handoff') or {}).get('sha256')!=row['current_handoff']):
                    row.update(status='stale',reason='Producer pins changed; reviewer must revalidate')
                    reg.event(state,'shared_review_decision_stale',row['key'],decision=row['id']);continue
                reg._delivery_stopped(state,lane)
                while row['applied']<len(row['decisions']) and budget:
                    d=row['decisions'][row['applied']];reg.evidence(d['evidence'])
                    request=dict(d,reviewer=row['reviewer'],handoff_sha256=row['current_handoff'])
                    reg._dispose_review(state,row['key'],row['generation'],lane['revision'],
                                        'queued-'+row['id']+'-'+str(row['applied']),request,
                                        (row.get('approvals') or [None]*len(row['decisions']))[row['applied']])
                    row['applied']+=1;budget-=1
                    row['current_handoff']=lane['handoff']['sha256']
                if row['applied']==len(row['decisions']):
                    row.update(status='applied',applied_at=reg.clock());row.pop('waiting_reason',None)
                    reg.event(state,'shared_review_decision_applied',row['key'],decision=row['id'])
        except (Rejected,OSError,ValueError,KeyError) as exc:
            # Let the failed transaction roll back all lane and receipt mutations.
            with reg.transaction() as state:
                row=state['shared_review_decisions'][item['id']]
                if row['status']=='pending':row['waiting_reason']=str(exc)



def main():
    import argparse
    from pathlib import Path
    from .registry import Registry
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--request',type=Path,required=True)
    a=p.parse_args();reg=Registry(a.root/'output/workflow/registry.sqlite3',a.root)
    print(json.dumps(record(reg,**json.loads(a.request.read_text(encoding='utf-8-sig'))),indent=2))

if __name__=='__main__':main()
