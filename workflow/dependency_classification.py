"""Fenced, independently assigned dependency classification (not resolution)."""
import copy
import json
from .control import fingerprint
from .provenance import cli
from .delivery_contracts import source_pins
from .handoff import require, nonempty


def signature(lane):
    return fingerprint(dict(pins=source_pins(lane), dependencies=sorted(lane.get('dependencies', [])),
                            evidence=(lane.get('outcome') or {}).get('evidence')))


def complete(state, key):
    lane=state['lanes'][key]
    for row in state.get('dependency_classifications', {}).values():
        if row['consumer']!=key or row['snapshot']!=signature(lane):continue
        if all(not d.get('contract_id') or state.get('delivery_contracts',{}).get(d['contract_id'],{}).get('active',False)
               for d in row['dispositions']):return True
    return False


def queue_status(state, pending):
    attempts=state.get('throughput_runtime',{}).get('autofill',{}).get('prerequisite_recovery',{})
    result=[]
    for row in pending:
        key=row['consumer'];identity='classification-v2:'+fingerprint([key,signature(state['lanes'][key])])
        attempt=attempts.get(identity,{})
        worker=state['lanes'].get(attempt.get('lane'),{})
        status=('pending' if not attempt else 'needs_attention' if worker.get('state') in ('done','blocked') else 'assigned')
        result.append(dict(consumer=key,status=status,helper=attempt.get('lane'),assignment=identity))
    return result



def allocations(state, helpers, records, prior=None):
    from .delivery_contracts import audit
    result=dict(prior or {})
    reserved={k for r in result.values() for k in r['request']['lanes']+r['request'].get('followup_owner_lanes',[])}
    for row in records.values():
        if 'completed_at' not in row:
            reserved.update(row.get('recovery_targets', []))
            reserved.update(row.get('followup_owner_lanes', []))
            reserved.update(t['lane'] for t in row.get('support_targets', []))
    available=[h for h in helpers if h['scope'] not in result and not h.get('kind') and
               (not records.get(h['scope']) or 'completed_at' in records[h['scope']])]
    attempts=state.get('throughput_runtime', {}).get('autofill', {}).get('prerequisite_recovery', {})
    for item in sorted(audit(state)['unclassified'], key=lambda r:(state['lanes'][r['consumer']].get('progress_at',0),r['consumer'])):
        key=item['consumer'];lane=state['lanes'][key]
        evidence=(lane.get('outcome') or {}).get('evidence')
        token=signature(lane);identity='classification-v2:'+fingerprint([key,token])
        if key in reserved or not evidence or identity in attempts:continue
        if any(x.get('lane')==key and x.get('status') in ('intent','spawned','running','exiting')
               for x in state.get('control',{}).get('launches',{}).values()):continue
        if not available:break
        h=available.pop(0)
        result[h['scope']]=dict(key=identity,input_snapshot=token,request=dict(id=identity,
            status='dependency-classification',scope=h['scope'],report=copy.deepcopy(evidence),lanes=[key],
            issues=[lane['issue']],classification=dict(consumer=key,snapshot=token,dependencies=lane.get('dependencies',[])),
            required_result=INSTRUCTION))
        reserved.add(key)
    return result


