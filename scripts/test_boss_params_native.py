"""Native boss packed-word read/write fixture; requires TEST_HOOKS build and user assets."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
import _winapi
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
from randomizer.catalog import ITEM_IDS, FLARLIC, progression_pool

p = argparse.ArgumentParser()
for name in ('exe', 'assets', 'output'): p.add_argument('--'+name, type=Path, required=True)

a = p.parse_args()
m = generate('boss-params-fixture', 'ap', permanent_checks=True, starting_area='forest', starting_color='red', starting_flarlic=1)
session = Session(m, a.output.resolve()); session.bind_ap('boss-params-native-fixture', 0, 1)
session.receive(0, [ITEM_IDS[item] for item in progression_pool(m) if item != FLARLIC and not item.startswith('Progressive ')])
run = NativeRun(session); run.write_state(True)
_winapi.CreateJunction(str(a.assets.resolve()), str(run.directory / 'assets'))
env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', SDL_AUDIODRIVER='dummy', PIKMIN_RANDOMIZER_TEST_SCRIPT='boss-params')
env.pop('BBFT_PORT', None)
startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
log = run.directory / 'native.log'
with log.open('w', encoding='utf-8') as stream:
    process = subprocess.Popen([str(a.exe.resolve()), '--randomizer-seed', str(run.bootstrap)],
                               cwd=run.directory, env=env, startupinfo=startup, stdout=stream, stderr=subprocess.STDOUT)
    try:
        import time
        deadline = time.monotonic() + 90
        while process.poll() is None and time.monotonic() < deadline:
            run.poll()
            run.write_state(True); time.sleep(.1)
        assert process.poll() == 0, f'native exit {process.poll()}; {log}'
    finally:
        if process.poll() is None: process.terminate(); process.wait(timeout=10)
text = log.read_text(encoding='utf-8', errors='replace')
assert 'TEST_ONLY boss_params_pass cases=7686' in text, log
assert 'BOSS_SPAWN type=0 ' not in text, log
print('PASS: 7686 native boss parameter read/write cases; no Spider in Hope')
print(log)
