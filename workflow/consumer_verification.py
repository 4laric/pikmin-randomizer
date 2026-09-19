"""Consumer acceptance is separate from immutable producer integration receipts."""
import copy
import json
from .control import fingerprint
from .provenance import cli
from .handoff import require, Rejected


def bind_context(reg, state, launch, lane):
    """A resumed generation gets its own pending check, never inherited success."""
    ledger = state.get('consumer_verifications', {})
    previous = [r for r in ledger.values() if r['consumer'] == lane['lane']]
    if not previous or launch['id'] in ledger:return
    old = max(previous, key=lambda r:r['created_at'])
    if old['status'] not in ('pending','unverified','failed','superseded'):
        if launch.get('consumer_verification'):
            launch['consumer_verification'] = None
            launch['instruction'] = ('CONSUMER VERIFICATION ALREADY REPORTED: verification='+old['id']+' is '+
                old['status']+'; do not report it again.\n'+launch['instruction'])
        return
    declined = None
    for p in old['producers']:
        receipt = state['lanes'].get(p['lane'],{}).get('integration') or {}
        if any(p.get(k)!=receipt.get(k) for k in ('root_commit','native_commit')):
            declined = 'producer receipt changed: '+p['lane'];break
        try:reg.evidence(p['validation'])
        except (Rejected,OSError,ValueError,KeyError):
            declined = 'producer validation evidence unreadable: '+p['lane'];break
    if declined:
        if launch.get('consumer_verification') or old['status']=='pending':
            if launch.get('consumer_verification'):  # A carried obligation must not point at an unreportable id.
                launch['consumer_verification'] = None
                launch['instruction'] = ('CONSUMER VERIFICATION NOT REBOUND: '+declined+'. verification='+old['id']+
                    ' belongs to an old generation and cannot be reported; do not reuse it. Finish with your '
                    'current blocker; a changed producer receipt wakes a new check.\n'+launch['instruction'])
            reg.event(state,'consumer_verification_rebind_declined',lane['lane'],previous=old['id'],reason=declined)
        return
    record = dict(id=launch['id'],launch=launch['id'],consumer=lane['lane'],
        consumer_generation=lane['generation'],created_at=launch['created_at'],status='pending',
        producers=copy.deepcopy(old['producers']), delivery_contracts=old.get('delivery_contracts',[]),
        acceptance_check=old['acceptance_check'],original_blocker=old.get('original_blocker'),
        evidence=None,replaces=old['id'])
    ledger[record['id']]=record
    if old['status']=='pending':old.update(status='superseded',checked_at=reg.clock())
    launch['consumer_verification']=record['id']
    launch['instruction']=('CURRENT CONSUMER VERIFICATION: use verification='+record['id']+
        ', consumer='+lane['lane']+', generation='+str(lane['generation'])+'. Prior verification IDs '
        'belong to old generations and must not be reused. Run this exact check before finish: '+
        record['acceptance_check']+'. Submit through '+cli('consumer_verification')+' --root <canonical> --request <json> with independent '
        'hashed evidence and current runtime proof where required. No prior success is inherited.\n'+launch['instruction'])
    reg.event(state,'consumer_verification_rebound',lane['lane'],verification=record['id'],previous=old['id'])


OBLIGATIONS = ('consumer_verification', 'delivery_contracts', 'consumer_acceptance_check', 'review_obligations',
               'inputs', 'focus', 'work_class')


def inherit(previous, follow):
    """A recovery continuation keeps the duties its failed launch carried; bind_context rebinds the check.

    Attempt counters (blocked_followup_ids, prerequisite_request_ids, shared_review_requests) stay with
    the original launch so a retry does not spend the demand's own attempt budget."""
    for field in OBLIGATIONS:
        if previous.get(field) is not None:follow[field] = copy.deepcopy(previous[field])
    if previous.get('reason','').startswith('consumer-prerequisite:') and not follow.get('consumer_verification'):
        follow['consumer_verification'] = previous['id']


def runtime_proof(reg, lane, runtime):
    """Bind a runtime unblock to an independently recorded real consumer run."""
    require(isinstance(runtime,dict) and runtime.get('kind')=='game_runtime',
            'Runtime consumer success requires runtime.kind=game_runtime, not diagnosis or contract tests')
    head=(lane.get('native') or {}).get('head')
    require(head and runtime.get('native_head')==head, 'Runtime native pin must match consumer source')
    exe=reg.evidence(runtime.get('executable') or {})
    log=reg.evidence(runtime.get('log') or {})
    result=reg.evidence(runtime.get('result') or {})
    require(len({exe,log,result})==3, 'Separate executable, log and supervisor result required')
    record=json.loads(result.read_text(encoding='utf-8-sig'))
    from pathlib import Path
    argv=record.get('argv') or []
    require(argv and Path(argv[0]).is_absolute() and Path(argv[0]).resolve()==exe.resolve(),
            'Supervisor executable does not match runtime evidence')
    require(record.get('passed') is True and type(record.get('exit_code')) is int
            and record['exit_code']==0 and record.get('timed_out') is False,
            'Successful bounded consumer run required')
    markers=record.get('markers')
    require(isinstance(markers,dict) and markers and all(isinstance(k,str) and k.strip()
            and v is True for k,v in markers.items()), 'Explicit observed consumer markers required')
    text=log.read_text(errors='replace')
    require(all(k in text for k in markers) and 'P2_FIXTURE_CAPTAIN_DOWN' not in text,
            'Consumer log must contain required markers without captain-down')
    return copy.deepcopy(runtime)


