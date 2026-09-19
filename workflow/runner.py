"""One durable launch attempt. Does not interpret completion or restart workers.

The runner owns its child's exit: OpenCode stays alive after its turn, so once the turn has
ended (stdout step_finish 'stop' or stderr 'exiting loop' for its session) and both streams have
been quiet for exit_grace_seconds, the runner stops the child through its own Popen handle after
re-checking the recorded identity and that nothing but conhost.exe runs below it (a tool's build,
server or detached shell defers the stop, rechecked every descendant_recheck_seconds, and the
sweepers' own idle-tree fences stay the backstop). A rate-limit line stops the child only while no tool has
started this turn; OpenCode buffers stdout JSON on a pipe, so stderr permission evaluations and
loop steps are the live tool signal and stdout is drained before the decision."""
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import threading
import time

from .processes import boot_id, busy_descendants, identify, process_rows


def write(path, value, durable=True):
    """Atomic; durable by default, so a crash after os.replace cannot leave a NUL-filled record."""
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2))
        if durable:
            stream.flush()
            os.fsync(stream.fileno())
    os.replace(temporary, path)


def decisions_from_text(text):
    value = text.strip()
    if '```' in value:
        matches = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', value)
        if len(matches) != 1: return None
        value = matches[0]
    try:
        result = json.loads(value)
    except ValueError:
        return None
    return result if isinstance(result, list) else None


def prompt_arguments(out, prompt):
    path=Path(out).resolve()/'prompt.txt'
    path.write_bytes(prompt.encode('utf-8'))
    return ['Read the attached prompt.txt and execute its complete workflow instructions.', '--file', str(path)]


def legacy_spawn_failure(directory):
    directory=Path(directory)
    if (directory/'child.json').exists():return False
    try:text=(directory/'runner.stderr').read_text(encoding='utf-8',errors='replace')
    except OSError:return False
    return all(part in text for part in ('Traceback (most recent call last)',
        'subprocess.Popen(command', '_winapi.CreateProcess',
        'FileNotFoundError: [WinError 206] The filename or extension is too long'))


RATE_LIMIT = ('rate limit exceeded', 'too many requests', 'statuscode=429')
SESSION = re.compile(r'^ses_[A-Za-z0-9]+$')
_LOOP = re.compile(r' message=loop session\.id=(\S+) step=(\d+)')
_EXIT = re.compile(r' message="exiting loop" session\.id=(\S+)')
_CLEANUP = re.compile(r' message=cleanup ')


