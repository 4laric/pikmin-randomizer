"""Lane-04 slice 2 runtime: stage a Dwarf Orange (BlueKochappy 44) arena,
write the catalog-join sidecar, and run the native placement probe against it.

This turns gate 1 into a real P2-identity spawn: lane-13's arena stager places a
native ``TEKI_Chappy`` with the BlueKochappy bank/health (id ``211001``) in the
original Impact Site map (practice = stage 0), and the native probe reports its
terrain/water/route evidence keyed by a REAL placement-catalog slot uid read
from the staged ``p2-placement-slots.txt`` sidecar. The chosen slot's catalog
stage is checked against the arena stage (stage 0) so evidence is never stamped
onto a different map.

Run only under the host GL slot:

    py -3.12 <repo>/output/deepseek-wave/slot.py run gl l04 -- \
        py -3.12 scripts/run_p2_catalog_placement.py \
            --assets <P1 assets> --bank <dwarf-orange bank dir> --profile <profile dir> \
            --exe <nectar.exe> --output <out dir>
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ARENA_STAGE = 0
SOURCE_GENERATOR = 211001


def _find_mingw():
    env = os.environ.get('MINGW_BIN')
    if env and (Path(env) / 'SDL2.dll').exists():
        return str(Path(env))
    for entry in os.environ.get('PATH', '').split(os.pathsep):
        if entry and (Path(entry) / 'SDL2.dll').exists():
            return entry
    fallback = Path(r'C:/msys64/mingw64/bin')
    return str(fallback) if (fallback / 'SDL2.dll').exists() else None


def choose_slot(catalog_doc, stage=ARENA_STAGE):
    """Pick a catalog slot whose stage matches the staged map (practice = stage 0).

    Restricted to the campaign ground cohort (the BlueKochappy host cohort); the
    earliest-activation slot by (first_day, uid) is chosen deterministically.
    """
    candidates = [s for s in catalog_doc['slots']
                  if s['stage'] == stage and s.get('cohort') == 'ground' and s['terrain'] == 'ground']
    if not candidates:
        raise SystemExit(f'no stage-{stage} ground-cohort catalog slot found')
    return min(candidates, key=lambda s: (s['first_day'], s['uid']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    from experimental.pikmin2_dwarf_orange_runtime import prepare  # noqa: E402
    from randomizer import p2_placement_probe  # noqa: E402
    from scripts.audit_p2_placement_evidence import run_audit, catalog_document  # noqa: E402

    args.output.mkdir(parents=True, exist_ok=True)
    stage = prepare(args.assets.resolve(), args.bank.resolve(), args.profile.resolve(), args.output)

    catalog_doc = catalog_document()
    chosen = choose_slot(catalog_doc, ARENA_STAGE)
    slot_uid = chosen['uid']
    (stage / 'p2-placement-slots.txt').write_text(
        f'P2_PLACEMENT_SLOTS_1\n{SOURCE_GENERATOR} {slot_uid}\n', encoding='ascii')

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
            subprocess.run([str(args.exe.resolve()), '--experimental-pikmin2-room'],
                           cwd=stage, env=env, stdout=stream, stderr=subprocess.STDOUT,
                           startupinfo=startup, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            code = 'timeout'

    text = log.read_text(encoding='utf-8', errors='replace')
    slots, window, summary = p2_placement_probe.capture_markers(text)
    probe = p2_placement_probe.build_probe(text)
    probe['arena_stage'] = ARENA_STAGE
    report = run_audit(probe, catalog_doc, arena_stage=ARENA_STAGE, allow_unmapped=True)

    identity_ready = [l.strip() for l in text.splitlines()
                      if l.startswith('P2_ENEMY_READY') and 'source_id=44' in l]
    evidence = {
        'run': str(stage), 'exit': code, 'window_marker': window,
        'room_ready': 'P2_ROOM_READY' in text or 'P2_ROOM_CARGO_FREE_READY' in text,
        'identity_ready': identity_ready,
        'probe_summary': summary,
        'slot_details': slots,
        'sidecar': f'{SOURCE_GENERATOR} -> {slot_uid}',
        'chosen_slot': {'uid': chosen['uid'], 'label': chosen['label'],
                        'stage': chosen['stage'], 'cohort': chosen.get('cohort'),
                        'terrain': chosen['terrain']},
    }
    (stage / 'probe.json').write_text(json.dumps(probe, indent=2) + '\n', encoding='utf-8')
    (stage / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    (stage / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (args.output / 'latest-catalog-run.json').write_text(
        json.dumps({'run': str(stage), 'slot_uid': slot_uid}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'run': str(stage), 'exit': code, 'slot_uid': slot_uid,
                      'arena_stage': ARENA_STAGE,
                      'catalog_join': report.get('catalog_join'),
                      'matched_slot_uids': report.get('matched_slot_uids'),
                      'unmapped_generators': report.get('unmapped_generators'),
                      'mapping': report.get('mapping'),
                      'evidence': evidence}, indent=2))


if __name__ == '__main__':
    main()