def reconcile(controller):
    reg = controller.reg
    with reg.transaction() as state:
        ledger = state.setdefault('consumer_verifications', {})
        latest={}
        for item in ledger.values():
            if item['created_at']>=latest.get(item['consumer'],{}).get('created_at',-1):latest[item['consumer']]=item
        for record in ledger.values():
            lane=state['lanes'].get(record['consumer'],{})
            if (record['status']=='passed' and latest.get(record['consumer']) is record
                    and lane.get('state')=='blocked' and lane.get('target_level')=='runtime'
                    and lane.get('generation')==record.get('consumer_generation')
                    and not record.get('runtime')):
                record.update(status='unverified',reported_status='passed',
                    result='Runtime consumer remains blocked and prior report lacks executable/log/supervisor proof. '
                           'Require a real consuming game run, including build membership and engine calls.',
                    resolution_review_required_at=reg.clock())
                reg.event(state,'consumer_runtime_unverified',record['consumer'],verification=record['id'])
            if record['status'] == 'passed' and record.get('prerequisite_resolved') is not True:
                record.update(status='unverified', reported_status='passed',
                    result='Legacy success did not attest that the original prerequisite was resolved; '
                           'diagnostic exit 0 and reproducing a failure are not an unblock.',
                    resolution_review_required_at=reg.clock())
                reg.event(state, 'consumer_resolution_unverified', record['consumer'], verification=record['id'])
        for launch in state.get('control', {}).get('launches', {}).values():
            if not launch.get('reason', '').startswith('consumer-prerequisite:') and not launch.get('consumer_verification'):
                continue
            key = launch['id']
            if key not in ledger:
                if not launch.get('reason', '').startswith('consumer-prerequisite:'):
                    continue  # A carried obligation gets its record from bind_context, never before binding.
                try:
                    producers = json.loads(launch['instruction'].split('Integrated prerequisites: ', 1)[1])
                    require(isinstance(producers, list) and producers, 'Producer pins required')
                    for producer in producers: reg.evidence(producer['validation'])
                except (ValueError, KeyError, IndexError, OSError, Rejected):
                    continue
                lane = state['lanes'].get(launch['lane'], {})
                ledger[key] = dict(id=key, consumer=launch['lane'], producers=producers,
                    delivery_contracts=launch.get('delivery_contracts', []),
                    launch=key, created_at=launch['created_at'], status='pending',
                    acceptance_check=launch.get('consumer_acceptance_check') or
                        'Reproduce the consumer prerequisite failure against these integrated pins; '
                        'record the exact command, expected result and observed result.',
                    original_blocker=lane.get('next_action'), evidence=None)
            record = ledger[key]
            if record['status'] != 'pending': continue
            lane = state['lanes'].get(record['consumer'], {})
            generation = launch.get('bound_generation')
            if generation is not None and lane.get('generation',0) > generation:
                record.update(status='superseded', checked_at=reg.clock())
                continue
            if generation is None or lane.get('generation') != generation: continue
            record['consumer_generation'] = generation
            outcome = lane.get('outcome') or {}
            if lane.get('progress_at', 0) < launch['created_at']: continue
            if lane.get('state') not in ('blocked', 'review_ready', 'handoff_ready', 'done'): continue
            if not outcome and lane.get('state') == 'done':
                record.update(status='unverified', checked_at=reg.clock(),
                    result='Consumer completed without a separate prerequisite acceptance report')
                continue
            if not outcome: continue
            try: reg.evidence(outcome['evidence'])
            except (Rejected, OSError, ValueError, KeyError): continue
            # No inferred success, even for a handoff or another integration.
            record.update(status='unverified', evidence=outcome['evidence'],
                result=outcome.get('summary'), checked_at=reg.clock(),
                source_pins={k:(lane.get(k) or {}).get('head') for k in ('root','native')})
            reg.event(state, 'consumer_verification_unresolved', record['consumer'], verification=key)


