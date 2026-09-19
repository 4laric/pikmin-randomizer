"""Durable promotion of exhausted planning inputs into owned prerequisite jobs."""
import argparse
import copy
import json
from pathlib import Path

from .control import fingerprint
from .handoff import require
from .planner_demand import inputs, is_helper, prerequisites

RESOLUTION_VERSION = 3


def outstanding(state, key):
    lane = state['lanes'].get(key, {})
    return not (lane.get('state') == 'done' and
                (lane.get('integration') or lane.get('review_disposition')))


def links(state, helper):
    runtime = state.get('throughput_runtime', {}).get('autofill', {}).get('prerequisite_links', {})
    return sorted(set(helper.get('prerequisite_lanes', []) + runtime.get(helper['scope'], [])))


def recovery_demand(state, helper, now, age_seconds=900):
    """One independent preparation turn when central promotion makes no progress."""
    if helper.get('kind'): return None
    data = state.get('throughput_runtime', {}).get('autofill', {})
    attempts = data.get('prerequisite_recovery', {})
    # A working producer must finish before discovery consumes its result.
    if any(outstanding(state, key) and state['lanes'].get(key, {}).get('state') != 'blocked'
           for key in links(state, helper)):
        return None
    stranded = sorted(k for k in links(state, helper) if outstanding(state, k))
    if stranded:
        lanes = [state['lanes'][k] for k in stranded]
        # A linked owner can become blocked after the original request was
        # dispositioned. Its current hashed outcome is fresh repair demand;
        # another no-work planning report is not required to discover it.
        if all((l.get('outcome') or {}).get('outcome') == 'blocked' and
               (l.get('outcome') or {}).get('evidence') and
               now - max(l.get('progress_at') or 0, l.get('started_at') or 0) >= max(300, age_seconds)
               for l in lanes):
            signal = fingerprint([inputs(state, [], stranded),
                                  [(k, state['lanes'][k]['outcome']['evidence']) for k in stranded]])
            key = fingerprint(['stranded-chain', signal])
            if key not in attempts:
                request = dict(id=key, scope=helper['scope'], status='stranded',
                    report=copy.deepcopy(lanes[0]['outcome']['evidence']), lanes=stranded,
                    issues=sorted({l['issue'] for l in lanes}),
                    blockers=[dict(lane=k, dependencies=state['lanes'][k].get('dependencies', []),
                                   outcome=state['lanes'][k]['outcome']) for k in stranded])
                return dict(key=key, input_snapshot=signal, request=request)
            return None
    candidates = sorted(data.get('prerequisite_requests', {}).values(),
                        key=lambda r: r['created_at'])
    for request in candidates:
        if request['scope'] != helper['scope']: continue
        if request['status'] != 'exhausted' and not (
                request['status'] == 'pending' and now - request['created_at'] >= max(300, age_seconds)):
            continue
        signal = inputs(state, request['issues'], request['lanes'])
        key = fingerprint([helper['scope'], signal])
        if key in attempts: continue
        return dict(key=key, input_snapshot=signal, request=copy.deepcopy(request))
    return None


def recovery_instruction(recovery):
    if recovery['request'].get('classification'):
        return (' PREREQUISITE RECOVERY / DEPENDENCY CLASSIFICATION overrides ordinary partition discovery and old no-work instructions. '
                'You are authorized to inspect the assigned consumer across partitions; use your private '
                'partition inbox only if preparing an optional proposal. Classification itself does not '
                'require a proposal or an implementation. Record all dependencies using the current '
                'workflow.dependency_classification API, including evidenced internal_blocker findings '
                'when no executable producer exists. Such a finding satisfies classification only and '
                'creates separate follow-up demand. Do not reinterpret a missing internal producer as a '
                'user asset or fabricate a contract. Assignment: '+json.dumps(recovery['request'])+'. ')
    return (' PREREQUISITE RECOVERY: blocked inputs need an executable resolution. '
            'This turn replaces ordinary no-work discovery for this partition. Read and verify this request: '
            + json.dumps(recovery['request']) + '. Trace the missing input to its actual producer. '
            'Prepare at most TWO complete issue-backed executable proposals in your private proposal inbox. '
            'If implementation pins are unknown, propose a bounded pin-discovery/ownership job with exact '
            'deliverables and downstream consumers. A completed contract, a blocked owner, or a referral '
            'to the coordinator/integrator is not an input producer. Reuse existing live owners; do not '
            'duplicate source scopes. Cross-partition prerequisites may be proposed here, with downstream '
            'scope/request IDs recorded for the publication reviewer. This specific recovery authorization '
            'supersedes the older partition-only/referral instruction; all canonical topic/provider/file '
            'claims and conflict checks still apply. Create and assign implementation '
            'issues before preparing private worktrees and immutable launch proofs. Report proposal paths '
            'and hashes, or evidence of an actual live producer or an exact user-owned asset/decision. '
            'Do not simply repeat no-work. Publication reviewers retain canonical merge_proposals validation; '
            'Re-read target state before preparing work. If another producer is now active, identify that '
            'producer and stop duplicate preparation. For review/landing blockers, prepare exact scoped '
            'decision requests and destination pins for the existing owner, rather than another contract '
            'describing the same blockage. Do not claim a repair is complete until the original consumer '
            'check passes; report any remaining owner action explicitly. '
            'no implementation, shared manifest writes, worker launches, builds or ADMIT in this turn.')


