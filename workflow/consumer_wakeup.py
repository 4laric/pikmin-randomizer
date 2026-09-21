"""Reassess stale consumer blockers after evidenced prerequisite integration.

Wakes only for producers mapped to the consumer (typed delivery contracts, a pinned producer link,
a coordinator link, or its own dependency entries excluding umbrella issues such as #186), only for
receipts not yet consumed by a reported verification at the consumer's current source pins, at
most once per debounce window and only after the integrations since the last wake have been quiet
for one. Consumed only suppresses re-waking; it never clears a dependency."""
import copy
import json
import re
import sqlite3

from .control import fingerprint
from .provenance import cli
from .handoff import Rejected
from .no_progress import Parked
from .planner_demand import is_helper

DEBOUNCE_SECONDS, UMBRELLA_ISSUES, RESERVE_SECONDS = 900, (186,), 600


def pins(lane):
    return {k: (lane.get(k) or {}).get('head') for k in ('root', 'native')}


def consumed(lane):
    """{producer: [root_commit, native_commit]} already verified by a report at the consumer's current pins."""
    ledger = lane.get('consumer_consumed') or {}
    return ledger.get('receipts', {}) if ledger.get('source_pins') == pins(lane) else {}


def reissue(state, key, prior):
    """A token whose latest check was superseded without any report (a lost rebind) may be issued again."""
    records = [r for r in state.get('consumer_verifications', {}).values() if r['consumer'] == key]
    latest = max(records, key=lambda r: r['created_at'], default=None)
    return (len(prior) < 3 and latest is not None and latest['status'] == 'superseded'
            and latest.get('launch') in {x['id'] for x in prior})


def linked(reg, state):
    """{consumer: producers} from current-pin producer links and verified coordinator links."""
    result = {}
    for consumer, record in state.get('blocked_producer_links', {}).items():
        lane=state['lanes'].get(consumer,{})
        if record.get('source_pins') != {k:(lane.get(k) or {}).get('head') for k in ('root','native')}: continue
        try: reg.evidence(record['evidence'])
        except (Rejected,OSError,ValueError,KeyError): continue
        result.setdefault(consumer,set()).update(record['producers'])
    requests = state.get('throughput_runtime', {}).get('autofill', {}).get('prerequisite_requests', {})
    for request in requests.values():
        if request.get('status') != 'linked': continue
        try:
            reg.evidence(request['report'])
            reg.evidence(request['disposition']['evidence'])
        except (Rejected, OSError, ValueError, KeyError):
            continue
        for consumer in request.get('lanes', []):
            result.setdefault(consumer, set()).update(request['disposition'].get('lanes', []))
    return result


def producers(reg, state, key, links, umbrella, invalid=None):
    """(producers with receipts not yet consumed at the consumer's pins, typed contracts, {producer: why skipped}).

    invalid(producer) is told about a receipt whose validation evidence no longer verifies."""
    lane = state['lanes'][key]
    issues = {int(n) for dep in lane.get('dependencies', []) for n in re.findall(r'#(\d+)\b', dep)} - umbrella
    done = consumed(lane)
    from .delivery_contracts import contracts
    typed=[r for r in contracts(state,key) if r['kind'] in ('source_integration','consumer_behavior')]
    found, skipped = [], {}
    for provider_key, provider in state['lanes'].items():
        if typed and provider_key not in {r['producer'] for r in typed}:continue
        if provider_key == key: continue
        explicit = provider_key in links.get(key, set()) or any(r['producer']==provider_key for r in typed)
        matches = provider_key in lane.get('dependencies', []) or provider.get('issue') in issues
        if not (explicit or matches): continue
        receipt = provider.get('integration')
        if provider.get('state') != 'done' or not receipt:
            skipped[provider_key] = 'not integrated (state %s)' % provider.get('state'); continue
        if not explicit and not (provider.get('integrated_at') or 0) > lane.get('progress_at', 0):
            skipped[provider_key] = 'integrated before the consumer last progressed and not linked'; continue
        if done.get(provider_key) == [receipt.get('root_commit'), receipt.get('native_commit')]:
            skipped[provider_key] = 'receipt already verified at the consumer pins'; continue
        evidence = dict(path=receipt.get('validation_path'), sha256=receipt.get('validation_sha256'))
        try:
            reg.evidence(evidence)
        except (Rejected, OSError, ValueError, TypeError):
            skipped[provider_key] = 'receipt validation evidence missing or changed'
            if invalid: invalid(provider_key)
            continue
        found.append(dict(lane=provider_key, issue=provider['issue'],
            root_commit=receipt.get('root_commit'), native_commit=receipt.get('native_commit'),
            validation=evidence, source=provider.get('root'), native=provider.get('native')))
    return found, typed, skipped


