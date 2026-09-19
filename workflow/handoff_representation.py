"""Break the missing producer handoff / maintained export circular wait."""
import json
import re
from .control import fingerprint
from .handoff import Rejected
from .support_actions import same
from .export_packet import error


def released_slot(state, lane):
    """A real same-worker completion after an explicit WIP wait is new input."""
    request = ' '.join([lane.get('next_action', ''), *lane.get('dependencies', [])])
    if not re.search(r'\bWIP\b|ready slot|handoff slot', request, re.I):
        return []
    return sorted((key, other.get('generation'), fingerprint(other.get('integration') or
                  other.get('review_disposition'))) for key, other in state['lanes'].items()
                  if key != lane['lane'] and lane.get('worker_id') and
                  other.get('worker_id') == lane['worker_id'] and other.get('state') == 'done' and
                  (other.get('integration') or other.get('review_disposition')) and
                  (other.get('integrated_at') or other.get('progress_at') or 0) > lane.get('progress_at', 0))


def passed_check(state, lane):
    """The lane's latest consumer check, when it passed with prerequisite_resolved and runtime proof at its current pins."""
    records=[r for r in state.get('consumer_verifications',{}).values() if r['consumer']==lane['lane']]
    latest=max(records,key=lambda r:r['created_at'],default=None)
    current={k:(lane.get(k) or {}).get('head') for k in ('root','native')}
    if (latest and latest['status']=='passed' and latest.get('prerequisite_resolved') is True and
            latest.get('runtime') and latest.get('evidence') and latest.get('source_pins')==current):
        return latest
    return None


VERIFIED=('HANDOFF RE-PRESENTATION AFTER A PASSED CONSUMER CHECK: the verification below passed with '
    'prerequisite_resolved and hashed runtime proof at your current source pins, yet your slice is still blocked '
    'with no handoff. Re-read your issue acceptance criteria. Gaps outside those criteria are follow-ons: list them '
    'in the handoff remaining_work instead of keeping them as blocking dependencies. Submit a truthful '
    'current-generation handoff through the normal implementation-ready API; every slice criterion must still pass '
    'validation, shared reviews stay pending and gameplay gates stay UNTESTED unless observed. Do not claim new tests '
    'without running them. If an in-scope criterion still fails, finish blocked naming exactly that criterion. '
    'This is one bounded turn for this verification. Verification: ')


def tick(controller):
    reg=controller.reg;state=reg.snapshot()
    launches=list(state.get('control',{}).get('launches',{}).values())
    for key,lane in state['lanes'].items():
        if key not in controller.config['lanes'] or lane['state']!='blocked' or lane.get('handoff'):continue
        check=passed_check(state,lane)
        token='handoff-representation:verification:'+check['id'] if check else None
        if check and not any(x['lane']==key and x['reason']==token for x in launches):
            if any(x['lane']==key and x['status'] in ('intent','spawned','running','exiting') for x in launches):continue
            if not reg.recovery_safe(state,lane) or not controller.available(key):continue
            try:
                reg.evidence(check['evidence'])
                reg.plan_launch(key,token,VERIFIED+json.dumps({k:check.get(k) for k in
                    ('id','acceptance_check','check','evidence','runtime','source_pins')}),
                    controller.config['models'],inputs=[token])
            except (Rejected,OSError,ValueError) as exc:
                reg.notice(key,'handoff_representation_blocked',dict(error=str(exc)))
            continue
        from .shared_decisions import approved_scope
        approved = approved_scope(state, lane)
        if not (lane.get('repair_history') or approved):continue
        token='handoff-representation:'+fingerprint([key,
            (lane.get('root') or {}).get('head'),(lane.get('native') or {}).get('head')])
        release = released_slot(state, lane)
        if release:
            token += ':slot-released:' + fingerprint(release)
        if any(x['lane']==key and (x['reason']==token or x['status'] in
               ('intent','spawned','running','exiting')) for x in launches):continue
        if any(b.get('state')=='claimed' and key in b.get('candidates',{}) and
               key not in b.get('isolated',{}) for b in state.get('throughput',{}).get('batches',{}).values()):continue
        if not reg.recovery_safe(state,lane) or not controller.available(key):continue
        packets=[a for a in state.get('support_actions',{}).values() if a['key']==key
                 and a['action']=='integration_packet' and (a['target'].get('kind')=='export_preparation' or approved)
                 and same(a['target'],lane) and not error(reg,a)]
        if not packets:continue
        packet=max(packets,key=lambda a:a['at'])
        try:
            reg.evidence(packet['evidence'])
            with reg.transaction() as current:
                actual=current['lanes'].get(key,{})
                if not same(lane,actual) or actual.get('state')!='blocked':continue
                current.setdefault('handoff_resume_reservations',{})[key]=dict(
                    worker_id=lane.get('worker_id'),generation=lane['generation'],
                    reason=token,expires_at=reg.clock()+120)
            reg.plan_launch(key,token,
                'PRODUCER HANDOFF RE-PRESENTATION: integration is waiting for your missing current handoff. '
                'Resume your existing issue, private source and preserved repair evidence. Inspect repair_history '
                'when present. Authenticated exact-source approvals may already resolve your review dependency: '
                'only shared_preflight_decisions for your current root/native heads (across prior generations) '
                'whose approval id is in the approvals ledger count; older rows are unauthenticated-legacy. '
                'An unchanged approved source diff does not need another approval because your generation changed. '
                'and this exact preparation packet: '+json.dumps(packet)+'. '
                'Revalidate your source pins and original acceptance evidence, then reconstruct a truthful '
                'current-generation handoff through the normal submit-handoff/implementation-ready API. '
                'Do not reuse another generation header or claim new tests without running them. '
                'The maintained export is a FINAL INTEGRATION requirement; waiting for it before presenting '
                'your producer handoff creates a circular wait. Carry pending shared reviews and unresolved '
                'gameplay gates honestly in the handoff. Helpers do not grant acceptance. '
                'Do not touch maintained worktrees, repeat landed cherry-picks, fabricate an export or grant ADMIT. '
                'If source/evidence cannot pass normal handoff validation, finish blocked with the exact failed '
                'check and correction needed. This is one bounded resumption at these source heads.',
                controller.config['models'],inputs=[token])
        except (Rejected,OSError,ValueError) as exc:
            reg.notice(key,'handoff_representation_blocked',dict(error=str(exc)))
