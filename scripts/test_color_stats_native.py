"""Synthetic native actor/ship-part fixture; requires TEST_HOOKS build and user assets."""
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
for seed in range(10000):
    m = generate('stats-fixture-'+str(seed), 'ap', randomize_color_stats=True, starting_flarlic=1, collection_checks=True)
    stats = m['color_stats']
    if stats['red']['carry'] == 3 and stats['blue']['carry'] == 2 and stats['red']['attack_rate'] != 100:
        break
else: raise AssertionError('no fixture profile')
session = Session(m, a.output.resolve()); session.bind_ap('stats-native-fixture', 0, 1)
session.receive(0, [ITEM_IDS[item] for item in progression_pool(m) if item != FLARLIC])
run = NativeRun(session); run.write_state(True)
_winapi.CreateJunction(str(a.assets.resolve()), str(run.directory / 'assets'))
env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', SDL_AUDIODRIVER='dummy', PIKMIN_RANDOMIZER_TEST_SCRIPT='stats')
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
            run.poll(); run.write_state(True); time.sleep(.1)
        assert process.poll() == 0, f'native exit {process.poll()}; {log}'
    finally:
        if process.poll() is None: process.terminate(); process.wait(timeout=10)
text = log.read_text(encoding='utf-8', errors='replace')
assert text.count('TEST_ONLY stats_actor color=') == 3, log
assert 'TEST_ONLY stats_carry_pass ' in text, log
print('PASS: three live color damage/movement/attack hooks, real mixed-crew ship-part lift, body slots, hauling and weight-loss put-down')
print(log)
