"""One durable launch attempt. Does not interpret completion or restart workers."""
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import threading
import time

from .processes import identify


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def decisions_from_text(text):
    value = text.strip()
    if value.startswith('```'):
        match = re.fullmatch(r'```(?:json)?\s*([\s\S]*?)\s*```', value)
        if not match: return None
        value = match.group(1)
    try:
        result = json.loads(value)
    except ValueError:
        return None
    return result if isinstance(result, list) else None


def main(directory):
    out = Path(directory)
    # Atomic filesystem claim prevents replayed spawns from executing twice.
    with (out / 'runner.claim').open('x') as stream:
        stream.write(str(os.getpid()))
    write(out / 'runner.json', identify(os.getpid()))
    deadline = time.monotonic() + 120
    while not (out / 'start.json').exists():
        if time.monotonic() > deadline:
            write(out / 'result.json', {'kind': 'registration_timeout', 'exit_code': None})
            return
        time.sleep(.2)
    data = json.loads((out / 'start.json').read_text(encoding='utf-8'))
    env = dict(os.environ, PYTHONUTF8='1', OPENCODE_CONFIG=data['config'])
    command = [data['executable'], 'run', '--dir', data['worktree'], '-m', data['model'],
               '--auto', '--format', 'json', '--print-logs', '--log-level', 'INFO']
    if data.get('session'):
        command += ['--session', data['session']]
    else:
        command += ['--title', 'Workflow shepherd ' + data['action_id']]
    command.append(data['prompt'])
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    activity = {'tools_started': False, 'rate_limit': False, 'session': data.get('session')}
    started = time.monotonic()
    with (out / 'stderr.log').open('w', encoding='utf-8') as errors:
        proc = subprocess.Popen(command, env=env, cwd=data['worktree'], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
                                creationflags=flags)
        try:
            write(out / 'child.json', identify(proc.pid))
        except ProcessLookupError:
            pass  # Already exited: preserve stdout/stderr and record the real exit below.
        def stderr():
            for line in proc.stderr:
                errors.write(line); errors.flush()
                if any(s in line.lower() for s in ('rate limit exceeded', 'too many requests', 'statuscode=429')):
                    activity['rate_limit'] = True
        def stdout():
            with (out / 'events.jsonl').open('w', encoding='utf-8') as log:
                for line in proc.stdout:
                    log.write(line); log.flush()
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if event.get('sessionID'):
                        activity['session'] = event['sessionID']
                    if event.get('type') == 'tool_use':
                        activity['tools_started'] = True
                    if data.get('read_only_shepherd') and event.get('type') == 'text':
                        decisions = decisions_from_text(event.get('part', {}).get('text', ''))
                        if decisions is not None:
                            write(out / 'decisions.json', decisions)
                    write(out / 'activity.json', dict(activity, at=time.time()))
        threads = [threading.Thread(target=f, daemon=True) for f in (stderr, stdout)]
        for thread in threads: thread.start()
        while proc.poll() is None:
            # Only pre-tool throttling can be stopped automatically. A tool may own children.
            if activity['rate_limit'] and not activity['tools_started']:
                proc.terminate()
            if data.get('read_only_shepherd') and time.monotonic() - started > data.get('max_seconds', 600):
                activity['budget_exhausted'] = True
                proc.terminate()  # Shepherd permissions forbid shell, builds and child agents.
            time.sleep(.5)
        for thread in threads: thread.join(10)
        write(out / 'result.json', dict(activity, exit_code=proc.returncode,
            kind='rate_limit' if activity['rate_limit'] and not activity['tools_started'] else 'exit'))


if __name__ == '__main__':
    main(sys.argv[1])
