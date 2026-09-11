"""Run the real-game bomb warning fixture in an isolated session."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import _winapi
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun

parser = argparse.ArgumentParser()
for name in ('exe', 'assets', 'output'): parser.add_argument('--'+name, type=Path, required=True)
args = parser.parse_args()
for case in ('bomb-warning',):
    m = generate('bomb warning-regression', 'ap', collection_checks=True, starting_flarlic=1)
    session = Session(m, args.output.resolve()/case)
    run = NativeRun(session); run.write_state(True)
    _winapi.CreateJunction(str(args.assets.resolve()), str(run.directory/'assets'))
    env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', SDL_AUDIODRIVER='dummy')
    env.pop('PIKMIN_RANDOMIZER_TEST_SCRIPT', None)
    startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    log = run.directory/'native.log'
    with log.open('w', encoding='utf-8') as stream:
        p = subprocess.Popen([str(args.exe.resolve()), '--randomizer-seed', str(run.bootstrap)],
                             cwd=run.directory, env=env, startupinfo=startup,
                             stdout=stream, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic()+90
            while p.poll() is None and time.monotonic() < deadline:
                run.poll(); run.write_state(True); time.sleep(.1)
            text = log.read_text(encoding='utf-8', errors='replace')
            assert p.poll() == 0 and 'PASS bomb warning' in text, str(log)
            print(case, next(l for l in text.splitlines() if l.startswith('PASS bomb warning')), flush=True)
        finally:
            if p.poll() is None: p.terminate(); p.wait(timeout=10)
