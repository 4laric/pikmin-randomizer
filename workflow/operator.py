"""Compact, read-only operator entrypoint: python -m workflow.operator."""
import argparse
import json
import subprocess
import time
from pathlib import Path

from .integration_wakeup import receipt_gaps
from .registry import Registry
from .handoff import local_path
from .processes import probe
from .planner_evidence_disposition import dispositions
from .review_acceptance import review_errors


DISPOSITION_STALE_SECONDS = 1800
CONFIG = 'output/workflow/controller/config.json'
WAKEABLE = ('review_ready', 'ready', 'running', 'reconciling')


def source_pin_errors(root, lane):
    """Report review source drift without mutating the registry or worktree."""
    errors = []
    if root is None:
        return errors
    for name in ('root', 'native'):
        source = lane.get(name)
        if not source:
            continue
        try:
            tree = local_path(root, source.get('worktree'))
            if not (tree / '.git').exists():
                continue
            head = subprocess.run(['git', '-C', str(tree), 'rev-parse', 'HEAD'],
                                  capture_output=True, text=True, check=True).stdout.strip()
            dirty = subprocess.run(['git', '-C', str(tree), 'status', '--porcelain'],
                                   capture_output=True, text=True, check=True).stdout.strip()
            if head != source.get('head'):
                errors.append(f'{name} HEAD is {head}, registry records {source.get("head")}')
            if dirty != str(source.get('dirty') or '').strip():
                errors.append(f'{name} dirty state differs from registry')
        except (OSError, subprocess.CalledProcessError, TypeError, ValueError) as exc:
            errors.append(f'{name} source pin could not be verified: {exc}')
    return errors


def dispatchable_lanes(root, state):
    """Controller lane keys that can be launched, or None when the config is unreadable.

    The controller merges persisted runtime launch specs into its configured lanes;
    both must be considered so the audit does not report a false outage.
    """
    if root is None:
        return None
    try:
        data = json.loads((Path(root) / CONFIG).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, UnicodeError):
        return None
    lanes = data.get('lanes') if isinstance(data, dict) else None
    if not isinstance(lanes, dict):
        return None
    specs = state.get('throughput_runtime', {}).get('launch_specs', {})
    return set(lanes) | (set(specs) if isinstance(specs, dict) else set())


def integration_line_outage(state, root, reviews, handoffs, export_repairs):
    """One action when integration demand exists but no workstream owner can be dispatched.

    A dead or `blocked` owner that is absent from the controller's configured lane set
    disables the whole integration wakeup path (`owner not in controller.config['lanes']`),
    so every terminal packet ages with no dispatch route. Surface that once instead of
    leaving N misleading per-packet "awaiting disposition" actions.
    """
    pool = state.get('throughput', {})
    streams = pool.get('workstreams', {}) if isinstance(pool, dict) else {}
    owners = sorted({s.get('owner_lane') for s in streams.values()
                     if isinstance(s, dict) and s.get('owner_lane')}) if isinstance(streams, dict) else []
    if not owners:
        return None
    demand = dict(reviews=sum(1 for r in reviews if r.get('disposition_ready')),
                  handoffs=len(handoffs), export_repairs=len(export_repairs))
    if not any(demand.values()):
        return None
    configured = dispatchable_lanes(root, state)
    rows = []
    for owner in owners:
        lane = state.get('lanes', {}).get(owner)
        row = dict(lane=owner, registered=bool(lane))
        if lane:
            alive = probe(lane.get('process') or {}) == 'alive'
            wakeable = lane.get('state') in WAKEABLE
            configured_ok = configured is None or owner in configured
            row.update(state=lane.get('state'),
                       process=probe(lane.get('process') or {}),
                       configured=(owner in configured) if configured is not None else None,
                       dispatchable=bool(alive or (wakeable and configured_ok)))
        else:
            row.update(state=None, process=None,
                       configured=(owner in configured) if configured is not None else None,
                       dispatchable=False)
        rows.append(row)
    if any(r['dispatchable'] for r in rows):
        return None
    return dict(
        priority=0, lane='integration-line-unavailable',
        reason=('Integration demand exists but no workstream owner can be dispatched '
                '(dead/blocked owner absent from the configured lane set)'),
        owners=rows, demand=demand,
        next_action=('Restore a dispatchable integration owner before expecting any disposition: add the owner '
                     'lane key to output/workflow/controller/config.json lanes (or its persisted launch specs) and '
                     'restart only the controller wrapper, or resume the stopped owner lane under a fresh generation; '
                     'then execute the prepared accept-review/handoff work. Do not integrate source or infer gameplay '
                     'acceptance here.'))


