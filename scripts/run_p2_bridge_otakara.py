"""Directive-012 live proof: a seed-bound generator spawns/binds the Otakara module.

Stages the FireOtakara (source 59) arena via lane 22's runtime, generates a REAL
seed on the admitted cohort (23/44/59-62, no admission injection), writes the
seed-derived placement sidecar for the arena generator and RENAMES the fixed
``p2-dweevil-actors.txt`` away, then boots the room with ``--randomizer-seed``.
The Otakara module must bind the generator purely from the seed
(``pc_randomizer_p2_source_for_70``), logging ``P2_OTAKARA_BIND source_id=59``
alongside ``P2_SEED_RESOLVE`` and ``P2_PLACEMENT_SLOT``.

Run only under the host GL slot:

    py -3.12 <repo>/output/deepseek-wave/slot.py run gl <lane> -- \\
        py -3.12 scripts/run_p2_bridge_otakara.py \\
            --assets <P1 assets> --imported <dweevil assets> \\
            --exe <nectar.exe> --output <out dir>
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import experimental.pikmin2_seed_placement as placement  # noqa: E402

FIRE_ID = 349001
FIRE_SOURCE = 59
ADMITTED_IDENTITIES = (
    'Sarai', 'BlueKochappy', 'FireOtakara', 'WaterOtakara', 'GasOtakara', 'ElecOtakara',
)


def _env():
    env = dict(os.environ)
    for entry in env.get('PATH', '').split(os.pathsep):
        if entry and (Path(entry) / 'SDL2.dll').exists():
            env['PATH'] = entry + os.pathsep + env.get('PATH', '')
            break
    else:
        fallback = Path('C:/msys64/mingw64/bin')
        if (fallback / 'SDL2.dll').exists():
            env['PATH'] = str(fallback) + os.pathsep + env.get('PATH', '')
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env['PYTHONUTF8'] = '1'
    env['SDL_AUDIODRIVER'] = 'dummy'
    env['PIKMIN_RANDOMIZER_TEST_BACKGROUND'] = '1'
    return env


def _startup():
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    return startup


def _lines(text, prefix):
    return [line.strip() for line in text.splitlines() if line.startswith(prefix + ' ')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--imported', type=Path, required=True)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=str, default='l03-bridge-otakara')
    parser.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()

    from experimental.pikmin2_otakara_runtime import prepare  # noqa: E402
    from randomizer import p2_placement_catalog as catalog  # noqa: E402
    from randomizer.seed import generate  # noqa: E402
    from randomizer.runner import NativeRun  # noqa: E402
    from randomizer.session import Session  # noqa: E402

    args.output.mkdir(parents=True, exist_ok=True)
    stage = prepare(args.assets.resolve(), args.imported.resolve(), args.output,
                    scenario='inject', species='FireOtakara')

    document = placement.placement_document(identities=ADMITTED_IDENTITIES,
                                            catalog_doc=catalog.build_document())
    manifest = generate(args.seed, p2_enemies=True, p2_placement=document)
    slots = placement.seed_slots(manifest, FIRE_SOURCE)
    if not slots:
        raise SystemExit(f'seed bound no slot to source {FIRE_SOURCE}')
    pairs = [(FIRE_ID, slots[0])]
    placement.write_sidecar(stage, pairs)

    # Prove the seed path: the fixed dweevil actor sidecar is renamed away, so the
    # Otakara module can only bind the generator through the ENEMY_P2 seed binding.
    fixed = stage / 'p2-dweevil-actors.txt'
    fixed_removed = False
    if fixed.exists():
        fixed.rename(fixed.with_name(fixed.name + '.disabled'))
        fixed_removed = True

    session = Session(manifest, stage / 'seed')
    run = NativeRun(session)
    bootstrap = run.bootstrap.resolve()

    log = stage / 'native.log'
    code = 'ok'
    with log.open('w', encoding='utf-8', errors='replace') as stream:
        try:
            subprocess.run([str(args.exe.resolve()), '--experimental-pikmin2-room',
                            '--randomizer-seed', str(bootstrap)],
                           cwd=stage, env=_env(), stdout=stream, stderr=subprocess.STDOUT,
                           startupinfo=_startup(), timeout=args.timeout)
        except subprocess.TimeoutExpired:
            code = 'timeout'
    text = log.read_text(encoding='utf-8', errors='replace')

    bind = _lines(text, 'P2_OTAKARA_BIND')
    report = {
        'run': str(stage),
        'seed': args.seed,
        'fixed_dweevil_sidecar_removed': fixed_removed,
        'sidecar_pairs': [[g, u] for g, u in pairs],
        'seed_binding_slots': slots,
        'otakara_bind': bind,
        'resolve_lines': _lines(text, 'P2_SEED_RESOLVE'),
        'placement_lines': _lines(text, 'P2_PLACEMENT_SLOT'),
        'ready_lines': _lines(text, 'P2_ENEMY_READY'),
        'bind_source_59': any(f'source_id={FIRE_SOURCE} ' in line for line in bind),
        'resolve_source_59': any(f'source_id={FIRE_SOURCE} ' in line
                                 for line in _lines(text, 'P2_SEED_RESOLVE')),
        'exit': code,
    }
    (stage / 'bridge-otakara-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (args.output / 'latest-bridge-otakara.json').write_text(json.dumps({'run': str(stage)}, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if not report['bind_source_59']:
        sys.exit(1)


if __name__ == '__main__':
    main()
