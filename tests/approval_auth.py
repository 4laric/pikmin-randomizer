"""Authenticated test reviewers for the approvals ledger (not a test module).

A reviewer is a running lane with a running launch bound to its generation; the calling
process is made its descendant by patching approvals.ancestry for the test's lifetime.
"""
from unittest.mock import patch


def identity(key):
    return dict(host='approval-test-host', pid=40000 + sum(map(ord, key)), started='1' + str(len(key)))


def reviewer(case, reg, key, owns=(), fake_diff=False):
    """Make lane `key` an authenticated live reviewer for this test; returns its process identity.

    owns names producer lanes put in a workstream the reviewer owns. fake_diff stands in for
    git on fixtures whose lane pins are synthetic (the real diff is covered in test_workflow_approvals)."""
    process = identity(key)
    with reg.transaction() as state:
        lane = state['lanes'][key]
        lane.update(state='running', process=process)
        reg.control(state)['launches']['launch-' + key] = dict(
            id='launch-' + key, lane=key, generation=lane['generation'], bound_generation=lane['generation'],
            status='running', process=process, models=['test/reviewer-model'], model='test/reviewer-model',
            reason='review', session='session-' + key)
        if owns:
            streams = state.setdefault('throughput', {}).setdefault('workstreams', {})
            streams['review-' + key] = dict(owner_lane=key, lanes=list(owns))
    probe = reg.probe
    live = getattr(reg, '_approval_live', set())
    live.add(tuple(sorted(process.items())))
    reg._approval_live = live
    reg.probe = lambda p, probe=probe: 'alive' if isinstance(p, dict) and tuple(sorted(p.items())) in live else probe(p)
    calling(case, process)
    if fake_diff:
        fake = patch('workflow.approvals.diff', side_effect=lambda root, lane, file: (
            'root', file, 'd' * 64))
        fake.start(); case.addCleanup(fake.stop)
    return process


def caller(case, *processes):
    """The caller's launch ancestry is exactly these processes, nearest first."""
    calling(case)
    case._approval_chain[:] = list(processes)


def calling(case, *processes):
    """The caller now descends from these processes (outside earlier ones in this test: the first stays nearest)."""
    chain = getattr(case, '_approval_chain', [])
    chain.extend(processes)
    case._approval_chain = chain
    if not getattr(case, '_approval_patched', False):
        patcher = patch('workflow.approvals.ancestry', side_effect=lambda: list(case._approval_chain))
        patcher.start(); case.addCleanup(patcher.stop)
        case._approval_patched = True
