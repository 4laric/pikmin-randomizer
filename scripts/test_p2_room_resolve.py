"""Lane-03 slice 2b runtime: the ENEMY_P2 seed bridge resolves a live Dwarf Orange.

Reuses lane 04/05 staging as-is (``experimental.pikmin2_dwarf_orange_runtime.prepare``
+ ``experimental.pikmin2_seed_placement.sidecar``) and additionally writes the
seed's ``ENEMY_P2`` bootstrap and runs the room preview with
``--randomizer-seed <bootstrap>``. The native room hook parses only the P2 bridge
(no full session, so the preview is not held), then ``pc_randomizer_bind_generator``
joins the room generator's ``_70`` (211001) to the seed-chosen slot uid through
``p2-placement-slots.txt``, resolving ``P2_SEED_RESOLVE source_id=44`` at birth
alongside lane 13/05's ``P2_ENEMY_READY species=BlueKochappy``.

Run only under the host GL slot:

    py -3.12 output/deepseek-wave/slot.py run gl l03 -- \\
        py -3.12 scripts/test_p2_room_resolve.py \\
            --assets <P1 assets> --bank <dwarf-orange bank> --profile <profile dir> \\
            --exe <nectar.exe> --output <out dir>
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental.pikmin2_dwarf_orange_runtime import prepare  # noqa: E402
import experimental.pikmin2_seed_placement as placement  # noqa: E402
import experimental.pikmin2_seed_bridge as bridge  # noqa: E402
from randomizer.p2_placement_catalog import build_document  # noqa: E402
from randomizer.runner import NativeRun  # noqa: E402
from randomizer.session import Session  # noqa: E402


def _find_mingw():
    for entry in os.environ.get('PATH', '').split(os.pathsep):
        if entry and (Path(entry) / 'SDL2.dll').exists():
            return entry
    fallback = Path(r'C:/msys64/mingw64/bin')
    return str(fallback) if (fallback / 'SDL2.dll').exists() else None


def run_native(exe, stage, bootstrap, timeout):
    env = dict(os.environ)
    mingw = _find_mingw()
    if mingw:
        env['PATH'] = mingw + os.pathsep + env.get('PATH', '')
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env['PYTHONUTF8'] = '1'
    env['SDL_AUDIODRIVER'] = 'dummy'
    env['PIKMIN_RANDOMIZER_TEST_BACKGROUND'] = '1'
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    log = stage / 'native.log'
    code = 'ok'
    with log.open('w', encoding='utf-8', errors='replace') as stream:
        try:
            subprocess.run([str(Path(exe).resolve()), '--experimental-pikmin2-room',
                            '--randomizer-seed', str(bootstrap)],
                           cwd=stage, env=env, stdout=stream, stderr=subprocess.STDOUT,
                           startupinfo=startup, timeout=timeout)
        except subprocess.TimeoutExpired:
            code = 'timeout'  # markers already flushed; window retired
    return log, code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=str, default='l03-room-resolve')
    parser.add_argument('--timeout', type=int, default=60)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    document = placement.placement_document(catalog_doc=build_document())
    manifest = placement.generate_admitted_seed(args.seed, document)
    seed_uid = placement.seed_slot_uid(manifest, placement.BLUEKOCHAPPY_SOURCE)

    stage = prepare(args.assets.resolve(), args.bank.resolve(), args.profile.resolve(), args.output)
    placement.write_sidecar(stage, placement.ARENA_SOURCE_GENERATOR, seed_uid)

    saved_admitted = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: list(placement.ADMITTED_COHORT)
    try:
        session = Session(manifest, stage / 'seed')
        run = NativeRun(session)
        bootstrap = run.bootstrap.resolve()
    finally:
        bridge.admitted_ids = saved_admitted

    log, code = run_native(args.exe, stage, bootstrap, args.timeout)
    text = log.read_text(encoding='utf-8', errors='replace')
    resolve_lines = [line for line in text.splitlines() if 'P2_SEED_RESOLVE' in line]
    ready_lines = [line for line in text.splitlines() if 'P2_ENEMY_READY' in line]
    result = {
        'stage': str(stage),
        'seed': args.seed,
        'seed_slot_uid': seed_uid,
        'exit': code,
        'resolve_lines': resolve_lines,
        'ready_lines': ready_lines,
        'resolved_bluekochappy': any(
            'source_id=44' in line for line in resolve_lines),
        'ready_bluekochappy': any(
            'source_id=44' in line for line in ready_lines),
    }
    (args.output / 'l03-room-resolve.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
