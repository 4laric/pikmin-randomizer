"""Local lane coordination CLI. See docs/PIKMIN2_WORKFLOW.md."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow.handoff import Rejected, local_path, validate_handoff
from workflow.processes import identify
from workflow.registry import Registry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1],
                        help='Workspace containing native/ and ignored output/')
    parser.add_argument('--db', type=Path, help='Defaults to <root>/output/workflow/registry.sqlite3')
    parser.add_argument('--request', type=Path, help='UTF-8 JSON arguments; paths resolve against --root')
    parser.add_argument('command', choices=('init', 'register', 'heartbeat', 'checkpoint', 'failure',
                        'acquire', 'renew', 'release', 'cancel-request', 'watchdog', 'claim-action',
                        'complete-action', 'finish', 'accept-review', 'publish', 'receipt', 'control-status', 'handoff', 'validate-handoff', 'integrate', 'status', 'process',
                        'reconcile-handoff', 'throughput-status', 'wait-events', 'configure-lane-launch',
                        'set-workstream', 'register-pool-worker', 'reassign-pool-worker', 'provision-pool-lane', 'enqueue-job', 'assign-job',
                        'validate-assignment', 'plan-assignment', 'complete-assignment', 'release-assignment', 'scheduling-status',
                        'snapshot-handoff', 'dispose-review', 'publish-candidate', 'subscribe-candidate-qa',
                        'candidate-qa-ready', 'claim-candidate-qa', 'queue-candidate-qa', 'bind-candidate-qa-launch', 'record-candidate-qa',
                        'batch-claim', 'batch-reassign', 'batch-record-build', 'batch-isolate', 'batch-close', 'report-cost', 'report-cost-batch'))
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.request.read_text(encoding='utf-8-sig')) if args.request else {}
        if not isinstance(data, dict):
            raise Rejected('Request must be a JSON object')
        registry = Registry(args.db or args.root / 'output/workflow/registry.sqlite3', args.root)
        if args.command == 'register':
            result = registry.register(data)
        elif args.command == 'process':
            result = identify(**data)
        elif args.command == 'wait-events':
            from workflow.wakeup import EventWaiter
            paths = [local_path(args.root, path) for path in data.get('paths', ['output/deepseek-wave/inbox'])]
            waiter = EventWaiter(registry.path, paths, local_path(args.root, 'output/workflow/controller/STOP'))
            result = waiter.wait(timeout=data.get('timeout', 15), cursor=data.get('cursor'))
        elif args.command == 'validate-handoff':
            path = local_path(args.root, data['path'])
            result = validate_handoff(args.root, json.loads(path.read_text(encoding='utf-8-sig')))
        else:
            method = {'handoff': 'submit_handoff'}.get(args.command, args.command.replace('-', '_'))
            result = getattr(registry, method)(**data)
        print(json.dumps(result, indent=2))
        return 0
    except (Rejected, OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
