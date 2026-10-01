"""Retire failed helper turns without claiming their producer blockers resolved."""
import copy
from .handoff import Rejected


def tick(reg):
    snapshot=reg.snapshot()
    items=snapshot.get('throughput_runtime',{}).get('autofill',{}).get('items',{})
    helpers={i.get('lane') for i in items.values() if i.get('planner_helper')}
    for key in helpers:
        lane=snapshot['lanes'].get(key,{})
        outcome=lane.get('outcome') or {}
        if (lane.get('state')!='blocked' or lane.get('target_level')!='planning-only' or
                outcome.get('outcome')!='blocked' or not outcome.get('evidence') or
                not reg.recovery_safe(snapshot,lane)):continue
        try:
            evidence=reg.archive_evidence(outcome['evidence'])
            with reg.transaction() as state:
                current=state['lanes'][key]
                if (current['state']!='blocked' or current['generation']!=lane['generation'] or
                        current['revision']!=lane['revision'] or not reg.recovery_safe(state,current)):continue
                current.update(state='done',revision=current['revision']+1,
                    helper_retirement=dict(status='unresolved',outcome=copy.deepcopy(outcome),at=reg.clock()),
                    review_disposition=dict(summary='Unresolved helper turn archived; producer blocker remains open',
                        evidence=evidence,archived_evidence=evidence,resolved=False))
                data=state['throughput_runtime']['autofill']
                for row in data.get('planner_pool',{}).get('scopes',{}).values():
                    if row.get('spec',{}).get('lane',{}).get('lane')==key:
                        row.update(completed_at=reg.clock(),no_work_checked=True,no_work=None,
                                   unresolved_outcome=copy.deepcopy(outcome))
                for item in data['items'].values():
                    if item.get('lane')==key:item.update(status='needs_attention',ready=False)
                reg.event(state,'unresolved_helper_retired',key,evidence=evidence)
        except (Rejected,OSError,ValueError) as exc:
            reg.notice(key,'helper_retirement_blocked',dict(error=str(exc)))
