"""Run the single durable workflow controller against an explicit configuration."""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow.controller import Controller
from workflow.registry import Registry
from workflow.processes import identify
from workflow.runner import write
from workflow.wakeup import EventWaiter
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--once', action='store_true', help='One real reconciliation/dispatch tick')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    registry = Registry(args.root / 'output/workflow/registry.sqlite3', args.root)
    registry.controller_claim(identify(os.getpid()))
    controller = Controller(registry, config)
    watched = [args.config, controller.base / 'WAKE']
    if config.get('integrator_inbox'):
        watched.append(args.root / config['integrator_inbox'])
    watched.extend(args.root / path for path in config.get('receipts', []))
    waiter = EventWaiter(registry.path, watched, controller.base / 'STOP')
    while not (controller.base / 'STOP').exists():
        try:
            controller.tick()
        except Exception as exc:
            # Keep the service alive; retain claimed actions and fail closed for this tick.
            write(controller.base / 'error.json', dict(at=time.time(), error=str(exc), type=type(exc).__name__))
            print(str(exc), file=sys.stderr, flush=True)
            if args.once: return 1
        if args.once: return 0
        waiter.wait(max(1, min(30, config.get('interval', 15))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