def parked_scope_diagnoses(root, state, now):
    """Read-only, fail-closed canonical reproduction of scopes parked for missing repair evidence.

    The live controller runs its own (possibly older) planner logic and persists only a
    `sleeping_scopes` summary. Reproduce the canonical selection here and classify each
    parked scope with the #855 read-only diagnostics, so the suppression of blocked-lane
    repair demand cannot stay invisible. Never mutates the registry or any file.
    """
    if root is None:
        return []
    try:
        config = json.loads((Path(root) / CONFIG).read_text(encoding='utf-8-sig'))
        planner = config['throughput']['autofill']['planner_pool']
    except (OSError, ValueError, UnicodeError, KeyError, TypeError):
        return []
    if not isinstance(planner, dict) or not planner.get('enabled'):
        return []
    try:
        from .recovery_evidence_refresh import audit
        from .prerequisite_queue import links
        records = state.get('planner_pool', {}).get('scopes', {})
        helpers = [dict(h, prerequisite_lanes=links(state, h))
                   for h in planner.get('helpers', []) if isinstance(h, dict) and h.get('scope')]
        result = audit(root, state, helpers, records, now,
                       age_seconds=planner.get('prerequisite_recovery_seconds', 900),
                       classify=True, cross_partition=planner.get('cross_partition_recovery', False))
        return result.get('diagnoses', [])
    except (ValueError, TypeError, KeyError, OSError):
        return []


def parked_scope_action(diagnoses, controller_sleeping, repairs=None, disposed=None):
    """Aggregate parked recovery scopes and controller-summary divergence into one action.

    Priority 0 when at least one scope is archive-refreshable (the #855 fallback would
    recover it) or a blocked lane has repairable dead-but-archived evidence, else 1.
    Scopes with an explicit coordinator historical-unavailable disposition
    (workflow.planner_evidence_disposition) are reported as history and no longer
    presented as actionable; their recorded hashes and lane dependencies are untouched.
    """
    disposed = disposed or {}
    diagnosed = {d['scope'] for d in diagnoses}
    active = [d for d in diagnoses if d.get('scope') not in disposed]
    if not active:
        return None
    refreshable = sorted(d['scope'] for d in active if d.get('status') == 'refreshable')
    reproduced = {d['scope'] for d in active}
    declared = set(controller_sleeping or {})
    repairable = len(repairs or [])
    rows = [dict(scope=d['scope'], status=d.get('status'), lanes=d.get('lanes') or [],
                 owner_action=d.get('owner_action'),
                 refreshed_path=((d.get('refreshed') or {}).get('report') or {}).get('path'))
            for d in sorted(active, key=lambda d: d['scope'])]
    history = [dict(scope=scope, status=disposed[scope].get('status'),
                    reason=disposed[scope].get('reason'))
               for scope in sorted(disposed) if scope in diagnosed]
    return dict(
        priority=0 if (refreshable or repairable) else 1,
        lane='planner-repair-evidence-parked',
        reason=(f"{len(active)} planner scopes are parked for unavailable repair evidence"
                + (f"; {len(refreshable)} archive-refreshable" if refreshable else '')
                + (f"; {repairable} blocked-lane pointers repairable" if repairable else '')
                + (f"; {len(history)} disposed historical-unavailable" if history else '')),
        scopes=rows, refreshable=refreshable, repairable_blocked_lanes=repairable,
        disposed=history,
        canonical_only=sorted(reproduced - declared), controller_only=sorted(declared - reproduced),
        next_action=('Repair dead-but-archived recovery pointers now with '
                     '`py -3.12 -m workflow.recovery_evidence_repair --root <canonical> --apply` '
                     '(byte-identical, hash-preserving), or deploy the #855 recovery-evidence fallback on the live '
                     'controller line: archive-refreshable scopes then resolve automatically without weakening the '
                     'recorded hash. For unavailable scopes the named owner lane must re-submit or re-archive the '
                     'exact outcome evidence (or the coordinator must re-run the recovery with fresh evidence); never '
                     'substitute changed bytes. Record one coordinator historical-unavailable disposition per scope '
                     '(`py -3.12 -m workflow.planner_evidence_disposition --root <canonical> --request <json>`) when '
                     'the exact bytes are confirmed lost, preserving every recorded hash and dependency. '
                     'Divergence from the controller summary is a deployed-line difference, '
                     'not a licence for another recovery tool.'))


