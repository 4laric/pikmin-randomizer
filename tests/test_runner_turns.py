"""Runner-owned worker exit and rate-limit classification against fake OpenCode processes."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

from workflow.runner import Turn, main, write

FAKE = r'''
import json, sys, time
from pathlib import Path
scenario = json.loads(Path(__import__('os').environ['OPENCODE_CONFIG']).read_text())
Path(scenario['argv']).write_text(json.dumps(sys.argv))
buffered = []
def err(message, level='INFO'):
    sys.stderr.write('timestamp=2026-09-19T07:57:40.988Z level=%s run=f883c6d3 message=%s\n' % (level, message)); sys.stderr.flush()
for step in scenario['steps']:
    kind, value = step
    if kind == 'err': err(value)
    elif kind == 'error': err(value, 'ERROR')
    elif kind == 'out': sys.stdout.write(json.dumps(value) + '\n'); sys.stdout.flush()
    elif kind == 'buffered': buffered.append(value)  # OpenCode on a pipe: stdout arrives at exit.
    elif kind == 'mark': Path(value).write_text(repr(time.time()))
    elif kind == 'sleep': time.sleep(value)
    elif kind == 'spawn':  # A tool's detached process (build, server, shell) outliving the turn.
        import subprocess
        subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(%r)' % value], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
    elif kind == 'linger':  # The CLI stays alive after its turn, printing only periodic cleanup.
        deadline = time.time() + value
        while time.time() < deadline:
            err('cleanup prune=7.days'); time.sleep(.1)
for value in buffered: sys.stdout.write(json.dumps(value) + '\n')
sys.stdout.flush()
sys.exit(scenario.get('exit', 0))
'''
SESSION = 'ses_f58986113ffe1trsdaCQ23hNaZ'


def tool(session=SESSION):
    return dict(type='tool_use', sessionID=session, timestamp=1, part=dict(tool='bash', callID='c1', state=dict(status='completed')))


def finish(reason, session=SESSION):
    return dict(type='step_finish', sessionID=session, timestamp=2, part=dict(type='step-finish', reason=reason))


class RunnerTurnTests(unittest.TestCase):
    def launch(self, steps, exit=0, runner=None, before=None, **start):
        """Run the real runner against the fake CLI; returns (result, seconds, directory)."""
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        worktree = root / 'worktree'; worktree.mkdir()
        (worktree / 'run').write_text(FAKE, encoding='utf-8')  # `python run ...` executes the fake CLI.
        out = root / 'launch'; out.mkdir()
        scenario = root / 'scenario.json'
        scenario.write_text(json.dumps(dict(steps=steps, exit=exit, argv=str(root / 'argv.json'))))
        write(out / 'start.json', dict(dict(action_id='launch-1', executable=sys.executable, worktree=str(worktree),
            config=str(scenario), model='go/muse', session=SESSION, prompt='work', exit_grace_seconds=.5,
            rate_limit_settle_seconds=.5, poll_seconds=.05), **start))
        if before: before(out)
        started = time.monotonic()
        main(str(out), **(runner or {}))
        elapsed = time.monotonic() - started
        self.argv = json.loads((root / 'argv.json').read_text())
        return json.loads((out / 'result.json').read_text()), elapsed, out

    def test_turn_end_releases_the_slot_within_grace_not_linger(self):
        with tempfile.TemporaryDirectory() as marks:
            ended = Path(marks) / 'ended'
            steps = [['err', 'loop session.id=%s step=0' % SESSION],
                     ['err', 'evaluated permission=bash pattern="git status" action.action=allow'],
                     ['buffered', tool()], ['err', 'loop session.id=%s step=1' % SESSION],
                     ['buffered', finish('stop')], ['mark', str(ended)],
                     ['err', '"exiting loop" session.id=%s' % SESSION], ['linger', 60]]
            result, elapsed, out = self.launch(steps)
            hold = (out / 'result.json').stat().st_mtime - float(ended.read_text())
        # Slot-hold after the turn: grace (0.5 s) plus polling, against a 60 s linger (sweepers: ~65-94 s median).
        self.assertLess(hold, 5, hold)
        self.assertLess(elapsed, 10)
        self.assertTrue(result['stopped_after_turn'])
        self.assertEqual(result['runner_stop']['reason'], 'turn_end')
        self.assertEqual(result['turn_end']['source'], 'stderr_exiting_loop')
        self.assertEqual(result['kind'], 'exit')
        self.assertTrue(result['tools_started'])
        self.assertIn('--session', self.argv)

    @unittest.skipUnless(os.name == 'nt', 'Toolhelp process inventory is Windows-only')
    def test_turn_end_waits_for_a_lingering_tool_process(self):
        steps = [['err', 'loop session.id=%s step=0' % SESSION], ['spawn', 3],
                 ['err', '"exiting loop" session.id=%s' % SESSION], ['linger', 60]]
        result, elapsed, out = self.launch(steps, descendant_recheck_seconds=.3)
        self.assertGreater(elapsed, 2.5)  # Not stopped while the grandchild ran (no orphan in the worktree).
        self.assertLess(elapsed, 10)
        self.assertTrue(result['stopped_after_turn'])
        deferred = result['turn_end_deferred']
        self.assertEqual(deferred['reason'], 'descendants')
        self.assertTrue(any('python' in n.lower() for n in deferred['descendants']), deferred)
        self.assertTrue(json.loads((out / 'boot.json').read_text())['boot_id'])

    def test_failed_side_record_never_stops_draining_a_stream(self):
        steps = [['out', tool()], ['out', finish('stop')], ['err', '"exiting loop" session.id=%s' % SESSION], ['linger', 60]]
        result, _, out = self.launch(steps, before=lambda out: (out / 'activity.json.tmp').mkdir())
        self.assertEqual(len((out / 'events.jsonl').read_text().splitlines()), 2)
        self.assertTrue(result['stopped_after_turn'])

    def test_unknown_process_tree_never_stops_the_turn(self):
        steps = [['err', '"exiting loop" session.id=%s' % SESSION], ['linger', 2]]
        result, elapsed, _ = self.launch(steps, runner=dict(inventory=lambda: None), descendant_recheck_seconds=.3)
        self.assertGreater(elapsed, 1.5)
        self.assertNotIn('runner_stop', result)
        self.assertEqual(result['turn_end_deferred']['reason'], 'inventory_unavailable')

    def test_events_step_finish_stop_also_ends_the_turn(self):
        steps = [['out', tool()], ['out', finish('tool-calls')], ['out', finish('stop')], ['linger', 60]]
        result, elapsed, _ = self.launch(steps)
        self.assertLess(elapsed, 10)
        self.assertEqual(result['turn_end']['source'], 'events_step_finish')
        self.assertEqual(result['tool_evidence'], 'events')

    def test_other_session_exit_and_tool_call_steps_do_not_end_the_turn(self):
        steps = [['err', '"exiting loop" session.id=ses_otherSubagent'], ['out', finish('tool-calls')],
                 ['out', finish('stop', 'ses_otherSubagent')], ['sleep', 1.5]]
        result, elapsed, _ = self.launch(steps, exit=0)
        self.assertEqual(result['exit_code'], 0)
        self.assertNotIn('runner_stop', result)
        self.assertIsNone(result['turn_end'])

    def test_mid_tool_rate_limit_never_stops_the_session(self):
        steps = [['err', 'loop session.id=%s step=0' % SESSION],
                 ['err', 'evaluated permission=bash pattern="build" action.action=allow'],
                 ['error', '"stream error" session.id=%s error="Rate limit exceeded statusCode=429"' % SESSION],
                 ['sleep', 1.5], ['err', 'loop session.id=%s step=1' % SESSION]]
        result, _, _ = self.launch(steps, exit=0)
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['kind'], 'exit')
        self.assertTrue(result['rate_limit'])
        self.assertEqual(result['rate_limit_phase'], 'mid_tool')
        self.assertNotIn('runner_stop', result)

    def test_stdout_tool_events_are_parsed_before_a_rate_limit_decision(self):
        # The tool event reaches stdout just before the 429 reaches stderr: the settle window drains it.
        steps = [['out', tool()], ['error', '"stream error" error="Too Many Requests"'], ['sleep', 1.5]]
        result, _, _ = self.launch(steps, exit=0)
        self.assertEqual(result['exit_code'], 0)
        self.assertTrue(result['tools_started'])
        self.assertEqual(result['kind'], 'exit')
        self.assertNotIn('runner_stop', result)

    def test_pre_tool_rate_limit_stops_after_settle(self):
        steps = [['err', 'loop session.id=%s step=0' % SESSION],
                 ['error', '"stream error" session.id=%s error="statusCode=429"' % SESSION], ['linger', 60]]
        result, elapsed, _ = self.launch(steps)
        self.assertLess(elapsed, 10)
        self.assertEqual(result['kind'], 'rate_limit')
        self.assertEqual(result['runner_stop']['reason'], 'rate_limit')
        self.assertEqual(result['rate_limit_phase'], 'pre_tool')
        self.assertFalse(result['tools_started'])

    def test_fresh_session_publishes_its_own_id(self):
        fresh = 'ses_freshLaneSession01'
        steps = [['err', 'loop session.id=%s step=0' % fresh], ['out', finish('stop', fresh)],
                 ['err', '"exiting loop" session.id=%s' % fresh], ['linger', 60]]
        result, _, out = self.launch(steps, session=None, fresh_session=True)
        self.assertNotIn('--session', self.argv)
        self.assertIn('--title', self.argv)
        self.assertEqual(json.loads((out / 'session.json').read_text())['session'], fresh)
        self.assertEqual(result['session'], fresh)
        self.assertTrue(result['stopped_after_turn'])


class TurnClassificationTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.turn = Turn(SESSION, clock=lambda: self.now)

    def line(self, message, level='INFO'):
        self.turn.stderr('timestamp=2026-09-19T07:57:40.988Z level=%s run=x message=%s\n' % (level, message))

    def test_cleanup_lines_are_not_activity(self):
        self.line('"exiting loop" session.id=' + SESSION)
        self.now = 5; self.line('cleanup prune=7.days')
        self.assertEqual(self.turn.decide(5, 5), 'turn_end')
        self.line('"disposing instance" directory=x')
        self.assertIsNone(self.turn.decide(5, 5))

    def test_reentered_loop_withdraws_the_turn_end(self):
        self.line('"exiting loop" session.id=' + SESSION)
        self.line('loop session.id=%s step=0' % SESSION)  # Queued message or compaction: the loop runs again.
        self.turn.event(finish('stop'))  # Buffered stdout from the earlier turn arrives late.
        self.now = 60  # A long, silent tool.
        self.assertIsNone(self.turn.decide(10, 5))
        self.line('"exiting loop" session.id=' + SESSION)
        self.now = 75
        self.assertEqual(self.turn.decide(10, 5), 'turn_end')

    def test_tool_event_after_stdout_stop_withdraws_it(self):
        self.turn.event(finish('stop'))
        self.turn.event(tool())
        self.now = 60
        self.assertIsNone(self.turn.decide(10, 5))

    def test_loop_step_past_zero_counts_as_tools(self):
        self.line('loop session.id=%s step=0' % SESSION)
        self.assertFalse(self.turn.record()['tools_started'])
        self.line('loop session.id=%s step=3' % SESSION)
        self.assertEqual(self.turn.record()['tool_evidence'], 'stderr_loop_step')

    def test_rate_limit_waits_for_quiet_stdout_and_never_follows_tools(self):
        self.line('"stream error" error="Rate limit exceeded"', 'ERROR')
        self.now = 4; self.turn.event(dict(type='text', sessionID=SESSION))
        self.now = 6
        self.assertIsNone(self.turn.decide(10, 5))  # stdout spoke 2 s ago: not yet drained.
        self.now = 9.5
        self.assertEqual(self.turn.decide(10, 5), 'rate_limit')
        self.turn.event(tool())
        self.now = 30
        self.assertIsNone(self.turn.decide(10, 5))
        self.assertEqual(self.turn.record()['rate_limit_phase'], 'pre_tool')


class DurableWriteTests(unittest.TestCase):
    def test_write_replaces_atomically_without_leftovers(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'child.json'
            write(path, {'pid': 1}); write(path, {'pid': 2})
            self.assertEqual(json.loads(path.read_text()), {'pid': 2})
            self.assertEqual([p.name for p in Path(d).iterdir()], ['child.json'])


if __name__ == '__main__':
    unittest.main()
