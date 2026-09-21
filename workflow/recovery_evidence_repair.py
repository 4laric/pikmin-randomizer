"""Bounded, hash-preserving repair of dead-but-archived recovery evidence.

Blocked lanes record an outcome evidence path that frequently lives in a transient
worker inbox which is cleaned after the turn. ``Registry.recovery_evidence`` (#855)
falls back to the canonical content-addressed archive at *read* time, but the
deployed controller line still parks a planner scope when the recorded path is
dead. This module durably repairs the recorded recovery *path* to the archive copy
only when the exact recorded ``sha256`` is verified byte-for-byte, so even a strict
verifier resumes. The hash is never changed, substituted or re-derived from other
bytes, and only blocked-lane recovery pointers are touched.

``plan`` is read-only; ``apply`` mutates through the normal registry transaction,
records the prior path and emits one audit event per repair. Repairs are
idempotent: an already-resolving pointer is skipped.
"""
import argparse
import json
from pathlib import Path

from .handoff import Rejected, digest, local_path, nonempty

ARCHIVE_RELATIVE = ('output', 'workflow', 'evidence')
REPAIR_HISTORY = 'recovery_evidence_repairs'


def _archived(root, sha256):
    """Return the canonical archive path for *sha256*, or ``None`` when absent/corrupt."""
    if not (isinstance(sha256, str) and len(sha256) == 64 and
            all(c in '0123456789abcdef' for c in sha256)):
        return None
    candidate = Path(root).joinpath(*ARCHIVE_RELATIVE) / sha256
    try:
        if candidate.is_file() and digest(candidate) == sha256:
            return candidate
    except OSError:
        return None
    return None


def verify(root, evidence):
    """Classify a recorded pointer: ``verified``/``missing``/``stale``/``malformed``.

    Matches ``workflow.recovery_evidence_refresh.verify_recorded`` so repair never
    acts where the read-only diagnosis would refuse. Only ``missing`` (an absent or
    unreadable source path) is eligible for archive repair; a live path holding
    changed bytes stays ``stale`` and is never silently replaced.
    """
    if not (isinstance(evidence, dict) and nonempty(evidence.get('path')) and nonempty(evidence.get('sha256'))):
        return 'malformed'
    try:
        path = local_path(root, evidence['path'])
    except Rejected:
        return 'malformed'
    if not path.is_file():
        return 'missing'
    try:
        actual = digest(path)
    except OSError:
        return 'missing'
    return 'verified' if actual == evidence['sha256'] else 'stale'


def resolves(root, evidence):
    """True when the recorded pointer already verifies byte-for-byte."""
    return verify(root, evidence) == 'verified'


def _relative(root, path):
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve())).replace('\\', '/')
    except ValueError:
        return str(path)


def _pointers(lane):
    """Yield ``(field, evidence)`` recovery pointers on one lane record."""
    outcome = lane.get('outcome')
    if isinstance(outcome, dict) and isinstance(outcome.get('evidence'), dict):
        yield 'outcome', outcome['evidence']
    if isinstance(lane.get('progress_evidence'), dict):
        yield 'progress_evidence', lane['progress_evidence']


def plan(root, state):
    """Read-only list of blocked-lane recovery pointers that can be repaired.

    Only blocked lanes are considered. A pointer is repairable when its source path
    is ``missing`` (not merely changed), its ``sha256`` is a canonical 64-hex value,
    and the archive holds byte-identical bytes for exactly that hash.
    """
    repairs = []
    for key, lane in (state.get('lanes') or {}).items():
        if not isinstance(lane, dict) or lane.get('state') != 'blocked':
            continue
        for field, evidence in _pointers(lane):
            if verify(root, evidence) != 'missing':
                continue
            candidate = _archived(root, evidence.get('sha256'))
            if candidate is None:
                continue
            repairs.append(dict(lane=key, field=field, sha256=evidence['sha256'],
                                previous_path=evidence.get('path'),
                                archive_path=_relative(root, candidate)))
    return repairs


def _target(lane, field):
    if field == 'outcome':
        return (lane.get('outcome') or {}).get('evidence')
    if field == 'progress_evidence':
        return lane.get('progress_evidence')
    return None


def apply(reg):
    """Repair every planned blocked-lane pointer; return the applied repairs.

    The transaction recomputes the plan so concurrent changes cannot be repaired
    from stale reads. Every rewrite preserves the recorded ``sha256`` and appends a
    bounded history entry plus an audit event.
    """
    with reg.transaction() as state:
        repairs = plan(reg.root, state)
        history = state.setdefault(REPAIR_HISTORY, [])
        for repair in repairs:
            lane = state['lanes'][repair['lane']]
            evidence = _target(lane, repair['field'])
            if not isinstance(evidence, dict):
                continue
            previous = evidence.get('path')
            evidence['path'] = repair['archive_path']
            record = dict(lane=repair['lane'], field=repair['field'],
                          sha256=repair['sha256'], previous_path=previous,
                          archive_path=repair['archive_path'], at=reg.clock())
            history.append(record)
            reg.event(state, 'recovery_evidence_repaired', repair['lane'],
                      field=repair['field'], sha256=repair['sha256'],
                      previous_path=previous, archive_path=repair['archive_path'])
        del history[:-200]
        return repairs


def main(argv=None):
    from .registry import Registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--db', type=Path, help='Registry database; defaults under --root/output/')
    parser.add_argument('--apply', action='store_true', help='Write the repairs (default: report only)')
    args = parser.parse_args(argv)
    reg = Registry(args.db or args.root / 'output/workflow/registry.sqlite3', args.root)
    if args.apply:
        repairs = apply(reg)
        print(json.dumps(dict(applied=len(repairs), repairs=repairs), indent=2))
    else:
        repairs = plan(reg.root, reg.snapshot())
        print(json.dumps(dict(repairable=len(repairs), repairs=repairs), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
