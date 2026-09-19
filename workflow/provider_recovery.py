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
        'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,'
        '@{Name="Started";Expression={if ($_.CreationDate) {$_.CreationDate.ToUniversalTime().ToFileTimeUtc().ToString()}}} | ConvertTo-Json -Compress'],
        capture_output=True, text=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise OSError('Cannot inspect process descendants')
    rows = json.loads(result.stdout)
    return rows if isinstance(rows, list) else [rows]


def safe_descendants(owners, rows):
    allowed = {p['pid'] for p in owners}
    if not allowed.issubset({p['ProcessId'] for p in rows}):
        return False
    def started(value):
        # Win32 creation FILETIME, not a wall-clock guess; absent/malformed data
        # cannot exclude descendants and therefore remains conservative.
        if isinstance(value, str) and value.isdecimal() and int(value) > 0:
            return int(value)
        return None
    # CIM timestamps retain microseconds; GetProcessTimes retains 100ns ticks.
    births = {p['ProcessId']: started(p.get('Started')) for p in rows}
    for owner in owners:
        expected, actual = started(owner.get('started')), births.get(owner['pid'])
        if expected is not None and actual is not None and expected // 10 != actual // 10:
            return False
    descendants = set(allowed)
    while True:
        extra = {p['ProcessId'] for p in rows if p['ParentProcessId'] in descendants
                 and not (births.get(p['ParentProcessId']) is not None
                          and births.get(p['ProcessId']) is not None
                          and births[p['ProcessId']] < births[p['ParentProcessId']])}
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
    recover_terminal(controller, table=table, stop=stop)
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
    for key, entry in controller.config['lanes'].copy().items():
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
            retry_models = list(models)
            failed_model = control['launches'].get(journal['launch'], {}).get('model')
            if failed_model:
                policy = controller.config.get('model_rate_limit', {})
                reg.model_rate_limit(failed_model, journal['launch'],
                    initial=policy.get('initial_seconds', 30), maximum=policy.get('max_seconds', 300),
                    reset_after=policy.get('reset_after_seconds', 1800))
                retry_models = [m for m in models if m != failed_model]
                if failed_model in models: retry_models.append(failed_model)
            item = reg.plan_launch(key, 'provider-stall:' + identity,
                'Recover the same session after an idle provider rate-limit failure. '
                'Inspect existing checkpoints, edits and commits; preserve completed work. '
                'Continue only the assigned slice and record a terminal outcome. '
                'Read docs/PIKMIN2_IMPLEMENTATION_FANOUT.md before the next runtime acceptance.', retry_models)
            with reg.transaction() as db:
                reg.control(db).setdefault('provider_recoveries', {})[identity] = dict(journal, status='planned', action=item['id'])
        except (OSError, ValueError) as exc:
            reg.notice(key, 'provider_recovery_inspection_failed', {'generation': fresh['generation'], 'error': str(exc)})

# Only the observed periodic cleanup message is ignorable. Unknown diagnostics,
# permission prompts, tool output and partial log lines are meaningful activity.
_CLEANUP = re.compile(r'^timestamp=\S+ level=INFO run=\S+ message=cleanup prune=\d+\.days$')
_EXIT = re.compile(r'^timestamp=(\S+) level=INFO run=\S+ message="exiting loop" session\.id=(\S+)$')


