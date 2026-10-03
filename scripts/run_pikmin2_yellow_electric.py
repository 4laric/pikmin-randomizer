"""Bounded staged Yellow electric contact and separate vulnerable Red control."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SOURCE_ROOT), str(SOURCE_ROOT / 'scripts')]
from scripts.stage_elecbug_contact_runtime import prepare
from scripts.run_elecbug_contact_runtime import contact_witness
from scripts.pikmin2_yellow_electric_witness import witness
from scripts.run_pikmin2_fixture import launch

WORKSPACE = SOURCE_ROOT.parent.parent if SOURCE_ROOT.parent.name == 'output' else SOURCE_ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--expected-exe-sha256', required=True)
    parser.add_argument('--content', type=Path, required=True)
    parser.add_argument('--assets', type=Path, default=Path(os.environ.get('APPDATA', Path.home())) / 'PikminRandomizer/game-data/assets')
    parser.add_argument('--mode', choices=('yellow-electric', 'red-electric'), default='yellow-electric')
    parser.add_argument('--captain-down', action='store_true')
    args = parser.parse_args()
    exe = args.exe.resolve(strict=True)
    if hashlib.sha256(exe.read_bytes()).hexdigest() != args.expected_exe_sha256.lower():
        parser.error('Executable differs from supplied reviewed fixture hash')
    run = WORKSPACE / 'output/p2-yellow-1263' / ('electric-' + uuid.uuid4().hex)
    prepare(args.assets.resolve(), args.content.resolve(), run)
    for key in list(os.environ):
        if key.upper().startswith(('PIKMIN_', 'P2_', 'BBFT_', 'NECTAR_', 'SDL_')):
            del os.environ[key]
    config = run / 'private-config'
    config.mkdir()
    save = run / 'private-save'
    save.mkdir()
    os.environ.update(PIKMIN_SETTINGS_PATH=str(config / 'pikmin-settings.ini'), NECTAR_SAVE_DIR=str(save), P2_ELECBUG_MODE=args.mode)
    if args.captain_down:
        os.environ['P2_ELECBUG_FORCE_CAPTAIN_DOWN'] = '1'
    print('Engineered ElecBug contact; Yellow is explicitly staged. Original acquisition/campaign/save untested.')
    print('Fresh evidence:', run, flush=True)
    marker = 'P2_FIXTURE_CAPTAIN_DOWN' if args.captain_down else 'P2_ELECBUG_CONTACT_CANDIDATE'
    result = launch(exe, run, ['--experimental-pikmin2-room'], [marker],
                    timeout=60, canonical_root=WORKSPACE, development_launch=os.name != 'nt')
    text = (run / 'native.log').read_text(encoding='utf-8', errors='replace') if (run / 'native.log').exists() else ''
    proof = witness(text) if args.mode == 'yellow-electric' else contact_witness(text, args.mode)
    expected_stop = (args.captain_down and result.get('exit_code') == 86 and marker in text
                     and 'PASS ' not in text and 'P2_ELECBUG_CONTACT_CANDIDATE' not in text)
    assessment = {'process': result, 'mode': args.mode, 'witness': proof,
                  'passed': bool(not args.captain_down and result.get('passed') and proof),
                  'expected_captain_stop': bool(expected_stop), 'original_acquisition': False,
                  'campaign_placement': False, 'save_resume': False}
    (run / 'electric-assessment.json').write_text(json.dumps(assessment, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(assessment, indent=2))
    return 0 if (expected_stop if args.captain_down else assessment['passed']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
