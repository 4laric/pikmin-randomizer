"""Wake the existing stopped integration owner only when new work needs it."""
import copy
import re

from .control import fingerprint
from .handoff import Rejected
from .batching import isolated_handoff
from .planner_demand import is_helper
from .review_followup import pin as review_pin, deferred, dependency_pin


def demand_token(work):
    # Admission queue churn must not reset the bounded retry budget for the same
    # packet/handoff. Admission-only recovery still has its own stable identity.
    substantive=[item for item in work if any(k in item for k in
        ('handoff','review','batch','shared_review','receipt_gap','admission_audit','prepared_action','delivery_contract'))]
    return 'integration-demand:'+fingerprint(sorted(substantive or work,key=str))


def receipt_gaps(state, stream):
    """Closed batch metadata is not a per-lane source integration receipt."""
    result = []
    for key, batch in state.get('throughput', {}).get('batches', {}).items():
        if batch.get('state') != 'closed' or batch.get('workstream') != stream:
            continue
        for name, pin in batch.get('candidates', {}).items():
            lane = state.get('lanes', {}).get(name, {})
            if (name in batch.get('isolated', {}) or lane.get('integration') or
                    lane.get('state') not in ('handoff_ready', 'integrating') or
                    lane.get('generation') != pin.get('generation')):
                continue
            result.append(dict(receipt_gap=name, closed_batch=key,
                               generation=lane['generation'], revision=lane['revision'],
                               needs_native_export=lane.get('native') is not None))
    return result


def shared_reviews(snapshot, stream, launches):
    """Route explicit shared-owner requests without treating them as handoffs."""
    result = []
    for key in stream.get('lanes', []):
        if is_helper(key) or key == stream.get('owner_lane'):
            continue
        lane = snapshot['lanes'].get(key, {})
        from .shared_decisions import approved_scope, requested
        if lane and approved_scope(snapshot,lane):continue
        request = lane.get('next_action', '') + ' ' + ' '.join(lane.get('dependencies', []))
        if (lane.get('integration') or lane.get('state') not in ('blocked', 'done') or
                (lane.get('state') == 'done' and not lane.get('review_disposition')) or
                not requested(request)):
            continue
        pins = {k:(lane.get(k) or {}).get('head') for k in ('root', 'native')}
        identity = fingerprint([key, request, pins])
        if sum(identity in x.get('shared_review_requests', []) for x in launches) >= 2:
            continue
        result.append(dict(shared_review=key, shared_review_id=identity, issue=lane.get('issue'),
                           pins=pins, request=request))
    return result


