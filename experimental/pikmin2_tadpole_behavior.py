"""Tadpole (Wogpole, EnemyID 27) source-behavior acceptance (#167/#374/#407).

Builds the private batch-3 aquatic arena from ``experimental.pikmin2_aquatic_arena``
(374002 Tadpole at x=-120, z=1850 next to the engine-added 20-red starting squad
at x in [-140,-68], z in [1812,1820]) and runs the native
``pc_port/pc_p2_tadpole.cpp`` FSM, which prints ``P2_TADPOLE_*`` markers.
``validate()`` checks only those source-behavior markers; no disc assets, build or
player save is touched here. The fixture is not run by the unit tests.
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_aquatic_arena import prepare as _prepare

TADPOLE_ID = 374002
TADPOLE_POS = (-120.0, 30.0, 1850.0)
SIGHT = 200.0  # source general fp12
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def normalize_pose_names(run):
    """Copy misindexed aquatic pose files to the contiguous names the native
    batch-3 bank loader reconstructs.

    The converter names each pose by its sample index; when a sampled frame fails
    to convert, the remaining indices are non-contiguous and the loader (which
    expects ``_00.._(n-1)`` for the bank's pose count) aborts on a missing
    ``aquatic_<species>_<clip>_NN.mod``. This is a private fixture normalization
    only; no shared converter, install receipt or committed asset is changed.
    """
    room = run / 'assets/dataDir/courses/pikmin2room'
    bank = (run / 'p2-aquatic-bank.txt').read_text().splitlines()
    normalized = []
    for line in bank:
        tokens = line.split()
        if not tokens or tokens[0] != 'clip':
            continue
        species, clip, poses = tokens[1], tokens[2], int(tokens[6])
        for index in range(poses):
            expected = room / f'aquatic_{species}_{clip}_{index:02d}.mod'
            if expected.exists():
                continue
            candidates = sorted(room.glob(f'aquatic_{species}_{clip}_*.mod'))
            if not candidates:
                continue
            expected.write_bytes(candidates[0].read_bytes())
            normalized.append(dict(species=species, clip=clip, index=index,
                                   source=candidates[0].name, target=expected.name))
    return normalized


def prepare(assets, imported, output):
    run = _prepare(Path(assets), Path(imported), Path(output))
    override = dict(species='Tadpole', generator=TADPOLE_ID,
                    arena_default=list(TADPOLE_POS),
                    behavior_fixture='arena default (no override needed; squad is adjacent)',
                    reason='the aquatic arena already stages Tadpole at x=-120, z=1850 next to '
                           'the 20-red starting squad inside the source fp12=200 sight radius',
                    production_placement=False,
                    pose_name_normalization=normalize_pose_names(run))
    (run / 'tadpole-override.json').write_text(json.dumps(override, indent=2) + '\n')
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
    (run_dir / 'tadpole-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    """Check the native log against the source Tadpole FSM contract.

    Confined to ``P2_TADPOLE_*`` / batch-3 bind markers so it makes no claim
    about unrelated families or about production placement.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    positions = [(m.group(1), m.group(2), float(m.group(3)), float(m.group(4)), float(m.group(6)))
                 for m in re.finditer(
        r'P2_TADPOLE_POS generator=374002 state=(\w+) clip=(\w+) phase=([\d.]+) '
        r'x=(-?[\d.]+) y=(-?[\d.]+) z=(-?[\d.]+)', text)]
    states = {p[0] for p in positions}
    states |= set(re.findall(r'P2_TADPOLE_STATE generator=374002 state=(\w+)', text))
    spread = 0.0
    if len(positions) >= 2:
        x0, z0 = positions[0][3], positions[0][4]
        spread = max(abs(x - x0) + abs(z - z0) for _, _, _, x, z in positions)
    clips_seen = {p[1] for p in positions}
    checks = dict(
        identity=bool(re.search(r'P2_TADPOLE_BIND generator=374002 source_id=27 visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=Tadpole .*generator=374002 .*behavior=native '
                             r'.*source_FSM=implemented', text)),
        batch3_bind=bool(re.search(r'P2_BATCH3_BIND generator=374002 key=aquatic\|Tadpole '
                                   r'visual_only=0 native_fsm=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        idle_or_move=('wait' in states or 'move' in states),
        leap='leap' in states,
        autonomous_motion=len(positions) >= 2 and spread > 5.0,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(checks.values()), checks=checks, motion_spread=spread,
                states_seen=sorted(states), clips_seen=sorted(clips_seen),
                sampled_positions=len(positions), exit_code=code,
                unmeasured=['natural controller play', 'P1 water box / true MoveWater gate',
                            'source Amaze non-damaging panic flick (declared N/A)',
                            'corpse carry/delivery receipt'],
                limitations=['No arena override: the aquatic arena already stages Tadpole inside the '
                             'source sight radius; still engineered placement, not production evidence.',
                             'The P1 host has no water box, so the source dry-land Leap fallback is '
                             'deferred to each state animation end; the vertical hop is a port value.',
                             'Tadpole is harmless: attacks/receivers are source-backed N/A.'])


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