def strand_reclaim_action(state, now):
    """Surface prerequisite-recovery chains stranded by a terminated planner attempt.

    A helper that ends without recording the expected classification or follow-up leaves
    a permanent "once per input" attempt that every allocation function skips, and a
    scope whose helper lane no longer exists pins the planning pool active forever. Both
    leave the blocked consumer as a non-actionable ``needs_attention`` row. Read-only;
    the bounded reclaim is an explicit operator action via ``workflow.planner_strand_reclaim``.
    """
    try:
        from .planner_strand_reclaim import plan as strand_plan
        strands = strand_plan(state, now=now)
    except (ValueError, TypeError, KeyError, OSError):
        return None
    if not strands:
        return None
    orphans = sum(1 for s in strands if s.get('kind') == 'orphaned-scope')
    chains = len(strands) - orphans
    return dict(
        priority=1, lane='planner-strand-reclaim',
        reason=(f"{chains} prerequisite classification/follow-up chains are stranded and {orphans} "
                'planner scopes are orphaned by a terminated planner attempt'),
        strands=strands,
        next_action=('Re-arm the stranded chains and release the orphaned scopes once with '
                     '`py -3.12 -m workflow.planner_strand_reclaim --root <canonical> --apply` '
                     '(bounded, fail-closed) or deploy the bounded reclaim on the controller line; a '
                     'terminal planner helper that recorded no classification/follow-up otherwise '
                     'suppresses its consumer chain forever, and a scope whose helper lane vanished pins '
                     'the planning pool active forever. Reclaiming is not classification and never '
                     'unblocks a consumer.'))


