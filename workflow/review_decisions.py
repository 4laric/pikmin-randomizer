"""Durable integrator-authored decisions; controller applies without producer handback."""
import copy
import json
from .control import fingerprint
from .provenance import cli
from .handoff import require, Rejected


INSTRUCTION = (' For handoff shared reviews, record your actual decision through '
    + cli('review_decisions') + ' --root <canonical-root> --request <json>. '
    'Fields: reviewer (your registered authorized reviewer lane), generation (your generation), '
    'key (producer lane), producer_generation, handoff_sha256, decisions '
    '[{file,status:approved|rejected,evidence:{path,sha256}}]. The controller applies '
    'each decision to a new immutable handoff once the producer is safely stopped. '
    'Do not hand approved status changes back to a stopped producer. Issue comments '
    'and prose approval alone do not complete the decision. Read the returned queue receipt. ')


def delegated(state, reviewer, lane):
    """Only the live cycle's exact frozen assignment grants decision authority."""
    if reviewer == lane['lane']:return False
    scopes=state.get('throughput_runtime',{}).get('autofill',{}).get('planner_pool',{}).get('scopes',{})
    for row in scopes.values():
        if row.get('review_authority') != 'shared-files-v1' or 'completed_at' in row:continue
        if row.get('spec',{}).get('lane',{}).get('lane') != reviewer:continue
        for target in row.get('support_targets',[]):
            if (target.get('lane')==lane['lane'] and target.get('generation')==lane['generation'] and
                    target.get('handoff')==lane.get('handoff') and target.get('root')==lane.get('root') and
                    target.get('native')==lane.get('native')):return True
    return False


def record(reg, reviewer, generation, key, producer_generation, handoff_sha256, decisions):
    require(isinstance(decisions,list) and decisions, 'Nonempty file decisions required')
    require(len({d['file'] for d in decisions}) == len(decisions), 'One decision per file required')
    for d in decisions:
        require(set(d)=={'file','status','evidence'} and d['status'] in ('approved','rejected'), 'Explicit scoped review required')
        reg.evidence(d['evidence'])
    from .provenance import stamp
    code=stamp()
    with reg.transaction() as state:
        owner=reg.lane(state,reviewer,generation)
        require(owner['state']=='running' and reg.probe(owner['process'])=='alive', 'Live integration reviewer required')
        lane=reg.lane(state,key,producer_generation)
        require(any(w.get('owner_lane')==reviewer and key in w.get('lanes',[]) for w in
                    state.get('throughput',{}).get('workstreams',{}).values()) or delegated(state,reviewer,lane),
                'Reviewer must own producer workstream or hold exact delegated assignment')
        require(lane['state'] in ('handoff_ready','integrating') and lane['handoff']['sha256']==handoff_sha256,
                'Exact current handoff required')
        data=reg._delivery_read_handoff(lane)
        require({d['file'] for d in decisions}<={r['file'] for r in data['shared_reviews']}, 'Unknown shared file')
        value=dict(reviewer=reviewer,reviewer_generation=generation,key=key,generation=producer_generation,
                   handoff_sha256=handoff_sha256,root=lane['root'],native=lane.get('native'),decisions=copy.deepcopy(decisions))
        identity=fingerprint(value)
        ledger=state.setdefault('shared_review_decisions',{})
        if identity not in ledger:
            ledger[identity]=dict(value,id=identity,status='pending',applied=0,current_handoff=handoff_sha256,at=reg.clock(),
                                  code_revision=code)
            reg.event(state,'shared_review_decision_queued',key,decision=identity)
        return copy.deepcopy(ledger[identity])


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
                                        'queued-'+row['id']+'-'+str(row['applied']),request)
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