class Turn:
    """Live classification of one OpenCode turn from both output streams (thread-safe).

    session is the resumed session, or None until a fresh session names itself. Tool evidence
    is any tool_use event, any evaluated permission, or a loop step past 0. A turn end is withdrawn
    when its own stream shows the loop running again; once stderr shows a re-entry, only stderr
    can end the turn (buffered stdout may still carry the earlier turn's step_finish)."""
    def __init__(self, session=None, clock=time.monotonic):
        self.lock, self.clock = threading.Lock(), clock
        self.session, self.tools = session, None
        self.rate_limit_at = self.rate_limit_phase = self.ended = self.deferred = None
        self.reentered = False
        self.output_at = self.stdout_at = clock()

    def _tool(self, source):
        if self.tools is None: self.tools = source

    def _mine(self, session):
        return session is None or self.session is None or session == self.session

    def stderr(self, line):
        line = line.rstrip('\r\n')
        if not line.strip() or _CLEANUP.search(line): return  # Periodic cleanup is not activity.
        with self.lock:
            now = self.output_at = self.clock()
            loop = _LOOP.search(line)
            if loop:
                if self.session is None and SESSION.match(loop[1]): self.session = loop[1]
                if int(loop[2]) >= 1: self._tool('stderr_loop_step')
                if self.ended and self._mine(loop[1]): self.ended, self.reentered = None, True  # Loop re-entered.
            if ' message=evaluated permission=' in line:
                self._tool('stderr_permission')
                if self.ended and self.ended['source'] == 'stderr_exiting_loop': self.ended, self.reentered = None, True
            if any(s in line.lower() for s in RATE_LIMIT):
                self.rate_limit_at = now
                self.rate_limit_phase = 'mid_tool' if self.tools else 'pre_tool'
            done = _EXIT.search(line)
            if done and self._mine(done[1]) and self.ended is None:
                self.ended = dict(source='stderr_exiting_loop', at=now, session=done[1])

    def event(self, event):
        with self.lock:
            now = self.output_at = self.stdout_at = self.clock()
            if not isinstance(event, dict): return
            session = event.get('sessionID')
            if isinstance(session, str) and self.session is None and SESSION.match(session): self.session = session
            if event.get('type') == 'tool_use':
                self._tool('events')
                if self.ended and self.ended['source'] == 'events_step_finish': self.ended = None
            part = event.get('part') if isinstance(event.get('part'), dict) else {}
            if (event.get('type') == 'step_finish' and part.get('reason') == 'stop' and not self.reentered and
                    session and session == self.session and self.ended is None):
                self.ended = dict(source='events_step_finish', at=now, session=session)

    def decide(self, grace, settle):
        """'turn_end' after the turn ended and both streams stayed quiet for grace seconds;
        'rate_limit' only before any tool, once the limit and stdout have both settled."""
        with self.lock:
            now = self.clock()
            if self.ended and now - max(self.ended['at'], self.output_at) >= grace:
                return 'turn_end'
            if (self.rate_limit_at is not None and not self.tools and now - self.rate_limit_at >= settle
                    and now - self.stdout_at >= settle):
                return 'rate_limit'
            return None

    def record(self):
        with self.lock:
            return dict(tools_started=self.tools is not None, tool_evidence=self.tools,
                        rate_limit=self.rate_limit_at is not None, rate_limit_phase=self.rate_limit_phase,
                        session=self.session, turn_end_deferred=self.deferred,
                        turn_end={k: v for k, v in self.ended.items() if k != 'at'} if self.ended else None)


def stop_exact(proc, child):
    """Stop our own child through its Popen handle, only while it is still the recorded identity."""
    if proc.poll() is not None: return False
    if child is not None:
        try:
            if identify(proc.pid) != child: return False
        except (ProcessLookupError, PermissionError, OSError, ValueError):
            return False
    proc.terminate()
    return True


def settled(proc, inventory, turn):
    """'turn_end' when nothing but conhost.exe runs below the child, else None with the reason kept
    on the turn: a stop would orphan a tool's build, server or shell in the lane's worktree."""
    try:
        busy = busy_descendants(inventory(), proc.pid)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        busy = None
    if busy == []:
        return 'turn_end'
    with turn.lock:
        checks = (turn.deferred or {}).get('checks', 0) + 1
        turn.deferred = dict(reason='descendants' if busy else 'inventory_unavailable',
                             descendants=(busy or [])[:20], checks=checks, at=time.time())
    return None


