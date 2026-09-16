"""Atomic planning claims in the shared registry (not build or implementation leases).

Helpers claim canonical issue/provider/file/topic resources before doing overlapping
research or creating issues. A batch either succeeds entirely or leaves no change.
Claims have no TTL and survive completion: unpublished proposals stay protected.
An owner may explicitly release while current and alive. The registered live
controller (or the registered acceptance-backlog-planner lane) may release a stopped
done/review_ready owner only with hashed disposition
evidence; unknown processes, protected children and in-flight launches fail closed.
This is cooperative registry fencing, not authentication against hostile local users.

CLI: python -m workflow.planner_claims --root <shared-absolute-root>
     --request <json-file> claim|release|inspect
Request keys match the public functions, excluding reg. Never initialize a private
registry for helpers. File keys use repository-relative semantic paths, not worktree
paths. File parents overlap descendants; unrelated topic/provider names require the
coordinator's shared vocabulary (semantic synonym detection is not attempted).
"""
import argparse
import copy
import json
from pathlib import Path
import re

from .handoff import require


def canonical_resource(value):
    require(isinstance(value, str) and ':' in value, 'Resource needs a namespace')
    kind, name = value.strip().lower().split(':', 1)
    if kind == 'issue':
        require(re.fullmatch(r'[0-9]+', name) and int(name) > 0, 'Positive issue number required')
        return 'issue:' + str(int(name))
    if kind == 'file':
        name = name.replace('\\', '/')
        require(not name.startswith('/') and ':' not in name, 'Repository-relative file required')
        parts = name.split('/')
        require(all(p and p not in ('.', '..') and not p.endswith((' ', '.')) and
                    re.fullmatch(r'[a-z0-9_.-]+', p) for p in parts), 'Canonical file path required')
        return 'file:' + '/'.join(parts)
    require(kind in ('provider', 'topic') and re.fullmatch(r'[a-z0-9][a-z0-9_-]*', name),
            'Use issue, file, provider or topic with a stable canonical name')
    return kind + ':' + name


def _resources(resources):
    require(isinstance(resources, list) and resources, 'Nonempty resource batch required')
    return sorted(set(canonical_resource(v) for v in resources))


def _overlap(first, second):
    return first == second or (first.startswith('file:') and second.startswith('file:') and
                              (first.startswith(second + '/') or second.startswith(first + '/')))


def _owner(record, lane, generation):
    return record['lane'] == lane and record['generation'] == generation


def claim(reg, lane, generation, resources):
    """Claim all resources for a current, running, confirmed-live lane; replay is safe."""
    keys = _resources(resources)
    require(type(generation) is int, 'Integer generation required')
    with reg.transaction() as state:
        owner = reg.lane(state, lane, generation)
        require(owner['state'] == 'running' and reg.probe(owner['process']) == 'alive',
                'Running, live planning owner required')
        claims = state.setdefault('planning_claims', {})
        for key in keys:
            for existing, record in claims.items():
                require(not _overlap(key, existing) or _owner(record, lane, generation),
                        'Planning resource already claimed: ' + existing)
        added = []
        for key in keys:
            if key not in claims:
                claims[key] = dict(resource=key, lane=lane, generation=generation,
                                   process=copy.deepcopy(owner['process']), claimed_at=reg.clock())
                added.append(key)
        if added:
            reg.event(state, 'planning_claimed', lane, generation=generation, resources=added)
        return [copy.deepcopy(claims[key]) for key in keys]


def inspect_claims(reg, lane=None):
    """Return claims in deterministic resource order without expiring any owner."""
    with reg.transaction() as state:
        return [copy.deepcopy(v) for k, v in sorted(state.get('planning_claims', {}).items())
                if lane is None or v['lane'] == lane]


def release(reg, lane, generation, resources, *, disposition=None, coordinator=None):
    """Explicit fenced batch release; absent keys are harmless idempotent replays."""
    keys = _resources(resources)
    require(type(generation) is int, 'Integer generation required')
    with reg.transaction() as state:
        owner = reg.lane(state, lane, generation)
        claims = state.setdefault('planning_claims', {})
        for key in keys:
            require(key not in claims or _owner(claims[key], lane, generation),
                    'Planning claim owner mismatch: ' + key)
        if coordinator is None:
            require(reg.probe(owner['process']) == 'alive', 'Live current owner required for release')
        else:
            if isinstance(coordinator, dict) and set(coordinator) == {'lane', 'generation'}:
                require(coordinator['lane'] == 'acceptance-backlog-planner',
                        'Only the acceptance backlog coordinator may dispose claims')
                lead = reg.lane(state, coordinator['lane'], coordinator['generation'])
                require(lead['state'] == 'running' and reg.probe(lead['process']) == 'alive',
                        'Registered live coordinator required')
            else:
                require(coordinator == state.get('control', {}).get('controller') and
                        reg.probe(coordinator) == 'alive', 'Registered live coordinator required')
            require(owner['state'] in ('done', 'review_ready'), 'Terminal reviewed owner required')
            require(reg.probe(owner['process']) == 'dead', 'Planning owner not confirmed stopped')
            for key in keys:
                if key in claims:
                    require(reg.probe(claims[key]['process']) == 'dead', 'Original claim owner not stopped')
            for group in ('leases', 'queue'):
                for item in state.get(group, {}).values():
                    if item['lane'] == lane:
                        require(reg.probe(item['process']) == 'dead', 'Protected process not stopped')
            for item in state.get('control', {}).get('launches', {}).values():
                if item['lane'] == lane:
                    require(item['status'] not in ('intent', 'spawned', 'running', 'exiting'),
                            'Planning dispatch still in flight')
                    if item.get('process'):
                        require(reg.probe(item['process']) == 'dead', 'Launch process not stopped')
            reg.evidence(disposition)
        removed = [key for key in keys if key in claims]
        for key in removed:
            del claims[key]
        if removed:
            reg.event(state, 'planning_released', lane, generation=generation,
                      resources=removed, disposition=disposition, coordinator=coordinator)
        return dict(released=removed)


def main(argv=None):
    from .registry import Registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--db')
    parser.add_argument('--request')
    parser.add_argument('command', choices=('claim', 'release', 'inspect', 'list'))
    args = parser.parse_args(argv)
    root = Path(args.root)
    require(root.is_absolute(), 'Absolute shared workspace root required')
    root = root.resolve()
    reg = Registry(Path(args.db) if args.db else root/'output/workflow/registry.sqlite3', root)
    request = json.loads(Path(args.request).read_text(encoding='utf-8-sig')) if args.request else {}
    action = {'claim': claim, 'release': release, 'inspect': inspect_claims, 'list': inspect_claims}[args.command]
    print(json.dumps(action(reg, **request), indent=2))


if __name__ == '__main__':
    main()