def collect(reg, settings):
    """Detect demand deterministically; issue/scope decisions belong to the coordinator."""
    from .autofill import _state
    if not settings.get('planner_pool', {}).get('enabled') or not settings.get('planner_lane'): return []
    with reg.transaction() as state:
        data = _state(state)
        data['prerequisite_coordinator'] = settings['planner_lane']
        requests = data.setdefault('prerequisite_requests', {})
        records = data.get('planner_pool', {}).get('scopes', {})
        current = set()
        for helper in settings['planner_pool'].get('helpers', []):
            if helper.get('kind'): continue
            record = records.get(helper['scope'], {})
            observation = record.get('no_work')
            if not observation or 'completed_at' not in record: continue
            linked = links(state, helper)
            linked_ready = prerequisites(state, linked)[0]
            pending_producers = [k for k in linked if outstanding(state, k)]
            stranded = (pending_producers if pending_producers and
                        all(state['lanes'].get(k, {}).get('state') == 'blocked' for k in pending_producers) else [])
            if linked and not linked_ready and not stranded: continue
            # Give newly accepted providers to discovery before promoting more work.
            if linked and linked_ready and record.get('prerequisite_snapshot') != prerequisites(state, linked)[1]: continue
            try:
                reg.evidence(observation['report'])
            except (OSError, ValueError) as exc:
                data.setdefault('prerequisite_errors', {})[helper['scope']] = str(exc)
                continue
            data.setdefault('prerequisite_errors', {}).pop(helper['scope'], None)
            request_lanes = sorted(set(observation['lanes'] + stranded))
            signal = inputs(state, observation['issues'], request_lanes)
            old = next((r for r in requests.values() if r.get('resolution_version') == RESOLUTION_VERSION and
                        r['scope'] == helper['scope'] and
                        r.get('stranded_producers', []) == stranded and
                        (r['status'] != 'exhausted' or r['input_snapshot'] == signal) and
                        r['report'] == observation['report'] and r['status'] in ('pending', 'dispatched', 'exhausted')), None)
            basis = [RESOLUTION_VERSION, helper['scope'], observation['report'], signal]
            if stranded: basis.append(['stranded-producers', stranded])
            identity = old['id'] if old else fingerprint(basis)
            current.add(identity)
            if identity not in requests:
                requests[identity] = dict(id=identity, scope=helper['scope'], report=copy.deepcopy(observation['report']),
                    issues=observation['issues'], lanes=request_lanes, input_snapshot=signal,
                    manifest=settings['manifest'], status='pending', created_at=reg.clock(), launches=[],
                    resolution_version=RESOLUTION_VERSION, stranded_producers=stranded)
            request = requests[identity]
            if request['status'] == 'dispatched':
                running = any(state.get('control', {}).get('launches', {}).get(k, {}).get('status')
                              in ('intent', 'spawned', 'running', 'exiting') for k in request['launches'])
                if not running:
                    request['status'] = 'exhausted' if len(request['launches']) >= 2 else 'pending'
        for identity, request in requests.items():
            if identity not in current and request['status'] in ('pending', 'dispatched', 'exhausted'):
                request.update(status='superseded', updated_at=reg.clock())
        def priority(request):
            consumers = [state['lanes'][k] for k in request['lanes'] if k in state['lanes']
                         and state['lanes'][k]['state'] == 'blocked']
            runtime = sum('runtime' in l.get('target_level', '') for l in consumers)
            return (-runtime, -len(consumers), request['created_at'], request['scope'])
        pending = sorted((copy.deepcopy(r) for r in requests.values() if r['status'] == 'pending'), key=priority)
        return pending[:3]


