"""Lane 07 in-process new-scene runtime acceptance (#397).

Stages a Snow campaign day (real P2 family bindings), plays it through an
ordinary day end to MapSelect, then drives the MenuSelect menu with the reusable
scripted pad (``pc_p2_input_script``) to load a fresh gameplay area in the same
process. ``pc_p2_scene_generation()`` (incremented in
``GameCoreSection::finalSetup``) is the safe new-scene readiness signal; the
transition frees the previous ``TekiMgr``, so the fixture must not touch it until
the generation advances.

Fixture source: ``scripts/p2_new_scene_fixture.cpp`` (replacement main), built
with ``scripts/build_pikmin2_fixture.py``. Requires the Snow bank at
``--snow`` (default ``output/p2-animation128/dense24``). See
``docs/PIKMIN2_TEKI_LIFETIME_SEAM.md``.
"""
import argparse
import os
import subprocess
import sys
import threading
import uuid
import _winapi
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--snow', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assets', type=Path,
                        default=Path(os.environ.get('APPDATA', '')) / 'PikminRandomizer' / 'game-data' / 'assets')
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experimental.pikmin2_animation import parse_bank, validate_files
    from scripts.preview_pikmin2_room import overlay

    args.output.mkdir(parents=True, exist_ok=True)
    campaign = args.output / ('campaign-' + uuid.uuid4().hex[:8])
    identity = uuid.uuid4().hex * 2
    bank = parse_bank((args.snow / 'p2-snow.txt').read_text())
    files, _ = validate_files(args.snow, bank)
    overrides = {'dataDir/courses/pikmin2room/' + p.name: p.read_bytes() for p in files}
    overrides.update({'p2-snow.txt': (args.snow / 'p2-snow.txt').read_bytes(),
                      'p2-snow-all-dwarfs.txt': b'P2_SNOW_ALL_DWARFS_1\n',
                      'p2-snow-interpolation.txt': b'P2_SNOW_INTERPOLATION_1\n'})

    token = uuid.uuid4().hex * 2
    run = campaign / 'runs' / token
    run.mkdir(parents=True)
    overlay(args.assets, run / 'assets', overrides)
    boot = run / 'bootstrap.txt'
    boot.write_text(f'PIKMIN_RANDOMIZER 5\nSESSION {token}\nFINGERPRINT {identity}\nPROFILE foh-day2\n'
                    f'CATALOG gameplay-checks-v5\nPLACEMENT identity-v1\nGOAL 25\nDAYS repeat-day29-v1\n'
                    f'COLOR red\nSTARTING_FLARLIC 10\nEND\n')

    done = threading.Event()

    def refresh():
        while not done.is_set():
            pending = run / 'state.tmp'
            pending.write_text(f'PIKMIN_STATE 5 {token} 1 0 127 0 0 END\n')
            os.replace(pending, run / 'state.txt')
            done.wait(0.1)

    threading.Thread(target=refresh, daemon=True).start()
    env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', SDL_AUDIODRIVER='dummy', PIKMIN_CAMPAIGN_TEST='1')
    env.pop('BBFT_PORT', None)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    log = run / 'native.log'
    try:
        with log.open('w') as stream:
            try:
                code = subprocess.run([str(args.exe), '--randomizer-seed', str(boot.resolve())], cwd=run, env=env,
                                      startupinfo=startup, stdout=stream, stderr=subprocess.STDOUT, timeout=300).returncode
            except subprocess.TimeoutExpired:
                code = 'timeout'
    finally:
        done.set()

    text = log.read_text(errors='replace')
    print('exit_code', code, 'run_dir', run)
    for line in text.splitlines():
        if any(k in line for k in ('P2_NEWSCENE', 'P2_SNOW_CAMPAIGN', 'PASS', 'FAIL')):
            print(line)
    passed = code == 0 and 'PASS P2_NEWSCENE_RELOAD' in text
    print('NEW_SCENE_RELOAD_PASS:', passed)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
