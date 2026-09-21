"""Supported development-stream owner activation path (#864).

`workflow.development_streams.bind_owner` can bind exactly one live existing
lane as a stream owner, but no supported role existed to create that owner lane
without stealing a live/blocked lane or hand-registering fabricated liveness.
This module is the minimal fenced contract the sole controller/coordinator
executes:

  prepare  -> read-only eligibility for a free/parked pool worker, no mutation
  activate -> register the issue-backed owner lane with the real long-lived
              worker PID and bind it to the stream at its live generation

The existing controller remains the only dispatcher; no new role is fabricated,
no live lane is stolen, and the pool's WIP/process/lease fences apply. One owner
per stream, one stream per lane and one ready batch per stream stay enforced by
`development_streams`. This module grants no source delivery, maintained
integration, export, consumer wakeup or gameplay admission.
"""
import argparse
import json
from pathlib import Path

from .development_streams import (CONFIG_PATH, bind_owner, observe_maintained_sources,
                                  observe_stream_worktrees, section, validate_sources)
from .handoff import Rejected, require
from .scheduling import OPEN

OWNER_TEMPLATE = ('Run exactly one bounded stream-local candidate through '
                  'workflow.development_streams; no canonical integration, maintained '
                  'merge/export, consumer wakeup or gameplay admission')


def _open_assignment(state, worker_id):
    return next((item for item in state.get('throughput', {}).get('assignments', {}).values()
                 if item.get('worker_id') == worker_id and item.get('status') in OPEN), None)


def _worker_lanes(state, worker_id):
    return [lane for lane in state.get('lanes', {}).values() if lane.get('worker_id') == worker_id]


def _free_worker(reg, state, worker_id):
    worker = state.get('throughput', {}).get('workers', {}).get(worker_id)
    require(worker is not None, 'Worker is not a registered pool worker: ' + str(worker_id))
    require('implementation' in worker.get('roles', []), 'Worker is not implementation-capable')
    require(_open_assignment(state, worker_id) is None,
            'Worker has an open assignment; park or release it through the controller first')
    previous = None
    for lane in _worker_lanes(state, worker_id):
        if lane['state'] == 'done':
            continue
        require(reg.probe(lane['process']) == 'dead',
                'Worker lane is live or unknown: ' + lane['lane'])
        require(lane['state'] == 'blocked',
                'Worker lane is not blocked for reuse: ' + lane['lane'] + ' (' + lane['state'] + ')')
        for name, lease in state.get('leases', {}).items():
            if lease.get('lane') == lane['lane']:
                require(reg.probe(lease['process']) == 'dead',
                        'Worker lane holds a live or uninspectable lease: ' + name)
        for request in state.get('queue', {}).values():
            if request.get('lane') == lane['lane']:
                require(reg.probe(request['process']) == 'dead',
                        'Worker lane has a live or uninspectable resource request')
        previous = previous or lane
    return previous


def _stream_record(state, stream):
    require(state.get('development_streams'), 'Development streams are not configured')
    record = section(state)['streams'].get(stream)
    require(record is not None, 'Unknown development stream: ' + str(stream))
    return record


def prepare(reg, stream, worker_id, issue, *, scope=None, owned_files=None, acceptance=None,
            milestone='development-streams', controller_config=None, observed=None,
            worktrees=None):
    """Read-only activation eligibility; returns a packet for `activate`."""
    require(type(issue) is int and issue > 0, 'Issue-backed owner lane required')
    state = reg.snapshot()
    record = _stream_record(state, stream)
    require(not record.get('owner'), 'Stream already has an owner')
    require(not record.get('ready_batch'), 'Stream already has a ready batch')
    previous = _free_worker(reg, state, worker_id)
    if observed is None:
        observed = observe_maintained_sources(reg, controller_config or CONFIG_PATH)
    if worktrees is None:
        worktrees = observe_stream_worktrees(reg, record)
    validate_sources(reg, stream, observed=observed, worktrees=worktrees)
    root_observation = worktrees.get('root') or {}
    root_head = root_observation.get('head')
    require(isinstance(root_head, str) and len(root_head) == 40,
            'Stream root worktree HEAD is not observable')
    return dict(schema=1, stream=stream, worker_id=worker_id, issue=issue,
                previous_lane=(previous or {}).get('lane'),
                previous_state=(previous or {}).get('state'),
                lane='stream-owner-' + stream,
                scope=scope or ('Development stream owner for ' + stream + ': ' + OWNER_TEMPLATE),
                owned_files=owned_files or ['output/development-streams/' + stream + '/owner.md'],
                acceptance=acceptance or [
                    'Record exactly one bounded stream-local candidate through workflow.development_streams',
                    'Keep stream-local completion separate from canonical integration and never wake maintained consumers',
                    'Preserve the maintained owner/dispatch authority and grant no gameplay acceptance',
                ],
                milestone=milestone,
                maintained_base=record['maintained_base'],
                root=dict(base=record['maintained_base']['root'], commits=[], head=root_head,
                          dirty='', worktree=(record['worktrees']['root'].get('path'))))


def activate(reg, packet, pid, task_id, *, controller_config=None, observed=None, worktrees=None):
    """Register the owner lane with the real live PID and bind it at that generation."""
    require(isinstance(packet, dict), 'Activation packet required')
    require(type(pid) is int and pid > 0, 'Live owner PID required')
    require(isinstance(task_id, str) and bool(task_id.strip()), 'Owner task id required')
    stream, worker_id, issue = packet.get('stream'), packet.get('worker_id'), packet.get('issue')
    state = reg.snapshot()
    existing = state['lanes'].get('stream-owner-' + str(stream))
    if existing is not None:
        require(existing.get('issue') == issue and existing.get('worker_id') == worker_id,
                'Existing owner lane differs from the activation packet')
        require(existing['state'] != 'done', 'Existing owner lane is done')
        bound = bind_owner(reg, stream, existing['lane'], existing['generation'])
        return dict(lane=existing['lane'], generation=existing['generation'], owner=bound,
                    replayed=True)
    fresh = prepare(reg, stream, worker_id, issue, scope=packet.get('scope'),
                    owned_files=packet.get('owned_files'), acceptance=packet.get('acceptance'),
                    controller_config=controller_config, observed=observed, worktrees=worktrees)
    record = dict(lane=fresh['lane'], owner='Codex through shared account 4laric; stream owner',
                  worker_id=worker_id, task_id=task_id, issue=issue, scope=fresh['scope'],
                  target_level='development-stream', milestone=fresh['milestone'],
                  closes_gates=[], next_action=OWNER_TEMPLATE,
                  owned_files=fresh['owned_files'], acceptance=fresh['acceptance'],
                  pid=pid, root=fresh['root'], native=None)
    registered = reg.register(record)
    bound = bind_owner(reg, stream, registered['lane'], registered['generation'])
    return dict(lane=registered['lane'], generation=registered['generation'], owner=bound,
                replayed=False)


def main():
    from .registry import Registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    request = json.loads(args.request.read_text(encoding='utf-8-sig'))
    registry = Registry(root / 'output/workflow/registry.sqlite3', root)
    operation = request.pop('operation', 'prepare')
    if operation == 'prepare':
        result = prepare(registry, **request)
    elif operation == 'activate':
        result = activate(registry, **request)
    else:
        raise Rejected('Unknown operation: ' + str(operation))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
