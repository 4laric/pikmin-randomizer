"""Run the single durable workflow controller against an explicit configuration."""
import argparse
import json
import traceback
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
    from workflow.build_capacity import start_monitor
    memory_monitor = start_monitor(controller)
    dashboard_monitor = None
    if not args.once and config.get('throughput', {}).get('enabled', False):
        from workflow.dashboard_refresh import start_monitor as start_dashboard
        dashboard_monitor = start_dashboard(controller)
    dispatch_monitor = None
    if not args.once:
        controller.config['lanes'].update(registry.snapshot().get('throughput_runtime', {}).get('launch_specs', {}))
        from workflow.fast_dispatch import start_monitor as start_dispatch
        dispatch_monitor = start_dispatch(controller)
    helper_monitor = None
    if not args.once and config.get('throughput', {}).get('enabled', False):
        from workflow.helper_refill import start_monitor as start_helpers
        helper_monitor = start_helpers(controller)
    admission_monitor = None
    if not args.once and config.get('throughput', {}).get('enabled', False):
        from workflow.implementation_admission import start_monitor as start_admission
        admission_monitor = start_admission(controller)
    pressure_monitor = None
    if not args.once and config.get('queue_pressure',{}).get('enabled'):
        from workflow.queue_pressure import start_monitor as start_pressure
        pressure_monitor = start_pressure(controller)
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
            write(controller.base / 'error.json', dict(at=time.time(), error=str(exc), type=type(exc).__name__,
                traceback=''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))))
            print(str(exc), file=sys.stderr, flush=True)
            if args.once:
                memory_monitor.set()
                return 1
        if args.once:
            memory_monitor.set()
            return 0
        waiter.wait(max(1, min(30, config.get('interval', 15))))
    memory_monitor.set()
    if dashboard_monitor is not None: dashboard_monitor.set()
    if dispatch_monitor is not None: dispatch_monitor.set()
    if helper_monitor is not None: helper_monitor.set()
    if admission_monitor is not None: admission_monitor.set()
    if pressure_monitor is not None: pressure_monitor.set()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
