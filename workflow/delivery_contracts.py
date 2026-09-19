"""Typed prerequisite delivery, explicit accountability, and blocked-chain audit."""
import argparse
import copy
import json
from pathlib import Path
from .control import fingerprint
from .handoff import require, nonempty
from .planner_demand import is_helper

KINDS = {'source_integration', 'review_artifact', 'consumer_behavior'}


def owners(state, consumer):
    return sorted({s['owner_lane'] for s in state.get('throughput', {}).get('workstreams', {}).values()
                   if consumer in s.get('lanes', [])})


def source_pins(lane):
    return {k: (lane.get(k) or {}).get('head') for k in ('root', 'native')}


def contracts(state, consumer):
    return [r for r in state.get('delivery_contracts', {}).values()
            if r['consumer'] == consumer and r.get('active', True)]


def status(state, row):
    producer = state['lanes'].get(row['producer'], {})
    consumer = state['lanes'].get(row['consumer'], {})
    if row['owner'] not in owners(state, row['consumer']):return 'owner_changed'
    if row['kind'] == 'review_artifact':
        return 'delivered' if producer.get('state') == 'done' and producer.get('review_disposition') else 'awaiting_review'
    receipt = producer.get('integration')
    if producer.get('state') != 'done' or not receipt:
        return 'awaiting_source' if producer else 'missing_producer'
    if row['kind'] == 'source_integration':return 'delivered'
    records = [v for v in state.get('consumer_verifications', {}).values()
               if v['consumer'] == row['consumer'] and row['id'] in v.get('delivery_contracts', [])]
    if not records:return 'awaiting_consumer'
    latest = max(records, key=lambda v: v['created_at'])
    matches = any(p['lane'] == row['producer'] and
                  p.get('root_commit') == receipt.get('root_commit') and
                  p.get('native_commit') == receipt.get('native_commit')
                  for p in latest['producers'])
    if (not matches or latest.get('consumer_generation') != consumer.get('generation') or
            latest.get('source_pins') != source_pins(consumer)):return 'awaiting_consumer'
    if latest['status'] == 'passed' and latest.get('prerequisite_resolved') is True:
        if consumer.get('target_level') == 'runtime' and not latest.get('runtime'):return 'awaiting_consumer'
        return 'verified'
    return 'consumer_failed' if latest['status'] in ('failed', 'unverified') else 'awaiting_consumer'


def record(reg, consumer, consumer_generation, producer, kind, requirement, acceptance_check,
           owner, evidence, supersedes=None):
    require(kind in KINDS and nonempty(requirement) and nonempty(acceptance_check),
            'Typed requirement and concrete acceptance check required')
    archived = reg.archive_evidence(evidence)
    with reg.transaction() as state:
        lane = reg.lane(state, consumer, consumer_generation)
        require(lane['state'] != 'done' and not is_helper(consumer), 'Unfinished implementation consumer required')
        require(owner in owners(state, consumer), 'Owner must be the registered consumer workstream owner')
        require(producer in state['lanes'] and producer != consumer and not is_helper(producer)
                and producer != owner, 'Independent concrete implementation producer required')
        require(kind == 'review_artifact' or nonempty(acceptance_check), 'Source check required')
        graph = {}
        for r in state.get('delivery_contracts', {}).values():
            if r.get('active', True) and r['id'] != supersedes:graph.setdefault(r['consumer'], []).append(r['producer'])
        pending=[producer];seen=set()
        while pending:
            key=pending.pop();require(key != consumer, 'Circular delivery contract')
            if key not in seen:seen.add(key);pending.extend(graph.get(key, []))
        value=dict(consumer=consumer, producer=producer, kind=kind, requirement=requirement,
                   acceptance_check=acceptance_check, owner=owner, evidence=archived)
        identity=fingerprint(value)
        ledger=state.setdefault('delivery_contracts', {})
        if supersedes:
            old=ledger.get(supersedes)
            require(old and old['consumer']==consumer and old['owner']==owner,
                    'Only the same owned consumer contract may be superseded')
            require(supersedes != identity, 'Replacement must change the requirement')
            old.update(active=False, superseded_by=identity)
        if identity not in ledger:
            ledger[identity]=dict(value,id=identity,active=True,created_at=reg.clock())
            reg.event(state,'delivery_contract_recorded',consumer,contract=identity,owner=owner)
        return copy.deepcopy(ledger[identity])


