"""Diagnostic fixture-to-reference adapter; no native save or authentication."""
from collections import Counter
import hashlib

from experimental.pikmin2_beasts_floor2_runtime import validate
from experimental.pikmin2_beasts_party_snapshot import party_snapshot
from experimental.pikmin2_beasts_boundary import validate_boundary


def bound_checkpoint_witnesses(adapter,checkpoint,log,readiness,*,refund=False):
    adapter.validate(checkpoint)
    validate_boundary(log,adapter.token(checkpoint))
    result=checkpoint_witnesses(adapter,checkpoint,log,readiness,refund=refund)
    result['native_boundary_correlated']=True
    return result


def checkpoint_witnesses(adapter, checkpoint, log, readiness, *, refund=False):
    """Return boundary-scoped events after verifying a complete fixture trace.

    Health, maturity and survivors come from the completed native fixture.
    Logs remain diagnostics, not an authenticated campaign handoff channel.
    """
    adapter.validate(checkpoint)
    if checkpoint['floor'] != 2 or checkpoint['status'] != 'active':
        raise ValueError('Witness bridge requires an active floor2 checkpoint')
    context = readiness.get('generation_context')
    if not isinstance(context, dict):
        raise ValueError('Explicit generation snapshot required')
    observed = validate(log, readiness, require_witnesses=True, refund=refund)
    party = party_snapshot(log,observed['final_population'])
    flower_ids = {62000: 'forest_1:floor2:BlackPom:0',
                  62001: 'forest_1:floor2:BlackPom:1'}
    expected_context = dict(
        global_plus_cave_purple=context['global_plus_cave_purple'],
        spawned_flowers=[flower_ids[i] for i in context['spawned_generators']])
    if checkpoint['context'] != expected_context or checkpoint['budgets'] != context['conversion_budgets']:
        raise ValueError('Checkpoint and native generation differ')
    expected_party = Counter(red=19, purple=1) if refund else Counter(red=20)
    if Counter(p['species'] for p in checkpoint['squad']) != expected_party:
        raise ValueError('Checkpoint does not match fixture incoming population')
    token = adapter.token(checkpoint)
    events = [dict(id=f'{token}:{record["sequence"]}',
                   flower=flower_ids[record['generator']], input=record['input'])
              for record in observed.get('witnesses', [])]
    return dict(schema='P2_BEASTS_DIAGNOSTIC_BRIDGE_1', token=token,
                log_text_sha256=hashlib.sha256(log.encode('utf-8')).hexdigest(),
                events=events, observed_population=observed['final_population'],
                party_snapshot=party,
                native_handoff_authenticated=False, native_ready=False)
