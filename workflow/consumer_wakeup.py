"""Reassess stale consumer blockers after evidenced prerequisite integration."""
import copy
import json
import re

from .control import fingerprint
from .handoff import Rejected
from .planner_demand import is_helper


def tick(controller):
    reg = controller.reg
    state = reg.snapshot()
    launches = state.get('control', {}).get('launches', {}).values()
    requests = state.get('throughput_runtime', {}).get('autofill', {}).get('prerequisite_requests', {})
    linked = {}
    for consumer, record in state.get('blocked_producer_links', {}).items():
        lane=state['lanes'].get(consumer,{})
        if record.get('source_pins') != {k:(lane.get(k) or {}).get('head') for k in ('root','native')}: continue
        try: reg.evidence(record['evidence'])
        except (Rejected,OSError,ValueError,KeyError): continue
        linked.setdefault(consumer,set()).update(record['producers'])
    for request in requests.values():
        if request.get('status') != 'linked': continue
        try:
            reg.evidence(request['report'])
            reg.evidence(request['disposition']['evidence'])
        except (Rejected, OSError, ValueError, KeyError):
            continue
        for consumer in request.get('lanes', []):
            linked.setdefault(consumer, set()).update(request['disposition'].get('lanes', []))
    for key, lane in state['lanes'].items():
        if (key not in controller.config['lanes'] or lane.get('state') != 'blocked'
                or is_helper(key) or key == 'acceptance-backlog-planner' or lane.get('handoff')):
            continue
        if not reg.recovery_safe(state, lane) or not controller.available(key): continue
        if any(x['lane'] == key and x['status'] in ('intent', 'spawned', 'running', 'exiting') for x in launches): continue
        issues = {int(n) for dep in lane.get('dependencies', []) for n in re.findall(r'#(\d+)\b', dep)}
        from .delivery_contracts import contracts
        typed=[r for r in contracts(state,key) if r['kind'] in ('source_integration','consumer_behavior')]
        producers = []
        for provider_key, provider in state['lanes'].items():
            if typed and provider_key not in {r['producer'] for r in typed}:continue
            receipt = provider.get('integration')
            if provider_key == key or provider.get('state') != 'done' or not receipt: continue
            explicit = provider_key in linked.get(key, set()) or any(r['producer']==provider_key for r in typed)
            matches = provider_key in lane.get('dependencies', []) or provider.get('issue') in issues
            if not explicit and not (matches and (provider.get('integrated_at') or 0) > lane.get('progress_at', 0)):
                continue
            evidence = dict(path=receipt.get('validation_path'), sha256=receipt.get('validation_sha256'))
            try:
                reg.evidence(evidence)
            except (Rejected, OSError, ValueError, TypeError):
                reg.notice(key, 'consumer_prerequisite_evidence_invalid', dict(producer=provider_key))
                continue
            producers.append(dict(lane=provider_key, issue=provider['issue'],
                root_commit=receipt.get('root_commit'), native_commit=receipt.get('native_commit'),
                validation=evidence, source=provider.get('root'), native=provider.get('native')))
        if not producers: continue
        contract_ids=sorted(r['id'] for r in typed if r['producer'] in {p['lane'] for p in producers})
        token = 'consumer-prerequisite:' + fingerprint([sorted(producers, key=lambda x:x['lane']),contract_ids] if typed else sorted(producers, key=lambda x:x['lane']))
        if any(x['lane'] == key and x['reason'] == token for x in launches): continue
        try:
            launch = reg.plan_launch(key, token,
                'A prerequisite has new verified integration evidence. Reassess your existing blocked slice; '
                'do not create duplicate work or treat all dependencies as satisfied. Preserve committed work '
                'and inspect the original blockers and these exact producer/receipt pins. Bring only the necessary '
                'accepted prerequisite changes into your own private worktrees, resolve conflicts there, and '
                'continue the authorized slice where evidence permits. All unresolved shared reviews and external '
                'dependencies remain gates. Clear a dependency only with recorded supporting evidence through '
                'normal checkpoint APIs. If still blocked, report the concrete remaining gap and stop. '
                'No shared source edits, maintained builds/exports, ADMIT or inferred gameplay acceptance. '
                'Use leased private builds and current fixture/captain-safety baseline for runtime work. '
                'Integrated prerequisites: ' + json.dumps(producers), controller.config['models'])
            with reg.transaction() as current:
                item=current['control']['launches'][launch['id']]
                check=(state.get('blocked_producer_links',{}).get(key) or {}).get('acceptance_check')
                item['delivery_contracts']=contract_ids
                item['consumer_acceptance_check']='; '.join(r['acceptance_check'] for r in typed if r['id'] in contract_ids) or check or lane.get('next_action')
                prefix=('CONSUMER VERIFICATION REQUIRED before finish: verification='+launch['id']+'. '
                    'Reproduce the actual consumer failure using the integrated producer pins. '
                    'Record command, expected result and observed result, plus independent hashed consumer evidence. '
                    'Submit python -m workflow.consumer_verification --root <canonical> --request <json> '
                    'with verification, consumer, current generation, passed (boolean), prerequisite_resolved (boolean), check '
                    '{command,expected,observed}, evidence {path,sha256}. Runtime consumers also require runtime '
                    '{kind:game_runtime,native_head,executable:{path,sha256},log:{path,sha256},result:{path,sha256}}; '
                    'result is the bounded supervisor JSON with argv, exit_code, timed_out, passed and markers. '
                    'Run the actual consuming game path; separate fixtures or diagnosis do not prove engine wiring. '
                    'Use canonical scripts/run_pikmin2_fixture.py for already staged arenas and explicit expected markers. '
                    'A contract/probe/simulated hook '
                    'does not pass an engine/runtime prerequisite. If the original defect is fixed but '
                    'another blocker remains, report passed=true and prerequisite_resolved=true for this check and finish blocked on the other gap. '
                    'A diagnostic command exiting 0 because it REPRODUCED the defect is NOT an unblock: report passed=false '
                    'and prerequisite_resolved=false. Success must demonstrate the original required consumer behavior now works. '
                    'Check: '+str(item['consumer_acceptance_check'])+'\n')
                item['instruction']=prefix+item['instruction']
            from .consumer_verification import reconcile
            reconcile(controller)
        except (Rejected, OSError, ValueError) as exc:
            reg.notice(key, 'consumer_prerequisite_wakeup_blocked', dict(reason=str(exc)))
