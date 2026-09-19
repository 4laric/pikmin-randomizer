"""Reassess explicit build contention after a real capacity release."""
import copy
import re

from .build_capacity import admission_paused
from .control import fingerprint
from .handoff import Rejected
from .planner_demand import is_helper


def tick(controller):
    reg = controller.reg
    state = reg.snapshot()
    if admission_paused(state, reg.clock()): return
    free = state['settings']['max_heavy_builds'] - sum(
        reg.heavy(k) and reg.probe(v['process']) != 'dead' for k,v in state['leases'].items())
    if free <= 0: return
    events = [e for e in state.get('events', []) if
              (e['kind'] in ('lease_released', 'lease_reaped', 'request_reaped', 'request_cancelled') and reg.heavy(e.get('resource', ''))) or
              (e['kind'] == 'build_capacity_changed' and e.get('capacity', 0) > e.get('previous', 0))]
    if not events: return
    event = max(events, key=lambda e:e['at'])
    token = 'build-resource-available:' + fingerprint(event)
    launches = list(state.get('control', {}).get('launches', {}).values())
    limit = min(2, free)
    for key, lane in sorted(state['lanes'].items(), key=lambda item:item[1].get('progress_at', 0)):
        if limit <= 0: break
        if (key not in controller.config['lanes'] or lane['state'] != 'blocked' or is_helper(key)
                or lane.get('handoff') or event['at'] <= lane.get('progress_at', 0)):
            continue
        text = lane.get('next_action', '') + ' ' + ' '.join(lane.get('dependencies', []))
        build_wait = (re.search(r'build.{0,40}(?:lease|slot|pool)', text, re.I) and
                      re.search(r'queued|held|wait|deferred|pool slot', text, re.I))
        fifo_wait = (re.search(r'FIFO.{0,100}(?:head|queue)', text, re.I) and
                     re.search(r'heavy.{0,20}pool|build.{0,20}(?:pool|queue)', text, re.I) and
                     re.search(r'blocked|wedg|wait|stall', text, re.I))
        if not (build_wait or fifo_wait):
            continue
        if not reg.recovery_safe(state, lane) or not controller.available(key): continue
        if any(x['lane'] == key and (x['reason'] == token or
               x['status'] in ('intent', 'spawned', 'running', 'exiting')) for x in launches): continue
        try:
            reg.plan_launch(key, token,
                'A canonical build lease or queue entry was released/reaped/cancelled, or the build cap increased after your '
                'recorded resource blocker. Reassess the existing slice in the same private worktrees. '
                'This is permission to retry normal lease acquisition, not a reserved slot or a source '
                'approval. Preserve FIFO and aggregate build limits; use canonical leases. Preserve '
                'commits and all unresolved asset, source, shared-review and runtime gates. Clear only '
                'blockers disproved by fresh evidence. Do not create duplicate work, bypass ADMIT or '
                'claim runtime acceptance. If another blocker remains, checkpoint it precisely and stop. '
                'Availability event: ' + str(event), controller.config['models'])
            limit -= 1
        except Rejected as exc:
            reg.notice(key, 'resource_wakeup_blocked', dict(error=str(exc)))
