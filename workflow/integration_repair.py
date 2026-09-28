"""Return isolated handoffs to their existing owner for bounded source repair."""
import copy
import json

from .batching import isolated_handoff
from .control import fingerprint
from .handoff import Rejected, require


def invalid_handoffs(reg):
    """Unusable evidence is producer repair demand, not an integration backlog."""
    snapshot=reg.snapshot()
    for key,lane in snapshot['lanes'].items():
        if lane['state']!='handoff_ready' or not lane.get('handoff'):continue
        batches=snapshot.get('throughput',{}).get('batches',{})
        if isolated_handoff(batches,key,lane) or not reg.recovery_safe(snapshot,lane):continue
        if any(b.get('state')=='claimed' and key in b.get('candidates',{}) and
               key not in b.get('isolated',{}) for b in batches.values()):continue
        candidate={f:copy.deepcopy(lane.get(f)) for f in ('generation','revision','root','native','handoff')}
        try:
            reg._delivery_read_handoff(lane)
            continue
        except (Rejected,OSError,ValueError,KeyError) as exc:
            reason='Invalid handoff evidence: '+str(exc)
        with reg.transaction() as state:
            current=state['lanes'].get(key,{})
            if current.get('state')!='handoff_ready' or any(current.get(f)!=v for f,v in candidate.items()):continue
            if not reg.recovery_safe(state,current):continue
            if any(b.get('state')=='claimed' and key in b.get('candidates',{}) and
                   key not in b.get('isolated',{}) for b in state.get('throughput',{}).get('batches',{}).values()):continue
            current['review_repair']=dict(candidate=candidate,pin=dict(batch_id=None,
                generation=lane['generation'],revision=lane['revision'],reason=reason,
                handoff=copy.deepcopy(lane['handoff']),invalid_evidence=True))
            reg.event(state,'invalid_handoff_repair_requested',key,reason=reason)


def review_rejections(reg):
    """Convert explicit, hashed REQUEST CHANGES dispositions into repair demand."""
    for key, lane in reg.snapshot()['lanes'].items():
        if lane['state'] != 'handoff_ready' or not lane.get('handoff'): continue
        candidate = {f: copy.deepcopy(lane.get(f)) for f in
                     ('generation', 'revision', 'root', 'native', 'handoff')}
        if (lane.get('review_repair') or {}).get('candidate') == candidate: continue
        try:
            path = reg.evidence({f: lane['handoff'][f] for f in ('path', 'sha256')})
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            rejected = [r for r in data.get('shared_reviews', []) if r.get('status') == 'rejected']
            if not rejected: continue
            for review in rejected:
                require(review.get('reviewer') and review.get('evidence'), 'Attributed rejection evidence required')
                for ref in review['evidence']: reg.evidence(data['evidence'][ref])
            pin = dict(batch_id=None, generation=lane['generation'], revision=lane['revision'],
                       reason='Shared review requested changes', reviews=rejected,
                       handoff=lane['handoff'], evidence=data['evidence'])
            with reg.transaction() as state:
                current = reg.lane(state, key, lane['generation'], lane['revision'])
                require(current['state'] == 'handoff_ready' and all(current.get(f) == v for f,v in candidate.items()),
                        'Review candidate changed')
                current['review_repair'] = dict(candidate=candidate, pin=pin)
                reg.event(state, 'review_repair_requested', key)
        except (Rejected, OSError, ValueError, KeyError) as exc:
            reg.notice(key, 'review_repair_invalid', dict(error=str(exc)))


def repair_pin(state, lane, reason, reg=None):
    batches = state.get('throughput', {}).get('batches', {})
    pin = isolated_handoff(batches, lane['lane'], lane)
    require(lane['state'] == 'handoff_ready' and pin is not None,
            'Exact isolated handoff required for repair')
    require(reason == 'integration-repair:' + fingerprint(pin), 'Repair isolation pins changed')
    if reg is not None and pin.get('reviews'):
        reg.evidence(pin['handoff'])
        for review in pin['reviews']:
            for ref in review['evidence']: reg.evidence(pin['evidence'][ref])
    if reg is not None and pin.get('independent_action'):
        action=state.get('support_actions',{}).get(pin['independent_action'])
        require(action and action['key']==lane['lane'] and action['action']=='repair','Recorded independent diagnosis required')
        reg.evidence(action['evidence'])
    require(not any(b.get('state') == 'claimed' and lane['lane'] in b.get('candidates', {})
                    and lane['lane'] not in b.get('isolated', {}) for b in batches.values()),
            'Handoff is claimed for integration')
    return pin


def tick(controller):
    from .handoff_representation import tick as represent
    represent(controller)
    reg = controller.reg
    if controller.config.get('invalid_handoff_recovery',False):invalid_handoffs(reg)
    review_rejections(reg)
    snapshot = reg.snapshot()
    launches = snapshot.get('control', {}).get('launches', {}).values()
    for key, lane in snapshot['lanes'].items():
        if lane['state'] != 'handoff_ready' or key not in controller.config['lanes']: continue
        pin = isolated_handoff(snapshot.get('throughput', {}).get('batches', {}), key, lane)
        if not pin or not reg.recovery_safe(snapshot, lane) or not controller.available(key): continue
        if any(l['lane'] == key and l['status'] in ('intent', 'spawned', 'running', 'exiting') for l in launches): continue
        # Repeated failed repairs require adjudication, not an endless model loop.
        independent=pin.get('independent_action')
        exhausted=(any(l['lane']==key and l['reason']=='integration-repair:'+fingerprint(pin) for l in launches)
                   if independent else sum(l['lane'] == key and l['reason'].startswith('integration-repair:') for l in launches)>=2)
        if exhausted:
            reg.notice(key, 'integration_repair_exhausted', pin)
            continue
        try:
            reg.plan_launch(key, 'integration-repair:' + fingerprint(pin),
                'Your handoff failed evidence validation or received an explicit review rejection/integration isolation. '
                'For invalid evidence, restore only exact hash-matching original bytes or produce a new truthful '
                'packet and newly pinned handoff. Never substitute a different archived packet under an old hash. '
                'Separate reviews for actual changes from future follow-on work outside this slice. Read the hashed '
                'review evidence and implement the requested correction. Repair this existing issue and lane within '
                'your registered owned files; do not create a duplicate lane or change shared checkouts. '
                'Read the isolation evidence and current destination workstream pins. Preserve the old '
                'candidate commits. In your private worktree prepare a self-contained replacement against '
                'the destination, including prerequisites that existed only in your original base. '
                'Verify the resulting patch and tests against that destination, preserve existing guards, '
                'and supply required private leased build evidence. Submit a newly pinned handoff through '
                'the normal API. If repair requires files outside your scope, finish BLOCKED with the exact '
                'required owner action; do not resubmit unchanged evidence. No gameplay acceptance or ADMIT. '
                'Isolation: ' + str(pin), controller.config['models'])
        except Rejected as exc:
            reg.notice(key, 'integration_repair_blocked', dict(isolation=pin, reason=str(exc)))
