"""Read-only grouping of maintained-export repair debt for the integration owner.

The compact operator (``python -m workflow.operator``) flags every integrated
native lane whose recorded export evidence is missing, changed, or an explicit
``none-performed`` statement. Those lanes are historical: their integration
receipts are immutable and must never be rewritten. This module reproduces that
exact classification, preserves each recorded receipt byte-for-byte, and emits
one grouped repair manifest that names the sole integration owner's single
maintained export step and the per-lane reconciliation commands.

The registry is only ever read. All derived output is written under ignored
``output/`` and nothing is auto-repaired: no integration record, no hash and no
lane state is changed. Generation fails closed if a recorded receipt changes
between the snapshots taken while building a manifest, or relative to a supplied
baseline manifest.
"""
import argparse
import copy
import json
import time
from pathlib import Path

from .control import fingerprint
from .handoff import Rejected, digest, local_path, require

HASH_MISMATCH = 'Recorded export evidence hash mismatch'
NONE_PERFORMED = 'Recorded export evidence says none-performed'
UNAVAILABLE = 'Recorded export evidence unavailable'
REASONS = (HASH_MISMATCH, NONE_PERFORMED, UNAVAILABLE)

MAINTAINED_EXPORT_COMMAND = 'py -3.12 scripts/export_native_source.py'
PRESERVE_NOTE = ('Historical integration receipts are immutable. Re-run the single maintained export, '
                 'then attach the resulting real evidence to this lane\'s issue. Never overwrite '
                 'export_sha256 in place or fabricate a replacement hash.')


def _reason(root, receipt):
    """Reproduce the operator's export-repair classification exactly."""
    try:
        path = local_path(root, receipt.get('export_evidence'))
        if digest(path) != receipt.get('export_sha256'):
            return HASH_MISMATCH
        try:
            proof = json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError, UnicodeError):
            proof = None
        return NONE_PERFORMED if isinstance(proof, dict) and proof.get('action') == 'none-performed' else None
    except (OSError, ValueError, TypeError):
        return UNAVAILABLE


def classify(root, lane):
    """Return the export-repair reason for one integrated lane, or None."""
    receipt = lane.get('integration') or {}
    if not receipt or lane.get('native') is None:
        return None
    return _reason(root, receipt)


def observed_sha256(root, receipt):
    """Hash the evidence file as it exists now; missing evidence yields None."""
    try:
        return digest(local_path(root, receipt.get('export_evidence')))
    except (OSError, ValueError, TypeError):
        return None


def receipt_fingerprint(lane, receipt):
    """Stable identity of an immutable receipt, scoped to its lane."""
    return fingerprint([lane, receipt])


def debt_rows(root, state):
    """One read-only row per flagged integrated lane, sorted by lane ID."""
    rows = []
    for key, lane in sorted(state.get('lanes', {}).items()):
        reason = classify(root, lane)
        if not reason:
            continue
        receipt = copy.deepcopy(lane.get('integration') or {})
        rows.append(dict(lane=key, issue=lane.get('issue'), reason=reason, state=lane.get('state'),
                         generation=lane.get('generation'), revision=lane.get('revision'),
                         integrated_at=lane.get('integrated_at'),
                         export_evidence=receipt.get('export_evidence'),
                         recorded_sha256=receipt.get('export_sha256'),
                         observed_sha256=observed_sha256(root, receipt),
                         receipt=receipt,
                         receipt_fingerprint=receipt_fingerprint(key, receipt)))
    return rows


def debt_fingerprint(row):
    """Receipt identity plus the observed evidence state at classification time."""
    return fingerprint([row['receipt_fingerprint'], row['observed_sha256'], row['reason']])


def identities(rows):
    """Combined fail-closed identity of the current export-repair debt."""
    return {row['lane']: debt_fingerprint(row) for row in rows}


def _require_unchanged(previous, current, message):
    changed = sorted(key for key in set(previous) | set(current)
                     if previous.get(key) != current.get(key))
    require(not changed, message + ': ' + json.dumps(changed))


def _baseline_fingerprints(baseline):
    require(isinstance(baseline, dict), 'Baseline manifest or receipt map required')
    value = baseline.get('debt_fingerprints', baseline)
    require(isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()),
            'Baseline debt fingerprints required')
    return value


