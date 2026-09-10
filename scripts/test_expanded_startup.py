"""Actual native withdrawal/death lifecycle with explicitly synthetic test stock."""
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
from randomizer.catalog import FLARLIC, ITEM_IDS, POPULATION


def main(exe, assets, output):
    session = Session(generate('expanded-startup', 'ap', expanded=True), output)
    session.bind_ap('synthetic-expanded-smoke', 0, 1)
    run = NativeRun(session)
    _winapi.CreateJunction(str(assets.resolve()), str((run.directory / 'assets').resolve()))
    env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',
               PIKMIN_RANDOMIZER_TEST_SCRIPT='capacity', SDL_AUDIODRIVER='dummy')
    env.pop('BBFT_PORT', None)
    log = run.directory / 'native.log'
    with log.open('w', encoding='utf-8') as stream:
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        process = subprocess.Popen([str(exe.resolve()), '--randomizer-seed', str(run.bootstrap.resolve())],
                                   cwd=run.directory, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, startupinfo=startup)
        try:
            def wait(marker):
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    assert process.poll() is None, f'native exited; {log}'
                    run.poll(); run.write_state(run.handshaken)
                    if marker in log.read_text(encoding='utf-8', errors='replace'):
                        return
                    time.sleep(.1)
                raise AssertionError(f'timeout {marker}; {log}')
            wait('PIKMIN_WORLD_RENDERED')
            wait('TEST_WITHDRAW cap=20 queued=0')
            assert not any(name in session.data['checked'] for name, n in POPULATION.items() if n > 20)
            for index in range(8):
                session.receive(index, [ITEM_IDS[FLARLIC]])
                cap = 30 + index * 10
                wait(f'TEST_FIELD actual={cap} cap={cap}')
                wait(f'Population: {cap} Pikmin in the field')
            run.poll()
            assert all(name in session.data['checked'] for name in POPULATION)
            assert 'Explore: The Forest of Hope - Land' in session.data['checked']
            assert not any('Final Trial' in name for name in session.data['checked'])
            session.receive(0, [ITEM_IDS[FLARLIC]] * 8)
            print('PASS actual native 20..100 population and capped Onion withdrawal. Synthetic stored stock; not player combat or breeding acceptance.')
            print('Dwarf death observed:', 'Bestiary: Dwarf Bulborb' in session.data['checked'])
            print(log)
        finally:
            if process.poll() is None:
                process.terminate(); process.wait(timeout=10)
            run.write_state(False)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('exe', 'assets', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    main(a.exe, a.assets, a.output.resolve())
