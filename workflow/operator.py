"""Compact, read-only operator entrypoint: python -m workflow.operator."""
import argparse
import json
import time
from pathlib import Path

from .integration_wakeup import receipt_gaps
from .registry import Registry
from .handoff import local_path, digest


def report(state, now, root=None, on_disk=None):
    """on_disk is the controller checkout's revision; found from its process and git only when root is given."""
    from .delivery_contracts import audit
    from .provenance import claimed, warnings
    lanes = state.get('lanes', {})
    autofill = state.get('throughput_runtime', {}).get('autofill', {})
    actions = []
    for key, row in state.get('admission_reconciliation', {}).items():
        if row['status'] == 'pending' and lanes.get(key, {}).get('state') != 'done':
            actions.append(dict(priority=0, lane=key, reason=row['reason'],
                next_action='Integration owner: complete delivery receipts or record a pinned admission disposition',
                family=row['family'], token=row['token']))
    if root is not None:
        for key, lane in lanes.items():
            receipt = lane.get('integration') or {}
            if not receipt or lane.get('native') is None:
                continue
            try:
                path = local_path(root, receipt.get('export_evidence'))
                if digest(path) != receipt.get('export_sha256'):
                    reason = 'Recorded export evidence hash mismatch'
                else:
                    try:
                        proof = json.loads(path.read_text(encoding='utf-8-sig'))
                    except (ValueError, UnicodeError):
                        proof = None
                    reason = ('Recorded export evidence says none-performed'
                              if isinstance(proof, dict) and proof.get('action') == 'none-performed' else None)
            except (OSError, ValueError, TypeError):
                reason = 'Recorded export evidence unavailable'
            if reason:
                actions.append(dict(priority=0,lane=key,issue=lane.get('issue'),reason=reason,
                    next_action='Integration lead must produce actual export proof; preserve historical receipt and record corrective evidence'))
    gaps = [g for stream in state.get('throughput', {}).get('workstreams', {})
            for g in receipt_gaps(state, stream)]
    for gap in gaps:
        lane = lanes[gap['receipt_gap']]
        actions.append(dict(priority=0, lane=lane['lane'], issue=lane.get('issue'),
            reason='Closed batch lacks per-lane integration receipt',
            next_action=('Verify landed pins and validation, obtain actual native export evidence, then checkpoint integrating and Registry.integrate'
                         if gap['needs_native_export'] else
                         'Verify landed pins and validation, then checkpoint integrating and Registry.integrate'),
            batch=gap['closed_batch'], generation=gap['generation'], revision=gap['revision']))
    for key, item in autofill.get('items', {}).items():
        if item.get('phase') == 'enqueued' or item.get('status') in ('completed', 'superseded'):
            continue
        actions.append(dict(priority=1 if item.get('ready') or item.get('dependency_kind') == 'worker_capacity' else 2,
            item=key, lane=item.get('lane'), reason=item.get('reason') or item.get('status'),
            next_action=('Check authorized worker adaptation profiles against spec role/capabilities; retain ownership checks'
                         if item.get('dependency_kind') == 'worker_capacity' else
                         'Inspect prepared spec and planner publication feedback; controller owns admission')))
    blocked = [dict(lane=k, issue=l.get('issue'), generation=l.get('generation'),
                    dependencies=l.get('dependencies', []), next_action=l.get('next_action'),
                    evidence=(l.get('outcome') or {}).get('evidence'))
               for k, l in lanes.items() if l.get('state') == 'blocked' and k != 'acceptance-backlog-planner']
    handoffs = sorted([dict(lane=k, issue=l.get('issue'), state=l['state'],
                            age_seconds=max(0, now-(l.get('handoff_at') or now)))
                       for k, l in lanes.items() if l.get('state') in ('handoff_ready', 'integrating')],
                      key=lambda x: -x['age_seconds'])
    pool = autofill.get('planner_pool', {})
    control = state.get('control') or {}
    if root is not None and on_disk is None:
        from .service import code_status
        code = code_status(control)
    else:
        running = claimed(control)
        code = dict(running=running, on_disk=on_disk, warnings=warnings(running, on_disk))
    return dict(at=now, code=code, delivery_audit=audit(state), actions=sorted(actions, key=lambda x:(x['priority'],x.get('lane') or '')),
                handoffs=handoffs, blocked=blocked,
                planning={k:pool.get(k) for k in ('active','target','target_reason','recovery_active','recovery_candidates','sleeping_scopes','cooling_scopes')},
                worker_count=len(state.get('throughput', {}).get('workers', {})))


def code_line(code):
    """One provenance line; dirty or mismatched code is loud."""
    running = code.get('running') or {}
    line = f"Code: running {(running.get('sha') or 'unknown')[:12]} dirty={running.get('dirty', 'unknown')}"
    if code.get('on_disk'):
        line += f" | on disk {(code['on_disk'].get('sha') or 'unknown')[:12]} dirty={code['on_disk'].get('dirty')}"
    return line + ''.join('\n!!! WARNING: ' + w for w in code.get('warnings', []))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--json', action='store_true', help='Machine-readable work and blocker details')
    args = parser.parse_args()
    root = args.root.resolve()
    data = report(Registry(root/'output/workflow/registry.sqlite3', root).snapshot(), time.time(), root)
    if args.json:
        print(json.dumps(data, indent=2))
        return
    print(code_line(data['code']))
    print(f"Workers: {data['worker_count']} | Handoffs: {len(data['handoffs'])} | Blocked lanes: {len(data['blocked'])}")
    p = data['planning']
    print(f"Planning: {p['active']}/{p['target']} — {p['target_reason']}")
    for action in data['actions']:
        print(f"\n{action.get('lane')} : {action['reason']}\n  Next: {action['next_action']}")
    print('\nUse --json for exact batch/generation pins and blocked consumer evidence.')
    print('Operating guide: docs/PIKMIN2_WORKFLOW_OPERATOR.md')


if __name__ == '__main__':
    main()
