"""Lane 18 Breadbug ordinary Onion/AP receipt runtime acceptance (#220).

Stages a real native randomizer session (``randomizer.seed.generate`` +
``NativeRun`` bootstrap and ``state.txt`` refresh; no live AP server) in the
Forest Navel (the audited native area for the Breadbug / TEKI_Collec, type 8),
kills a real Breadbug, drives its real corpse through the real Onion endpoint
(``GoalItem::suckMe`` -> ``pc_randomizer_corpse_delivered`` ->
``pc_randomizer_check("Bestiary: Deliver Breadbug")``), then re-runs a fresh
process against the same session to prove the ordinary check is granted exactly
once across restart.

The fixture source is ``scripts/p2_ordinary_receipt_fixture.cpp`` (the shared
parameterised replacement main, driven with ``--enemy-type 8 --check`` for the
Breadbug), built with ``scripts/build_pikmin2_fixture.py``. The Pikmin carry step is
injected: the fixture calls the same public Onion endpoint with the real corpse
pellet because natural carry does not move the corpse; natural transport is lane
04. See ``docs/PIKMIN2_REWARD_RECEIPTS.md``.
"""
import argparse
import os
import subprocess
import sys
import threading
import uuid
import _winapi
from pathlib import Path

TARGET = 'Bestiary: Deliver Breadbug'


def run_once(session, exe, assets, label):
    from randomizer.runner import NativeRun
    native_run = NativeRun(session)
    run = native_run.directory
    _winapi.CreateJunction(str(assets.resolve()), str((run / 'assets').resolve()))
    done = threading.Event()

    def refresh():
        while not done.is_set():
            native_run.write_state(True)
            done.wait(0.1)

    threading.Thread(target=refresh, daemon=True).start()
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', PIKMIN_RANDOMIZER_TEST_BACKGROUND='1')
    env.pop('BBFT_PORT', None)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    log = run / 'native.log'
    try:
        with log.open('w') as stream:
            try:
                code = subprocess.run([str(exe), '--randomizer-seed', str(native_run.bootstrap.resolve()),
                                      '--enemy-type', '8', '--check', TARGET],
                                      cwd=run, env=env, startupinfo=startup, stdout=stream,
                                      stderr=subprocess.STDOUT, timeout=300).returncode
            except subprocess.TimeoutExpired:
                code = 'timeout'
    finally:
        done.set()
    text = log.read_text(errors='replace')
    checks = run / 'checks.txt'
    names = [session.names[int(x)] for x in checks.read_text().split()] if checks.exists() else []
    target_lines = [line for line in text.splitlines() if 'CHECK' in line and TARGET in line]
    print(f'[{label}] exit={code} target_check_lines={len(target_lines)} checks={names}')
    return code, names, target_lines, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--assets', type=Path,
                        default=Path(os.environ.get('APPDATA', '')) / 'PikminRandomizer' / 'game-data' / 'assets')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', default='lane18-breadbug-ordinary-restart')
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from randomizer.seed import generate
    from randomizer.session import Session
    from randomizer.catalog import ITEM_IDS

    args.output.mkdir(parents=True, exist_ok=True)
    manifest = generate(args.seed, 'ap', expanded=True, all_areas=True,
                        collection_checks=True, starting_flarlic=10,
                        starting_area='navel')
    session = Session(manifest, args.output / ('session-' + uuid.uuid4().hex[:8]))
    session.bind_ap('lane18-fixture', 0, 1)
    wanted = [uid for name, uid in ITEM_IDS.items()
              if uid in session.allowed_items and (name.endswith('Onion') or name.endswith('Access'))]
    session.receive(0, wanted)
    print('schema', manifest['schema'], 'catalog', manifest['catalog'], 'profile', manifest.get('profile'))

    code1, names1, lines1, run1 = run_once(session, args.exe, args.assets, 'run1')
    for name in names1:
        if name not in session.data['checked']:
            session.collect(name)
    code2, names2, lines2, run2 = run_once(session, args.exe, args.assets, 'run2')

    ok = code1 == 0 and len(lines1) == 1 and TARGET in session.data['checked'] and code2 == 0 and len(lines2) == 0
    print('EXACTLY_ONCE_ACROSS_RESTART:', ok)
    print('run1', run1)
    print('run2', run2)
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
