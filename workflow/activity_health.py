"""Observed session activity, separate from controller-renewed heartbeats."""
import datetime
import re

from .provider_recovery import _CLEANUP, idle_terminal


def snapshot(controller, *, notices=True):
    reg = controller.reg
    now = reg.clock()
    result = {}
    for launch in reg.snapshot().get('control', {}).get('launches', {}).values():
        if launch.get('status') != 'running':
            continue
        directory = controller.launch_directory(launch['id'])
        events, errors = directory / 'events.jsonl', directory / 'stderr.log'
        latest = launch.get('created_at', now)
        try:
            if events.stat().st_size:
                latest = max(latest, events.stat().st_mtime)
            for line in errors.read_text(encoding='utf-8', errors='replace').splitlines():
                if _CLEANUP.fullmatch(line):
                    continue
                match = re.match(r'timestamp=(\S+)', line)
                if match:
                    stamp = datetime.datetime.fromisoformat(match[1].replace('Z', '+00:00')).timestamp()
                    latest = max(latest, stamp)
            evidence = idle_terminal(events, errors, launch.get('session'), now)
            age = max(0, now - latest)
            status = ('provider failed' if evidence and evidence.get('failure') else
                      'turn ended' if evidence else 'stalled / inspect' if age > 600 else 'recent session activity')
            result[launch['lane']] = dict(status=status, activity_age_seconds=round(age),
                process=reg.probe(launch['process']), launch=launch['id'])
            if notices and age > 600:
                reg.notice(launch['lane'], 'session_activity_stalled',
                           dict(launch=launch['id'], reason=status,
                                action='Inspect session logs; PID liveness is not progress'))
        except (OSError, ValueError, TypeError):
            result[launch['lane']] = dict(status='activity unavailable', launch=launch['id'])
    return result
