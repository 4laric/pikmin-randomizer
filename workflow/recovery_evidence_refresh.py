"""Read-only, fail-closed diagnosis for prerequisite-recovery evidence gaps.

`workflow.planner_pool.tick` parks a planning scope with reason
``Repair evidence unavailable`` when it re-verifies a prerequisite-recovery
request's hashed report through ``Registry.evidence`` and that verification
raises ``Missing or changed evidence`` (a removed file or changed bytes).

This module reproduces that verification without writing the registry, without
dispatching work and without weakening the recorded ``sha256``. For each
affected scope it either:

* reports that the recorded bytes still verify (no action), or
* reports ``stale_bytes`` / ``unavailable`` and the precise owner action, or
* finds a byte-identical surviving copy keyed by the exact recorded hash (the
  canonical ``output/workflow/evidence/<sha256>`` archive) and returns a
  *refreshed* request that is only ever reported, never applied.

Applying a refreshed request remains the existing owner/coordinator workflow
(``workflow.prerequisite_queue.resolve`` / a new recovery turn). This module
does not edit ``planner_pool.py``, ``prerequisite_queue.py`` or the registry
transaction APIs.
"""
import argparse
import copy
import json
from pathlib import Path

from .handoff import Rejected, digest, local_path, nonempty

REPAIR_EVIDENCE_REASON = 'Repair evidence unavailable'
MISSING_EVIDENCE_DETAIL = 'Missing or changed evidence'
ARCHIVE_RELATIVE = ('output', 'workflow', 'evidence')

STATUSES = ('verified', 'refreshable', 'stale_bytes', 'unavailable', 'malformed')


def _archive_dir(root, override=None):
    return Path(override) if override is not None else Path(root).joinpath(*ARCHIVE_RELATIVE)


def _canonical(root, path):
    """Render *path* as a root-relative POSIX path when it stays inside root."""
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve())).replace('\\', '/')
    except ValueError:
        return str(path)


def _lanes(request):
    values = request.get('lanes') or []
    return sorted(v for v in values if nonempty(v))


def _action(request, status, recorded, actual=None):
    owners = ', '.join(_lanes(request)) or 'the recorded owner lane'
    path = recorded.get('path')
    sha = recorded.get('sha256')
    if status == 'stale_bytes':
        return (f'Refused: {path} now holds bytes {actual}, not the recorded {sha}. '
                f'Owner lane(s) {owners} must re-submit outcome evidence matching the recorded hash '
                'or submit a new outcome; the changed bytes are never substituted and the recorded '
                'hash is never rewritten.')
    if status in ('unavailable', 'malformed'):
        return (f'Refused: exactly hashed evidence for {sha} is unavailable at {path}. '
                f'Owner lane(s) {owners} must re-submit or re-archive the outcome evidence, or the '
                'coordinator must re-run the recovery with fresh evidence; the recorded hash is not '
                'weakened.')
    return None


def verify_recorded(root, report):
    """Re-verify one ``{path, sha256}`` report exactly as ``Registry.evidence`` does.

    Returns a dict with ``status`` in ``verified``/``missing``/``stale``/``malformed``.
    Never raises for a missing or changed file; malformed input fails closed.
    """
    if not isinstance(report, dict) or not nonempty(report.get('path')) or not nonempty(report.get('sha256')):
        return dict(status='malformed', detail='Hashed evidence record required', path=None, actual=None)
    try:
        path = local_path(root, report['path'])
    except Rejected as exc:
        return dict(status='malformed', detail=str(exc), path=None, actual=None)
    if not path.is_file():
        return dict(status='missing', detail=MISSING_EVIDENCE_DETAIL, path=path, actual=None)
    try:
        actual = digest(path)
    except OSError as exc:
        return dict(status='missing', detail=str(exc) or MISSING_EVIDENCE_DETAIL, path=path, actual=None)
    if actual != report['sha256']:
        return dict(status='stale', detail=MISSING_EVIDENCE_DETAIL, path=path, actual=actual)
    return dict(status='verified', detail=None, path=path, actual=actual)


def find_truthful(root, report, archive_dir=None):
    """Return a verified copy of the exact recorded bytes, or ``None``.

    Only the canonical content-addressed archive keyed by the recorded ``sha256``
    is consulted. A different file is never re-hashed into the recorded identity.
    """
    sha = report.get('sha256') if isinstance(report, dict) else None
    if not nonempty(sha):
        return None
    candidate = _archive_dir(root, archive_dir) / sha
    try:
        if candidate.is_file() and digest(candidate) == sha:
            return candidate
    except OSError:
        return None
    return None


def diagnose(root, request, *, scope=None, archive_dir=None):
    """Diagnose one recovery request's recorded report without mutating anything.

    Returns ``status`` in :data:`STATUSES`, the precise ``owner_action`` when the
    evidence cannot be used, and a ``refreshed`` request copy when byte-identical
    evidence survives. ``refreshed`` is always reported with ``applied: False``.
    """
    request = copy.deepcopy(request or {})
    report = request.get('report')
    scope = scope or request.get('scope')
    result = dict(scope=scope, request_id=request.get('id'), lanes=_lanes(request),
                  recorded=copy.deepcopy(report), status='malformed', reason=None,
                  detail=None, actual_sha256=None, owner_action=None, refreshed=None,
                  applied=False, dispatched=False)
    check = verify_recorded(root, report)
    result['detail'] = check['detail']
    result['actual_sha256'] = check['actual']
    if check['status'] == 'verified':
        result.update(status='verified', reason='Recorded evidence bytes verified')
        return result
    if check['status'] == 'stale':
        result.update(status='stale_bytes', reason=check['detail'],
                      owner_action=_action(request, 'stale_bytes', report, check['actual']))
        return result
    if check['status'] == 'missing':
        survivor = find_truthful(root, report, archive_dir)
        if survivor is not None:
            refreshed = copy.deepcopy(request)
            refreshed['report'] = dict(path=_canonical(root, survivor), sha256=report['sha256'])
            result.update(status='refreshable', refreshed=refreshed,
                          reason='Recorded path missing; byte-identical archived evidence found',
                          owner_action=None)
            return result
        result.update(status='unavailable', reason=check['detail'],
                      owner_action=_action(request, 'unavailable', report))
        return result
    result.update(status='malformed', reason=check['detail'],
                  owner_action=_action(request, 'malformed', report if isinstance(report, dict) else {}))
    return result


