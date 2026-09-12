"""Run the real-game emperor fixture in an isolated session."""
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
from randomizer.catalog import ITEM_IDS, REPAIR

parser = argparse.ArgumentParser()
for name in ('exe', 'assets', 'output'): parser.add_argument('--'+name, type=Path, required=True)
args = parser.parse_args()
for case in ('emperor',):
    m = generate('emperor-regression', 'ap', collection_checks=True, starting_flarlic=1, starting_area="trial", goal_mode="emperor_bulblax")
    session = Session(m, args.output.resolve()/case)
    session.bind_ap("emperor-fixture",0,1); session.receive(0,[ITEM_IDS[REPAIR]]*24)
    granted=False
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
                text = log.read_text(encoding='utf-8', errors='replace')
                if 'EMPEROR_LOCKED_PASS' in text and not granted:
                    session.receive(24,[ITEM_IDS[REPAIR]]); granted=True
                run.poll(); run.write_state(True); time.sleep(.1)
            text = log.read_text(encoding='utf-8', errors='replace')
            assert p.poll() == 0 and 'PASS Emperor' in text, str(log)
            run.poll(); assert session.goal and Session(m,args.output.resolve()/case).goal
            print(case, next(l for l in text.splitlines() if l.startswith('PASS Emperor')), flush=True)
        finally:
            if p.poll() is None: p.terminate(); p.wait(timeout=10)
