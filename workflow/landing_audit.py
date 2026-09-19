"""Read-only audit of every integration receipt against the landing proof integrate() now requires.

  <python> <checkout>/scripts/workflow_module.py landing_audit --root <root> [--out <file.json>] [--lane KEY ...]

Reads one committed registry snapshot (no transaction, never writes the registry) and
runs the same per-file git checks: missing commits, files absent or different at the
receipt commit, deleted files still present, commits not on a declared integration line (or,
undeclared, on no branch outside the lane's own worktree).
Exit 1 when any receipt has a mismatch, 2 when the audit itself cannot run.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys

from .handoff import Rejected
from .landing import inspect, lines


def audit(root, lanes, declared=None, only=None):
    """{summary, receipts} over integrated lanes; each lane's git failure is its own finding."""
    root = Path(root).resolve()
    declared = lines(root) if declared is None else declared
    receipts, counts = [], Counter()
    for key, lane in sorted(lanes.items()):
        record = lane.get('integration')
        if not isinstance(record, dict) or (only and key not in only):
            continue
        item = dict(lane=key, generation=lane.get('generation'), root_commit=record.get('root_commit'),
                    native_commit=record.get('native_commit'), kind=record.get('kind', 'landed'),
                    proven_at_integration=bool(lane.get('integration_landing')))
        try:
            attestation, problems = inspect(root, lane, record, declared)
            item.update(files_changed=attestation['files_changed'],
                        head_is_ancestor={k: (attestation[k] or {}).get('head_is_ancestor') for k in ('root', 'native')},
                        line_check={k: (attestation[k] or {}).get('line_check') for k in ('root', 'native')})
            if not attestation['files_changed'] and not any(p['kind'] == 'missing_commit' for p in problems):
                item['no_changes'] = True  # Legacy no-op receipt; new ones must say already_landed.
        except (Rejected, OSError, ValueError) as exc:  # One unreadable lane never aborts the audit.
            problems = [dict(kind='unverifiable', detail=str(exc) or type(exc).__name__)]
        item['problems'] = problems
        counts.update(p['kind'] for p in problems)
        counts['receipts'] += 1
        counts['clean' if not problems else 'mismatched'] += 1
        counts['no_changes'] += bool(item.get('no_changes'))
        receipts.append(item)
    return dict(summary=dict(sorted(counts.items())), receipts=receipts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--db', type=Path, help='Defaults to <root>/output/workflow/registry.sqlite3')
    parser.add_argument('--out', type=Path, help='Also write the full JSON report here')
    parser.add_argument('--lane', action='append', help='Audit only these lanes (repeatable)')
    parser.add_argument('--all', action='store_true', help='Print clean receipts too')
    args = parser.parse_args(argv)
    from .registry import Registry
    root = args.root.resolve()
    try:
        lanes = Registry(args.db or root / 'output/workflow/registry.sqlite3', root).snapshot(section=('lanes',))
        report = audit(root, lanes, only=set(args.lane or ()))
    except (Rejected, OSError, ValueError, sqlite3.Error) as exc:
        print('Refused: ' + str(exc), file=sys.stderr)
        return 2
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text + '\n', encoding='utf-8')
    shown = report if args.all else dict(report, receipts=[r for r in report['receipts'] if r['problems']])
    print(json.dumps(shown, indent=2))
    return 1 if report['summary'].get('mismatched') else 0


if __name__ == '__main__':
    raise SystemExit(main())
