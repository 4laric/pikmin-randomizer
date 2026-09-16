"""Lane-03 slice 4 runtime: cross-process generator-cache round trip for the P2 room.

Reuses lane 04/05 staging as-is (``experimental.pikmin2_dwarf_orange_runtime.prepare``
+ ``experimental.pikmin2_seed_placement.sidecar``) and writes the seed's ``ENEMY_P2``
bootstrap. Two modes, both run only under the host GL slot:

- default: natural resolve. One boot with the ``_70`` sidecar, asserting the live
  Dwarf Orange binds (``P2_SEED_RESOLVE source_id=44`` + ``P2_ENEMY_READY``).
- ``--cache-roundtrip``: cross-process round trip. Boot 1 writes the generator
  cache (``PIKMIN_P2_CACHE_SAVE``) to ``p2-gencache.bin``; the ``_70`` sidecar is
  then renamed away; boot 2 (``PIKMIN_P2_CACHE_RESUME``) reloads that cache and must
  re-emit ``P2_SEED_RESOLVE`` from the cache, not the sidecar.

    py -3.12 output/deepseek-wave/slot.py run gl <lane> -- \\
        py -3.12 scripts/test_p2_room_resolve.py \\
            --assets <P1 assets> --bank <dwarf-orange bank> --profile <profile dir> \\
            --exe <nectar.exe> --output <out dir> [--cache-roundtrip]
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


def run_native(exe, stage, bootstrap, timeout, extra_env=None, log_name='native.log'):
    env = dict(os.environ)
    mingw = _find_mingw()
    if mingw:
        env['PATH'] = mingw + os.pathsep + env.get('PATH', '')
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env['PYTHONUTF8'] = '1'
    env['SDL_AUDIODRIVER'] = 'dummy'
    env['PIKMIN_RANDOMIZER_TEST_BACKGROUND'] = '1'
    if extra_env:
        env.update(extra_env)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    log = stage / log_name
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
                        help='cross-process round trip: save the generator cache, '
                             'rename the sidecar, resume reading only the cache')
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    document = placement.placement_document(catalog_doc=build_document())
    manifest = placement.generate_admitted_seed(args.seed, document)
    seed_uid = placement.seed_slot_uid(manifest, placement.BLUEKOCHAPPY_SOURCE)

    stage = prepare(args.assets.resolve(), args.bank.resolve(), args.profile.resolve(), args.output)
    sidecar = placement.write_sidecar(stage, placement.ARENA_SOURCE_GENERATOR, seed_uid)

    saved_admitted = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: list(placement.ADMITTED_COHORT)
    try:
        session = Session(manifest, stage / 'seed')
        run = NativeRun(session)
        bootstrap = run.bootstrap.resolve()
    finally:
        bridge.admitted_ids = saved_admitted

    if args.cache_roundtrip:
        # Boot 1: write the generator cache, then exit.
        save_log, save_rc = run_native(args.exe, stage, bootstrap, args.timeout,
                                       {'PIKMIN_P2_CACHE_SAVE': '1'}, 'native-save.log')
        save_text = save_log.read_text(encoding='utf-8', errors='replace')
        cache_file = stage / 'p2-gencache.bin'
        # Prove the source of the second boot is the cache, not the sidecar.
        sidecar.rename(sidecar.with_name(sidecar.name + '.disabled'))
        # Boot 2: resume from the cache only.
        resume_log, resume_rc = run_native(args.exe, stage, bootstrap, args.timeout,
                                           {'PIKMIN_P2_CACHE_RESUME': '1'}, 'native-resume.log')
        resume_text = resume_log.read_text(encoding='utf-8', errors='replace')

        (args.output / 'p2-room-cache-save.log').write_text(save_text, encoding='utf-8', errors='replace')
        (args.output / 'p2-room-cache-resume.log').write_text(resume_text, encoding='utf-8', errors='replace')

        save_ok = ('P2_GENCACHE_SAVE' in save_text) and cache_file.exists()
        resume_validation = validate_log(resume_text, require_ready=True)._asdict()
        resume_loaded = 'P2_GENCACHE_RESUME' in resume_text
        result = {
            'stage': str(stage),
            'seed': args.seed,
            'seed_slot_uid': seed_uid,
            'cache_roundtrip': True,
            'save_exit': 'ok' if save_rc == 0 else ('timeout' if save_rc is None else f'exit-{save_rc}'),
            'resume_exit': 'ok' if resume_rc == 0 else ('timeout' if resume_rc is None else f'exit-{resume_rc}'),
            'save_ok': save_ok,
            'cache_file_bytes': cache_file.stat().st_size if cache_file.exists() else 0,
            'resume_loaded': resume_loaded,
            'resume_validation': resume_validation,
            'resume_resolve_lines': [line for line in resume_text.splitlines() if 'P2_SEED_RESOLVE' in line],
            'sidecar_renamed': not sidecar.exists(),
        }
        (args.output / 'p2-room-cache-roundtrip.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        ok = save_ok and resume_loaded and resume_validation['ok']
        sys.exit(0 if ok else 1)

    log, returncode = run_native(args.exe, stage, bootstrap, args.timeout)
    text = log.read_text(encoding='utf-8', errors='replace')
    (args.output / 'p2-room-resolve.log').write_text(text, encoding='utf-8', errors='replace')
    resolve_lines = [line for line in text.splitlines() if 'P2_SEED_RESOLVE' in line]
    ready_lines = [line for line in text.splitlines() if 'P2_ENEMY_READY' in line]
    exit_reason = 'ok' if returncode == 0 else ('timeout' if returncode is None else f'exit-{returncode}')
    validation = validate_log(text, require_ready=True)._asdict()
    result = {
        'stage': str(stage),
        'seed': args.seed,
        'seed_slot_uid': seed_uid,
        'cache_roundtrip': False,
        'exit': exit_reason,
        'returncode': returncode,
        'validation': validation,
        'resolve_lines': resolve_lines,
        'ready_lines': ready_lines,
        'resolved_bluekochappy': any('source_id=44' in line for line in resolve_lines),
        'ready_bluekochappy': any('source_id=44' in line for line in ready_lines),
    }
    (args.output / 'p2-room-resolve.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if not validation['ok']:
        sys.exit(1)


if __name__ == '__main__':
    main()