def idle_terminal(events_path, errors_path, session, now, quiet=60, allowed_output=None):
    """Recognize an exact idle session-loop boundary without inferring acceptance."""
    import math
    if not isinstance(session, str) or not session or not math.isfinite(now):
        return None
    quiet = max(60, quiet)
    try:
        errors = Path(errors_path).read_text(encoding='utf-8')
        raw = Path(events_path).read_text(encoding='utf-8')
        if (errors and not errors.endswith('\n')) or (raw and not raw.endswith('\n')):
            return None
        lines = [line.strip() for line in errors.splitlines() if line.strip() and not _CLEANUP.fullmatch(line.strip())]
        if not lines:
            return None
        latest_line = lines[-1]
        if allowed_output is not None and not raw.strip():
            original_lines = lines[:]
            # Parallel reads may finish after another read asks for directory
            # access. Ignore only their known read-only log tail, never a new
            # model turn, permission answer, write, shell or arbitrary output.
            while len(lines) > 1 and (
                    re.fullmatch(r'timestamp=\S+ level=INFO run=\S+ message="touching file" file=.*', lines[-1]) or
                    (re.fullmatch(r'timestamp=\S+ level=INFO run=\S+ message=evaluated permission=(read|external_directory) .*', lines[-1])
                     and 'action.action=allow' in lines[-1])):
                lines.pop()
            if ' message=asking ' not in lines[-1]:
                lines = original_lines
        match = _EXIT.fullmatch(lines[-1])
        failure = None
        if not match:
            # OpenCode can remain alive after a provider failure, emitting only
            # cleanup forever. Require a session-specific final error boundary.
            line = lines[-1]
            recognized = any(word in line.lower() for word in (
                'insufficient balance', 'rate limit exceeded', 'too many requests', 'statuscode=429',
                '[invalid_request_error]'))
            stamp = re.match(r'^timestamp=(\S+) level=ERROR ', line)
            if not recognized or not stamp or ('session.id=' + session + ' ') not in line:
                # Only default-policy access inside the managed repository
                # may be repaired. Never approve arbitrary external paths.
                ask = re.fullmatch(r'timestamp=(\S+) level=INFO .* message=asking id=\S+ '
                                  r'permission=external_directory patterns=(".*")', line)
                if allowed_output is None or not ask or raw.strip():
                    return None
                patterns = json.loads(json.loads(ask[2]))
                if not isinstance(patterns, list) or len(patterns) != 1:
                    return None
                pattern = patterns[0].replace('\\', '/')
                allowed = allowed_output if isinstance(allowed_output, list) else [allowed_output]
                from .managed_config import permission_path_allowed
                if not pattern.endswith('/*') or not permission_path_allowed(pattern[:-2], allowed):
                    return None
                stamp = ask
                failure = 'output_permission'
            else:
                failure = 'provider_failure'
            timestamp = stamp[1]
            if failure == 'output_permission':
                timestamp = re.match(r'^timestamp=(\S+)', latest_line)[1]
        else:
            if match[2] != session:
                return None
            timestamp = match[1]
        moment = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        if moment.tzinfo is None:
            return None
        exited_at = moment.timestamp()
        if now - exited_at < quiet or now - Path(events_path).stat().st_mtime < quiet:
            return None
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
        if events and (not isinstance(events[-1], dict) or events[-1].get('type') != 'step_finish'):
            return None
        tools = {}
        for event in events:
            if not isinstance(event, dict):
                return None
            stamp = event.get('timestamp')
            if type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp / 1000 > exited_at:
                return None
            if event.get('sessionID') not in (None, session):
                return None
            if event.get('type') == 'tool_use':
                part = event.get('part')
                if not isinstance(part, dict) or not isinstance(part.get('state'), dict):
                    return None
                key = part.get('callID') or part.get('id')
                if not isinstance(key, str) or not key:
                    return None
                tools[key] = part['state'].get('status')
        if any(status not in ('completed', 'error') for status in tools.values()):
            return None
        return dict(session=session, exited_at=exited_at, events=str(events_path), errors=str(errors_path), failure=failure)
    except (OSError, ValueError, OverflowError, TypeError):
        return None


def first_response_timeout(events_path, errors_path, session, now, quiet=300):
    """Recognize a silent initial stream, never an in-flight tool or permission."""
    try:
        if Path(events_path).read_bytes():
            return None
        raw = Path(errors_path).read_text(encoding='utf-8')
        if not raw.endswith('\n'):
            return None
        lines = [s for s in raw.splitlines() if s.strip() and not _CLEANUP.fullmatch(s)]
        streams = [i for i,s in enumerate(lines) if ' message=stream ' in s and
                   'session.id=' + session + ' ' in s]
        if len(streams) != 1:
            return None
        index = streams[0]
        # Any permission/tool boundary anywhere in this launch is disqualifying.
        if any('message=asking ' in s or 'permission=' in s for s in lines):
            return None
        allowed = ('message="llm runtime selected" ', 'message="project copy refresh done" ')
        if any(not any(marker in s for marker in allowed) for s in lines[index+1:]):
            return None
        stamp = re.match(r'^timestamp=(\S+)', lines[index])
        moment = datetime.datetime.fromisoformat(stamp[1].replace('Z', '+00:00'))
        if moment.tzinfo is None:
            return None
        at = moment.timestamp()
        if now-at < max(60, quiet) or now-Path(events_path).stat().st_mtime < max(60, quiet):
            return None
        return dict(session=session, exited_at=at, events=str(events_path),
                    errors=str(errors_path), failure='first_response_timeout')
    except (OSError, ValueError, TypeError, IndexError):
        return None


