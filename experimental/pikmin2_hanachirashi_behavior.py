"""Hanachirashi (Withering Blowhog, EnemyID 55) source-behavior acceptance
(#407/#166).

Builds the private batch-3 flying arena (Mar + Hanachirashi + P1 control) via
`experimental.pikmin2_flying_arena.prepare`. The arena stages Hanachirashi at
(-50, 30, 1850), about 35 units from the 20-red fixture squad, so the source
sight radius (fp12=275) is satisfied without a behavior-fixture position
override. The native `pc_port/pc_p2_hanachirashi.cpp` drives the bounded source
FSM Wait -> Move/Chase -> Attack (withering InteractFlick at the attack
KEYEVENT_2) -> Laugh -> Wait and prints `P2_HANACHIRASHI_*` markers;
`validate()` checks only those markers plus the batch-3 bind/ready lines, and
makes no claim about other families.
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_flying_arena import prepare

HANA_ID = 375002
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))
HANA_POSITION = (-50.0, 30.0, 1850.0)
SIGHT = 275.0


def normalize_pose_names(run):
    """Copy misindexed pose files to the contiguous names the native bank loader
    reconstructs.

    The converted flying bank may name a clip's first pose `_01` where the
    native loader expects `_00`. This is a private fixture normalization only;
    no shared converter, install receipt or committed asset is changed.
    """
    room = run / 'assets/dataDir/courses/pikmin2room'
    bank = (run / 'p2-flying-bank.txt').read_text().splitlines()
    normalized = []
    for line in bank:
        tokens = line.split()
        if not tokens or tokens[0] != 'clip':
            continue
        species, clip, poses = tokens[1], tokens[2], int(tokens[6])
        for index in range(poses):
            expected = room / f'fly_{species}_{clip}_{index:02d}.mod'
            if expected.exists():
                continue
            candidates = sorted(room.glob(f'fly_{species}_{clip}_*.mod'))
            if not candidates:
                continue
            expected.write_bytes(candidates[0].read_bytes())
            normalized.append(dict(species=species, clip=clip, index=index,
                                   source=candidates[0].name, target=expected.name))
    return normalized


def run(assets, imported, output, exe, seconds=30):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    override = dict(species='Hanachirashi', generator=HANA_ID,
                    arena_default=list(HANA_POSITION), behavior_fixture=None,
                    reason='batch-3 flying arena already stages Hanachirashi within '
                           'fp12=275 of the fixture squad; no behavior position override '
                           'applied',
                    production_placement=False,
                    pose_name_normalization=normalize_pose_names(run_dir))
    (run_dir / 'hanachirashi-override.json').write_text(json.dumps(override, indent=2) + '\n')
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'hanachirashi-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_HANACHIRASHI_STATE generator=375002 state=(\w+)', text)
    blows = [int(n) for n in re.findall(
        r'P2_HANACHIRASHI_BLOW generator=375002 pikmin=(\d+)', text)]
    positions = [(m.group(1), m.group(2), float(m.group(3)), float(m.group(4)), float(m.group(5)))
                 for m in re.finditer(
        r'P2_HANACHIRASHI_POS generator=375002 state=(\w+) clip=(\w+) phase=([\d.]+) '
        r'x=(-?[\d.]+) z=(-?[\d.]+)', text)]
    spread = 0.0
    if len(positions) >= 2:
        x0, z0 = positions[0][3], positions[0][4]
        spread = max(abs(x - x0) + abs(z - z0) for _, _, _, x, z in positions)
    clips_seen = {p[1] for p in positions}
    checks = dict(
        identity=bool(re.search(r'P2_HANACHIRASHI_BIND generator=375002 source_id=55 '
                                r'visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=Hanachirashi native_family=Mar '
                             r'generator=375002 .*behavior=native .*source_FSM=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        wait='wait' in states,
        chase='chase' in states,
        attack='attack' in states,
        laugh='laugh' in states,
        blow=bool(blows) and all(n >= 1 for n in blows),
        blow_pikmin=(blows[0] if blows else 0),
        state_fsm={'wait', 'chase', 'attack'} <= set(states),
        autonomous_motion=spread > 5.0,
        animation=len(clips_seen) >= 2,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(v for k, v in checks.items()
                           if k not in ('blow_pikmin',)),
                checks=checks, motion_spread=spread, states_seen=sorted(set(states)),
                clips_seen=sorted(clips_seen), blow_events=blows,
                sampled_positions=len(positions), exit_code=code,
                unmeasured=['Fall/Land/Ground/TakeOff/FlyFlick/GroundFlick (stuck-Pikmin '
                            'counter not simulated on the P1 host)',
                            'P2 InteractHanaChirashi receiver (invincible/KokeDamage states, '
                            'wither BlowStateArg)',
                            'source ramped mWindScaleTimer wind radius (single-frame port)',
                            'ChaseInside and source FOV/view-angle search',
                            'full source wav/tex effect bank', 'cleanup/re-entry'],
                limitations=['Batch-3 flying arena placement is engineered fixture evidence, '
                             'not production placement evidence.',
                             'Withering wind is resolved as a single InteractFlick blow/stagger '
                             'at the source attack KEYEVENT_2 frame; the P1 engine has no '
                             'InteractWind/InteractHanaChirashi. Purple bud/flower receivers in '
                             'the cone are stripped to Leaf instead of being blown.'])


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