def gate(reg, state, key, *, configured, available, links, launches, umbrella, debounce, invalid=None):
    """Why one lane is or is not woken now, in tick's order: {gate, detail}; gate 'wake' carries the plan.

    available(key) is the controller's launch-config check (it may record a notice)."""
    lane = state['lanes'].get(key)
    if key not in configured: return dict(gate='not_configured', detail='No controller launch config or launch spec')
    if lane is None or lane.get('state') != 'blocked':
        return dict(gate='not_blocked', detail='Lane state %s' % (lane or {}).get('state'))
    if is_helper(key) or key == 'acceptance-backlog-planner':
        return dict(gate='helper', detail='Helpers and the coordinator are woken by their own demand')
    if lane.get('handoff'): return dict(gate='handoff', detail='Lane holds a handoff')
    if not reg.recovery_safe(state, lane):
        return dict(gate='process_live', detail='Lane process, lease or queued request is live or unknown')
    if not available(key):
        return dict(gate='unavailable', detail='Pinned launch files changed or a legacy supervisor is not confirmed dead')
    live = [x['id'] for x in launches if x['lane'] == key and x['status'] in ('intent', 'spawned', 'running', 'exiting')]
    if live: return dict(gate='launch_in_flight', detail='Launch %s is in flight' % live[0][:12])
    found, typed, skipped = producers(reg, state, key, links, umbrella, invalid)
    if not found:
        return dict(gate='no_new_receipt', skipped=skipped,
                    detail='No mapped producer has an integration receipt this consumer has not verified')
    now = reg.clock()
    recent = [x['created_at'] for x in launches if x['lane'] == key and x['reason'].startswith('consumer-prerequisite:')]
    if recent and now - max(recent) < debounce:  # At most one wake per window.
        return dict(gate='debounce', detail='Last prerequisite wake %d s ago; window %d s' % (now - max(recent), debounce))
    fresh = [t for t in (state['lanes'][p['lane']].get('integrated_at') or 0 for p in found) if t > max(recent, default=0)]
    # Quiet window: integrations since the last wake settle into one; the first never waits two windows.
    if fresh and now - max(fresh) < debounce and now - min(fresh) < 2 * debounce:
        return dict(gate='quiet_window', detail='Integrations still settling; newest %d s ago' % (now - max(fresh)))
    contract_ids=sorted(r['id'] for r in typed if r['producer'] in {p['lane'] for p in found})
    token = 'consumer-prerequisite:' + fingerprint([sorted(found, key=lambda x:x['lane']),contract_ids] if typed else sorted(found, key=lambda x:x['lane']))
    prior = [x for x in launches if x['lane'] == key and x['reason'] == token]
    if prior and not reissue(state, key, prior):
        return dict(gate='already_woken', detail='These receipts were already offered by launch %s' % prior[-1]['id'][:12])
    plan = dict(producers=found, typed=typed, contract_ids=contract_ids, token=token)
    from .worker_capacity import occupant
    holder = occupant(reg, state, lane)
    if holder:  # Registry.check_wip would refuse: wait for the worker instead of taking the writer to be refused.
        held = (state.get('handoff_resume_reservations', {}).get(key) or {}).get('reason') == token
        return dict(plan, gate='worker_busy', occupant=holder, reserved=held, detail=(
            'Wake due, but worker %s is busy on %s (one active slice per worker); the worker is %s for this wake and '
            'it launches once that lane stops' % (lane.get('worker_id'), holder, 'reserved' if held else 'being reserved')))
    return dict(plan, gate='wake', detail='Wake due for ' + ', '.join(p['lane'] for p in found))


