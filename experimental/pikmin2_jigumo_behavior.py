"""Jigumo (Hermit Crawmad, EnemyID 63) source-behavior acceptance (#167/#407).

Builds the private batch-3 aquatic arena from
``experimental.pikmin2_aquatic_arena`` (374003 Jigumo at x=0, z=1850, inside
the source fp12=400 sight radius and source fp20=200 attack radius of the
engine-added 20-red starting squad at x in [-140,-68], z in [1812,1820]) and
runs the native ``pc_port/pc_p2_jigumo.cpp`` FSM, which prints ``P2_JIGUMO_*``
markers. The arena default already stages Jigumo near the squad, so no
coordinate override is needed; the decision and distance are recorded in
``jigumo-override.json``. ``validate()`` checks only the ``P2_JIGUMO_*``
source-behavior markers. The fixture is not run by the unit tests.
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_aquatic_arena import prepare as _prepare
import experimental.pikmin2_aquatic_arena as arena
from experimental.pikmin2_tadpole_behavior import normalize_pose_names

JIGUMO_ID = 374003
JIGUMO_INDEX = arena.SPECIES.index('Jigumo')
ARENA_DEFAULT = tuple(arena.POSITIONS[JIGUMO_INDEX])
BEHAVIOR_POS = ARENA_DEFAULT
SATTACK_BITE_FRAME = 13.0      # source Jigumo::Parms mSAttackActiveFrame (Jigumo.h:133)
ATTACK_BITE_FRAME = 26.0       # source attack1 animation key event 2
SATTACK_SWALLOW_FRAME = 115.0  # source sattack1 animation key event 10
ATTACK_SWALLOW_FRAME = 80.0    # source dive1 animation key event 8
SOURCE_BITE_FRAMES = (SATTACK_BITE_FRAME, ATTACK_BITE_FRAME)
ATTACK_RANGE = 200.0  # source general fp20
SIGHT = 400.0  # source general fp12
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def squad_distance(position):
    return min((position[0] - x) ** 2 + (position[2] - z) ** 2
               for x in SQUAD_X for z in SQUAD_Z) ** 0.5


def prepare(assets, imported, output):
    run = _prepare(Path(assets), Path(imported), Path(output))
    distance = squad_distance(BEHAVIOR_POS)
    override = dict(species='Jigumo', generator=JIGUMO_ID,
                    arena_default=list(ARENA_DEFAULT),
                    behavior_fixture='arena default (no override needed; squad is adjacent)',
                    reason='the aquatic arena already stages Jigumo at x=0, z=1850, %.1f units '
                           'from the 20-red starting squad: inside the source fp12=400 sight '
                           'radius and inside the source fp20=200 attack radius, so no coordinate '
                           'override is needed' % distance,
                    production_placement=False,
                    pose_name_normalization=normalize_pose_names(run))
    (run / 'jigumo-override.json').write_text(json.dumps(override, indent=2) + '\n')
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
    (run_dir / 'jigumo-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    """Check the native log against the source Jigumo FSM contract.

    Confined to ``P2_JIGUMO_*`` / batch-3 bind markers so it makes no claim
    about unrelated families or about production placement.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_JIGUMO_STATE generator=374003 state=(\w+)', text)
    bites = re.findall(r'P2_JIGUMO_BITE generator=374003 frame=([\d.]+) pikmin=1', text)
    eats = re.findall(r'P2_JIGUMO_EAT generator=374003 pikmin=1', text)
    frames = [float(f) for f in bites]
    bite_in_window = bool(frames) and all(f in SOURCE_BITE_FRAMES for f in frames)
    positions = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(
        r'P2_JIGUMO_POS generator=374003 state=\w+ clip=\w+ phase=[\d.]+ '
        r'x=(-?[\d.]+) y=-?[\d.]+ z=(-?[\d.]+)', text)]
    spread = 0.0
    if len(positions) >= 2:
        spread = max(abs(x - positions[0][0]) + abs(z - positions[0][1]) for x, z in positions)
    checks = dict(
        identity=bool(re.search(r'P2_JIGUMO_BIND generator=374003 source_id=63 visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=Jigumo .*generator=374003 .*behavior=native '
                             r'.*source_FSM=implemented', text)),
        batch3_bind=bool(re.search(r'P2_BATCH3_BIND generator=374003 key=aquatic\|Jigumo '
                                   r'visual_only=0 native_fsm=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        nest_or_search=any(state in states for state in ('appear', 'wait', 'hide', 'search')),
        attack=('attack' in states or 'sattack' in states),
        animation_event_bite=bite_in_window,
        bite_frames=frames,
        bite_eat_accounting=len(eats) >= 1 and len(eats) <= len(frames),
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(v for k, v in checks.items() if k != 'bite_frames'),
                checks=checks, motion_spread=spread,
                states_seen=sorted(set(states)), clips_seen=[],
                sampled_positions=len(positions), exit_code=code,
                unmeasured=['PanHouse/nest actor and its lifetime/persistence',
                            'source damageCallBack part rule (Carry/Return only)',
                            'waterBox soil/water attack effects',
                            'source carry/walk root motion and mouth slot attach'],
                limitations=['No arena override: the aquatic arena already stages Jigumo inside the '
                             'source sight and attack radii; still engineered placement, not production evidence.',
                             'No PanHouse/nest exists on the P1 host; Appear/Hide are animation-only '
                             'around the Jigumo home point.',
                             'The source mouth slot is not representable: the bite is an explicit capture '
                             'at the source bite event frame (short attack active frame 13 / attack key 2 '
                             'frame 26) plus one kill at the source swallow frame (sattack key 10 frame 115 / '
                             'dive key 8 frame 80).'])


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
