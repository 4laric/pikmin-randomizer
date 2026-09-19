"""Fenced handoff reconciliation for blocked lanes (p2-reconcile #511).

Reads the current lane revision from status, then invokes
ControlMixin.reconcile_handoff with explicit generation/revision fencing.
All safety checks live in workflow/control.py; this wrapper performs no
mutation beyond that single audited call. Never edits SQLite directly.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow.registry import Registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, help='Workspace root holding output/workflow/registry.sqlite3')
    parser.add_argument('--db', default=None, help='Registry path override within output/')
    parser.add_argument('--key', required=True, help='Lane key, e.g. muse-fuefuki')
    parser.add_argument('--generation', required=True, type=int)
    parser.add_argument('--revision', required=True, type=int,
                        help='Current revision from status; stale values are rejected')
    parser.add_argument('--summary', required=True, help='Reconcile summary recorded on the lane')
    parser.add_argument('--evidence', required=True, help='Hashed evidence file path (root-relative or absolute)')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    db = Path(args.db).resolve() if args.db else root / 'output/workflow/registry.sqlite3'
    evidence = (root / args.evidence).resolve() if not Path(args.evidence).is_absolute() else Path(args.evidence)
    digest = hashlib.file_digest(evidence.open('rb'), 'sha256').hexdigest()
    reg = Registry(db, root)
    try:
        lane = reg.reconcile_handoff(args.key, args.generation, args.revision,
                                     args.summary, {'path': args.evidence, 'sha256': digest})
    except Exception as error:
        print(json.dumps({'error': str(error)}))
        return 1
    print(json.dumps({'lane': lane['lane'], 'state': lane['state'],
                      'generation': lane['generation'], 'revision': lane['revision'],
                      'handoff': lane['handoff'], 'reconcile': lane.get('reconcile')}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
