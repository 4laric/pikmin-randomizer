"""Windows-only recovery of a provider error at a completed tool boundary.

The controller persists intent before stopping owners. A replay can finish that
intent without rediscovering dead processes or starting a second contributor.
"""
import ctypes
import datetime
import json
import os
from pathlib import Path
import re
import subprocess

from .control import fingerprint
from .processes import probe


def idle_error(events_path, errors_path, now, quiet):
    """Require a provider failure newer than the last complete event boundary."""
    try:
        raw = Path(events_path).read_text(encoding='utf-8')
        errors = Path(errors_path).read_text(encoding='utf-8')
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (OSError, ValueError):
        return None
    if not events or events[-1].get('type') != 'step_finish':
        return None
    tools = {}
    for event in events:
        if event.get('type') == 'tool_use':
            part = event.get('part', {})
            tools[part.get('callID', part.get('id', 'unknown'))] = part.get('state', {}).get('status')
    if not tools or any(s not in ('completed', 'error') for s in tools.values()):
        return None
    latest = max(float(e.get('timestamp', 0)) / 1000 for e in events)
    failures = []
    for line in errors.splitlines():
        if not any(s in line.lower() for s in ('rate limit exceeded', 'too many requests', 'statuscode=429')):
            continue
        match = re.search(r'timestamp=(\S+)', line)
        if not match:
            continue
        try:
            failures.append(datetime.datetime.fromisoformat(match[1].replace('Z', '+00:00')).timestamp())
        except ValueError:
            continue
    if not failures or max(failures) < latest or now - max(latest, max(failures)) < quiet:
        return None
    # File freshness additionally catches partial new output and tool output.
    if now - Path(events_path).stat().st_mtime < quiet:
        return None
    return dict(last_event=latest, provider_error=max(failures),
                events=str(events_path), errors=str(errors_path))


def process_table():
    if os.name != 'nt':
        raise OSError('Automatic provider-stop inspection currently supports Windows only')
    result = subprocess.run(['powershell', '-NoProfile', '-Command',
        'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress'],
        capture_output=True, text=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise OSError('Cannot inspect process descendants')
    rows = json.loads(result.stdout)
    return rows if isinstance(rows, list) else [rows]


def safe_descendants(owners, rows):
    allowed = {p['pid'] for p in owners}
    if not allowed.issubset({p['ProcessId'] for p in rows}):
        return False
    descendants = set(allowed)
    while True:
        extra = {p['ProcessId'] for p in rows if p['ParentProcessId'] in descendants}
        if extra.issubset(descendants):
            break
        descendants.update(extra)
    return all(p['ProcessId'] in allowed or p['Name'].lower() == 'conhost.exe'
               for p in rows if p['ProcessId'] in descendants)


def stop_exact(identity):
    """Validate creation time and terminate through the SAME Windows handle."""
    if probe(identity) == 'dead':
        return
    if os.name != 'nt' or probe(identity) != 'alive':
        raise OSError('Process identity is not confirmed alive')
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1001, False, identity['pid'])
    if not handle:
        raise OSError('Cannot open exact process for stop')
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
            raise OSError('Cannot validate process creation time')
        started = str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
        if started != identity['started']:
            raise OSError('Process identity changed')
        if not kernel.TerminateProcess(handle, 1):
            raise OSError('Exact process stop failed')
    finally:
        kernel.CloseHandle(handle)


