"""Run the real-game progg fixture in an isolated session."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import _winapi
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.catalog import ITEM_IDS
from randomizer.benefits import PROGG, DELIVERY
from randomizer.session import Session
from randomizer.runner import NativeRun

parser = argparse.ArgumentParser()
for name in ('exe', 'assets', 'output'): parser.add_argument('--'+name, type=Path, required=True)
args = parser.parse_args()
for case in ('impact', 'forest', 'navel', 'spring', 'trial'):
    m = generate('progg-regression', 'ap', collection_checks=True, starting_flarlic=1, progg_trap_weight=1, starting_area=case)
    session = Session(m, args.output.resolve()/case)
    session.bind_ap('fixture', 0, 1)
    run = NativeRun(session); run.write_state(True)
    _winapi.CreateJunction(str(args.assets.resolve()), str(run.directory/'assets'))
    env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', SDL_AUDIODRIVER='dummy')
    env.pop('PIKMIN_RANDOMIZER_TEST_SCRIPT', None)
    env.pop('PROGG_FIXTURE_LONG', None)
    if case == 'forest': env['PROGG_FIXTURE_LONG'] = '1'
    startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    log = run.directory/'native.log'
    with log.open('w', encoding='utf-8') as stream:
        p = subprocess.Popen([str(args.exe.resolve()), '--randomizer-seed', str(run.bootstrap)],
                             cwd=run.directory, env=env, startupinfo=startup,
                             stdout=stream, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic()+90
            while p.poll() is None and time.monotonic() < deadline:
                run.poll()
                text = log.read_text(encoding='utf-8', errors='replace')
                if 'PROGG_PAUSED_READY' in text: session.receive(0, [ITEM_IDS[PROGG]] * 2 + [ITEM_IDS[DELIVERY]])
                run.write_state(True); time.sleep(.1)
            text = log.read_text(encoding='utf-8', errors='replace')
            assert p.poll() == 0 and 'PASS progg' in text, str(log)
            print(case, next(l for l in text.splitlines() if l.startswith('PASS progg')), flush=True)
        finally:
            if p.poll() is None: p.terminate(); p.wait(timeout=10)
