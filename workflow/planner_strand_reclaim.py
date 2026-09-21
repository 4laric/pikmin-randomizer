"""Bounded, fail-closed reclaim of stranded planner recovery chains.

A prerequisite-recovery helper claims one semantic chain and the chain identity is
recorded in ``throughput_runtime.autofill.prerequisite_recovery`` as a "once per
input" budget. When that helper terminates (``done``/``blocked``) without recording
the expected artifact -- a dependency classification for the exact current snapshot,
or a validated proposal/support action for an internal follow-up -- the identity is
still present and every allocation function skips it forever. The chain is then
invisible on the operator surface as a non-actionable ``needs_attention`` row, and
the blocked consumer never progresses.

This module detects exactly those stranded chains and re-arms each one *once* by
removing its terminal attempt record, so the live controller re-allocates it on its
normal tick. It never fabricates a classification, never edits a lane, never
resolves a dependency and never weakens any gate. ``plan`` is read-only; ``apply``
mutates through the normal registry transaction, records the prior attempt plus a
bounded reclaim history and emits one audit event per reclaimed chain. A chain whose
identity was already reclaimed for the same snapshot is refused, so a persistently
failing helper cannot loop.
"""
import argparse
import json
from pathlib import Path

from .control import fingerprint

LIVE_HELPER_STATES = (None, 'done', 'blocked')
DELIVERED_ACTIONS = ('proposal', 'producer', 'integration_packet')
RECLAIM_HISTORY = 'strand_reclaims'
HISTORY_LIMIT = 200


def _autofill(state):
    return state.setdefault('throughput_runtime', {}).setdefault('autofill', {})


def _attempts(state):
    return state.get('throughput_runtime', {}).get('autofill', {}).get('prerequisite_recovery', {})


def _history_read(state):
    history = state.get('throughput_runtime', {}).get('autofill', {}).get(RECLAIM_HISTORY, {})
    return history if isinstance(history, dict) else {}


def _classification_strands(state, attempts, history):
    """Unclassified consumers whose only classifier attempt terminated without recording."""
    from .dependency_classification import signature
    from .delivery_contracts import audit
    rows = state.get('dependency_classifications', {})
    strands = []
    for item in audit(state).get('unclassified', []):
        key = item.get('consumer')
        lane = state.get('lanes', {}).get(key)
        if not lane:
            continue
        snapshot = signature(lane)
        identity = 'classification-v2:' + fingerprint([key, snapshot])
        attempt = attempts.get(identity)
        if not attempt:
            continue
        helper = state['lanes'].get(attempt.get('lane'))
        helper_state = helper.get('state') if helper else None
        if helper_state not in LIVE_HELPER_STATES:
            continue
        if any(row.get('consumer') == key and row.get('snapshot') == snapshot for row in rows.values()):
            continue
        if identity in history:
            continue
        strands.append(dict(kind='classification', identity=identity, consumer=key,
                            helper=attempt.get('lane'), helper_state=helper_state, snapshot=snapshot))
    return strands


def _internal_strands(state, attempts, history):
    """Internal follow-ups whose only preparation attempt terminated without a deliverable."""
    from .internal_followup import requests as followup_requests
    strands = []
    for identity, row in followup_requests(state).items():
        attempt = attempts.get(identity)
        if not attempt:
            continue
        helper = state['lanes'].get(attempt.get('lane'))
        helper_state = helper.get('state') if helper else None
        if helper_state not in LIVE_HELPER_STATES:
            continue
        actions = [a for a in state.get('support_actions', {}).values()
                   if a.get('reviewer') == attempt.get('lane') and a.get('key') == row.get('consumer')]
        if any(a.get('action') in DELIVERED_ACTIONS for a in actions):
            continue
        if identity in history:
            continue
        strands.append(dict(kind='internal-follow-up', identity=identity, consumer=row.get('consumer'),
                            helper=attempt.get('lane'), helper_state=helper_state, snapshot=row.get('snapshot')))
    return strands


def plan(state):
    """Read-only list of stranded prerequisite-recovery chains, sorted by kind/consumer."""
    attempts = _attempts(state)
    history = _history_read(state)
    if not isinstance(attempts, dict):
        return []
    strands = _classification_strands(state, attempts, history)
    strands.extend(_internal_strands(state, attempts, history))
    return sorted(strands, key=lambda s: (s['kind'], s['consumer']))


def apply(reg):
    """Re-arm every planned stranded chain once; return the reclaimed chains.

    The transaction recomputes the plan so a concurrent change cannot be reclaimed
    from stale reads. Each removal records the prior attempt and appends a bounded
    history entry plus an audit event.
    """
    with reg.transaction() as state:
        strands = plan(state)
        autofill = _autofill(state)
        attempts = autofill.setdefault('prerequisite_recovery', {})
        history = autofill.setdefault(RECLAIM_HISTORY, {})
        for strand in strands:
            identity = strand['identity']
            prior = attempts.pop(identity, None)
            if prior is None:
                continue
            history[identity] = dict(strand, prior=prior, at=reg.clock())
            reg.event(state, 'planner_strand_reclaimed', strand['consumer'],
                      strand_kind=strand['kind'], identity=identity, helper=strand.get('helper'))
        if len(history) > HISTORY_LIMIT:
            ordered = sorted(history.items(), key=lambda kv: kv[1].get('at', 0))
            for identity, _ in ordered[:-HISTORY_LIMIT]:
                del history[identity]
        return strands


def main(argv=None):
    from .registry import Registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--db', type=Path, help='Registry database; defaults under --root/output/')
    parser.add_argument('--apply', action='store_true', help='Re-arm the stranded chains (default: report only)')
    args = parser.parse_args(argv)
    reg = Registry(args.db or args.root / 'output/workflow/registry.sqlite3', args.root)
    if args.apply:
        strands = apply(reg)
        print(json.dumps(dict(reclaimed=len(strands), strands=strands), indent=2))
    else:
        strands = plan(reg.snapshot())
        print(json.dumps(dict(stranded=len(strands), strands=strands), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
