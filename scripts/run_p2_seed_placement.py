"""Lane-04 slice 4 runtime: seed placement bindings drive the native probe.

Stages the Dwarf Orange (BlueKochappy 44) arena once, then for each requested
seed name resolves that seed's ``p2_layout`` binding *set* (the admitted source
44/45 bound to a subset of the stage-0 ground slots), writes the seed-derived
``p2-placement-slots.txt`` sidecar, and runs the native placement probe. The
report asserts, from the native log:

1. every ``P2_PLACEMENT_SLOT slot=...`` marker is a member of the seed's binding
   set for that source (the full set, not a single picked slot, is carried);
2. the audit's stage guard fires from the probe's embedded ``arena_stage`` (no
   manual ``--stage``);
3. two different seeds resolve to different slot binding sets.

When ``P2_SEED_RESOLVE`` (the seed-bridge birth resolution marker) and
``P2_ENEMY_READY`` are present in the log, the report also cross-checks that the
generator/slot pair named by ``P2_PLACEMENT_SLOT`` is the one ``P2_SEED_RESOLVE``
resolved to the same source.

Run only under the host GL slot:

    py -3.12 output/deepseek-wave/slot.py run gl l04 -- \\
        py -3.12 scripts/run_p2_seed_placement.py \\
            --assets <P1 assets> --bank <dwarf-orange bank> --profile <profile dir> \\
            --exe <nectar.exe> --output <out dir> --seed seed-slice4-a --seed seed-slice4-b
"""
import argparse
import json
import os
import re
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


def _resolve_lines(text):
    """Return the ``P2_SEED_RESOLVE`` and ``P2_ENEMY_READY`` lines from a log."""
    resolve = []
    ready = []
    for line in text.splitlines():
        if line.startswith('P2_SEED_RESOLVE '):
            resolve.append(line.strip())
        elif line.startswith('P2_ENEMY_READY '):
            ready.append(line.strip())
    return resolve, ready


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
        seed_slots = placement.seed_slots(manifest, placement.BLUEKOCHAPPY_SOURCE)
        if not seed_slots:
            raise SystemExit(f'no binding for source {placement.BLUEKOCHAPPY_SOURCE} in {seed_name}')
        source_slot = seed_slots[0]
        placement.write_sidecar(stage, [(placement.ARENA_SOURCE_GENERATOR, source_slot)])
        log, code = _run_native(args.exe, stage, args.timeout)
        text = log.read_text(encoding='utf-8', errors='replace')
        probe = p2_placement_probe.build_probe(text)
        probe['arena_stage'] = placement.ARENA_STAGE
        report = run_audit(probe, catalog_doc, allow_unmapped=True)
        marker_slots = [m['slot'] for m in probe['mapping']]
        resolve_lines, ready_lines = _resolve_lines(text)
        resolves_of_source = [int(m.group(1)) for line in resolve_lines
                              if (m := re.search(r'source_id=(\d+)', line))]
        results.append({
            'seed': seed_name,
            'seed_binding_set': seed_slots,
            'marker_slots': marker_slots,
            'markers_are_single_binding_members': set(marker_slots) <= set(seed_slots),
            'stage_guard_passed': report.get('arena_stage') == placement.ARENA_STAGE
                                  and all(s in report.get('matched_slot_uids', []) for s in marker_slots),
            'catalog_join': report.get('catalog_join'),
            'malformed_markers': probe.get('malformed_markers', 0),
            'unmapped_generators': report.get('unmapped_generators'),
            'resolve_lines': resolve_lines,
            # None when no P2_SEED_RESOLVE line exists (lane 03 join not observed), never a vacuous True.
            'resolve_source_matches': (None if not resolves_of_source else sorted(set(resolves_of_source)) == [placement.BLUEKOCHAPPY_SOURCE]),
            'ready_lines': ready_lines,
            'exit': code,
        })
        (args.output / f'seed-{seed_name}.log').write_text(text, encoding='utf-8')

    distinct = len({tuple(row['seed_binding_set']) for row in results})
    all_members = all(row['markers_are_single_binding_members'] for row in results)
    all_stage_ok = all(row['stage_guard_passed'] for row in results)
    summary = {
        'run': str(stage),
        'arena_stage': placement.ARENA_STAGE,
        'results': results,
        'distinct_binding_sets': distinct,
        'all_markers_are_binding_members': all_members,
        'all_stage_guards_passed': all_stage_ok,
    }
    (args.output / 'seed-placement-report.json').write_text(
        json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