def provider_error_event(path, session):
    """Classify an actual exited runner's session-specific API error event."""
    try:
        rows = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
        if not rows:
            return False
        event = rows[-1]
        return (event.get('type') == 'error' and event.get('sessionID') == session and
                event.get('error', {}).get('name') == 'APIError')
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def recover_terminal(controller, *, table=process_table, stop=stop_exact):
    """Stop only a managed idle CLI child; its runner records the real exit.

    Registry outcomes are preserved. A running lane with no terminal submission
    follows complete_runs' existing reconciliation path after the runner exits.
    """
    settings = controller.config.get('terminal_idle_recovery', {})
    if not settings.get('enabled', False):
        return
    reg = controller.reg
    quiet = max(60, settings.get('quiet_seconds', 60))
    eligible = {'done', 'review_ready', 'handoff_ready', 'blocked', 'running'}
    for launch in reg.control_status()['launches'].values():
        if launch.get('status') != 'running' or not launch.get('session'):
            continue
        key = launch['lane']
        directory = controller.launch_directory(launch['id'])
        if (directory / 'result.json').exists():
            continue
        try:
            child = json.loads((directory / 'child.json').read_text())
            runner = json.loads((directory / 'runner.json').read_text())
            start = json.loads((directory / 'start.json').read_text())
            if start.get('session') != launch['session'] or start.get('action_id') != launch['id']:
                continue
            if not isinstance(child, dict) or not isinstance(runner, dict) or child == runner:
                continue
            owners = [runner, child]
            if any(not all(k in owner for k in ('pid', 'host', 'started')) for owner in owners):
                continue
            from .managed_config import output_access
            entry = controller.config.get('lanes', {}).get(key, {})
            allowed_output = None
            if entry.get('config') and entry.get('output'):
                config_path = reg.root / entry['config']
                output_path = reg.root / entry['output']
                brief_path = reg.root / entry['brief'] if entry.get('brief') else None
                derived = output_access(config_path, output_path, reg.root, brief_path)
                if derived is not None:
                    allowed_output = list(derived['permission']['external_directory'])
            def observe():
                evidence = idle_terminal(directory / 'events.jsonl', directory / 'stderr.log',
                                         launch['session'], reg.clock(), quiet, allowed_output)
                timeout = settings.get('first_response_seconds', 300)
                if evidence is None and timeout > 0:
                    evidence = first_response_timeout(directory / 'events.jsonl', directory / 'stderr.log',
                                                      launch['session'], reg.clock(), timeout)
                return evidence
            evidence = observe()
            if not evidence:
                continue
            def fenced(state):
                lane = state['lanes'].get(key, {})
                current = state.get('control', {}).get('launches', {}).get(launch['id'], {})
                def protects(group, resource, value):
                    if value['lane'] != key or reg.probe(value['process']) == 'dead':
                        return False
                    # A completed session cannot release its own expired lease
                    # while an idle CLI keeps the runner alive. Never remove the
                    # lease here: the real runner exit enables normal reclamation.
                    expired_build = (group == 'leases' and resource.startswith('build:')
                                     and isinstance(value.get('expires_at'), (int, float))
                                     and value['expires_at'] <= reg.clock())
                    completed_build = (group == 'leases' and resource.startswith('build:')
                                       and type(value.get('acquired_at')) in (int, float)
                                       and 0 <= value['acquired_at'] <= evidence['exited_at'])
                    abandoned_wait = (group == 'queue' and value.get('resource', '').startswith('build:')
                                      and isinstance(value.get('requested_at'), (int, float))
                                      and value['requested_at'] <= evidence['exited_at'])
                    terminal = (lane.get('state') in ('done', 'blocked', 'review_ready', 'handoff_ready')
                                and evidence.get('failure') is None)
                    # A missing outcome or provider failure can leave the same
                    # waiting runner holding the completed build reservation.
                    # Require a pre-boundary acquisition, not expiry alone;
                    # descendant/activity fences below still prove no work runs.
                    idle_running = (lane.get('state') == 'running'
                                    and evidence.get('failure') in (None, 'provider_failure')
                                    and (completed_build or abandoned_wait))
                    return not ((expired_build or completed_build or abandoned_wait)
                                and (terminal or idle_running)
                                and value.get('process') == runner
                                and value.get('generation') == lane.get('generation'))
                return (lane.get('state') in eligible and lane.get('generation') == launch.get('bound_generation')
                        and lane.get('task_id') == 'opencode:' + launch['session']
                        and lane.get('process') == runner and current.get('status') == 'running'
                        and current.get('process') == runner and current.get('bound_generation') == lane.get('generation')
                        and all(reg.probe(owner) == 'alive' for owner in owners)
                        and not any(protects(group, resource, value) for group in ('leases', 'queue')
                                    for resource, value in state[group].items()))
            with reg.transaction() as state:
                if not fenced(state):
                    continue
            rows = table()
            if not safe_descendants(owners, rows):
                continue
            # The recorded child must actually belong to the recorded runner.
            if not any(p['ProcessId'] == child['pid'] and p['ParentProcessId'] == runner['pid'] for p in rows):
                continue
            identity = fingerprint([launch['id'], launch['bound_generation'], child, 'idle-terminal'])
            with reg.transaction() as state:
                if not fenced(state):
                    continue
                reg.control(state).setdefault('terminal_recoveries', {}).setdefault(identity,
                    dict(lane=key, launch=launch['id'], generation=launch['bound_generation'],
                         child=child, runner=runner, evidence=evidence, status='stopping', at=reg.clock()))
            # Revalidate after persisting intent. Never reuse stale liveness,
            # descendant, lease or log checks from a previous recovery attempt.
            with reg.transaction() as state:
                if not fenced(state) or (directory / 'result.json').exists():
                    continue
                if json.loads((directory / 'child.json').read_text()) != child:
                    continue
                if observe() != evidence:
                    continue
                rows = table()
                if not safe_descendants(owners, rows) or not any(
                        p['ProcessId'] == child['pid'] and p['ParentProcessId'] == runner['pid'] for p in rows):
                    continue
                if observe() != evidence:
                    continue
                stop(child)  # Never stop the runner or synthesize its result.
                reg.control(state)['terminal_recoveries'][identity]['status'] = 'child_stop_requested'
                reg.event(state, 'terminal_child_stop_requested', key, launch=launch['id'])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            reg.notice(key, 'terminal_recovery_inspection_failed', {'launch': launch['id'], 'error': str(exc)})