def audit(state):
    from .dependency_classification import complete, queue_status
    from .internal_followup import queue_status as followup_status
    groups={};unclassified=[]
    for key,lane in state['lanes'].items():
        if lane['state']!='blocked' or is_helper(key) or key=='acceptance-backlog-planner':continue
        rows=contracts(state,key)
        if not complete(state,key) and (not rows or any(dep not in {r['requirement'] for r in rows} for dep in lane.get('dependencies', []))):
            unclassified.append(dict(consumer=key,issue=lane.get('issue'),owners=owners(state,key),
                                     dependencies=lane.get('dependencies',[])))
        for row in rows:
            phase=status(state,row)
            if phase in ('delivered','verified'):continue
            group=groups.setdefault((row['owner'],row['producer']),dict(owner=row['owner'],
                producer=row['producer'],consumers=[],requirements=[]))
            if key not in group['consumers']:group['consumers'].append(key)
            group['requirements'].append(dict(id=row['id'],consumer=key,kind=row['kind'],phase=phase,
                requirement=row['requirement'],acceptance_check=row['acceptance_check']))
    return dict(groups=sorted(groups.values(),key=lambda g:(-len(g['consumers']),g['producer'])),
                unclassified=unclassified, classification_queue=queue_status(state,unclassified), internal_followups=followup_status(state))


def owner_work(state, owner):
    work=[]
    report=audit(state)
    for group in report['groups']:
        if group['owner']!=owner:continue
        producer=state['lanes'].get(group['producer'],{})
        # Healthy executing producers retain ownership; no duplicate coordination turns.
        if producer.get('state') in ('ready','running','waiting_resource','handoff_ready','integrating'):continue
        work.append(dict(delivery_contract=group['producer'], **group,
            producer_state=producer.get('state'), source_pins=source_pins(producer),
            receipt=producer.get('integration'),report=producer.get('review_disposition')))
    from .action_routing import integration_work
    work.extend(integration_work(state,owner))
    return work


INSTRUCTION = (' Typed delivery_contract demand is owned by you through consumer verification. '
    'For classification_required entries, inspect the original evidence and identify each actual '
    'artifact or behavior requirement; register typed contracts only for evidenced concrete producers. '
    'Missing producers require an issue-backed executable proposal, not a guessed link to #186 '
    'or another blocked consumer. Unclassified requirements remain open and visible. '
    'A completed report does not satisfy source_integration or consumer_behavior. '
    'Inspect the named producer, exact missing artifact and original consumer check. '
    'For a review-only completed producer whose source is not delivered, prepare a bounded issue-backed '
    'delivery successor using its preserved source/evidence through normal proposal/admission gates; '
    'do not rewrite done lanes or fabricate integration. Reuse active scopes and serialize conflicting '
    'ownership. Register or replace the exact contract via python -m workflow.delivery_contracts '
    '--root <canonical-root> --request <json>: consumer, consumer_generation, producer, '
    'kind (source_integration|review_artifact|consumer_behavior), requirement, acceptance_check, '
    'owner (your registered workstream owner lane), evidence {path,sha256}, optional supersedes ID. '
    'Keep the named requirement when linking a replacement producer. No blanket prerequisite resolution, '
    'source acceptance or ADMIT from a report. Responsibility remains with the owner until verified. ')


def main():
    from .registry import Registry
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--request',type=Path)
    args=p.parse_args();reg=Registry(args.root/'output/workflow/registry.sqlite3',args.root)
    result=record(reg,**json.loads(args.request.read_text(encoding='utf-8-sig'))) if args.request else audit(reg.snapshot())
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
