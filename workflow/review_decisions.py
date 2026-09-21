"""Durable integrator-authored decisions; controller applies without producer handback."""
import copy
import json
from .control import fingerprint
from .provenance import cli
from .handoff import nonempty, require, Rejected
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


def delegated_review_enabled(config):
    """True while a delegated review worker still owns shared decisions."""
    config = config or {}
    if config.get('shared_review_routing', {}).get('enabled'):
        return True
    throughput = config.get('throughput', {})
    if throughput.get('autofill', {}).get('delegate_shared_reviews'):
        return True
    if config.get('delegate_shared_reviews'):
        return True
    return False


def sole_integrator(config):
    """Explicitly configured sole integration owner, or '' when unset."""
    value = (config or {}).get('sole_integrator', '')
    return value if isinstance(value, str) else ''


def require_sole_authority(config, reviewer):
    """Gate the reviewer identity; delegated mode keeps existing behavior."""
    if delegated_review_enabled(config):
        require(nonempty(reviewer), 'Version, reviewer and explicit review disposition required')
        return 'delegated'
    owner = sole_integrator(config)
    require(nonempty(owner), 'Sole integrator not configured (set sole_integrator)')
    require(reviewer == owner, 'Reviewer is not the configured sole integrator')
    return 'sole'


def check_source_pins(lane, generation, source):
    """Exact producer generation/source pins before touching the writer."""
    require(lane is not None, 'Unknown producer lane')
    require(lane['generation'] == generation, 'Stale producer generation')
    if source is None:
        return
    require(isinstance(source, dict), 'Source pins required')
    if 'root' in source:
        require(source['root'] == lane['root'], 'Producer root source changed')
    if 'native' in source:
        require(source['native'] == lane['native'], 'Producer native source changed')


def apply_sole_disposition(registry, config, key, generation, revision, version,
                           handoff_sha256, file, status, reviewer, evidence, source=None):
    """Record one explicit per-file decision into a new immutable handoff.

    Reduced mode (delegated review workers disabled) authenticates the
    configured sole integration owner from config instead of a live reviewer
    lane, then reuses the single fenced dispose_review writer. The decision is
    appended to the approvals ledger so integration still reads authenticated
    truth, and gameplay acceptance is never promoted.
    """
    from .storage import read_record
    from .provenance import stamp
    require(status in ('approved', 'rejected') and nonempty(version),
            'Version and explicit review disposition required')
    mode = require_sole_authority(config, reviewer)
    check_source_pins(registry.status()['lanes'].get(key), generation, source)
    registry.evidence(evidence)
    request = dict(file=file, status=status, reviewer=reviewer, evidence=evidence,
                   handoff_sha256=handoff_sha256)
    code = stamp()  # Warm the per-process revision before taking the writer lock.
    before = read_record(registry, ('lanes',), key)
    require(isinstance(before, dict), 'Unknown lane: ' + str(key))
    # The reviewed-diff digest is supporting evidence; reduced mode must also work
    # where the canonical root is not a git checkout (e.g. isolated fixtures).
    try:
        digest = approvals.diff(registry.root, before, file)
    except (Rejected, OSError, ValueError):
        name, path = approvals.split(before, file)
        digest = (name, path, None)
    identity = dict(lane=reviewer, source=mode, generation=generation, launch=None,
                    models=[], model=None, session=None)
    with registry.transaction() as state:
        lane = registry.lane(state, key, generation)
        if fingerprint([key, generation, version]) in registry.delivery(state)['dispositions']:
            return registry._dispose_review(state, key, generation, revision, version, request)
        require(approvals.pins(lane) == approvals.pins(before),
                'Producer pins changed while hashing the reviewed diff')
        require(lane['state'] in ('running', 'handoff_ready', 'integrating') and lane.get('handoff') and
                lane['handoff']['sha256'] == handoff_sha256, 'Review source hash changed')
        row = approvals.review_row(registry, state, 'dispose_review', lane, file, digest, status,
                                   evidence, identity, code, handoff_sha256=handoff_sha256)
        record = registry._dispose_review(state, key, generation, revision, version, request, row['id'])
    lane = registry.status()['lanes'][key]
    require(lane['handoff']['result']['gameplay_accepted'] is False,
            'Disposition must never promote gameplay acceptance')
    return record


def main():
    import argparse
    from pathlib import Path
    from .registry import Registry
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--request',type=Path,required=True)
    a=p.parse_args();reg=Registry(a.root/'output/workflow/registry.sqlite3',a.root)
    print(json.dumps(record(reg,**json.loads(a.request.read_text(encoding='utf-8-sig'))),indent=2))

if __name__=='__main__':main()
