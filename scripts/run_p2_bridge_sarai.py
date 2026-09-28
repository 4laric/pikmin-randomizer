"""Directive-012 live proof: a seed-bound generator spawns/binds the Sarai module.

Stages a Chappy room generator via lane 22's arena runtime, generates a REAL seed
on the admitted cohort (no admission injection), writes the seed-derived placement
sidecar mapping the arena generator to a slot the seed bound to Sarai (23), renames
the fixed family actor sidecars away, copies lane 30's staged Sarai banks + model
into the run, and boots the room with ``--randomizer-seed`` and
``PIKMIN_SARAI_ORDINARY=1``. The Sarai module must bind the generator purely from
the seed (the birth-time ``pc_p2_generated_placement_bind`` dispatcher), logging ``P2_SARAI_READY source_id=23`` with
``resolution=seed``.

Run only under the host GL slot:

    py -3.12 <repo>/output/deepseek-wave/slot.py run gl <lane> -- \\
        py -3.12 scripts/run_p2_bridge_sarai.py \\
            --assets <P1 assets> --imported <dweevil assets> --sarai-source <lane30 run> \\
            --exe <nectar.exe> --output <out dir>
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import experimental.pikmin2_seed_placement as placement  # noqa: E402

ARENA_ID = 349001
SARAI_SOURCE = 23
SARAI_FILES = (
    'sarai-attack-mouths.txt', 'sarai-attack-poses.txt', 'sarai-move-poses.txt',
    'sarai-retail-events.txt', 'sarai-wait-poses.txt', 'sarai-waitact1-poses.txt',
    'sarai-waitact2-poses.txt',
)
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
    env['PIKMIN_SARAI_ORDINARY'] = '1'
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
    parser.add_argument('--sarai-source', type=Path, required=True)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=str, default='l03-bridge-sarai')
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
    slots = placement.seed_slots(manifest, SARAI_SOURCE)
    if not slots:
        raise SystemExit(f'seed bound no slot to source {SARAI_SOURCE}')
    pairs = [(ARENA_ID, slots[0])]
    placement.write_sidecar(stage, pairs)

    # Prove the seed path: rename every fixed family actor sidecar away, so only
    # the Sarai module's seed-driven selection can bind the Chappy anchor.
    fixed_removed = []
    for name in ('p2-dweevil-actors.txt', 'p2-dwarf-orange-actors.txt', 'p2-snow-actors.txt'):
        path = stage / name
        if path.exists():
            path.rename(path.with_name(path.name + '.disabled'))
            fixed_removed.append(name)

    # Copy lane 30's staged Sarai banks + model + every pose mesh into the run.
    src = args.sarai_source.resolve()
    for name in SARAI_FILES:
        source = src / name
        if not source.is_file():
            raise SystemExit(f'missing Sarai bank: {source}')
        shutil.copyfile(source, stage / name)
    room_src = src / 'assets/dataDir/courses/pikmin2room'
    room_dst = stage / 'assets/dataDir/courses/pikmin2room'
    model_src = room_src / 'sarai0.mod'
    if not model_src.is_file():
        raise SystemExit(f'missing Sarai model: {model_src}')
    # `wait1_0000.mod` etc. are the sampled pose meshes the banks reference; the
    # room's own room.mod/room.ini/treasure.mod stay from the arena staging.
    mesh_count = 0
    for mesh in sorted(room_src.glob('*.mod')):
        if mesh.name in ('room.mod', 'treasure.mod'):
            continue
        shutil.copyfile(mesh, room_dst / mesh.name)
        mesh_count += 1

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

    ready = _lines(text, 'P2_SARAI_READY')
    generated = _lines(text, 'P2_GENERATED_PLACEMENT')
    report = {
        'run': str(stage),
        'seed': args.seed,
        'fixed_sidecars_removed': fixed_removed,
        'pose_meshes_copied': mesh_count,
        'sidecar_pairs': [[g, u] for g, u in pairs],
        'seed_binding_slots': slots,
        'sarai_ready': ready,
        'generated_placement_lines': generated,
        'resolve_lines': _lines(text, 'P2_SEED_RESOLVE'),
        'placement_lines': _lines(text, 'P2_PLACEMENT_SLOT'),
        'sarai_ready_source_23': any('source_id=23 ' in line for line in ready),
        # The surviving owner is the wave's birth-time dispatcher
        # (`P2_GENERATED_PLACEMENT ... bound=1`, and the host `generated=1`);
        # lane-03's superseded setup marker was `resolution=seed`.
        'sarai_seed_bound': (
            any(('generated=1' in line or 'resolution=seed' in line) for line in ready)
            or any('source_id=23 ' in line and 'bound=1' in line for line in generated)
        ),
        'exit': code,
    }
    (stage / 'bridge-sarai-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (args.output / 'latest-bridge-sarai.json').write_text(json.dumps({'run': str(stage)}, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if not report['sarai_seed_bound']:
        sys.exit(1)


if __name__ == '__main__':
    main()
