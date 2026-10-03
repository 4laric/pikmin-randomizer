"""Fresh, bounded Blue rescue check on the imported tutorial shoreline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))
from scripts.stage_pikmin2_surface_water import prepare
from scripts.run_pikmin2_fixture import launch

WORKSPACE = SOURCE_ROOT.parent.parent if SOURCE_ROOT.parent.name == 'output' else SOURCE_ROOT
IDENTITY = 'c8598f04bb884ab396d126b8dfbed6a6ce78d2f6afc92e7b366a5e5c11ccc8d5'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--expected-exe-sha256', required=True)
    parser.add_argument('--assets', type=Path, default=Path(os.environ.get('APPDATA', Path.home()))/'PikminRandomizer/game-data/assets')
    parser.add_argument('--bundle', type=Path, default=WORKSPACE/'output/p2-level-imports/tutorial-09')
    parser.add_argument('--mode', choices=['human', 'startup', 'automatic', 'captain-down'], default='human')
    args = parser.parse_args()
    exe = args.exe.resolve(strict=True)
    if hashlib.sha256(exe.read_bytes()).hexdigest() != args.expected_exe_sha256.lower():
        parser.error('Executable differs from the reviewed Blue rescue build')
    output = WORKSPACE/'output/p2-blue-rescue'/('check-'+uuid.uuid4().hex)
    run = prepare(args.assets.resolve(), args.bundle.resolve(), IDENTITY, output, species_probe=True)
    for key in list(os.environ):
        if key.startswith(('PIKMIN_RANDOMIZER_', 'P2_SURFACE_WATER_', 'P2_FULL_SURFACE_')):
            del os.environ[key]
    markers = {'human': 'READY P2_SURFACE_WATER_HUMAN_SMOKE',
               'startup': 'PASS P2_SURFACE_WATER_HUMAN_AUTO_STARTUP',
               'automatic': 'PASS P2_BLUE_RESCUE_RUNTIME',
               'captain-down': 'P2_FIXTURE_CAPTAIN_DOWN'}
    if args.mode in ('human', 'startup'):
        os.environ['P2_SURFACE_WATER_HUMAN_SMOKE'] = '1'
    if args.mode == 'startup':
        os.environ['P2_SURFACE_WATER_HUMAN_AUTO_STARTUP'] = '1'
    if args.mode == 'captain-down':
        os.environ['P2_SURFACE_WATER_FORCE_CAPTAIN_DOWN'] = '1'
    if args.mode == 'human':
        print('Blue rescue: 19 Red and one Blue are staged; eighteen Reds wait on the bank.')
        print('Whistle the nearby Red and Blue (Shift/controller B), then walk east down the slope toward the pool.')
        print('When the Red struggles, stop whistling and disband using your configured disband key/controller action.')
        print('Watch the Blue hold and throw the Red. Confirm a living dry landing, then recall all twenty.')
        print('This checks staged rescue, not natural Blue acquisition or campaign/save acceptance.')
        print('The centered 960x540 game stops after 60 seconds. Human judgment is recorded separately.')
    print('Fresh run evidence:', run, flush=True)
    result = launch(exe, run, ['--experimental-pikmin2-surface', 'tutorial'],
                    [markers[args.mode]], timeout=60, canonical_root=WORKSPACE,
                    development_launch=os.name != 'nt')
    print(json.dumps(result, indent=2))
    if args.mode == 'captain-down':
        text = (run/'native.log').read_text(encoding='utf-8', errors='replace') if (run/'native.log').exists() else ''
        expected = result.get('exit_code') == 86 and 'P2_FIXTURE_CAPTAIN_DOWN' in text and 'PASS ' not in text
        (run/'negative-assessment.json').write_text(json.dumps({'expected_stop': expected}, indent=2)+'\n')
        return 0 if expected else 1
    if args.mode == 'human':
        text = (run/'native.log').read_text(encoding='utf-8', errors='replace') if (run/'native.log').exists() else ''
        ready = markers['human'] in text
        acceptable_stop = result.get('timed_out') or result.get('exit_code') == 0
        guard = 'P2_FIXTURE_CAPTAIN_DOWN' in text
        (run/'manual-assessment.json').write_text(json.dumps(dict(
            ready=ready, captain_down=guard, human_judgment_recorded=False,
            gameplay_pass=False), indent=2)+'\n')
        return 0 if ready and acceptable_stop and not guard else 1
    return 0 if result.get('passed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
