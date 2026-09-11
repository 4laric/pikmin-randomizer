"""Hidden, silent startup/item-state smoke; not a physical carry or sunset test."""
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
from randomizer.catalog import UNLOCKS, ITEM_IDS, REPAIR, FOREST_ACCESS, NAVEL_ACCESS, progression_pool, FLARLIC, START_AREAS


def main(exe, assets, output, expanded=False, starting_area='forest', seed='startup-smoke', starting_color='red', all_areas=False, enemy_shuffle=False):
    session = Session(generate(seed, "ap", expanded=expanded, starting_area=starting_area, starting_color=starting_color, all_areas=all_areas, enemy_shuffle=enemy_shuffle), output)
    color = session.manifest.get('starting_color', 'red')
    native_color = {'blue': 0, 'red': 1, 'yellow': 2}[color]
    stage, area, _ = START_AREAS[session.manifest['profile']]
    expanded = session.manifest['schema'] >= 2
    session.bind_ap("synthetic-native-smoke", 0, 1)
    run = NativeRun(session)
    _winapi.CreateJunction(str(assets.resolve()), str((run.directory / "assets").resolve()))
    env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND="1", SDL_AUDIODRIVER="dummy")
    env.pop("BBFT_PORT", None)
    log = run.directory / "native.log"
    with log.open("w", encoding="utf-8") as stream:
        startup = subprocess.STARTUPINFO();startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        process = subprocess.Popen([str(exe.resolve()), "--randomizer-seed", str(run.bootstrap.resolve())],
                                   cwd=run.directory, env=env, stdout=stream, stderr=subprocess.STDOUT, startupinfo=startup)
        try:
            def wait(marker, timeout=60):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise AssertionError(f"native exited {process.returncode}; {log}")
                    run.poll();run.write_state(run.handshaken)
                    if marker in log.read_text(encoding="utf-8", errors="replace"): return
                    time.sleep(.1)
                raise AssertionError(f"timeout: {marker}; {log}")
            wait(f"START_COLOR_READY stage={stage} color={native_color} field=20")
            wait("PIKMIN_WORLD_RENDERED")
            wait('PIKMIN_AREA_ACCESS ' + ' '.join(f'{name}={int(i == stage)}' for i, name in enumerate(('impact', 'forest', 'navel', 'spring', 'trial'))))
            grants = [item for item in progression_pool(session.manifest) if item != FLARLIC]
            for i, item in enumerate(grants):
                session.receive(i, [ITEM_IDS[item]])
                if i < 2:
                    wait(f"PIKMIN_{item.split()[0].upper()}_ONION_GRANTED starter=5")
            wait(f"PIKMIN_AREA_ACCESS impact={int(session.manifest['schema'] >= 5)} forest=1 navel=1 spring=1 trial=1")
            session.receive(len(grants), [ITEM_IDS[REPAIR]] * 25)
            wait("GOAL: Ship repaired!")
            run.poll()
            expected = {'Population: 20 Pikmin in the field', f'Explore: {area} - Land'} if expanded else set()
            assert set(session.data['checked']) == expected, session.data['checked']
            text = log.read_text(encoding="utf-8", errors="replace")
            for item in grants[:2]:
                assert text.count(f"PIKMIN_{item.split()[0].upper()}_ONION_GRANTED starter=5") == 1
            assert f'PIKMIN_{color.upper()}_ONION_GRANTED starter=5' not in text
            assert 'TEST_ONLY' not in text, 'test fixtures enabled unexpectedly'
            print(f"PASS native startup: {area}, 20 {color} Pikmin, other color grants exactly once, area gates, goal; expected checks only", sorted(expected), flush=True)
            print(log)
        finally:
            if process.poll() is None: process.terminate();process.wait(timeout=10)
            run.write_state(False)

if __name__ == "__main__":
    p = argparse.ArgumentParser();p.add_argument("--exe", type=Path, required=True)
    p.add_argument("--assets", type=Path, required=True);p.add_argument("--output", type=Path, required=True)
    p.add_argument('--expanded', action='store_true')
    p.add_argument('--starting-area', choices=['impact', 'forest', 'navel', 'spring', 'trial', 'random'], default='forest')
    p.add_argument('--all-areas', action='store_true')
    p.add_argument('--enemy-shuffle', action='store_true')
    p.add_argument('--seed', default='startup-smoke')
    p.add_argument('--starting-color', choices=['red', 'yellow', 'blue', 'random'], default='red')
    a=p.parse_args();main(a.exe,a.assets,a.output.resolve(),a.expanded,a.starting_area,a.seed,a.starting_color,a.all_areas,a.enemy_shuffle)
