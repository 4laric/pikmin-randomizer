"""TamagoMushi (Mitite, EnemyID 68) source-behavior acceptance (#165/#407).

Private batch-2 ground arena with TamagoMushi placed next to the 20-red fixture
squad. The native `pc_p2_tamago.cpp` runs Walk/Hide/Appear/Wait and the
collision Astonish receiver, and prints `P2_TAMAGO_*` markers.
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
TAMAGO_ID = 346004
SPECIES = tuple(CFG['arena_species'])
TAMAGO_INDEX = SPECIES.index('TamagoMushi')
DEFAULT_POSITIONS = tuple(((-(len(SPECIES) - 2) / 2 + index) * 120.0, 30.0, 1850.0)
                          for index in range(len(SPECIES) - 1)) + ((240.0, 30.0, 1500.0),)
BEHAVIOR_POSITION = (-100.0, 30.0, 1850.0)
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def prepare(assets, imported, output):
    cfg = dict(CFG)
    positions = list(DEFAULT_POSITIONS)
    positions[TAMAGO_INDEX] = BEHAVIOR_POSITION
    cfg['arena_positions'] = tuple(positions)
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    override = dict(index=TAMAGO_INDEX, species='TamagoMushi', generator=TAMAGO_ID,
                    arena_default=list(DEFAULT_POSITIONS[TAMAGO_INDEX]),
                    behavior_fixture=list(BEHAVIOR_POSITION),
                    reason='place TamagoMushi next to the starting squad so the walk cycle and '
                           'the collision Astonish receiver are observable',
                    production_placement=False,
                    pose_name_normalization=normalize_pose_names(run))
    (run / 'tamago-override.json').write_text(json.dumps(override, indent=2) + '\n')
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
    (run_dir / 'tamago-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_TAMAGO_STATE generator=346004 state=(\w+)', text)
    astonish = re.findall(r'P2_TAMAGO_ASTONISH generator=346004 pikmin=1', text)
    positions = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(
        r'P2_TAMAGO_POS generator=346004 state=\w+ clip=\w+ phase=[\d.]+ x=(-?[\d.]+) z=(-?[\d.]+)', text)]
    spread = 0.0
    if len(positions) >= 2:
        spread = max(abs(x - positions[0][0]) + abs(z - positions[0][1]) for x, z in positions)
    checks = dict(
        identity=bool(re.search(r'P2_TAMAGO_BIND generator=346004 source_id=68 visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=TamagoMushi .*generator=346004 .*behavior=native '
                             r'.*source_FSM=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        appear='appear' in states,
        hide='hide' in states,
        walk='walk' in states,
        astonish_receiver=len(astonish) >= 1,
        autonomous_motion=spread > 5.0,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(checks.values()), checks=checks, astonish=len(astonish),
                motion_spread=spread, exit_code=code,
                unmeasured=['manager-owned group birth (createGroup 10/30)',
                            'true InteractAstonish panic state (P1 has no Astonish)',
                            'honey reward (requires a death source)', 'death/transport/cleanup'],
                limitations=['Behavior fixture overrides TamagoMushi arena coordinate; not production placement.',
                             'Astonish is resolved as an InteractFlick knockback once per contact.'])


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
