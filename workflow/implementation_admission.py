"""Bounded admission of already prepared work, independent of historical audits."""
import json
import threading
import time
from .autofill import _state, _private, _prepare, _blocked, github_issue, PRIORITIES
from .handoff import Rejected
from .queue_pressure import dependents
from .runner import write


def tick(controller, issue_reader=github_issue):
    reg = controller.reg
    settings = controller.config.get('throughput', {}).get('autofill', {})
    if not settings.get('enabled') or not controller.capacity(): return []
    manifest = json.loads(_private(reg, settings['manifest']).read_text(encoding='utf-8-sig'))
    state = reg.snapshot()
    observed = _state(state)['items']
    candidates = []
    for spec in manifest.get('items', []):
        item = observed.get(spec.get('id'), {})
        capacity_retry = (item.get('status') == 'blocked' and
                          item.get('dependency_kind') == 'worker_capacity' and
                          reg.clock() - item.get('updated_at', 0) >= 30)
        owner_retry=False
        if (item.get('status')=='blocked' and item.get('dependency_kind')=='integration_owner'
                and reg.clock()-item.get('updated_at',0)>=30):
            stream=state.get('throughput',{}).get('workstreams',{}).get(spec.get('workstream'),{})
            owner=state['lanes'].get(stream.get('owner_lane'))
            owner_retry=bool(owner and reg.integration_owner_available(state,owner))
        if (item.get('phase') != 'enqueued' and not item.get('planner_helper') and
                (item.get('ready') or item.get('previous_lane') or capacity_retry or owner_retry)):
            candidates.append(spec)
    admitted = []
    limit = min(4, max(1, int(settings.get('admissions_per_pass', 4))))
    for spec in sorted(candidates, key=lambda i: (PRIORITIES.get(i.get('priority'), 99),
            -dependents(state['lanes'], i['lane']['lane'], i['lane']['issue']), i['id'])):
        if not controller.capacity(): break
        try:
            if _prepare(controller, spec, issue_reader):
                admitted.append(spec['lane']['lane'])
                if len(admitted) >= limit: break
        except (Rejected, OSError, ValueError, KeyError, TypeError) as exc:
            _blocked(reg, spec['id'], exc)
    return admitted


def start_monitor(controller):
    existing = getattr(controller, '_admission_monitor', None)
    if existing is not None: return existing
    stop = threading.Event()
    controller._admission_monitor = stop
    def monitor():
        while not stop.is_set():
            started = time.monotonic()
            try:
                admitted = tick(controller)
                write(controller.base / 'implementation-admission-status.json',
                      dict(at=controller.reg.clock(), admitted=admitted,
                           elapsed_seconds=time.monotonic()-started))
            except Exception as exc:
                write(controller.base / 'implementation-admission-error.json',
                      dict(at=controller.reg.clock(), error=str(exc), type=type(exc).__name__))
            stop.wait(max(1, 5-(time.monotonic()-started)))
    threading.Thread(target=monitor, name='implementation-admission', daemon=True).start()
    return stop
