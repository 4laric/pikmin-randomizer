"""Publish current observations independently of slow scheduler maintenance."""
import threading
import time

from .runner import write


def start_monitor(controller):
    existing = getattr(controller, '_dashboard_monitor', None)
    if existing is not None:
        return existing
    stop = threading.Event()
    controller._dashboard_monitor = stop
    interval = max(5, float(controller.config.get('dashboard_refresh_seconds', 15)))

    def monitor():
        from .throughput_controller import publish_status
        while not stop.is_set():
            started = time.monotonic()
            try:
                publish_status(controller)
            except Exception as exc:
                write(controller.base / 'dashboard-refresh-error.json',
                      dict(at=controller.reg.clock(), error=str(exc), type=type(exc).__name__))
            stop.wait(max(1, interval - (time.monotonic() - started)))

    thread = threading.Thread(target=monitor, name='dashboard-publisher', daemon=True)
    thread.start()
    return stop
