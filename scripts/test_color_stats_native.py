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
p.add_argument('--progressive', action='store_true')
a = p.parse_args()
# Keep this mixed-strength actor fixture on the legacy profile protocol.
# Modern starting rolls always have carry=1; progressive protocol tests cover v2 caps.
m = generate('stats-fixture', 'ap', randomize_color_stats=True, starting_flarlic=1, collection_checks=True)
m['capabilities'][m['capabilities'].index('color-stats-v3')] = 'color-stats-v2'
m['color_stats'] = {c: dict(damage=75, movement=75, attack_rate=75, carry=1) for c in ('red', 'yellow', 'blue')}
m['color_stats']['red']['carry'] = 3
m['color_stats']['blue']['carry'] = 2
if a.progressive:
    m = generate('progressive-fixture', 'ap', progressive_color_stats=True, starting_flarlic=1)
    m['capabilities'][m['capabilities'].index('progressive-color-stats-v2')] = 'progressive-color-stats-v1'
session = Session(m, a.output.resolve()); session.bind_ap('stats-native-fixture', 0, 1)
session.receive(0, [ITEM_IDS[item] for item in progression_pool(m) if item != FLARLIC and not item.startswith('Progressive ')])
run = NativeRun(session); run.write_state(True)
_winapi.CreateJunction(str(a.assets.resolve()), str(run.directory / 'assets'))
env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', SDL_AUDIODRIVER='dummy', PIKMIN_RANDOMIZER_TEST_SCRIPT='progressive-stats' if a.progressive else 'stats')
env.pop('BBFT_PORT', None)
startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
log = run.directory / 'native.log'
with log.open('w', encoding='utf-8') as stream:
    process = subprocess.Popen([str(a.exe.resolve()), '--randomizer-seed', str(run.bootstrap)],
                               cwd=run.directory, env=env, startupinfo=startup, stdout=stream, stderr=subprocess.STDOUT)
    try:
        import time
        deadline = time.monotonic() + 90
        upgraded = False
        while process.poll() is None and time.monotonic() < deadline:
            run.poll()
            if a.progressive and not upgraded and 'TEST_ONLY progressive_baseline_live' in log.read_text(errors='replace'):
                from randomizer.stats import upgrade_pool
                rewards = upgrade_pool(m); rewards.remove('Progressive Blue Carry Strength')
                session.receive(len(session.data['received']), [ITEM_IDS[n] for n in rewards])
                upgraded = True
            run.write_state(True); time.sleep(.1)
        assert process.poll() == 0, f'native exit {process.poll()}; {log}'
    finally:
        if process.poll() is None: process.terminate(); process.wait(timeout=10)
text = log.read_text(encoding='utf-8', errors='replace')
assert text.count('TEST_ONLY stats_actor color=') == 3, log
assert 'TEST_ONLY stats_carry_pass ' in text, log
print('PASS: three live color damage/movement/attack hooks, real mixed-crew ship-part lift, body slots, hauling and weight-loss put-down')
print(log)