def reserve(reg, state, key, token):
    """Hold a busy worker for a due prerequisite wake, so helper refill cannot take it again when its current
    lane stops: the handoff_resume_reservations row autofill._workers honours until a launch with this reason
    exists, the lane moves on or it expires. Written only when missing or half expired, from one lane row."""
    lane, now = state['lanes'][key], reg.clock()
    old = state.get('handoff_resume_reservations', {}).get(key) or {}
    if old.get('expires_at', 0) > now and not str(old.get('reason')).startswith('consumer-prerequisite:'):
        return  # A handoff re-presentation holds this worker already.
    if (old.get('reason') == token and old.get('generation') == lane['generation'] and
            old.get('expires_at', 0) - now > RESERVE_SECONDS / 2):
        return
    from .storage import selected
    with selected(reg, [(('lanes',), key), ((), '')]) as rows:
        current, meta = rows[(('lanes',), key)], rows[((), '')]
        if current and current.get('state') == 'blocked' and current.get('generation') == lane['generation']:
            meta.setdefault('handoff_resume_reservations', {})[key] = dict(worker_id=lane.get('worker_id'),
                generation=lane['generation'], reason=token, expires_at=now + RESERVE_SECONDS)


def explain(reg, state, key, configured, available, config=None):
    """Read-only: why consumer_wakeup does or does not wake this lane now; never notices or plans."""
    from . import no_progress
    settings = (config or {}).get('consumer_wakeup', {})
    launches = list(state.get('control', {}).get('launches', {}).values())
    result = gate(reg, state, key, configured=configured, available=available, links=linked(reg, state),
                  launches=launches, umbrella=set(settings.get('umbrella_issues', UMBRELLA_ISSUES)),
                  debounce=settings.get('debounce_seconds', DEBOUNCE_SECONDS))
    if result['gate'] == 'wake':
        inputs = ['receipt:%s:%s:%s' % (p['lane'], p['root_commit'], p['native_commit']) for p in result['producers']]
        refusal = no_progress.verdict(state['lanes'][key], inputs, reg.clock())
        if refusal: result = dict(result, gate='would_park', detail=refusal['message'])
    result.pop('typed', None)
    return result


def tick(controller):
    reg = controller.reg
    settings = controller.config.get('consumer_wakeup', {})
    debounce = settings.get('debounce_seconds', DEBOUNCE_SECONDS)
    umbrella = set(settings.get('umbrella_issues', UMBRELLA_ISSUES))
    state = reg.snapshot()
    launches = state.get('control', {}).get('launches', {}).values()
    links = linked(reg, state)
    for key, lane in state['lanes'].items():
        if lane.get('state') != 'blocked': continue
        plan = gate(reg, state, key, configured=controller.config['lanes'], available=controller.available, links=links,
                    launches=launches, umbrella=umbrella, debounce=debounce,
                    invalid=lambda p, key=key: reg.notice(key, 'consumer_prerequisite_evidence_invalid', dict(producer=p)))
        if plan['gate'] == 'worker_busy':
            try: reserve(reg, state, key, plan['token'])
            except sqlite3.OperationalError:
                pass  # Writer lock busy past the retry budget (RegistryBusy): the next tick retries; check_wip still refuses.
            except (Rejected, OSError, ValueError) as exc:
                reg.notice(key, 'consumer_prerequisite_wakeup_blocked', dict(error='Worker reservation failed: ' + str(exc)))
        if plan['gate'] != 'wake': continue
        producers, typed, contract_ids, token = plan['producers'], plan['typed'], plan['contract_ids'], plan['token']
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
                'Integrated prerequisites: ' + json.dumps(producers), controller.config['models'],
                inputs=['receipt:%s:%s:%s' % (p['lane'], p['root_commit'], p['native_commit']) for p in producers])
            if any(x['id'] == launch['id'] for x in launches): continue  # Same identity: nothing new was planned.
            with reg.transaction() as current:
                item=current['control']['launches'][launch['id']]
                check=(state.get('blocked_producer_links',{}).get(key) or {}).get('acceptance_check')
                item['delivery_contracts']=contract_ids
                item['consumer_acceptance_check']='; '.join(r['acceptance_check'] for r in typed if r['id'] in contract_ids) or check or lane.get('next_action')
                prefix=('CONSUMER VERIFICATION REQUIRED before finish: verification='+launch['id']+'. '
                    'Reproduce the actual consumer failure using the integrated producer pins. '
                    'Record command, expected result and observed result, plus independent hashed consumer evidence. '
                    'Submit '+cli('consumer_verification')+' --root <canonical> --request <json> '
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
            if not isinstance(exc, Parked): reg.notice(key, 'consumer_prerequisite_wakeup_blocked', dict(reason=str(exc)))