def report(reg, verification, consumer, generation, passed, check, evidence, prerequisite_resolved=None, runtime=None):
    require(type(passed) is bool, 'Boolean passed required')
    require(prerequisite_resolved is None or type(prerequisite_resolved) is bool,
            'Boolean prerequisite_resolved required')
    require(not passed or prerequisite_resolved is True,
            'Successful unblock requires prerequisite_resolved=true: reproducing the failure must report passed=false')
    require(passed or prerequisite_resolved is not True, 'Failed check cannot claim prerequisite resolved')
    require(isinstance(check, dict) and all(isinstance(check.get(k), str) and check[k].strip()
            for k in ('command', 'expected', 'observed')), 'Concrete command, expected and observed result required')
    reg.evidence(evidence)
    from .provenance import stamp
    code = stamp()
    with reg.transaction() as state:
        record = state.get('consumer_verifications', {}).get(verification)
        require(record and record['consumer'] == consumer, 'Consumer verification not found')
        launch = state['control']['launches'][record['launch']]
        lane = reg.lane(state, consumer, generation)
        require(launch.get('bound_generation') == generation, 'Verification generation changed')
        require(lane['state'] == 'running' and reg.probe(lane['process']) == 'alive', 'Live consumer owner required')
        require(lane['task_id'].removeprefix('opencode:') == launch['session'], 'Consumer session changed')
        require(record['status'] == 'pending', 'Verification already reported')
        require(evidence not in [p['validation'] for p in record['producers']], 'Consumer evidence must be independent of producer validation')
        if passed and lane.get('target_level')=='runtime':
            runtime=runtime_proof(reg,lane,runtime)
        record.update(status='passed' if passed else 'failed', check=check, evidence=evidence,
            runtime=runtime,
            prerequisite_resolved=passed and prerequisite_resolved is True,
            consumer_generation=generation, checked_at=reg.clock(), code_revision=code,
            source_pins={k:(lane.get(k) or {}).get('head') for k in ('root','native')})
        # Consumed ledger: these receipts were checked at these pins, pass or fail. It only stops
        # consumer_wakeup re-waking for them; it never clears a dependency or implies success.
        ledger = lane.get('consumer_consumed') or {}
        receipts = dict(ledger.get('receipts', {})) if ledger.get('source_pins') == record['source_pins'] else {}
        receipts.update({p['lane']:[p.get('root_commit'),p.get('native_commit')] for p in record['producers']})
        lane['consumer_consumed'] = dict(source_pins=record['source_pins'], receipts=receipts,
                                         verification=verification, at=reg.clock())
        reg.event(state, 'consumer_verification_reported', consumer, verification=verification, passed=passed)
        return copy.deepcopy(record)


def repairs(state):
    """Group unresolved checks by the exact integrated producer receipt set."""
    latest = {}
    for record in state.get('consumer_verifications', {}).values():
        consumer = record['consumer']
        if record['created_at'] >= latest.get(consumer, {}).get('created_at', -1): latest[consumer] = record
    grouped = {}
    for consumer, record in latest.items():
        if record['status'] not in ('failed','unverified'): continue
        lane = state['lanes'].get(consumer,{})
        if lane.get('state') != 'blocked' or lane.get('generation') != record.get('consumer_generation'): continue
        if record.get('source_pins') != {k:(lane.get(k) or {}).get('head') for k in ('root','native')}: continue
        pins = sorted((p['lane'],p.get('root_commit'),p.get('native_commit')) for p in record['producers'])
        # A strengthened acceptance policy is new repair input, not another
        # unlimited retry against the same historical referral budget.
        key = fingerprint([pins,'game-runtime-proof-v1'] if lane.get('target_level')=='runtime' else pins)
        group = grouped.setdefault(key, dict(id='consumer-repair:'+key, producers=record['producers'], consumers=[]))
        group['consumers'].append(dict(lane=consumer, verification=record['id'],
            acceptance_check=record['acceptance_check'], result=record.get('result') or record.get('check'), evidence=record['evidence']))
    return list(grouped.values())


def metrics(state, now, window=3600):
    records = list(state.get('consumer_verifications', {}).values())
    verified = len({r['consumer'] for r in records if r['status']=='passed' and r.get('prerequisite_resolved') is True and now-window < r.get('checked_at',0) <= now})
    return dict(verified_unblocks=verified, verified_unblocks_per_hour=verified*3600/window,
                pending=sum(r['status']=='pending' for r in records),
                unresolved_repair_groups=len(repairs(state)))


def main():
    import argparse
    from pathlib import Path
    from .registry import Registry
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--request',type=Path,required=True)
    args=parser.parse_args();reg=Registry(args.root/'output/workflow/registry.sqlite3',args.root)
    print(json.dumps(report(reg,**json.loads(args.request.read_text(encoding='utf-8-sig'))),indent=2))


if __name__=='__main__': main()