def recovery_requests(root, state, helpers, records, now, *, age_seconds=900,
                      classify=True, cross_partition=False):
    """Read-only reproduction of ``planner_pool.tick``'s recovery selection.

    ``helpers`` must be the same list the live tick evaluates: each entry carries
    its ``prerequisite_lanes`` links and any ``kind`` field. Returns
    ``recovery`` (scopes that would be admitted), ``demands`` (every candidate
    recovery request) and ``sleeping`` (scopes parked by this branch). Nothing in
    ``state`` is mutated.
    """
    from .prerequisite_queue import recovery_demand

    blocked = {}
    if cross_partition:
        from .blocked_recovery import allocations as blocked_allocations
        blocked = blocked_allocations(state, helpers, records, now, age_seconds, classify=classify)
    sleeping, recovery, demands = {}, {}, {}
    recovery_chains = set()
    recovery_targets = {k for r in blocked.values() for k in r['request']['lanes']}
    for helper in helpers:
        record = records.get(helper['scope'])
        demand = blocked.get(helper['scope']) or (
            recovery_demand(state, helper, now, age_seconds) if record and 'completed_at' in record else None)
        if not demand:
            continue
        demands[helper['scope']] = demand
        if helper['scope'] not in blocked and recovery_targets.intersection(demand['request']['lanes']):
            sleeping[helper['scope']] = dict(reason='Blocked input already assigned to a repair planner')
            continue
        if demand['key'] in recovery_chains:
            sleeping[helper['scope']] = dict(reason='Same blocked chain already assigned to a repair planner')
            continue
        report = demand['request'].get('report')
        check = verify_recorded(root, report)
        if check['status'] != 'verified':
            sleeping[helper['scope']] = dict(reason=REPAIR_EVIDENCE_REASON,
                                             error=check['detail'],
                                             report=copy.deepcopy(report))
            continue
        recovery_chains.add(demand['key'])
        recovery_targets.update(demand['request']['lanes'])
        recovery[helper['scope']] = demand
    return dict(recovery=recovery, demands=demands, sleeping=sleeping)


def audit(root, state, helpers, records, now, *, age_seconds=900, classify=True,
          cross_partition=False, archive_dir=None):
    """Diagnose every scope parked for unavailable repair evidence."""
    reproduction = recovery_requests(root, state, helpers, records, now,
                                     age_seconds=age_seconds, classify=classify,
                                     cross_partition=cross_partition)
    diagnoses = []
    for scope, entry in reproduction['sleeping'].items():
        if entry.get('reason') != REPAIR_EVIDENCE_REASON:
            continue
        demand = reproduction['demands'].get(scope)
        if not demand:
            continue
        diagnoses.append(diagnose(root, demand['request'], scope=scope, archive_dir=archive_dir))
    return dict(sleeping=reproduction['sleeping'], recovery=reproduction['recovery'],
                diagnoses=diagnoses)


def _load_helpers(config):
    helpers = copy.deepcopy(config['throughput']['autofill']['planner_pool']['helpers'])
    return [h for h in helpers if nonempty(h.get('scope'))]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--request', type=Path,
                        help='JSON recovery request (or {"report": {...}}) to diagnose')
    parser.add_argument('--audit', action='store_true',
                        help='Read the live registry and config to reproduce sleeping scopes')
    parser.add_argument('--config', type=Path, help='Controller config for --audit')
    parser.add_argument('--db', type=Path, help='Registry database; defaults under --root/output/')
    parser.add_argument('--archive-dir', type=Path)
    args = parser.parse_args(argv)
    if args.request:
        payload = json.loads(args.request.read_text(encoding='utf-8-sig'))
        request = payload if 'report' in payload or 'id' in payload else dict(report=payload)
        print(json.dumps(diagnose(args.root, request, scope=payload.get('scope'),
                                  archive_dir=args.archive_dir), indent=2))
        return 0
    if not args.audit:
        raise SystemExit('Use --request or --audit')
    from .prerequisite_queue import links
    from .registry import Registry
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    planner = config['throughput']['autofill']['planner_pool']
    registry = Registry(args.db or args.root / 'output/workflow/registry.sqlite3', args.root)
    state = registry.snapshot()
    records = state.get('planner_pool', {}).get('scopes', {})
    helpers = [dict(h, prerequisite_lanes=links(state, h)) for h in _load_helpers(config)]
    result = audit(args.root, state, helpers, records, registry.clock(),
                   age_seconds=planner.get('prerequisite_recovery_seconds', 900),
                   classify=True, cross_partition=planner.get('cross_partition_recovery', False),
                   archive_dir=args.archive_dir)
    print(json.dumps(result['diagnoses'], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
