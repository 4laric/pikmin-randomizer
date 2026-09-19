"""Group typed prerequisite preparation on existing spare planning partitions."""
import copy
from .control import fingerprint
from .delivery_contracts import audit, source_pins, contracts, status


def allocations(state, helpers, records):
    data = state.get('throughput_runtime', {}).get('autofill', {})
    attempts = data.get('prerequisite_recovery', {})
    def outstanding_proposal(action):
        item=data.get('items',{}).get(action.get('details',{}).get('proposal_id'),{})
        lane=state['lanes'].get(item.get('lane'),{})
        if lane:return lane.get('state') in active or lane.get('state')=='review_ready'
        return item.get('status') not in ('completed','rejected','superseded')
    reserved = set()
    for row in records.values():
        if 'completed_at' not in row:
            reserved.update(row.get('recovery_targets', []))
            reserved.update(row.get('followup_owner_lanes', []))
            reserved.update(t['lane'] for t in row.get('support_targets', []))
    active = {'ready', 'running', 'waiting_resource', 'reconciling', 'handoff_ready', 'integrating'}
    result = {}
    available = [h for h in helpers if not h.get('kind') and
                 (not records.get(h['scope']) or 'completed_at' in records[h['scope']])]
    for group in audit(state)['groups']:
        producer = state['lanes'].get(group['producer'], {})
        # Prepare the upstream missing delivery before its blocked consumer.
        # Otherwise downstream impact can select the same blocked wiring owner
        # repeatedly while the source prerequisite never gets a producer.
        if any(status(state,r) not in ('delivered','verified') for r in contracts(state,group['producer'])):
            continue
        targets = set(group['consumers']) | {group['producer']}
        if targets & reserved or producer.get('state') in active: continue
        if any(x.get('lane') in targets and x.get('status') in ('intent','spawned','running','exiting')
               for x in state.get('control', {}).get('launches', {}).values()): continue
        if any(a.get('key') in targets and a.get('action') == 'proposal' and outstanding_proposal(a)
               for a in state.get('support_actions', {}).values()): continue
        # Source/consumer semantics, not report wording, generation or heartbeat.
        signature = fingerprint(dict(producer=group['producer'], pins=source_pins(producer),
            receipt=producer.get('integration'),
            requirements=sorted((r['consumer'], r['kind'], r['requirement'], r['acceptance_check'], r['phase'])
                                for r in group['requirements'])))
        identity = 'delivery-recovery:' + signature
        if identity in attempts: continue
        # Old recovery is not a license to repeat forever. One new typed delivery
        # preparation per semantic chain; changed source or requirement rearms it.
        evidence = next(((state['lanes'][key].get('outcome') or {}).get('evidence')
                         for key in group['consumers'] if (state['lanes'][key].get('outcome') or {}).get('evidence')), None)
        if not evidence or not available: continue
        helper = available.pop(0)
        result[helper['scope']] = dict(key=identity, input_snapshot=signature,
            request=dict(id=identity, status='typed-delivery-recovery', scope=helper['scope'],
                report=copy.deepcopy(evidence), lanes=sorted(targets),
                issues=sorted({state['lanes'][key]['issue'] for key in targets if key in state['lanes']}),
                delivery_group=copy.deepcopy(group),
                source_pins=source_pins(producer),
                required_result='Prepare a publishable issue-backed delivery successor for a review-only done '
                    'producer, or a concrete repair of the named unresolved source/consumer gap. Reuse all '
                    'healthy owners and already published proposals. Preserve completed records. Include '
                    'exact source pins, owned files, original consumer checks, and the contract IDs to '
                    'supersede after admission. A referral back to the integrator is not a deliverable.'))
        reserved.update(targets)
    return result
