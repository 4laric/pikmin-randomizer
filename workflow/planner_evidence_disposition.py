"""Coordinator dispositions for permanently unavailable planner repair evidence (#855).

For a set of long-parked planner scopes the recorded recovery report no longer exists
anywhere reachable: the recorded path is dead, the content-addressed archive holds no
matching bytes, and the named lanes' own outcome evidence files are gone. The operator
would otherwise present that unfixable set as an actionable repair demand forever.

This module records one explicit, evidence-backed coordinator disposition per scope so
the operator stops presenting it as work, while every recorded hash, lane dependency,
outcome and source obligation is preserved byte-for-byte. `dispositions`/`list` are
pure reads; `dispose` writes only the `planner_evidence_dispositions` registry section
through the normal transaction and never touches lanes, evidence bytes or dependencies.
"""
import argparse
import json
from pathlib import Path

from .handoff import require

SECTION = 'planner_evidence_dispositions'
STATUS = 'historical-unavailable'


def dispositions(state):
    return dict((state.get(SECTION) or {}).get('scopes') or {})


def dispose(reg, scopes, *, reason, evidence, recorded=None, applied_by='coordinator'):
    """Record a historical-unavailable disposition; exact replay is idempotent."""
    require(isinstance(scopes, list) and scopes and
            all(isinstance(scope, str) and scope for scope in scopes),
            'Explicit scope list required')
    require(isinstance(reason, str) and reason.strip(), 'Disposition reason required')
    require(isinstance(applied_by, str) and applied_by.strip(), 'Disposition owner required')
    if recorded is not None:
        require(isinstance(recorded, dict), 'recorded must map scope to its recorded evidence')
    reg.evidence(evidence)
    with reg.transaction() as state:
        section = state.setdefault(SECTION, dict(schema=1, scopes={}))
        now = reg.clock()
        result = []
        for scope in sorted(set(scopes)):
            record = dict(scope=scope, status=STATUS, reason=reason,
                          evidence=dict(evidence), applied_by=applied_by, at=now)
            if isinstance(recorded, dict) and recorded.get(scope):
                record['recorded_evidence'] = dict(recorded[scope])
            previous = section['scopes'].get(scope)
            if previous:
                require(all(previous.get(key) == record.get(key)
                            for key in ('status', 'reason', 'evidence', 'recorded_evidence')),
                        'Conflicting disposition for ' + scope + '; record the new decision explicitly')
                result.append(previous)
                continue
            section['scopes'][scope] = record
            reg.event(state, 'planner_evidence_disposed', scope, status=STATUS)
            result.append(record)
        return result


def main():
    from .registry import Registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    request = json.loads(args.request.read_text(encoding='utf-8-sig'))
    registry = Registry(root / 'output/workflow/registry.sqlite3', root)
    operation = request.get('operation', 'list')
    if operation == 'list':
        result = dispositions(registry.snapshot())
    elif operation == 'dispose':
        result = dispose(registry, request['scopes'], reason=request['reason'],
                         evidence=request['evidence'], recorded=request.get('recorded'),
                         applied_by=request.get('applied_by', 'coordinator'))
    else:
        raise SystemExit('Unknown operation: ' + str(operation))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
