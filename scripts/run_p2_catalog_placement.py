"""Lane-04 slice 2 runtime: stage a Dwarf Orange (BlueKochappy 44) arena,
write the catalog-join sidecar, and run the native placement probe against it.

This turns gate 1 into a real P2-identity spawn: lane-13's arena stager places a
native ``TEKI_Chappy`` with the BlueKochappy bank/health (id ``211001``) in the
original Impact Site map, and the native probe reports its terrain/water/route
evidence keyed by a REAL placement-catalog slot uid read from the staged
``p2-placement-slots.txt`` sidecar.

Run only under the host GL slot:

    py -3.12 output/deepseek-wave/slot.py run gl l04 -- \
        py -3.12 scripts/run_p2_catalog_placement.py \
            --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets \
            --bank C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank \
            --profile C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref \
            --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l04-build/bin/nectar.exe \
            --output C:/Users/alari/pikmin-randomizer/output/dsw/l04-out
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ASSETS = Path(r'C:/Users/alari/bbft/dist/cohesion/pikmin/assets')
BANK = Path(r'C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank')
PROFILE = Path(r'C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref')
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


def choose_slot_uid():
    from randomizer import p2_placement_catalog as catalog
    doc = catalog.build_document()
    dwarf = [s for s in doc['slots'] if s.get('cohort') == 'dwarf']
    if not dwarf:
        raise SystemExit('no dwarf-cohort catalog slot found')
    return min(dwarf, key=lambda s: s['uid']), doc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=ASSETS)
    parser.add_argument('--bank', type=Path, default=BANK)
    parser.add_argument('--profile', type=Path, default=PROFILE)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    from experimental.pikmin2_dwarf_orange_runtime import prepare  # noqa: E402
    from randomizer import p2_placement_probe  # noqa: E402
    from scripts.audit_p2_placement_evidence import run_audit  # noqa: E402

    args.output.mkdir(parents=True, exist_ok=True)
    stage = prepare(args.assets.resolve(), args.bank.resolve(), args.profile.resolve(), args.output)

    chosen, catalog_doc = choose_slot_uid()
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
    report = run_audit(probe, catalog_doc)

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
                      'catalog_join': report.get('catalog_join'),
                      'matched_slot_uids': report.get('matched_slot_uids'),
                      'evidence': evidence}, indent=2))


if __name__ == '__main__':
    main()
