"""Seed-driven placement with both Snow (45) and Dwarf Orange (44) birthing.

Stages the three-actor mixed arena (Dwarf Orange 211001 = BlueKochappy 44, Snow
5001 = YellowKochappy 45, plus the P1 Chappy control 211002) on the original
Impact Site map, generates a seed on the admitted {44,45} cohort, writes the sidecar
mapping one generator to a slot of each source, writes the ``ENEMY_P2`` bootstrap,
and runs the room with ``--randomizer-seed``. The report runs the three-marker
co-occurrence validator on the real log: both sources must close a
`generator -> slot -> source` + birth chain.

Expected single-log evidence:

* ``P2_ENEMY_READY species=BlueKochappy source_id=44 ... generator=211001``
* ``P2_ENEMY_READY species=YellowKochappy source_id=45 ... generator=5001``
* ``P2_SEED_RESOLVE source_id=44 target=<u>`` / ``source_id=45 target=<u>``
* ``P2_PLACEMENT_SLOT generator=211001 slot=<u>`` / ``generator=5001 slot=<u>``

Run only under the host GL slot:

    py -3.12 <repo>/output/deepseek-wave/slot.py run gl <lane> -- \\
        py -3.12 scripts/run_p2_cohort_seed_placement.py \\
            --assets <P1 assets> --bank <dwarf-orange bank> --profile <profile dir> \\
            --snow <snow-prepared dir> --exe <nectar.exe> --output <out dir> --seed <name>
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
from randomizer import p2_placement_probe

ORANGE_GENERATOR = 211001
SNOW_GENERATOR = 5001


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
    parser.add_argument('--snow', type=Path, required=True)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=str, default='p2-cohort-seed-placement')
    parser.add_argument('--timeout', type=int, default=60)
    args = parser.parse_args()

    from experimental.pikmin2_mixed_bulborb_runtime import prepare  # noqa: E402
    from randomizer import p2_placement_catalog  # noqa: E402
    import experimental.pikmin2_seed_bridge as bridge  # noqa: E402
    from randomizer.runner import NativeRun  # noqa: E402
    from randomizer.session import Session  # noqa: E402

    args.output.mkdir(parents=True, exist_ok=True)
    stage = prepare(args.assets.resolve(), args.bank.resolve(), args.profile.resolve(),
                    args.snow.resolve(), args.output)

    catalog_doc = p2_placement_catalog.build_document()
    document = placement.placement_document(catalog_doc=catalog_doc)
    manifest = placement.generate_admitted_seed(args.seed, document)
    slots = placement.seed_slot_uids(manifest)
    orange_slots = slots.get(placement.BLUEKOCHAPPY_SOURCE, [])
    snow_slots = slots.get(placement.YELLOWKOCHAPPY_SOURCE, [])
    if not orange_slots or not snow_slots:
        raise SystemExit(f'seed must bind both sources 44 and 45; got {slots}')
    pairs = [(ORANGE_GENERATOR, orange_slots[0]), (SNOW_GENERATOR, snow_slots[0])]
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
    co_occurrence = validate_cooccurrence(text)
    _, _, probe_summary = p2_placement_probe.capture_markers(text)
    report = {
        'run': str(stage),
        'seed': args.seed,
        'arena_stage': placement.ARENA_STAGE,
        'sidecar_pairs': [[g, u] for g, u in pairs],
        'placement_lines': _lines(text, 'P2_PLACEMENT_SLOT'),
        'placement_probe_summary': probe_summary,
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
    (stage / 'cohort-seed-placement-report.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (args.output / 'latest-cohort-seed-placement-run.json').write_text(
        json.dumps({'run': str(stage), 'seed': args.seed}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
