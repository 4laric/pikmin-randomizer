"""Imomushi (Ravenous Whiskerpillar, EnemyID 65) source-behavior acceptance (#165/#407).

Private batch-2 ground arena with Imomushi placed inside its source sight radius
(fp12=500) next to the 20-red fixture squad. The native `pc_p2_imomushi.cpp` runs
the Stay/Appear/Move/GoHome/Dive cycle (Fall/Dead on death) and prints
`P2_IMOMUSHI_*` markers. Plant-eating (getRandFruitsPlant/startClimbPlant/
eatTsuyukusa) is source-backed N/A: the arena stages no fruit-bearing plants.
"""
import argparse
import functools
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install
from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_sokkuri_behavior import normalize_pose_names

CFG = dict(FAMILIES['ground'])
IDS = tuple(CFG['arena_ids'])
IMOMUSHI_ID = 346003
SPECIES = tuple(CFG['arena_species'])
IMOMUSHI_INDEX = SPECIES.index('Imomushi')
DEFAULT_POSITIONS = tuple(((-(len(SPECIES) - 2) / 2 + index) * 120.0, 30.0, 1850.0)
                          for index in range(len(SPECIES) - 1)) + ((240.0, 30.0, 1500.0),)
BEHAVIOR_POSITION = (-100.0, 30.0, 1850.0)
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def prepare(assets, imported, output):
    cfg = dict(CFG)
    positions = list(DEFAULT_POSITIONS)
    positions[IMOMUSHI_INDEX] = BEHAVIOR_POSITION
    cfg['arena_positions'] = tuple(positions)
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    override = dict(index=IMOMUSHI_INDEX, species='Imomushi', generator=IMOMUSHI_ID,
                    arena_default=list(DEFAULT_POSITIONS[IMOMUSHI_INDEX]),
                    behavior_fixture=list(BEHAVIOR_POSITION),
                    reason='place Imomushi within the source fp12=500 sight radius of the '
                           'starting squad so the Stay/Appear/Move/GoHome/Dive cycle is observable',
                    production_placement=False,
                    pose_name_normalization=normalize_pose_names(run))
    (run / 'imomushi-override.json').write_text(json.dumps(override, indent=2) + '\n')
    return run


def run(assets, imported, output, exe, seconds=30):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'imomushi-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_IMOMUSHI_STATE generator=346003 state=(\w+)', text)
    positions = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(
        r'P2_IMOMUSHI_POS generator=346003 state=\w+ clip=\w+ phase=[\d.]+ x=(-?[\d.]+) z=(-?[\d.]+)', text)]
    spread = 0.0
    if len(positions) >= 2:
        spread = max(abs(x - positions[0][0]) + abs(z - positions[0][1]) for x, z in positions)
    checks = dict(
        identity=bool(re.search(r'P2_IMOMUSHI_BIND generator=346003 source_id=65 visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=Imomushi .*generator=346003 .*behavior=native '
                             r'.*source_FSM=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        appear='appear' in states,
        move='move' in states,
        gohome_or_dive=('gohome' in states or 'dive' in states),
        autonomous_motion=spread > 5.0,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(checks.values()), checks=checks, states=states,
                motion_spread=spread, exit_code=code,
                unmeasured=['plant-eating (getRandFruitsPlant/startClimbPlant/eatTsuyukusa): '
                            'no fruit-bearing plants staged (source-backed N/A)',
                            'Wait/Climb/Attack states (plant CollPart bound)',
                            'death/fall and corpse transport (requires a death source)',
                            'cleanup/re-entry'],
                limitations=['Behavior fixture overrides Imomushi arena coordinate; not production placement.',
                             'Wake is sight-of-Pikmin/Navi instead of source fruit-plant availability.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'run'):
        sub = commands.add_parser(name)
        for flag in ('assets', 'imported', 'output'):
            sub.add_argument('--' + flag, type=Path, required=True)
        if name == 'run':
            sub.add_argument('--exe', type=Path, required=True)
            sub.add_argument('--seconds', type=int, default=30)
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
