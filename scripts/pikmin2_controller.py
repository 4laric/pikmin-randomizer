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

FATAL = {}  # Where a last-resort traceback goes once the output directory is known.


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--once', action='store_true', help='One real reconciliation/dispatch tick')
    args = parser.parse_args(argv)
    FATAL.update(root=args.root, base=args.root / 'output/workflow/controller')
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    if isinstance(config, dict) and isinstance(config.get('output'), str):
        FATAL['base'] = args.root / config['output']
    from workflow.landing import CONFIG
    for key in ('integration_lines', 'release_target'):  # Never silently unchecked.
        if key in config and args.config.resolve() != (args.root / CONFIG).resolve():
            parser.error(f'{key} is read only from <root>/{CONFIG}; declare it there')
    interval = max(1, min(30, config.get('interval', 15)))
    spacing = config.get('min_tick_seconds', 5)  # Registry events arrive every few seconds.
    if type(spacing) not in (int, float) or not 0 <= spacing <= interval:
        parser.error('min_tick_seconds must be a number between 0 and the wait interval (%s)' % interval)
    registry_events = config.get('wake_on_registry_events', False)  # Opt-in: ticks on every registry event.
    if type(registry_events) is not bool:
        parser.error('wake_on_registry_events must be true or false')
    registry = Registry(args.root / 'output/workflow/registry.sqlite3', args.root)
    registry.controller_claim(identify(os.getpid()))
    controller = Controller(registry, config)
    from workflow.controller import record_restart
    record_restart(registry, controller.base)  # The wrapper's saved crash logs, if the last run failed.
    from workflow.build_capacity import start_monitor
    memory_monitor = start_monitor(controller)
    from workflow.registry_wal import start_monitor as start_wal_maintenance
    wal_monitor = start_wal_maintenance(controller)  # Bounded WAL checkpoint housekeeping.
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
    waiter = EventWaiter(registry.path, watched, controller.base / 'STOP', registry_events=registry_events)
    while not (controller.base / 'STOP').exists():
        started = waiter.clock()
        try:
            controller.tick()
        except Exception as exc:
            # Keep the service alive; retain claimed actions and fail closed for this tick.
            write(controller.base / 'error.json', dict(at=time.time(), error=str(exc), type=type(exc).__name__,
                traceback=''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))))
            print(str(exc), file=sys.stderr, flush=True)
            if args.once:
                memory_monitor.set()
                wal_monitor.set()
                return 1
        if args.once:
            memory_monitor.set()
            wal_monitor.set()
            return 0
        try:
            waiter.paced(interval, started, spacing)
        except Exception as exc:  # A failed wait must not end the service; fall back to the plain interval.
            write(controller.base / 'error.json', dict(at=time.time(), error=str(exc), type=type(exc).__name__, stage='wait',
                traceback=''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))))
            print(str(exc), file=sys.stderr, flush=True)
            time.sleep(max(0, started + interval - waiter.clock()))
    memory_monitor.set()
    wal_monitor.set()
    if dashboard_monitor is not None: dashboard_monitor.set()
    if dispatch_monitor is not None: dispatch_monitor.set()
    if helper_monitor is not None: helper_monitor.set()
    if admission_monitor is not None: admission_monitor.set()
    if pressure_monitor is not None: pressure_monitor.set()
    return 0


def run(argv=None):
    """main(), but an exception escaping it (startup, monitors, shutdown) leaves its traceback in
    <output>/error.json and on stderr before the non-zero exit the restart wrapper preserves."""
    try:
        return main(argv)
    except Exception as exc:
        text = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        print(text, file=sys.stderr, flush=True)
        base, root = FATAL.get('base'), FATAL.get('root')
        try:
            if base is not None and base.resolve().is_relative_to((root / 'output').resolve()):  # Private output only.
                base.mkdir(parents=True, exist_ok=True)
                write(base / 'error.json', dict(at=time.time(), error=str(exc), type=type(exc).__name__,
                                                stage='fatal', pid=os.getpid(), traceback=text))
        except OSError:
            pass  # stderr already holds the traceback.
        return 1


if __name__ == '__main__':
    raise SystemExit(run())
