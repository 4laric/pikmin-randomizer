"""Private TEST_HOOKS fixture: partial states, final completion and native serializer reload."""
import argparse
import os
import subprocess
import sys
import time
import _winapi
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.catalog import ITEM_IDS, REPAIR, progression_pool, OBSTACLES, START_AREAS
from randomizer.session import Session
from randomizer.runner import NativeRun

p = argparse.ArgumentParser()
for name in ('exe', 'assets', 'output'): p.add_argument('--'+name, type=Path, required=True)
p.add_argument('--area', choices=['impact', 'forest', 'navel', 'spring', 'trial'], required=True)
a = p.parse_args()
m = generate('permanent-fixture', 'ap', permanent_checks=True, starting_area=a.area, starting_flarlic=1)
s = Session(m, a.output.resolve()); s.bind_ap('fixture', 0, 1)
s.receive(0, [ITEM_IDS[n] for n in progression_pool(m)])
r = NativeRun(s)
_winapi.CreateJunction(str(a.assets.resolve()), str(r.directory / 'assets'))
env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', PIKMIN_RANDOMIZER_TEST_SCRIPT='permanent', SDL_AUDIODRIVER='dummy')
env.pop('BBFT_PORT', None)
startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
log = r.directory / 'native.log'
with log.open('w') as out:
    proc = subprocess.Popen([str(a.exe.resolve()), '--randomizer-seed', str(r.bootstrap)], cwd=r.directory,
                            env=env, startupinfo=startup, stdout=out, stderr=subprocess.STDOUT)
    try:
        def until(predicate, timeout=75):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                assert proc.poll() is None, f'exit {proc.returncode}; {log}'
                r.poll(); r.write_state(True)
                if predicate(): return
                time.sleep(.1)
            raise AssertionError(f'timeout; {log}')
        until(lambda: 'TEST_ONLY permanent_partial_ready' in log.read_text(errors='replace'))
        # Let real observers run multiple frames against the partial structures.
        deadline = time.monotonic() + .5
        until(lambda: time.monotonic() >= deadline)
        assert not set(s.data['checked']) & set(OBSTACLES), s.data['checked']
        s.receive(len(s.data['received']), [ITEM_IDS[REPAIR]])
        until(lambda: 'TEST_ONLY permanent_complete_loaded' in log.read_text(errors='replace'))
        stage = START_AREAS[m['profile']][0]
        expected = {n for n, row in OBSTACLES.items() if row[0] == stage}
        until(lambda: expected <= set(s.data['checked']))
        deadline = time.monotonic() + .5
        until(lambda: time.monotonic() >= deadline)
        assert set(s.data['checked']) & set(OBSTACLES) == expected
        entries = (r.directory / 'checks.txt').read_text().splitlines()
        assert len(entries) == len(set(entries)), 'repeat observers produced duplicate rewards'
        print(f'PASS {a.area}: {len(expected)} real structures; partial rejection, completion/serializer reload, repeated-frame deduplication', flush=True)
    finally:
        if proc.poll() is None: proc.terminate(); proc.wait(timeout=10)
