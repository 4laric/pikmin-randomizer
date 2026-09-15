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

    py -3.12 output/deepseek-wave/slot.py run gl <lane> -- \\
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
from experimental.pikmin2_seed_roundtrip import validate_log  # noqa: E402
from randomizer.p2_placement_catalog import build_document  # noqa: E402
from randomizer.runner import NativeRun  # noqa: E402
from randomizer.session import Session  # noqa: E402


def _find_mingw():
    for entry in os.environ.get('PATH', '').split(os.pathsep):
        if entry and (Path(entry) / 'SDL2.dll').exists():
            return entry
    fallback = Path(r'C:/msys64/mingw64/bin')
    return str(fallback) if (fallback / 'SDL2.dll').exists() else None


def run_native(exe, stage, bootstrap, timeout, roundtrip=False):
    env = dict(os.environ)
    mingw = _find_mingw()
    if mingw:
        env['PATH'] = mingw + os.pathsep + env.get('PATH', '')
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env['PYTHONUTF8'] = '1'
    env['SDL_AUDIODRIVER'] = 'dummy'
    env['PIKMIN_RANDOMIZER_TEST_BACKGROUND'] = '1'
    if roundtrip:
        env['PIKMIN_P2_CACHE_ROUNDTRIP'] = '1'
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    log = stage / 'native.log'
    returncode = None
    with log.open('w', encoding='utf-8', errors='replace') as stream:
        try:
            completed = subprocess.run([str(Path(exe).resolve()), '--experimental-pikmin2-room',
                            '--randomizer-seed', str(bootstrap)],
                           cwd=stage, env=env, stdout=stream, stderr=subprocess.STDOUT,
                           startupinfo=startup, timeout=timeout)
            returncode = completed.returncode
        except subprocess.TimeoutExpired:
            returncode = None  # markers already flushed; window retired
    return log, returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=str, default='p2-room-resolve')
    parser.add_argument('--timeout', type=int, default=60)
    parser.add_argument('--cache-roundtrip', action='store_true',
                        help='run the Generator::write/read room cache round-trip instead of the resolve pass')
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

    log, returncode = run_native(args.exe, stage, bootstrap, args.timeout, args.cache_roundtrip)
    text = log.read_text(encoding='utf-8', errors='replace')
    log_name = 'p2-room-cache-roundtrip.log' if args.cache_roundtrip else 'p2-room-resolve.log'
    (args.output / log_name).write_text(text, encoding='utf-8', errors='replace')
    resolve_lines = [line for line in text.splitlines() if 'P2_SEED_RESOLVE' in line]
    ready_lines = [line for line in text.splitlines() if 'P2_ENEMY_READY' in line]
    exit_reason = 'ok' if returncode == 0 else ('timeout' if returncode is None else f'exit-{returncode}')
    validation = validate_log(text, require_ready=not args.cache_roundtrip)._asdict()
    roundtrip_pass = 'TEST_ONLY p2_room_cache_roundtrip_pass' in text
    result = {
        'stage': str(stage),
        'seed': args.seed,
        'seed_slot_uid': seed_uid,
        'cache_roundtrip': args.cache_roundtrip,
        'exit': exit_reason,
        'returncode': returncode,
        'roundtrip_pass': roundtrip_pass,
        'validation': validation,
        'resolve_lines': resolve_lines,
        'ready_lines': ready_lines,
        'resolved_bluekochappy': any(
            'source_id=44' in line for line in resolve_lines),
        'ready_bluekochappy': any(
            'source_id=44' in line for line in ready_lines),
    }
    (args.output / ('p2-room-cache-roundtrip.json' if args.cache_roundtrip else 'p2-room-resolve.json')) \
        .write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    ok = roundtrip_pass if args.cache_roundtrip else validation['ok']
    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
