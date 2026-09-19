"""Group explicitly reported repeated failures, never fuzzy-match unrelated bugs."""
from .control import fingerprint
from .planner_demand import is_helper


def groups(state):
    buckets = {}
    latest = {}
    for event in state.get('events', []):
        if event.get('kind') == 'failure': latest[event['lane']] = event
    for key,lane in state.get('lanes', {}).items():
        if lane.get('state') != 'blocked' or is_helper(key): continue
        event = latest.get(key)
        pattern = lane.get('failure_fingerprint')
        if not pattern or not event or event.get('fingerprint') != pattern: continue
        if lane.get('failure_streak',0) <= 0: continue
        if 'generation' in event and (event['generation'] != lane['generation'] or
                event.get('source_pins') != {k:(lane.get(k) or {}).get('head') for k in ('root','native')}): continue
        if 'generation' not in event and event['at'] < lane.get('progress_at',0): continue
        buckets.setdefault(pattern,[]).append(dict(lane=key,issue=lane.get('issue'),
            generation=lane['generation'],source_pins={k:(lane.get(k) or {}).get('head') for k in ('root','native')},
            evidence=event['evidence'],acceptance_check=lane.get('next_action'),
            streak=lane.get('failure_streak',0)))
    result = []
    for pattern, consumers in buckets.items():
        if len(consumers)<2 and max(c['streak'] for c in consumers)<2: continue
        consumers.sort(key=lambda c:c['lane'])
        identity = fingerprint([pattern,[(c['lane'],c['source_pins']) for c in consumers]])
        result.append(dict(id='recurring-failure:'+identity,pattern=pattern,consumers=consumers,
                           summary='Prepare one shared fix for this exact reported failure fingerprint; '
                           'verify a common cause from hashed evidence before linking every consumer. '
                           'Reuse existing owners and require independent consumer rechecks after integration.'))
    return result
