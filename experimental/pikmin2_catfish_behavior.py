"""Catfish (Water Dumple, EnemyID 26) source-behavior acceptance (#167/#374/#407).

Builds the private batch-3 aquatic arena from
``experimental.pikmin2_aquatic_arena`` and runs the native
``pc_port/pc_p2_catfish.cpp`` FSM, which prints ``P2_CATFISH_*`` markers. The
default arena stages Catfish at x=-240, z=1850, which is inside the source
fp12=200 sight radius of the engine-added 20-red starting squad but about 104
units away, outside the source fp20=50 attack sweep. ``prepare`` locally
overrides the arena position so Catfish starts inside the attack sweep and the
banked animation-event bite/swallow is observable; the override is recorded in
``catfish-override.json`` exactly as the ground runners record theirs. This is
engineered placement, not production placement evidence. ``validate()`` checks
only the ``P2_CATFISH_*`` source-behavior markers. The fixture is not run by the
unit tests.
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

CATFISH_ID = 374001
CATFISH_INDEX = arena.SPECIES.index('Catfish')
ARENA_DEFAULT = tuple(arena.POSITIONS[CATFISH_INDEX])
BEHAVIOR_POS = (-108.0, 30.0, 1850.0)
BITE_FRAME = 17.0   # source attack event (17,2)
SWALLOW_FRAME = 75.0  # source attack event (75,3)
ATTACK_RANGE = 50.0  # source general fp20/fp22
SIGHT = 200.0  # source general fp12
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def prepare(assets, imported, output):
    positions = list(arena.POSITIONS)
    positions[CATFISH_INDEX] = BEHAVIOR_POS
    original = arena.POSITIONS
    arena.POSITIONS = tuple(positions)
    try:
        run = _prepare(Path(assets), Path(imported), Path(output))
    finally:
        arena.POSITIONS = original
    override = dict(species='Catfish', generator=CATFISH_ID,
                    arena_default=list(ARENA_DEFAULT),
                    behavior_fixture=list(BEHAVIOR_POS),
                    reason='the default arena stages Catfish at x=-240, z=1850, about 104 units '
                           'from the squad (inside the source fp12=200 sight radius but outside '
                           'the source fp20=50 attack sweep); move it inside the sweep so the '
                           'banked attack bite/swallow event is observable',
                    production_placement=False,
                    pose_name_normalization=normalize_pose_names(run))
    (run / 'catfish-override.json').write_text(json.dumps(override, indent=2) + '\n')
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
    (run_dir / 'catfish-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    """Check the native log against the source Catfish/KochappyBase FSM contract.

    Confined to ``P2_CATFISH_*`` / batch-3 bind markers so it makes no claim
    about unrelated families or about production placement.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_CATFISH_STATE generator=374001 state=(\w+)', text)
    bites = re.findall(r'P2_CATFISH_BITE generator=374001 frame=([\d.]+) pikmin=1', text)
    eats = re.findall(r'P2_CATFISH_EAT generator=374001 pikmin=1', text)
    frames = [float(f) for f in bites]
    bite_in_window = bool(frames) and all(BITE_FRAME - 1.0 <= f < SWALLOW_FRAME for f in frames)
    positions = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(
        r'P2_CATFISH_POS generator=374001 state=\w+ clip=\w+ phase=[\d.]+ '
        r'x=(-?[\d.]+) y=-?[\d.]+ z=(-?[\d.]+)', text)]
    spread = 0.0
    if len(positions) >= 2:
        spread = max(abs(x - positions[0][0]) + abs(z - positions[0][1]) for x, z in positions)
    checks = dict(
        identity=bool(re.search(r'P2_CATFISH_BIND generator=374001 source_id=26 visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=Catfish .*generator=374001 .*behavior=native '
                             r'.*source_FSM=implemented', text)),
        batch3_bind=bool(re.search(r'P2_BATCH3_BIND generator=374001 key=aquatic\|Catfish '
                                   r'visual_only=0 native_fsm=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        wait_or_walk=('wait' in states or 'walk' in states or 'turn' in states),
        attack='attack' in states,
        animation_event_bite=bite_in_window,
        bite_frames=frames,
        bite_eat_accounting=len(eats) >= 1 and len(eats) <= len(frames),
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(v for k, v in checks.items() if k != 'bite_frames'),
                checks=checks, motion_spread=spread,
                states_seen=sorted(set(states)), clips_seen=[],
                sampled_positions=len(positions), exit_code=code,
                unmeasured=['kamu1/kamu2 two-slot mouth attachment visual',
                            'attackNavi captain damage and fp02 poison swallow',
                            'full action animation bank', 'cleanup/re-entry'],
                limitations=['Behavior fixture overrides the Catfish arena coordinate; not production placement evidence.',
                             'P2 mouth swallow is resolved as an explicit P1-host capture inside the attack '
                             'sweep at the banked bite event (attack frame 17) plus one kill at the banked '
                             'swallow event (attack frame 75).',
                             'Catfish ships no waitact1 Turn clip; the port Turn state reuses wait1.'])


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
