"""Lane 06 ordinary P2 delivery runtime acceptance (#441).

Stages a real native randomizer session (schema 9 + collection_checks), binds a
live P2 source (Dwarf Orange Bulborb, source 44) onto the ordinary Chappy host
— a labelled fixture intervention standing in for the lane-13 bind path — kills
it, drives its real corpse through the real Onion endpoint
(``GoalItem::suckMe`` -> ``pc_randomizer_p2_corpse_delivered``), then re-runs a
fresh process over the SAME durable receipt ledger (written by the production
open path into the session ``campaign`` directory) to prove the ordinary P2
reward is granted exactly once across restart.

Fixture: ``scripts/p2_delivery_fixture.cpp`` (replacement main). Carry is injected
(natural carry does not move the corpse; transport is lane 04). Persistence is
process restart only: the durable ``campaign/p2-delivery-receipts.txt`` sidecar is
re-read by the second cold process, but no memory-card checkpoint save is
triggered in this fixture. See ``docs/PIKMIN2_REWARD_RECEIPTS.md``.
"""
import argparse
import os
import subprocess
import sys
import time
import uuid
import _winapi
from pathlib import Path

# MinGW runtime DLLs (libstdc++/libgcc/libwinpthread) must be on PATH for the
# fixture exe; this is the maintained toolchain's bin directory.
MINGW_BIN = Path('C:/msys64/mingw64/bin')


def run_once(session, exe, assets, label):
    from randomizer.runner import NativeRun
    native_run = NativeRun(session)
    run = native_run.directory
    _winapi.CreateJunction(str(assets.resolve()), str((run / 'assets').resolve()))
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', PIKMIN_RANDOMIZER_TEST_BACKGROUND='1')
    if MINGW_BIN.is_dir():
        env['PATH'] = str(MINGW_BIN) + ';' + env['PATH']
    env.pop('BBFT_PORT', None)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 1
    log = run / 'native.log'
    native_run.write_state(True)
    with log.open('w') as stream:
        proc = subprocess.Popen([str(exe), '--randomizer-seed', str(native_run.bootstrap.resolve())],
                                cwd=run, env=env, startupinfo=startup, stdout=stream,
                                stderr=subprocess.STDOUT)
        deadline = time.time() + 300
        while proc.poll() is None and time.time() < deadline:
            native_run.write_state(True)
            time.sleep(0.1)
        code = proc.poll()
        if code is None:
            proc.kill()
            code = 'timeout'
    text = log.read_text(errors='replace')
    grants = [l for l in text.splitlines() if 'P2_ORDINARY_P2_RECEIPT' in l]
    news = [l for l in grants if ' new=1' in l]
    dups = [l for l in grants if ' new=0' in l]
    print(f'[{label}] exit={code} receipt_grants={len(news)} receipt_duplicates={len(dups)}')
    for line in grants:
        print(f'  {line.strip()}')
    return code, news, dups, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--assets', type=Path,
                        default=Path(os.environ.get('APPDATA', '')) / 'PikminRandomizer' / 'game-data' / 'assets')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', default='p2-delivery-two-process-restart')
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from randomizer.seed import generate
    from randomizer.session import Session
    from randomizer.catalog import ITEM_IDS

    args.output.mkdir(parents=True, exist_ok=True)
    manifest = generate(args.seed, 'ap', expanded=True, all_areas=True,
                        collection_checks=True, starting_flarlic=10)
    session = Session(manifest, args.output / ('session-' + uuid.uuid4().hex[:8]))
    session.bind_ap('lane06-fixture', 0, 1)
    wanted = [uid for name, uid in ITEM_IDS.items()
              if uid in session.allowed_items and (name.endswith('Onion') or name.endswith('Access'))]
    session.receive(0, wanted)
    print('schema', manifest['schema'], 'catalog', manifest['catalog'])

    # The production open path writes the ledger to the session campaign
    # directory (a live save/checkpoint root), not the run cwd.
    receipt_path = session.directory / 'campaign' / 'p2-delivery-receipts.txt'

    code1, news1, dups1, run1 = run_once(session, args.exe, args.assets, 'run1')
    code2, news2, dups2, run2 = run_once(session, args.exe, args.assets, 'run2')

    ledger_rows = 0
    if receipt_path.exists():
        lines = [l for l in receipt_path.read_text().splitlines() if l.strip() and l.split()[0] != 'P2_RECEIPTS_1']
        ledger_rows = len([l for l in lines if 'onion:p2:44:' in l])

    ok = (code1 == 0 and len(news1) == 1 and len(dups1) == 0
          and code2 == 0 and len(news2) == 0 and len(dups2) >= 1
          and ledger_rows == 1)
    print('EXACTLY_ONCE_ACROSS_RESTART:', ok)
    print('receipt_file', receipt_path, 'onion_p2_rows=', ledger_rows)
    print('run1', run1)
    print('run2', run2)
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
