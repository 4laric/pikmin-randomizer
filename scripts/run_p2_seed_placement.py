"""Lane-04 slice 3 runtime: placement catalog drives the native probe via a seed.

Stages the Dwarf Orange (BlueKochappy 44) arena once, then for each requested
seed name resolves that seed's ``p2_layout`` (lane 03 bridge over lane 02's
admitted cohort + lane 04's catalog) to the catalog slot uid it bound to the
identity, writes that uid into the generator -> slot sidecar, and runs the
native placement probe. The report proves, from the native log:

1. the ``P2_PLACEMENT_SLOT slot=...`` marker equals the seed's chosen slot uid;
2. the audit's stage guard passed from the probe's embedded ``arena_stage``
   (no manual ``--stage``);
3. two different seeds emit different slot markers.

Run only under the host GL slot:

    py -3.12 output/deepseek-wave/slot.py run gl l04 -- \
        py -3.12 scripts/run_p2_seed_placement.py \
            --assets <P1 assets> --bank <dwarf-orange bank> --profile <profile dir> \
            --exe <nectar.exe> --output <out dir> --seed seed-slice3-a --seed seed-slice3-b
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import experimental.pikmin2_seed_placement as placement


def _find_mingw():
    env = os.environ.get('MINGW_BIN')
    if env and (Path(env) / 'SDL2.dll').exists():
        return str(Path(env))
    for entry in os.environ.get('PATH', '').split(os.pathsep):
        if entry and (Path(entry) / 'SDL2.dll').exists():
            return entry
    fallback = Path(r'C:/msys64/mingw64/bin')
    return str(fallback) if (fallback / 'SDL2.dll').exists() else None


def _run_native(exe, stage, timeout):
    env = dict(os.environ)
    mingw = _find_mingw()
    if mingw:
        env['PATH'] = mingw + os.pathsep + env.get('PATH', '')
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env['PYTHONUTF8'] = '1'
    env['SDL_AUDIODRIVER'] = 'dummy'
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    log = stage / 'native.log'
    code = 'ok'
    with log.open('w', encoding='utf-8', errors='replace') as stream:
        try:
            subprocess.run([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
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
    parser.add_argument('--seed', type=str, action='append', required=True,
                        help='seed name to bind and probe (repeatable)')
    parser.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experimental.pikmin2_dwarf_orange_runtime import prepare  # noqa: E402
    from randomizer import p2_placement_probe  # noqa: E402
    from randomizer import p2_placement_catalog  # noqa: E402
    from scripts.audit_p2_placement_evidence import run_audit  # noqa: E402
    args.output.mkdir(parents=True, exist_ok=True)
    stage = prepare(args.assets.resolve(), args.bank.resolve(), args.profile.resolve(), args.output)

    catalog_doc = p2_placement_catalog.build_document()
    document = placement.placement_document(catalog_doc=catalog_doc)

    results = []
    for seed_name in args.seed:
        manifest = placement.generate_admitted_seed(seed_name, document)
        seed_uid = placement.seed_slot_uid(manifest, placement.BLUEKOCHAPPY_SOURCE)
        placement.write_sidecar(stage, placement.ARENA_SOURCE_GENERATOR, seed_uid)
        log, code = _run_native(args.exe, stage, args.timeout)
        text = log.read_text(encoding='utf-8', errors='replace')
        probe = p2_placement_probe.build_probe(text)
        probe['arena_stage'] = placement.ARENA_STAGE
        report = run_audit(probe, catalog_doc, allow_unmapped=True)
        marker_slot = probe['mapping'][0]['slot'] if probe['mapping'] else None
        results.append({
            'seed': seed_name,
            'seed_slot_uid': seed_uid,
            'marker_slot': marker_slot,
            'slot_matches_seed': marker_slot == seed_uid,
            'stage_guard_passed': report.get('arena_stage') == placement.ARENA_STAGE
                                  and seed_uid in report.get('matched_slot_uids', []),
            'catalog_join': report.get('catalog_join'),
            'malformed_markers': probe.get('malformed_markers', 0),
            'unmapped_generators': report.get('unmapped_generators'),
            'exit': code,
        })
        # Keep the seed-specific log beside the shared stage dir.
        (args.output / f'seed-{seed_name}.log').write_text(text, encoding='utf-8')

    distinct = len({row['seed_slot_uid'] for row in results})
    all_match = all(row['slot_matches_seed'] for row in results)
    all_stage_ok = all(row['stage_guard_passed'] for row in results)
    summary = {
        'run': str(stage),
        'arena_stage': placement.ARENA_STAGE,
        'results': results,
        'distinct_slots': distinct,
        'all_markers_match_seed': all_match,
        'all_stage_guards_passed': all_stage_ok,
    }
    (args.output / 'seed-placement-report.json').write_text(
        json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