def tick(controller):
    reg = controller.reg
    snapshot = reg.snapshot()
    pool = snapshot.get('throughput', {})
    items = snapshot.get('throughput_runtime', {}).get('autofill', {}).get('items', {})
    prior_launches = list(snapshot.get('control', {}).get('launches', {}).values())
    demand = {}
    for name, stream in pool.get('workstreams', {}).items():
        owner = stream.get('owner_lane')
        work = [dict(stream=name, item=k, spec=v.get('spec_hash')) for k, v in items.items()
                if v.get('workstream') == name and v.get('dependency_kind') == 'integration_owner'
                and v.get('status') == 'blocked' and not v.get('planner_helper')]
        work += [dict(stream=name, handoff=k, generation=snapshot['lanes'][k]['generation'],
                      revision=snapshot['lanes'][k]['revision']) for k in stream.get('lanes', [])
                 if snapshot['lanes'].get(k, {}).get('state') == 'handoff_ready'
                 and not isolated_handoff(pool.get('batches', {}), k, snapshot['lanes'][k])]
        work += [dict(stream=name, review=k, generation=snapshot['lanes'][k]['generation'],
                      evidence=snapshot['lanes'][k].get('review', {}).get('evidence'),
                      disposition_required=reg.clock() - (snapshot['lanes'][k].get('handoff_at') or reg.clock()) >= 1800,
                      prerequisite_input=dependency_pin(snapshot['lanes'].get(
                          snapshot.get('review_followups', {}).get(k, {}).get('waiting_on'), {})),
                      review_pin=review_pin(snapshot['lanes'][k]))
                 for k in stream.get('lanes', []) if k != owner
                 and snapshot['lanes'].get(k, {}).get('state') == 'review_ready'
                 and not deferred(snapshot, k)
                 and not k.startswith(('planning-', 'publication-review-', 'integration-support-'))]
        work += [dict(stream=name, job=k) for k, v in pool.get('jobs', {}).items()
                 if v.get('workstream') == name and v.get('status') in ('queued', 'assigned')
                 and v.get('lane')!=owner and not is_helper(v.get('lane',''))]
        work += [dict(stream=name, batch=k, candidates=sorted(v.get('candidates', {})))
                 for k, v in pool.get('batches', {}).items()
                 if v.get('workstream') == name and v.get('integrator') == owner
                 and v.get('state') == 'claimed']
        work += [dict(stream=name, **gap) for gap in receipt_gaps(snapshot, name)]
        from .admission_reconciliation import pins as admission_pins
        work += [dict(stream=name, admission_audit=k, **row) for k,row in
                 snapshot.get('admission_reconciliation', {}).items()
                 if k in stream.get('lanes', []) and row['status']=='pending' and
                 snapshot['lanes'][k]['state']=='blocked' and row['pins']==admission_pins(snapshot['lanes'][k])]
        from .support_actions import same
        from .export_packet import error as export_error
        work += [dict(stream=name,prepared_action=a['id'],handoff=a['key'],packet=a['evidence'],
                      destination=a['details']['destination'],
                      export_patch=a['details'].get('export_patch'),
                      export_validation=a['details'].get('export_validation'),
                      apply_commands=a['details'].get('apply_commands'))
                 for a in snapshot.get('support_actions',{}).values()
                 if a['action']=='integration_packet' and a['key'] in stream.get('lanes',[]) and
                 not export_error(reg,a) and
                 same(a['target'],snapshot['lanes'].get(a['key'],{})) and
                 snapshot['lanes'].get(a['key'],{}).get('state') in ('blocked','handoff_ready','integrating')]
        work += [dict(stream=name, **item) for item in shared_reviews(snapshot, stream, prior_launches)
                 if reg.recovery_safe(snapshot, snapshot['lanes'][item['shared_review']])]
        if work:
            demand.setdefault(owner, []).extend(work)
    from .delivery_contracts import owner_work, INSTRUCTION as DELIVERY_INSTRUCTION
    for owner in {s.get('owner_lane') for s in pool.get('workstreams',{}).values()}:
        work=owner_work(snapshot,owner)
        if work:demand.setdefault(owner,[]).extend(work)
    for owner, work in demand.items():
        lane = snapshot['lanes'].get(owner)
        if owner not in controller.config['lanes'] or not lane:
            continue
        if lane['state'] not in ('review_ready', 'ready', 'running', 'reconciling'):
            continue
        if not any('handoff' in item or 'review' in item or 'batch' in item or 'shared_review' in item or 'receipt_gap' in item or 'admission_audit' in item or 'delivery_contract' in item for item in work) and reg.integration_owner_available(snapshot, lane):
            continue  # Verified standby ownership already permits admission.
        if not reg.recovery_safe(snapshot, lane) or not controller.available(owner):
            continue
        launches = reg.control_status()['launches'].values()
        if any(x['lane'] == owner and x['status'] in ('intent', 'spawned', 'running', 'exiting') for x in launches):
            continue
        token = demand_token(work)
        if sum(x['lane'] == owner and x['reason'] == token for x in launches) >= 2:
            reg.notice(owner, 'integration_wakeup_exhausted', dict(demand=work))
            continue
        try:
            launch = reg.plan_launch(owner, token,
                'New admission or handoff demand needs your existing integration ownership. '
                'Inspect the canonical registry and your preserved previous batch report. '
                'Continue as the sole registered integration writer for your workstreams. '
                'Resume your existing claimed batches first; recovery preserves candidate pins, builds and isolation '
                'and rebinds batch ownership to your new generation. Reread batch revisions before any mutation. '
                'An open batch must be closed or explicitly isolated with evidence before standby. '
                'Check output/deepseek-wave/inbox/integration-support-prep-*.md for helper preparation packets. '
                'Verify packet hashes and producer/destination pins before reusing private resolution commits; '
                'stale destination evidence requires revalidation. Helpers do not grant integration acceptance. '
                'For export preparation packets, verify the archived patch/validation hashes and current '
                'producer/destination pins, inspect curated engine differences, then apply and validate '
                'through your sole integration ownership. Execute final export and receipt steps only with '
                'real evidence; helper rehearsal is not an export receipt. If the destination moved, '
                'revalidate the minimal patch against its new base before applying. '
                'Claim and validate eligible batches using the workflow APIs; preserve all prior receipts. '
                'For receipt_gap entries, the closed batch did NOT complete its candidate lane. '
                'Verify landed source pins and hashed build/validation evidence, obtain actual native export '
                'evidence when required, checkpoint integrating and call Registry.integrate for that lane. '
                'Never duplicate a cherry-pick, fabricate export evidence, or call missing lane receipts intact. '
                'For admission_audit entries, the family is already admitted but the lane remains open. '
                'Finish real source/export receipts through normal integration first. Otherwise use '
                'python -m workflow.admission_reconciliation --root <canonical-root> --request <json>: '
                'lane, token from audit, reviewer, reviewer_generation, decision retain/superseded, reason, '
                'evidence {path,sha256}. Retain requires next_action; superseded requires '
                'no_remaining_delivery:true and covered_criteria explaining acceptance coverage. '
                'Only retire work whose criteria are covered and whose delivery is complete; preserve independent follow-ups. '
                'If evidence is missing, record the precise missing artifact and responsible owner. '
                'The controller may need the next tick to admit waiting slices after you bind. '
                'For pending review reports, inspect their pinned evidence and issue acceptance criteria, '
                'A disposition_required review is enforced before review-ready standby. Accept a completed '
                'review only with evidence via accept_review, or resume its stopped producer through normal '
                'plan_launch for missing delivery. For a genuine prerequisite wait, record a pinned deferral '
                'using python -m workflow.review_followup --root <canonical-root> --request <json>. '
                'Fields: key, generation, review_pin from demand, reviewer (your lane), reviewer_generation, '
                'waiting_on (existing independent unfinished prerequisite lane, not yourself or the report), '
                'next_action, reason, evidence {path,sha256}. This preserves the unresolved report and '
                'automatically reopens review demand when the prerequisite changes or completes. '
                'then record an explicit accepted review through accept_review only when justified, or '
                'identify the exact required correction. Review acceptance is not source integration or '
                'gameplay acceptance; land any required source changes through normal handoff validation. '
                'For shared_review entries, inspect the producer commits, pinned reports and exact #186 request. '
                'These are shared-hook review tasks even when the producer is blocked or review-only done; '
                'absence of a valid integration handoff does not make the review itself ineligible. '
                'Record an evidence-backed review decision and the exact next owner/action in the issue. '
                'For a safely stopped blocked producer without a handoff, record the substantive decision '
                'using py -3.12 -m workflow.shared_decisions --root <canonical-root> --request <json>. '
                'Fields: key, generation, source_pins {root,native} from current lane heads, file (owned path), '
                'status approved/rejected, reviewer, reason, evidence {path,sha256}. This tool wakes the '
                'same producer without granting integration or clearing unrelated gates. You own the '
                'delegated focused #186 review: verify the diff and decide; a referral back to #186 is '
                'not a substantive decision. Never infer approval when evidence is insufficient. '
                'If shared source work is needed, prepare a bounded issue-backed private change or executable '
                'proposal within authorized ownership; preserve existing producer files and final validation. '
                'Use canonical checkpoints/dependencies to make the result consumable; never mark a review '
                'as source integration or clear runtime gates without evidence. '
                'If neither handoffs nor review reports remain, record a bounded standby report; never invent acceptance. '
                'No ADMIT. ' + DELIVERY_INSTRUCTION + 'Demand: ' + str(work), controller.config['models'])
            with reg.transaction() as state:
                state['control']['launches'][launch['id']]['shared_review_requests'] = sorted(
                    {item['shared_review_id'] for item in work if 'shared_review_id' in item})
                state['control']['launches'][launch['id']]['review_obligations'] = [
                    dict(lane=item['review'], pin=item['review_pin']) for item in work
                    if item.get('disposition_required')]
        except Rejected as exc:
            reg.notice(owner, 'integration_wakeup_blocked', dict(reason=str(exc), demand=work))