def record(reg, reviewer, generation, consumer, snapshot, dispositions, evidence):
    from .support_actions import assignment, same
    archived=reg.archive_evidence(evidence)
    with reg.transaction() as state:
        worker=reg.lane(state,reviewer,generation)
        require(worker['state']=='running','Classifier must be running at the current generation')
        row=assignment(state,reviewer);target=row.get('classification_target',{})
        require(target.get('consumer')==consumer and target.get('snapshot')==snapshot,'Exact classifier assignment required')
        lane=state['lanes'][consumer]
        require(lane['state']=='blocked' and signature(lane)==snapshot,'Classification inputs changed')
        deps=lane.get('dependencies',[]) or ['<unspecified>']
        require(isinstance(dispositions,list) and len(dispositions)==len(set(deps)) and
                {d.get('requirement') for d in dispositions}==set(deps),'Every dependency needs exactly one disposition')
        for d in dispositions:
            require(nonempty(d.get('check')) and nonempty(d.get('reason')),'Concrete consumer check and evidence rationale required')
            contract=state.get('delivery_contracts',{}).get(d.get('contract_id'))
            action=state.get('support_actions',{}).get(d.get('action_id'))
            internal=d.get('internal_blocker')
            require(sum(bool(x) for x in (d.get('contract_id'),d.get('action_id'),internal))==1,
                    'Exactly one contract, action or internal blocker required')
            if internal:
                from .internal_followup import validate_finding
                validate_finding(state,consumer,internal)
            elif contract:
                require(contract.get('active',True) and contract['consumer']==consumer and
                        contract['requirement']==d['requirement'],'Matching active typed contract required')
            else:
                require(action and action['reviewer']==reviewer and action['generation']==generation and
                        action['key']==consumer and same(action['target'],lane) and
                        action['action'] in ('proposal','external'),'Validated executable proposal or exact external input required')
        value=dict(consumer=consumer,snapshot=snapshot,reviewer=reviewer,generation=generation,
                   dispositions=copy.deepcopy(dispositions),evidence=archived)
        identity=fingerprint(value)
        state.setdefault('dependency_classifications',{})[identity]=dict(value,id=identity,at=reg.clock())
        reg.event(state,'dependency_classified',consumer,classification=identity,reviewer=reviewer)
        return value


def require_outcomes(state, reviewer):
    from .support_actions import assignment
    target=assignment(state,reviewer).get('classification_target')
    if not target:return
    lane=state['lanes'][target['consumer']]
    # A changed target is retained as an explicit stale assignment; never classify old inputs.
    if lane['state']!='blocked' or signature(lane)!=target['snapshot']:return
    require(any(r['reviewer']==reviewer and r['consumer']==target['consumer'] and
                r['snapshot']==target['snapshot'] and r['generation']==state['lanes'][reviewer]['generation']
                for r in state.get('dependency_classifications',{}).values()),
            'Record complete dependency classification before finishing review-ready')


INSTRUCTION=('CLASSIFICATION ASSIGNMENT: classify EVERY exact dependency of the assigned consumer. '
 'For concrete independent producers, register typed contracts via workflow.delivery_contracts using the '
 'registered consumer workstream owner; inspect its CLI and original evidence. Classification does NOT '
 'require implementing the prerequisite or staging a proposal. For an unresolved internal dependency use '
 'internal_blocker:{kind:missing_producer|owner_blocked|integration_review, missing:<precise artifact or '
 'behavior>, next_action:<bounded concrete follow-up with deliverable>, inspected_lanes:[<existing lane '
 'IDs examined, may be empty for missing_producer>], owner_lane:<existing implementation lane for '
 'owner_blocked/integration_review; omit for missing_producer>}. Explain the evidence in reason and '
 'the hashed report. Do not invent a user-owned blocker, self-referential contract or duplicate scope. '
 'Internal findings create separate bounded preparation demand; consumers remain blocked. Existing '
 'validated proposals may still be referenced through action_id. Exact user assets/decisions require '
 'an external support action. '
 'Then run '+cli('dependency_classification')+' --root <canonical-root> --request <json>, with '
 'reviewer (your lane), generation, consumer, snapshot (assigned classification snapshot), evidence '
 '{path,sha256}, dispositions [{requirement (exact dependency, or <unspecified> if none), check '
 '(original consumer acceptance command and expected result), reason, contract_id OR action_id OR internal_blocker}]. '
 'No-work/referral reports cannot complete this assignment. This classifies dependencies; it never '
 'resolves them, accepts source, or grants ADMIT. Existing healthy owners must be reused.')


def main():
    import argparse
    from pathlib import Path
    from .registry import Registry
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--request',type=Path,required=True)
    a=p.parse_args();print(json.dumps(record(Registry(a.root/'output/workflow/registry.sqlite3',a.root),
                      **json.loads(a.request.read_text(encoding='utf-8-sig'))),indent=2))

if __name__=='__main__':main()