def reconciliation(root, rows):
    """Per-lane read-only reconciliation commands for the integration owner."""
    result = []
    for row in rows:
        result.append(dict(
            lane=row['lane'], issue=row['issue'], reason=row['reason'],
            export_evidence=row['export_evidence'], recorded_sha256=row['recorded_sha256'],
            observed_sha256=row['observed_sha256'], receipt=copy.deepcopy(row['receipt']),
            inspect_command=(f'py -3.12 -m workflow.export_repair --root "{root}" '
                             f'--json --lane {row["lane"]}'),
            operator_command=f'py -3.12 -m workflow.operator --root "{root}" --json',
            preserve_receipt=True, note=PRESERVE_NOTE))
    return result


def manifest(root, state=None, *, lanes=None, baseline=None, now=None):
    """Build the grouped repair manifest without mutating any lane record."""
    if state is None:
        from .registry import Registry
        state = Registry(Path(root) / 'output/workflow/registry.sqlite3', root).snapshot()
    rows = debt_rows(root, state)
    if lanes is not None:
        wanted = set(lanes)
        rows = [row for row in rows if row['lane'] in wanted]
    current = identities(rows)
    if baseline is not None:
        _require_unchanged(_baseline_fingerprints(baseline), current,
                           'Recorded receipts/evidence changed since baseline')
    breakdown = {}
    for row in rows:
        breakdown[row['reason']] = breakdown.get(row['reason'], 0) + 1
    return dict(
        schema=1, at=now if now is not None else (state.get('at') if isinstance(state, dict) else None) or time.time(),
        root=str(root),
        debt_count=len(rows), breakdown=breakdown,
        lanes=[row['lane'] for row in rows],
        classifications={row['lane']: row['reason'] for row in rows},
        receipts={row['lane']: copy.deepcopy(row['receipt']) for row in rows},
        recorded_hashes={row['lane']: dict(export_evidence=row['export_evidence'],
                                           export_sha256=row['recorded_sha256'],
                                           observed_sha256=row['observed_sha256'],
                                           validation_path=row['receipt'].get('validation_path'),
                                           validation_sha256=row['receipt'].get('validation_sha256'))
                         for row in rows},
        receipt_fingerprints={row['lane']: row['receipt_fingerprint'] for row in rows},
        debt_fingerprints=current,
        maintained_export=dict(
            command=MAINTAINED_EXPORT_COMMAND, workdir=str(root),
            owner='sole registered integration lead',
            description=('Run the one maintained export on the integration line after its fast-forward/merge. '
                         'It produces the real export evidence these lanes lack. It does not, by itself, '
                         'rewrite any historical integration receipt.')),
        reconciliation=reconciliation(root, rows))


def prepare(reg, out_dir='output/workflow/export-repair', *, lanes=None, baseline=None, state=None):
    """Write the manifest under output/; fail closed on any receipt drift."""
    require(str(out_dir or '').strip() not in ('', '.'), 'Manifest output directory required')
    out = local_path(reg.root, str(out_dir))
    require(out.is_relative_to(local_path(reg.root, 'output')),
            'Repair manifests must stay under output/')
    wanted = None if lanes is None else set(lanes)
    first_state = state if state is not None else reg.snapshot()
    first = identities([row for row in debt_rows(reg.root, first_state)
                        if wanted is None or row['lane'] in wanted])
    second_state = reg.snapshot()
    second = identities([row for row in debt_rows(reg.root, second_state)
                         if wanted is None or row['lane'] in wanted])
    _require_unchanged(first, second, 'Recorded receipts/evidence changed while building the manifest')
    result = manifest(reg.root, second_state, lanes=lanes, baseline=baseline)
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'repair-manifest.json'
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    result['manifest_path'] = str(path)
    result['manifest_sha256'] = digest(path)
    return result


def main():
    from .registry import Registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', default='output/workflow/export-repair',
                        help='Output directory under <root>/output')
    parser.add_argument('--lane', action='append', dest='lanes',
                        help='Limit to one or more debt lane IDs')
    parser.add_argument('--baseline', type=Path,
                        help='Prior manifest; fail closed if any recorded receipt changed')
    parser.add_argument('--write', action='store_true',
                        help='Write the grouped manifest (default: plan only)')
    args = parser.parse_args()
    root = args.root.resolve()
    reg = Registry(root / 'output/workflow/registry.sqlite3', root)
    baseline = json.loads(args.baseline.read_text(encoding='utf-8-sig')) if args.baseline else None
    if args.write:
        result = prepare(reg, args.out, lanes=args.lanes, baseline=baseline)
    else:
        result = manifest(root, reg.snapshot(), lanes=args.lanes, baseline=baseline)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
