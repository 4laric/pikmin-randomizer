"""Hashed review dispositions; no timers or silent proposal mutation."""
import copy
from .handoff import require, digest


def record(reg, lane, generation, proposal, sha256, outcome, reason, evidence, wait_for_lanes=None):
    from .autofill import _private
    path = _private(reg, proposal)
    require(digest(path) == sha256, 'Proposal changed since review')
    require(outcome in ('repair', 'dependency'), 'Expected repair or dependency disposition')
    require(isinstance(reason, str) and reason.strip(), 'Actionable reason required')
    waiting = wait_for_lanes or []
    require(isinstance(waiting, list) and all(isinstance(k, str) for k in waiting), 'Explicit dependency lane list required')
    require(outcome != 'dependency' or waiting, 'Dependency disposition needs named lanes')
    reg.evidence(evidence)
    with reg.transaction() as state:
        owner = reg.lane(state, lane, generation)
        require(lane.startswith('publication-review-') or lane == 'acceptance-backlog-planner',
                'Registered publication reviewer required')
        require(owner['state'] in ('running', 'review_ready', 'done'), 'Reviewer not active or reviewed')
        if owner['state'] == 'running':
            require(reg.probe(owner['process']) == 'alive', 'Live reviewer required')
        else:
            require(owner.get('review', {}).get('evidence', {}).get('review') == evidence,
                    'Terminal reviewer evidence must match registered report')
        require(all(k in state['lanes'] for k in waiting), 'Unknown dependency lane')
        entry = dict(proposal=str(path), sha256=sha256, outcome=outcome, reason=reason,
                     evidence=copy.deepcopy(evidence), wait_for_lanes=waiting,
                     reviewer=lane, generation=generation, at=reg.clock())
        state.setdefault('proposal_feedback', {})[str(path)] = entry
        reg.event(state, 'proposal_disposition', lane, proposal=str(path), outcome=outcome)
        return entry


def feedback(reg, path, *, state=None, observed_sha=None):
    from contextlib import nullcontext
    with nullcontext(reg.snapshot() if state is None else state) as state:
        entry = copy.deepcopy(state.get('proposal_feedback', {}).get(str(path)))
        if not entry or entry['sha256'] != (observed_sha or digest(path)): return None
        if entry['outcome'] == 'dependency' and all(
                state['lanes'].get(k, {}).get('state') == 'done' for k in entry['wait_for_lanes']):
            return None
        return entry
