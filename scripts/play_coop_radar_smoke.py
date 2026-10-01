"""Fresh local co-op radar smoke; user-operated, no network connection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import uuid


def main():
    checkout = Path(__file__).resolve().parents[1]
    root = checkout.parent.parent if checkout.parent.name == 'output' else checkout
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, default=root/'output/native-coop-radar-build/bin/nectar.exe')
    parser.add_argument('--assets', type=Path, default=Path('C:/Users/alari/AppData/Roaming/PikminRandomizer/game-data/assets'))
    parser.add_argument('--orientation', choices=['vertical', 'horizontal'], default='vertical')
    parser.add_argument('--seconds', type=int, default=90)
    args = parser.parse_args()
    exe, assets = args.exe.resolve(strict=True), args.assets.resolve(strict=True)
    if not 15 <= args.seconds <= 300:
        parser.error('--seconds must be 15..300')
    run = root/'output/coop-radar'/('manual-'+uuid.uuid4().hex)
    run.mkdir(parents=True)
    import _winapi
    _winapi.CreateJunction(str(assets), str(run/'assets'))
    token = uuid.uuid4().hex*2
    boot = (f'PIKMIN_RANDOMIZER 5\nSESSION {token}\nFINGERPRINT {token}\n'
            'PROFILE impact-day2\nCATALOG gameplay-checks-v5\nPLACEMENT identity-v1\n'
            'GOAL 25\nDAYS repeat-day29-v1\nCOLOR red\nSTARTING_FLARLIC 10\nEND\n')
    (run/'bootstrap.txt').write_text(boot, encoding='ascii')
    state = f'PIKMIN_STATE 5 {token} 1 0 127 0 16 END\n'
    (run/'pikmin_settings.conf').write_text(
        f'coopSplit = {int(args.orientation == "horizontal")}\nwindowMode = 0\nwindowWidth = 960\nwindowHeight = 540\n', encoding='ascii')
    stopped = threading.Event()
    def refresh():
        while not stopped.is_set():
            try:
                (run/'state.tmp').write_text(state, encoding='ascii')
                os.replace(run/'state.tmp', run/'state.txt')
            except OSError:
                pass
            stopped.wait(.1)
    worker = threading.Thread(target=refresh)
    worker.start()
    env = {k:v for k,v in os.environ.items() if not k.startswith(('PIKMIN_NETPLAY_', 'PIKMIN_INPUT_', 'PIKMIN_RANDOMIZER_TEST_', 'PIKMIN_COOP', 'PIKMIN_FRAME_DUMP'))}
    env['PATH'] = 'C:/msys64/mingw64/bin;'+env.get('PATH','')
    env['NECTAR_SAVE_DIR'] = str(run/'save')
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    (run/'smoke-inputs.json').write_text(json.dumps(dict(exe=str(exe),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),assets=str(assets),orientation=args.orientation,human_judgment='unrecorded'),indent=2),encoding='utf-8')
    print('Local co-op radar check: P1 keyboard Y and P2 controller Y/triangle open their menus; Shift/B/circle closes. Try each menu and both together. Move captains apart for split views. Check the OTHER view center stays clear and labels remain readable. Close the game or wait 90 seconds; rerun for a fresh reset.', flush=True)
    try:
        with (run/'native.log').open('wb') as log:
            proc = subprocess.Popen([str(exe),'--coop','--randomizer-seed',str(run/'bootstrap.txt')],cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT)
            try:
                proc.wait(timeout=args.seconds)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=10)
    finally:
        stopped.set()
        worker.join()
    print(f'Private run: {run}. No automated visual/readability approval inferred.')


if __name__ == '__main__':
    main()