def dispatched(reg, requests, launch_id):
    from .autofill import _state
    with reg.transaction() as state:
        for request in requests:
            live = _state(state)['prerequisite_requests'][request['id']]
            if live['status'] not in ('pending', 'dispatched'): continue
            if launch_id not in live['launches']: live['launches'].append(launch_id)
            live.update(status='dispatched', updated_at=reg.clock())
        state['control']['launches'][launch_id]['prerequisite_request_ids'] = [r['id'] for r in requests]


def resolve(reg, coordinator, generation, request_id, outcome, lanes, reason, evidence, external_input=None):
    """Coordinator disposition after publication; no acceptance or dispatch here."""
    from .autofill import _state, _private
    require(outcome in ('linked', 'no_action'), 'Use linked or no_action')
    require(isinstance(reason, str) and reason.strip(), 'Evidence-backed disposition required')
    require(isinstance(lanes, list) and all(isinstance(k, str) and k for k in lanes), 'Explicit lane list required')
    require(bool(lanes) == (outcome == 'linked'), 'Linked outcome requires prerequisite lanes; no_action requires none')
    reg.evidence(evidence)
    with reg.transaction() as state:
        data = _state(state)
        require(coordinator == data.get('prerequisite_coordinator'), 'Registered prerequisite coordinator required')
        owner = reg.lane(state, coordinator, generation)
        require(owner['state'] == 'running' and reg.probe(owner['process']) == 'alive', 'Live coordinator generation required')
        request = data.get('prerequisite_requests', {}).get(request_id)
        require(request is not None, 'Unknown prerequisite request')
        result = dict(outcome=outcome, lanes=sorted(set(lanes)), reason=reason, evidence=evidence)
        if external_input is not None:
            require(outcome == 'no_action' and isinstance(external_input, dict), 'External input requires no_action')
            require(external_input.get('kind') in ('user_asset', 'user_decision') and
                    external_input.get('owner') == 'user' and
                    isinstance(external_input.get('detail'), str) and external_input['detail'].strip(),
                    'External input must identify a user-owned asset or decision and exact required detail')
            result['external_input'] = external_input
        if request.get('disposition') == result: return copy.deepcopy(request)
        require(request['status'] in ('pending', 'dispatched'), 'Request already dispositioned, superseded or exhausted')
        record = data.get('planner_pool', {}).get('scopes', {}).get(request['scope'], {})
        require((record.get('no_work') or {}).get('report') == request['report'], 'Planning report changed')
        reg.evidence(request['report'])
        blocked = [k for k in request.get('lanes', []) if
                   state['lanes'].get(k, {}).get('state') == 'blocked' and not is_helper(k)]
        require(outcome != 'no_action' or not blocked or external_input is not None,
                'Blocked consumers require an outstanding producer or an explicit user-owned external_input; '
                'internal provider/controller/integrator referrals are actionable workflow work. '
                'Publish a bounded pin-discovery/ownership slice if implementation cannot yet be scoped. '
                'Consumers: ' + ', '.join(blocked))
        manifest = json.loads(_private(reg, request['manifest']).read_text(encoding='utf-8-sig'))
        require(manifest.get('repository') == '4laric/pikmin-randomizer' and manifest.get('schema') == 1,
                'Canonical published manifest required')
        published = {s['lane']['lane']:s for s in manifest['items']}
        helper_lanes = {r['spec']['lane']['lane'] for r in data.get('planner_pool', {}).get('scopes', {}).values()}
        for key in lanes:
            require(not is_helper(key) and key != coordinator and key not in helper_lanes,
                    'Prerequisites must be executable non-planner lanes')
            require(key in state['lanes'] or key in published, 'Publish a validated spec before linking its lane')
        if lanes:
            require(any(outstanding(state, key) for key in lanes),
                    'Completed producers do not resolve an unmet prerequisite: publish or link an outstanding '
                    'producer for the actual gap, or record evidence-backed no_action if no gap remains')
            require(any(outstanding(state, key) and state['lanes'].get(key, {}).get('state') != 'blocked'
                        for key in lanes),
                    'Linking only blocked owners creates a circular wait: publish or link a producer for '
                    'their missing input, or a bounded discovery job that makes that input actionable')
        if lanes:
            graph = data.setdefault('prerequisite_links', {})
            graph[request['scope']] = sorted(set(graph.get(request['scope'], []) + lanes))
        request.update(status=outcome, disposition=result, updated_at=reg.clock())
        reg.event(state, 'prerequisite_disposition', coordinator, request_id=request_id,
                  scope=request['scope'], outcome=outcome, lanes=lanes)
        return copy.deepcopy(request)


def main():
    from .registry import Registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    reg = Registry(args.root/'output/workflow/registry.sqlite3', args.root)
    result = resolve(reg, **json.loads(args.request.read_text(encoding='utf-8-sig')))
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
