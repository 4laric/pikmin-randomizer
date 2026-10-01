"""Prepare sole-integrator accept-review dispositions from fenced registry state.

Review-ready lanes are terminal worker outcomes awaiting the integration
owner's `accept_review`, not implementation handoffs. This module is read-only
planning plus derived output under ignored `output/`: it revalidates each
stored review's evidence bytes and source pins, then emits the exact
`accept-review` request the owner can execute. The registry is never mutated,
nothing is auto-accepted, and no gameplay/source acceptance is implied.
"""
import argparse
import json
from pathlib import Path

from .handoff import Rejected, digest, local_path, require, validate_review


def review_errors(root, lane):
    """Revalidate stored review evidence without touching registry state."""
    review = lane.get('review') or {}
    if not review:
        return ['Review record missing']
    try:
        validate_review(root, review, lane)
    except (Rejected, OSError, ValueError, KeyError, TypeError) as exc:
        return ['Review evidence: ' + str(exc)]
    return []


def summary_for(lane):
    detail = lane.get('next_action') or (lane.get('review') or {}).get('conclusion')
    return 'Sole-integrator accept-review of review-ready outcome: ' + str(
        detail or 'review outcome recorded')


def request_for(lane):
    review = lane.get('review') or {}
    evidence = review.get('evidence') or {}
    require(evidence, 'Review evidence required')
    key = sorted(evidence)[0]
    require(isinstance(evidence[key], dict), 'Review evidence entry required')
    return dict(key=lane['lane'], generation=lane['generation'],
                summary=summary_for(lane), evidence=dict(evidence[key]))


def rows(reg):
    """One plan row per review-ready lane; unsafe lanes are never marked ready."""
    from .operator import source_pin_errors
    snapshot = reg.snapshot()
    covered = {key for stream in snapshot.get('throughput', {}).get('workstreams', {}).values()
               for key in stream.get('lanes', [])}
    result = []
    for key, lane in sorted(snapshot.get('lanes', {}).items()):
        if lane.get('state') != 'review_ready':
            continue
        errors = review_errors(reg.root, lane) + source_pin_errors(reg.root, lane)
        row = dict(lane=key, issue=lane.get('issue'), generation=lane.get('generation'),
                   revision=lane.get('revision'), errors=errors,
                   workstream=lane.get('workstream'), orphaned=key not in covered,
                   disposition_ready=not errors)
        if not errors:
            row['request'] = request_for(lane)
        result.append(row)
    return result


def prepare(reg, out_dir='output/workflow/review-acceptance', lane=None):
    """Write prepared requests and a hashed manifest; fail closed on any drift."""
    require(str(out_dir or '').strip() not in ('', '.'), 'Disposition output directory required')
    out = local_path(reg.root, str(out_dir))
    require(out.is_relative_to(local_path(reg.root, 'output')),
            'Disposition requests must stay under output/')
    planned = [row for row in rows(reg) if lane is None or row['lane'] == lane]
    require(planned, 'No matching review-ready lanes')
    unsafe = [row for row in planned if row['errors']]
    require(not unsafe, 'Unsafe review dispositions refused: ' + json.dumps(
        [dict(lane=row['lane'], errors=row['errors']) for row in unsafe]))
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    for row in planned:
        path = out / (row['lane'] + '.accept-review.json')
        path.write_text(json.dumps(row['request'], indent=2, sort_keys=True) + '\n', encoding='utf-8')
        entries.append(dict(lane=row['lane'], issue=row['issue'], generation=row['generation'],
                            revision=row['revision'], request_path=str(path),
                            request_sha256=digest(path)))
    manifest = dict(schema=1, at=reg.clock(), lanes=entries)
    manifest_path = out / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    manifest['manifest_path'] = str(manifest_path)
    manifest['manifest_sha256'] = digest(manifest_path)
    return manifest


def main():
    from .registry import Registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', default='output/workflow/review-acceptance',
                        help='Output directory under <root>/output')
    parser.add_argument('--lane', help='Limit to one review-ready lane')
    parser.add_argument('--write', action='store_true',
                        help='Write prepared request files (default: plan only)')
    args = parser.parse_args()
    root = args.root.resolve()
    reg = Registry(root / 'output/workflow/registry.sqlite3', root)
    if args.write:
        result = prepare(reg, args.out, args.lane)
    else:
        result = dict(at=reg.clock(),
                      lanes=[row for row in rows(reg) if args.lane is None or row['lane'] == args.lane])
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
