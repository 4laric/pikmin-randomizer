"""Pinned, evidence-backed deferrals for aging integration review reports."""
import argparse
import json
from pathlib import Path
from .control import fingerprint
from .handoff import require, nonempty


def pin(lane):
    return fingerprint([lane.get('generation'), lane.get('review'),
                        lane.get('root'), lane.get('native')])


def dependency_pin(lane):
    return fingerprint([lane.get('state'), lane.get('integration'),
                        lane.get('review_disposition'),
                        (lane.get('root') or {}).get('head'),
                        (lane.get('native') or {}).get('head')])


def deferred(state, key):
    lane = state['lanes'].get(key, {})
    row = state.get('review_followups', {}).get(key, {})
    dependency = state['lanes'].get(row.get('waiting_on'), {})
    return bool(row and row['pin'] == pin(lane) and dependency and
                dependency.get('state') != 'done' and
                row['dependency_pin'] == dependency_pin(dependency))


def require_dispositions(state, owner, generation):
    obligations = [o for launch in state.get('control', {}).get('launches', {}).values()
                   if launch['lane'] == owner and launch.get('bound_generation') == generation
                   for o in launch.get('review_obligations', [])]
    pending = [o['lane'] for o in obligations
               if state['lanes'].get(o['lane'], {}).get('state') == 'review_ready'
               and pin(state['lanes'][o['lane']]) == o['pin'] and not deferred(state, o['lane'])]
    require(not pending, 'Aging reviews need acceptance, producer resumption, or a pinned '
            'workflow.review_followup deferral before standby: ' + ', '.join(pending))


def record(reg, key, generation, review_pin, reviewer, reviewer_generation,
           waiting_on, next_action, reason, evidence):
    require(nonempty(next_action) and nonempty(reason), 'Concrete next action and reason required')
    reg.evidence(evidence)
    with reg.transaction() as state:
        lane = reg.lane(state, key, generation)
        owner = reg.lane(state, reviewer, reviewer_generation)
        require(owner['state'] == 'running' and reg.probe(owner['process']) == 'alive',
                'Live current reviewer required')
        require(any(s.get('owner_lane') == reviewer and key in s.get('lanes', [])
                    for s in state.get('throughput', {}).get('workstreams', {}).values()),
                'Registered integration owner required')
        require(lane['state'] == 'review_ready' and pin(lane) == review_pin,
                'Review evidence or generation changed')
        require(waiting_on not in (key, reviewer), 'Independent prerequisite lane required')
        dependency = reg.lane(state, waiting_on)
        require(dependency['state'] != 'done', 'Completed prerequisite cannot justify deferral')
        row = dict(pin=review_pin, reviewer=reviewer, reviewer_generation=reviewer_generation,
                   waiting_on=waiting_on, dependency_pin=dependency_pin(dependency),
                   next_action=next_action, reason=reason, evidence=reg.archive_evidence(evidence),
                   at=reg.clock())
        state.setdefault('review_followups', {})[key] = row
        reg.event(state, 'review_followup_recorded', key, waiting_on=waiting_on)
        return row


def main():
    from .registry import Registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    reg = Registry(args.root / 'output/workflow/registry.sqlite3', args.root)
    print(json.dumps(record(reg, **json.loads(args.request.read_text(encoding='utf-8-sig')))))


if __name__ == '__main__':
    main()
