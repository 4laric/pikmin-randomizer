"""Admission-triggered, source-pinned cleanup; admission is never a delivery receipt."""
import argparse
import copy
import json
import re
from pathlib import Path
from .control import fingerprint
from .handoff import require


def pins(lane):
    return dict(generation=lane['generation'], revision=lane['revision'],
                root=(lane.get('root') or {}).get('head'),
                native=(lane.get('native') or {}).get('head'))


def audit(reg, admission, settings):
    if admission.get('status') != 'observed':
        return []
    accepted = set(admission.get('ids', []))
    families = settings.get('lane_families', {})
    snapshot = reg.snapshot()
    rows = {}
    for key, lane in snapshot['lanes'].items():
        family = families.get(key, lane.get('admission_family'))
        if family is None and lane.get('target_level') not in ('planning-only', 'continuous backlog planning'):
            # Discovery only: a name match queues human/agent review, never automatic closure.
            text = key + ' ' + lane.get('scope', '')
            matches = {f['id'] for f in admission.get('families', []) if
                re.search(r'(?<![a-zA-Z0-9])' + re.escape(f['enum']) + r'[-_ ]?' + str(f['id']) + r'(?![0-9])', text, re.I)
                or re.search(r'\b' + re.escape(f['name']) + r'\b', text, re.I)}
            if len(matches) == 1:
                family = matches.pop()
        if family not in accepted or lane['state'] == 'done':
            continue
        target = pins(lane)
        token = fingerprint([key, family, target])
        previous = snapshot.get('admission_reconciliation', {}).get(key, {})
        if previous.get('token') == token:
            rows[key] = previous
            continue
        rows[key] = dict(lane=key, family=family, token=token, pins=target,
            status='pending', source=admission.get('source'),
            reason='Family admitted; reconcile remaining acceptance scope and source delivery',
            at=reg.clock())
    with reg.transaction() as state:
        table = state.setdefault('admission_reconciliation', {})
        for key, row in rows.items():
            if pins(state['lanes'][key]) == row['pins'] and state['lanes'][key]['state'] != 'done':
                table[key] = row
        for key, row in table.items():
            if state['lanes'].get(key, {}).get('state') == 'done' and row['status'] == 'pending':
                row.update(status='completed', completed_at=reg.clock())
    return list(rows.values())


def resolve(reg, request, admission):
    """The live integration owner may retain follow-up work or retire superseded scope."""
    evidence = reg.archive_evidence(request['evidence'])
    require(request.get('decision') in ('retain', 'superseded'), 'Unknown admission disposition')
    require(isinstance(request.get('reason'), str) and request['reason'].strip(), 'Reason required')
    require(admission.get('status') == 'observed', 'Canonical admission unavailable')
    with reg.transaction() as state:
        lane = state['lanes'][request['lane']]
        row = state.get('admission_reconciliation', {}).get(request['lane'])
        require(row and row['status'] == 'pending' and row['token'] == request['token'] and
                row['pins'] == pins(lane), 'Admission audit changed; reread current pins')
        require(row['family'] in admission.get('ids', []), 'Family no longer admitted')
        owners = {s['owner_lane'] for s in state.get('throughput', {}).get('workstreams', {}).values()
                  if request['lane'] in s.get('lanes', [])}
        require(request['reviewer'] in owners, 'Only the registered integration owner may decide')
        reviewer = reg.lane(state, request['reviewer'], request['reviewer_generation'])
        require(reviewer['state'] == 'running' and reg.probe(reviewer['process']) == 'alive',
                'Reviewer must be the live current integration generation')
        require(lane['state'] == 'blocked' and reg.recovery_safe(state, lane), 'Target must be stopped and blocked')
        require(not lane.get('handoff') and not any(
            b.get('state') == 'claimed' and request['lane'] in b.get('candidates', {})
            for b in state.get('throughput', {}).get('batches', {}).values()), 'Finish pending delivery first')
        require(not any(x['lane'] == request['lane'] and x['status'] in ('intent','spawned','running','exiting')
                for x in state.get('control', {}).get('launches', {}).values()), 'Launch still in flight')
        if request['decision'] == 'superseded':
            require(request.get('no_remaining_delivery') is True,
                    'Owner must verify no source delivery or export remains outstanding')
            require(request.get('covered_criteria'), 'Explain how admission covers the lane acceptance criteria')
            lane.update(state='done', revision=lane['revision']+1,
                admission_retirement=dict(family=row['family'], evidence=evidence,
                    covered_criteria=request['covered_criteria'], prior_outcome=copy.deepcopy(lane.get('outcome'))),
                review_disposition=dict(summary=request['reason'], evidence=evidence,
                    archived_evidence=evidence, resolved=True, superseded=True))
            pool = state.get('throughput', {})
            for assignment in pool.get('assignments', {}).values():
                if assignment['lane'] == request['lane'] and assignment['status'] in ('assigned','dispatched','parked'):
                    assignment['status'] = 'completed'
                    if assignment.get('job') in pool.get('jobs', {}):
                        pool['jobs'][assignment['job']]['status'] = 'completed'
        else:
            require(request.get('next_action'), 'Retained work needs a concrete next action')
        row.update(status=request['decision'], reason=request['reason'], evidence=evidence,
                   next_action=request.get('next_action'), reviewer=request['reviewer'], decided_at=reg.clock())
        reg.event(state, 'admission_reconciled', request['lane'], decision=request['decision'], evidence=evidence)
        return copy.deepcopy(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    from .registry import Registry
    from .admission_progress import snapshot
    config = json.loads((args.root/'output/workflow/controller/config.json').read_text(encoding='utf-8-sig'))
    reg = Registry(args.root/'output/workflow/registry.sqlite3', args.root)
    print(json.dumps(resolve(reg, json.loads(args.request.read_text(encoding='utf-8-sig')),
                             snapshot(args.root, config.get('monster_admission', {})))))


if __name__ == '__main__':
    main()
