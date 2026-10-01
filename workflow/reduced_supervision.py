"""Bounded, model-free reduced-mode supervision. Never merges or approves reviews."""
import json
import re
from collections import Counter

from .control import fingerprint, git
from .handoff import Rejected, local_path
from .no_progress import normalize, Parked


def inputs(state, lane):
    """Only durable relevant source/delivery/decision changes count, not wake text/time."""
    dependencies = lane.get('dependencies') or []
    issues = {int(x) for d in dependencies for x in re.findall(r'#(\d+)\b', d)}
    producers = {}
    for key, other in state.get('lanes', {}).items():
        if key == lane['lane']:
            continue
        if other.get('issue') in issues or any(re.search(r'(?<![\w-])' + re.escape(key) + r'(?![\w-])', d) for d in dependencies):
            producers[key] = {k: other.get(k) for k in ('integration', 'review_disposition')}
            producers[key]['source'] = [(other.get(k) or {}).get('head') for k in ('root', 'native')]
    approvals = sorted(k for k, row in state.get('approvals', {}).items()
                       if row.get('lane') == lane['lane'])
    return fingerprint(dict(source=[(lane.get(k) or {}).get('head') for k in ('root', 'native')],
                            dependencies=sorted({normalize(d) for d in dependencies}),
                            producers=producers, approvals=approvals))


def record_blocked(state, lane):
    if lane['lane'].startswith('rd-') and lane['state'] == 'blocked':
        lane['reduced_blocked_inputs'] = inputs(state, lane)


def check_retry(state, lane):
    if (lane['lane'].startswith('rd-') and lane['state'] == 'blocked'
            and lane.get('reduced_blocked_inputs') == inputs(state, lane)):
        raise Parked('Reduced lane blocked on unchanged inputs; supply a producer/source/approved '
                     'decision change or an explicit operator retry with hashed evidence. Time and prompt changes do not count.')


def tick(controller):
    options = controller.config.get('reduced_supervision', {})
    if not options.get('enabled'):
        return
    now = controller.reg.clock()
    if now < getattr(controller, '_reduced_next', 0):
        return
    controller._reduced_next = now + max(30, options.get('interval_seconds', 300))
    reg = controller.reg
    state = reg.snapshot(sections=[('lanes',), ('leases',), ('queue',)])
    lanes = {k: v for k, v in state.get('lanes', {}).items() if k.startswith('rd-')}
    pending = sorted(k for k, l in lanes.items() if l['state'] in ('handoff_ready', 'integrating'))
    results = []
    limit = min(4, max(1, options.get('max_per_tick', 2)))
    offset = getattr(controller, '_reduced_offset', 0) % max(1, len(pending))
    selected = (pending[offset:] + pending[:offset])[:limit]
    controller._reduced_offset = offset + len(selected)
    for key in selected:
        lane = lanes[key]
        item = dict(lane=key, generation=lane['generation'])
        try:
            if not reg.recovery_safe(state, lane):
                item['action'] = 'wait_for_worker'
            else:
                path = local_path(reg.root, f'output/reduced/{key}/receipt-request.json')
                if path.is_file():
                    request = json.loads(path.read_text(encoding='utf-8-sig'))
                    if request.get('key') != key or request.get('generation') != lane['generation']:
                        raise Rejected('Receipt request lane/generation mismatch')
                    # receipt() verifies hashes, source bytes, line reachability and ledger approvals.
                    # Never invent validation or export evidence and never auto-approve a shared change.
                    reg.receipt(**request)
                    item['action'] = 'receipted'
                else:
                    from .landing import inspect
                    record = {}
                    for name in ('root', 'native'):
                        if name == 'native' and not lane.get(name):
                            continue
                        line = controller.config['integration_lines'][name]
                        record[name + '_commit'] = git(local_path(reg.root, line['repo']), 'rev-parse', line['ref'])
                    proof, problems = inspect(reg.root, lane, record)
                    item.update(action='needs_landing' if problems else 'needs_review_and_receipt',
                                files_changed=proof['files_changed'],
                                problems=[p['detail'][:300] for p in problems[:3]])
        except (Rejected, OSError, ValueError, KeyError, TypeError) as exc:
            item.update(action='needs_operator', error=str(exc)[:600])
        results.append(item)
    blocked = [dict(lane=k, issue=l.get('issue'),
                    unchanged=l.get('reduced_blocked_inputs') == inputs(state, l),
                    reason=l.get('next_action', '')[:350])
               for k, l in sorted(lanes.items()) if l['state'] in ('blocked', 'review_ready')]
    report = dict(at=now, states=dict(Counter(l['state'] for l in lanes.values())),
                  pending_total=len(pending), checked=results, attention=blocked,
                  running=[k for k, l in lanes.items() if l['state'] == 'running'])
    report['signature'] = fingerprint({k: v for k, v in report.items() if k != 'at'})
    from .runner import write
    write(controller.base / 'reduced-supervision.json', report, durable=False)


def main(argv=None):
    import argparse
    from pathlib import Path
    p = argparse.ArgumentParser(description='Compact reduced supervisor report; no full registry dump.')
    p.add_argument('--root', type=Path, required=True)
    a = p.parse_args(argv)
    path = a.root / 'output/workflow/controller/reduced-supervision.json'
    print(path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