def report(state, now, root=None):
    from .delivery_contracts import audit
    lanes = state.get('lanes', {})
    autofill = state.get('throughput_runtime', {}).get('autofill', {})
    actions = []
    export_repairs = []
    export_reconciled = []
    for key, row in state.get('admission_reconciliation', {}).items():
        if row['status'] == 'pending' and lanes.get(key, {}).get('state') != 'done':
            actions.append(dict(priority=0, lane=key, reason=row['reason'],
                next_action='Integration owner: complete delivery receipts or record a pinned admission disposition',
                family=row['family'], token=row['token']))
    if root is not None:
        # Split historical debt into outstanding vs. durably reconciled against the
        # maintained export. A reconciliation only holds while the receipt identity,
        # observed evidence and reason fingerprint are unchanged; any drift re-flags.
        from .export_repair import reconciled_rows
        outstanding, reconciled = reconciled_rows(root, state)
        export_repairs = [dict(lane=row['lane'], issue=row.get('issue'), reason=row['reason'])
                          for row in outstanding]
        export_reconciled = [dict(lane=row['lane'], issue=row.get('issue'), reason=row['reason'])
                             for row in reconciled]
    if export_repairs:
        counts = {}
        for repair in export_repairs:
            counts[repair['reason']] = counts.get(repair['reason'], 0) + 1
        actions.append(dict(priority=0, lane='maintained-export-repair',
            reason=f"{len(export_repairs)} integrated lanes need corrective export evidence",
            breakdown=counts,
            next_action=('Integration lead: repair the maintained export evidence once, then reconcile the exact '
                         'affected lanes listed in export_repairs; preserve historical receipts')))
    gaps = [g for stream in state.get('throughput', {}).get('workstreams', {})
            for g in receipt_gaps(state, stream)]
    for gap in gaps:
        lane = lanes[gap['receipt_gap']]
        actions.append(dict(priority=0, lane=lane['lane'], issue=lane.get('issue'),
            reason='Closed batch lacks per-lane integration receipt',
            next_action=('Verify landed pins and validation, obtain actual native export evidence, then checkpoint integrating and Registry.integrate'
                         if gap['needs_native_export'] else
                         'Verify landed pins and validation, then checkpoint integrating and Registry.integrate'),
            batch=gap['closed_batch'], generation=gap['generation'], revision=gap['revision']))
    for key, item in autofill.get('items', {}).items():
        if item.get('phase') == 'enqueued' or item.get('status') in ('completed', 'superseded'):
            continue
        actions.append(dict(priority=1 if item.get('ready') or item.get('dependency_kind') == 'worker_capacity' else 2,
            item=key, lane=item.get('lane'), reason=item.get('reason') or item.get('status'),
            next_action=('Check authorized worker adaptation profiles against spec role/capabilities; retain ownership checks'
                         if item.get('dependency_kind') == 'worker_capacity' else
                         'Inspect prepared spec and planner publication feedback; controller owns admission')))
    blocked = [dict(lane=k, issue=l.get('issue'), generation=l.get('generation'),
                    dependencies=l.get('dependencies', []), next_action=l.get('next_action'),
                    evidence=(l.get('outcome') or {}).get('evidence'))
               for k, l in lanes.items() if l.get('state') == 'blocked' and k != 'acceptance-backlog-planner']
    handoffs = sorted([dict(lane=k, issue=l.get('issue'), state=l['state'],
                            age_seconds=max(0, now-(l.get('handoff_at') or now)))
                       for k, l in lanes.items() if l.get('state') in ('handoff_ready', 'integrating')],
                      key=lambda x: -x['age_seconds'])
    reviews = []
    for k, l in lanes.items():
        if l.get('state') != 'review_ready':
            continue
        pin_errors = source_pin_errors(root, l)
        evidence_errors = review_errors(root, l) if root is not None else []
        reviews.append(dict(lane=k, issue=l.get('issue'), state=l['state'],
                            generation=l.get('generation'), revision=l.get('revision'),
                            age_seconds=max(0, now-(l.get('handoff_at') or l.get('progress_at') or now)),
                            next_action=l.get('next_action'),
                            source_pin_errors=pin_errors, evidence_errors=evidence_errors,
                            disposition_ready=not pin_errors and not evidence_errors))
    reviews.sort(key=lambda x: -x['age_seconds'])
    for review in reviews:
        if review['source_pin_errors']:
            actions.append(dict(priority=0, lane=review['lane'], issue=review.get('issue'),
                reason='Review-ready source pins differ from the actual worktree',
                pin_errors=review['source_pin_errors'], generation=review['generation'],
                revision=review['revision'],
                next_action=('Independently verify the worktree and evidence, resume the lane, checkpoint '
                             'the exact source record, then resubmit review-ready; do not integrate stale pins')))
        if review['evidence_errors']:
            actions.append(dict(priority=0, lane=review['lane'], issue=review.get('issue'),
                reason='Review-ready evidence differs from its recorded bytes',
                evidence_errors=review['evidence_errors'], generation=review['generation'],
                revision=review['revision'],
                next_action=('Resume the lane, record the exact current evidence hash, and resubmit '
                             'review-ready; do not attempt an accept-review disposition on changed bytes')))
        if review['disposition_ready']:
            # A safe stored review still needs the sole integration owner to
            # execute accept-review or record a pinned deferral. Without this
            # action a valid terminal packet is invisible to the live action
            # list and ages silently; surface it explicitly instead.
            actions.append(dict(
                priority=0 if review['age_seconds'] >= DISPOSITION_STALE_SECONDS else 1,
                lane=review['lane'], issue=review.get('issue'),
                reason='Review-ready outcome awaiting sole-integrator disposition',
                generation=review['generation'], revision=review['revision'],
                age_seconds=int(review['age_seconds']),
                next_action=('Sole integration owner: execute the prepared accept-review request under '
                             'output/workflow/review-acceptance/<lane>.accept-review.json (regenerate with '
                             'py -3.12 -m workflow.review_acceptance --root <canonical> --write) or record a '
                             'pinned review_followup deferral; review acceptance is not source integration')))
    outage = integration_line_outage(state, root, reviews, handoffs, export_repairs)
    if outage:
        actions.append(outage)
    pool = autofill.get('planner_pool', {})
    repairs = []
    if root is not None:
        # Blocked lanes whose recorded recovery path is dead but whose exact bytes
        # survive in the archive are repairable now, even before #855 is deployed.
        try:
            from .recovery_evidence_repair import plan as recovery_evidence_plan
            repairs = recovery_evidence_plan(root, state)
        except (OSError, ValueError, TypeError):
            repairs = []
    parked = parked_scope_action(parked_scope_diagnoses(root, state, now),
                                 pool.get('sleeping_scopes'), repairs,
                                 disposed=dispositions(state))
    if parked:
        actions.append(parked)
    strands = strand_reclaim_action(state, now)
    if strands:
        actions.append(strands)
    return dict(at=now, delivery_audit=audit(state), export_repairs=export_repairs,
                export_reconciled=export_reconciled,
                actions=sorted(actions, key=lambda x:(x['priority'],x.get('lane') or '')),
                handoffs=handoffs, reviews=reviews, blocked=blocked,
                planning={k:pool.get(k) for k in ('active','target','target_reason','recovery_active','recovery_candidates','sleeping_scopes','cooling_scopes')},
                worker_count=len(state.get('throughput', {}).get('workers', {})))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--json', action='store_true', help='Machine-readable work and blocker details')
    args = parser.parse_args()
    root = args.root.resolve()
    data = report(Registry(root/'output/workflow/registry.sqlite3', root).snapshot(), time.time(), root)
    if args.json:
        print(json.dumps(data, indent=2))
        return
    print(f"Workers: {data['worker_count']} | Review-ready: {len(data['reviews'])} | Handoffs: {len(data['handoffs'])} | Blocked lanes: {len(data['blocked'])}")
    p = data['planning']
    print(f"Planning: {p['active']}/{p['target']} — {p['target_reason']}")
    for review in data['reviews']:
        print(f"\n{review['lane']} : review-ready ({int(review['age_seconds'])}s)\n  Next: {review['next_action'] or 'Independent review, then integration-owner disposition'}")
        for error in review['source_pin_errors']:
            print(f"  PIN MISMATCH: {error}")
    for action in data['actions']:
        print(f"\n{action.get('lane')} : {action['reason']}\n  Next: {action['next_action']}")
    print('\nUse --json for exact batch/generation pins and blocked consumer evidence.')
    print('Operating guide: docs/PIKMIN2_WORKFLOW_OPERATOR.md')


if __name__ == '__main__':
    main()
