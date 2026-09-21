"""Sole helper preparation loop; no worker execution or duplicate scheduler."""
import threading
import time
from .runner import write


def start_monitor(controller):
    existing = getattr(controller, '_helper_monitor', None)
    if existing is not None:
        return existing
    stop = threading.Event()
    controller._helper_monitor = stop
    def monitor():
        from .planner_pool import tick
        from .autofill import github_issue
        while not stop.is_set():
            started = time.monotonic()
            try:
                settings = controller.config.get('throughput', {}).get('autofill', {})
                if settings.get('enabled'):
                    from .action_routing import tick as route_actions
                    route_actions(controller)
                    tick(controller, settings, github_issue)
                write(controller.base / 'helper-refill-status.json',
                      dict(at=controller.reg.clock(), elapsed_seconds=time.monotonic()-started), durable=False)
            except Exception as exc:
                write(controller.base / 'helper-refill-error.json',
                      dict(at=controller.reg.clock(), error=str(exc), type=type(exc).__name__))
            stop.wait(max(1, 5 - (time.monotonic() - started)))
    threading.Thread(target=monitor, name='helper-preparation', daemon=True).start()
    return stop
