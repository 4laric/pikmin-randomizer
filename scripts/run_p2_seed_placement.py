"""Seed-driven placement: both arena generators bind and resolve in one room run.

Stages the two-actor arena (native Chappy generators ``211001``/``211002``) once,
marks both generators in the dwarf-orange actor list, generates a single seed on
the admitted cohort, writes the seed-derived sidecar (one ``(generator, slot)``
pair per arena generator), writes the ``ENEMY_P2`` bootstrap, and runs the room
with ``--randomizer-seed``. The report then runs the three-marker co-occurrence
validator on the real log and records its verdict.

Expected single-log evidence (one complete chain per resolving generator):

* ``P2_PLACEMENT_SLOT generator=<g> slot=<u> ...``
* ``P2_SEED_RESOLVE source_id=<s> target=<u> ...``
* ``P2_ENEMY_READY source_id=<s> ... generator=<g> ...``

Run only under the host GL slot:

    py -3.12 <repo>/output/deepseek-wave/slot.py run gl <lane> -- \\
        py -3.12 scripts/run_p2_seed_placement.py \\
            --assets <P1 assets> --bank <dwarf-orange bank> --profile <profile dir> \\
            --exe <nectar.exe> --output <out dir> --seed <seed name>
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import experimental.pikmin2_seed_placement as placement
from experimental.pikmin2_seed_placement_native import validate_cooccurrence


def _find_mingw():
    env = os.environ.get('MINGW_BIN')
    if env and (Path(env) / 'SDL2.dll').exists():
        return str(Path(env))
    for entry in os.environ.get('PATH', '').split(os.pathsep):
        if entry and (Path(entry) / 'SDL2.dll').exists():
            return entry
    fallback = Path(r'C:/msys64/mingw64/bin')
    return str(fallback) if (fallback / 'SDL2.dll').exists() else None


def _run_native(exe, stage, bootstrap, timeout):
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


def _lines(text, prefix):
    return [line.strip() for line in text.splitlines() if line.startswith(prefix + ' ')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=str, default='p2-seed-placement')
    parser.add_argument('--timeout', type=int, default=60)
    args = parser.parse_args()

    from experimental.pikmin2_dwarf_orange_runtime import prepare  # noqa: E402
    from experimental.pikmin2_dwarf_orange_install import ACTORS_HEADER  # noqa: E402
    from randomizer import p2_placement_probe, p2_placement_catalog  # noqa: E402
    import experimental.pikmin2_seed_bridge as bridge  # noqa: E402
    from randomizer.runner import NativeRun  # noqa: E402
    from randomizer.session import Session  # noqa: E402

    args.output.mkdir(parents=True, exist_ok=True)
    stage = prepare(args.assets.resolve(), args.bank.resolve(), args.profile.resolve(), args.output)

    # Mark BOTH arena generators as dwarf-orange source actors (both must close
    # the three-marker chain, not just the single source generator).
    actors_text = (f'{ACTORS_HEADER} {len(placement.ARENA_GENERATORS)}\n'
                   + '\n'.join(map(str, placement.ARENA_GENERATORS)) + '\n')
    (stage / 'p2-dwarf-orange-actors.txt').write_text(actors_text, encoding='ascii')

    catalog_doc = p2_placement_catalog.build_document()
    document = placement.placement_document(catalog_doc=catalog_doc)
    manifest = placement.generate_admitted_seed(args.seed, document)
    seed_slots = placement.seed_slots(manifest, placement.BLUEKOCHAPPY_SOURCE)
    if len(seed_slots) < len(placement.ARENA_GENERATORS):
        raise SystemExit(
            f'seed bound only {len(seed_slots)} slot(s) to source '
            f'{placement.BLUEKOCHAPPY_SOURCE}; need {len(placement.ARENA_GENERATORS)} '
            f'for the two arena generators')
    pairs = list(zip(placement.ARENA_GENERATORS, seed_slots[:len(placement.ARENA_GENERATORS)]))
    placement.write_sidecar(stage, pairs)

    saved_admitted = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: list(placement.ADMITTED_COHORT)
    try:
        session = Session(manifest, stage / 'seed')
        native_run = NativeRun(session)
        bootstrap = native_run.bootstrap.resolve()
    finally:
        bridge.admitted_ids = saved_admitted

    log, code = _run_native(args.exe, stage, bootstrap, args.timeout)
    text = log.read_text(encoding='utf-8', errors='replace')

    probe = p2_placement_probe.build_probe(text)
    marker_slots = [m['slot'] for m in probe['mapping']]
    co_occurrence = validate_cooccurrence(text)
    report = {
        'run': str(stage),
        'seed': args.seed,
        'arena_stage': placement.ARENA_STAGE,
        'sidecar_pairs': [[g, u] for g, u in pairs],
        'seed_binding_set': seed_slots,
        'marker_slots': marker_slots,
        'markers_are_binding_members': set(marker_slots) <= set(seed_slots),
        'placement_lines': _lines(text, 'P2_PLACEMENT_SLOT'),
        'resolve_lines': _lines(text, 'P2_SEED_RESOLVE'),
        'ready_lines': _lines(text, 'P2_ENEMY_READY'),
        'validate_cooccurrence': {
            'ok': co_occurrence.ok,
            'reason': co_occurrence.reason,
            'generator': co_occurrence.generator,
            'slot': co_occurrence.slot,
            'source': co_occurrence.source,
        },
        'exit': code,
    }
    (stage / 'seed-placement-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (args.output / 'latest-seed-placement-run.json').write_text(
        json.dumps({'run': str(stage), 'seed': args.seed}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