def main(directory, *, clock=time.monotonic, inventory=process_rows):
    out = Path(directory)
    # Atomic filesystem claim prevents replayed spawns from executing twice.
    with (out / 'runner.claim').open('x') as stream:
        stream.write(str(os.getpid()))
    write(out / 'runner.json', identify(os.getpid()))
    write(out / 'boot.json', dict(boot_id=boot_id()))  # Lets a crash proof tell a reboot from a clock change.
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
    fresh = bool(data.get('fresh_session')) or not data.get('session')
    if not fresh:
        command += ['--session', data['session']]
    else:
        command += ['--title', ('Workflow lane ' if data.get('fresh_session') else 'Workflow shepherd ') + data['action_id']]
    command += prompt_arguments(out, data['prompt'])
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    grace = max(0.0, float(data.get('exit_grace_seconds', 10)))
    settle = max(0.0, float(data.get('rate_limit_settle_seconds', 5)))
    poll = min(.5, max(.05, float(data.get('poll_seconds', .5))))
    recheck = max(poll, float(data.get('descendant_recheck_seconds', 30)))
    turn = Turn(None if fresh else data['session'], clock)
    stopped = {}
    started = time.monotonic()
    with (out / 'stderr.log').open('w', encoding='utf-8') as errors:
        try:
            proc = subprocess.Popen(command, env=env, cwd=data['worktree'], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
                                    creationflags=flags)
        except OSError as exc:
            write(out / 'result.json', dict(kind='spawn_error',exit_code=None,error=str(exc),
                  winerror=getattr(exc,'winerror',None),child_created=False))
            return
        child = None
        try:
            child = identify(proc.pid)
            write(out / 'child.json', child)
        except ProcessLookupError:
            pass  # Already exited: preserve stdout/stderr and record the real exit below.
        published, observed, once = [], [0.0], threading.Lock()
        def publish_session():
            # A fresh session names itself once; the controller adopts it as the lane's task.
            with once:  # Both readers call this; one temp file must never be written twice at once.
                if fresh and data.get('fresh_session') and not published and turn.session:
                    write(out / 'session.json', dict(session=turn.session, action_id=data['action_id'], at=time.time()))
                    published.append(turn.session)
        def side(effect, *args, **kwargs):
            try: effect(*args, **kwargs)
            except OSError: pass  # A failed side record never stops a reader: an undrained pipe blocks the child.
        def stderr():
            for line in proc.stderr:
                errors.write(line); errors.flush()
                turn.stderr(line)
                side(publish_session)
        def stdout():
            with (out / 'events.jsonl').open('w', encoding='utf-8') as log:
                for line in proc.stdout:
                    log.write(line); log.flush()
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    turn.event(event)
                    side(publish_session)
                    if data.get('read_only_shepherd') and isinstance(event, dict) and event.get('type') == 'text':
                        decisions = decisions_from_text(event.get('part', {}).get('text', ''))
                        if decisions is not None:
                            side(write, out / 'decisions.json', decisions)
                    if time.monotonic() - observed[0] >= 1:  # Advisory and frequent: throttled, not fsynced.
                        observed[0] = time.monotonic()
                        side(write, out / 'activity.json', dict(turn.record(), at=time.time()), durable=False)
        threads = [threading.Thread(target=f, daemon=True) for f in (stderr, stdout)]
        for thread in threads: thread.start()
        recheck_at = 0.0
        while proc.poll() is None:
            if not stopped:
                decision = turn.decide(grace, settle)
                if decision == 'turn_end':  # Never orphan a tool's process tree; recheck on a slow cadence.
                    if time.monotonic() < recheck_at: decision = None
                    elif settled(proc, inventory, turn) is None:
                        decision, recheck_at = None, time.monotonic() + recheck
                        side(write, out / 'activity.json', dict(turn.record(), at=time.time()), durable=False)
                if decision and stop_exact(proc, child):
                    stopped.update(reason=decision, at=time.time(), after_seconds=round(time.monotonic() - started, 3))
            if (not stopped and data.get('read_only_shepherd') and
                    time.monotonic() - started > data.get('max_seconds', 600) and stop_exact(proc, child)):
                stopped.update(reason='budget_exhausted', at=time.time())  # Shepherd permissions forbid shell, builds and child agents.
            time.sleep(poll)
        for thread in threads: thread.join(10)
        activity = turn.record()
        rate_limited = stopped.get('reason') == 'rate_limit' or (
            activity['rate_limit'] and not activity['tools_started'] and not activity['turn_end'])
        result = dict(activity, exit_code=proc.returncode, kind='rate_limit' if rate_limited else 'exit')
        if stopped:
            result['runner_stop'] = stopped
            result['stopped_after_turn'] = stopped['reason'] == 'turn_end'
            result['budget_exhausted'] = stopped['reason'] == 'budget_exhausted'
        write(out / 'result.json', result)


if __name__ == '__main__':
    main(sys.argv[1])