def recover(controller, *, table=process_table, stop=stop_exact):
    settings = controller.config.get('provider_stall_recovery', {})
    if not settings.get('enabled'):
        return
    reg = controller.reg
    quiet = max(60, settings.get('quiet_seconds', 180))
    models = settings.get('models', [])
    if not models:
        return
    state = reg.status()
    control = reg.control_status()
    journals = control.get('provider_recoveries', {})
    for key, entry in controller.config['lanes'].items():
        lane = state['lanes'].get(key)
        if not lane or lane['state'] not in ('running', 'ready', 'reconciling'):
            continue
        identity = fingerprint([key, lane['generation'], 'idle-provider-error'])
        journal = journals.get(identity)
        if journal and journal['status'] == 'planned':
            continue
        if not journal:
            if reg.probe(lane['process']) != 'alive':
                continue
            # A new source head resets the bounded automatic recovery allowance.
            used = sum(j['lane'] == key and j['head'] == lane['root']['head'] for j in journals.values())
            if used >= settings.get('max_attempts_per_head', 2):
                reg.notice(key, 'provider_recovery_exhausted', {'head': lane['root']['head']})
                continue
            active = [x for x in control['launches'].values() if x['lane'] == key and x['status'] in ('running', 'exiting')]
            if len(active) > 1:
                continue
            launch = active[0] if active else None
            if launch:
                directory = controller.launch_directory(launch['id'])
                try:
                    child = json.loads((directory / 'child.json').read_text())
                except (OSError, ValueError):
                    continue
                owners = [lane['process'], child]
                events, errors = directory / 'events.jsonl', directory / 'stderr.log'
            else:
                owners = entry.get('legacy_supervisors', []) + [lane['process']]
                logs = list(Path(entry['output']).glob('run-*.jsonl'))
                if not logs:
                    continue
                events = max(logs, key=lambda p: p.stat().st_mtime)
                errors = events.with_suffix('.err')
            if any(reg.probe(p) != 'alive' for p in owners):
                continue
            evidence = idle_error(events, errors, reg.clock(), quiet)
            if not evidence:
                continue
            journal = dict(lane=key, generation=lane['generation'], head=lane['root']['head'],
                owners=owners, evidence=evidence, launch=launch['id'] if launch else None,
                status='stopping', at=reg.clock())
        # Fresh checks on every replay; no timeout grants permission to kill a build.
        current = reg.status()
        fresh = current['lanes'][key]
        if fresh['generation'] != journal['generation'] or fresh['state'] not in ('running', 'ready', 'reconciling'):
            continue
        live = [p for p in journal['owners'] if reg.probe(p) == 'alive']
        if any(reg.probe(p) == 'unknown' for p in journal['owners']):
            continue
        if any(reg.probe(lease['process']) != 'dead' for lease in current['leases'].values() if lease['lane'] == key):
            continue
        try:
            if live:
                if not idle_error(journal['evidence']['events'], journal['evidence']['errors'], reg.clock(), quiet):
                    continue
                if not safe_descendants(live, table()):
                    reg.notice(key, 'provider_recovery_child_busy', {'generation': fresh['generation']})
                    continue
                with reg.transaction() as db:
                    reg.control(db).setdefault('provider_recoveries', {})[identity] = journal
                # Stop supervisors first, preventing a competing legacy restart.
                for owner in live:
                    remaining = [p for p in journal['owners'] if reg.probe(p) == 'alive']
                    if not idle_error(journal['evidence']['events'], journal['evidence']['errors'], reg.clock(), quiet):
                        break
                    if remaining and not safe_descendants(remaining, table()):
                        break
                    stop(owner)
                continue  # Observe confirmed death on the next tick.
            if not reg.recovery_safe(current, fresh):
                continue
            if journal['launch']:
                controller.mark_exited(journal['launch'])
            item = reg.plan_launch(key, 'provider-stall:' + identity,
                'Recover the same session after an idle provider rate-limit failure. '
                'Inspect existing checkpoints, edits and commits; preserve completed work. '
                'Continue only the assigned slice and record a terminal outcome. '
                'Read docs/PIKMIN2_IMPLEMENTATION_FANOUT.md before the next runtime acceptance.', models)
            with reg.transaction() as db:
                reg.control(db).setdefault('provider_recoveries', {})[identity] = dict(journal, status='planned', action=item['id'])
        except (OSError, ValueError) as exc:
            reg.notice(key, 'provider_recovery_inspection_failed', {'generation': fresh['generation'], 'error': str(exc)})
