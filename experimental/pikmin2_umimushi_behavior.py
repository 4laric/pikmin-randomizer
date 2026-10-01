"""UmiMushi (Toady Bloyster, EnemyID 71) source-behavior acceptance (#167/#374/#407).

Builds the private batch-3 aquatic arena from
``experimental.pikmin2_aquatic_arena`` and runs the native
``pc_port/pc_p2_umimushi.cpp`` FSM, which prints ``P2_UMIMUSHI_*`` markers. The
default arena stages UmiMushi at x=120, z=1850 (arena ``POSITIONS`` index 3),
about 190 units from the engine-added 20-red starting squad at x in
[-140,-68], z in [1812,1820]. That is inside the source fp12=700 sight radius
but outside the source fp22=170 attack hit radius, so ``plan_positions``
locally overrides the arena coordinate to sit the actor beside the squad and
make the banked tongue bite / Eat swallow observable; the override is recorded
in ``umimushi-override.json`` exactly as the other species runners record
theirs. This is engineered placement, not production placement evidence. The
fixture is not run by the unit tests. ``validate()`` checks only the
``P2_UMIMUSHI_*`` source-behavior markers plus the batch-3 bind/ready lines and
the source bite frame window.
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

UMI_ID = 374004
UMI_INDEX = arena.SPECIES.index('UmiMushi')
SOURCE_ID = 71
ARENA_POSITION = tuple(arena.POSITIONS[UMI_INDEX])
BEHAVIOR_POSITION = (-108.0, 30.0, 1850.0)
BITE_FRAME = 39.0      # source attack1 event (39,3) tongue active
ATTACK_HIT = 170.0     # source general fp22 attack hit radius
SIGHT = 700.0          # source general fp12 sight radius
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def squad_distance(position):
    """Horizontal distance from a position to the nearest starting red Pikmin."""
    return min(((position[0] - x) ** 2 + (position[2] - z) ** 2) ** 0.5
               for x in SQUAD_X for z in SQUAD_Z)


def plan_positions(positions):
    """Move UmiMushi beside the fixture squad only if the arena default is
    outside the source fp22=170 attack hit radius. Returns (positions, override)."""
    positions = list(positions)
    current = tuple(positions[UMI_INDEX])
    if squad_distance(current) < ATTACK_HIT:
        return tuple(positions), None
    positions[UMI_INDEX] = BEHAVIOR_POSITION
    return tuple(positions), dict(
        index=UMI_INDEX, species='UmiMushi', generator=UMI_ID, source_id=SOURCE_ID,
        arena_default=list(current), behavior_fixture=list(BEHAVIOR_POSITION),
        reason='arena default x=120 is outside the source fp22=170 attack hit radius; '
               'move UmiMushi beside the starting squad so the banked tongue bite and '
               'Eat swallow are observable',
        production_placement=False)


def prepare(assets, imported, output):
    assets, imported, output = Path(assets), Path(imported), Path(output)
    original = arena.POSITIONS
    positions, override = plan_positions(original)
    arena.POSITIONS = positions
    try:
        run = _prepare(assets, imported, output)
    finally:
        arena.POSITIONS = original
    record = dict(species='UmiMushi', generator=UMI_ID, source_id=SOURCE_ID,
                  arena_default=list(ARENA_POSITION),
                  distance_to_squad=squad_distance(ARENA_POSITION),
                  attack_hit=ATTACK_HIT, sight=SIGHT,
                  bite_frame=BITE_FRAME,
                  behavior_fixture=None if override is None else list(BEHAVIOR_POSITION),
                  override_applied=override is not None, override=override,
                  pose_name_normalization=normalize_pose_names(run),
                  reason='arena default already inside the source fp22=170 attack hit radius; '
                         'no override applied'
                  if override is None else override['reason'],
                  production_placement=False)
    (run / 'umimushi-override.json').write_text(json.dumps(record, indent=2) + '\n')
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
    (run_dir / 'umimushi-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    """Check the native log against the source UmiMushi FSM contract.

    Confined to ``P2_UMIMUSHI_*`` / batch-3 bind markers so it makes no claim
    about unrelated families or about production placement.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_UMIMUSHI_STATE generator=374004 state=(\w+)', text)
    bites = re.findall(r'P2_UMIMUSHI_BITE generator=374004 frame=([\d.]+) pikmin=1', text)
    eats = re.findall(r'P2_UMIMUSHI_EAT generator=374004 pikmin=1', text)
    flicks = [int(n) for n in re.findall(
        r'P2_UMIMUSHI_FLICK generator=374004 frame=\d+ pikmin=(\d+)', text)]
    frames = [float(f) for f in bites]
    bite_in_window = bool(frames) and all(
        BITE_FRAME - 1.0 <= f <= BITE_FRAME + 1.0 for f in frames)
    positions = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(
        r'P2_UMIMUSHI_POS generator=374004 state=\w+ clip=\w+ phase=[\d.]+ '
        r'x=(-?[\d.]+) y=-?[\d.]+ z=(-?[\d.]+)', text)]
    spread = 0.0
    if len(positions) >= 2:
        x0, z0 = positions[0]
        spread = max(abs(x - x0) + abs(z - z0) for x, z in positions)
    checks = dict(
        identity=bool(re.search(r'P2_UMIMUSHI_BIND generator=374004 source_id=71 visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=UmiMushi native_family=Chappy '
                             r'generator=374004 .*behavior=native .*source_FSM=implemented', text)),
        batch3_bind=bool(re.search(r'P2_BATCH3_BIND generator=374004 key=aquatic\|UmiMushi '
                                   r'visual_only=0 native_fsm=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        walk_or_wait=('walk' in states or 'wait' in states or 'search' in states or 'turn' in states),
        attack='attack' in states,
        animation_event_bite=bite_in_window,
        bite_frames=frames,
        bite_eat_accounting=len(eats) >= 1 and len(eats) <= len(frames),
        flick=bool(flicks) and all(n >= 1 for n in flicks),
        flick_pikmin=(max(flicks) if flicks else 0),
        autonomous_motion=spread > 5.0,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(v for k, v in checks.items()
                           if k not in ('bite_frames', 'flick', 'flick_pikmin',
                                        'autonomous_motion')),
                checks=checks, motion_spread=spread, exit_code=code,
                states_seen=sorted(set(states)),
                unmeasured=['P2 water box / Hamon sea height / dive and splash presentation',
                            'shared UmiMushi::Mgr base (100) exclusion and Blind (101) '
                            'half-scale / fp12=800 health / reduced turn-rate split',
                            'mid-boss BGM phase staging',
                            'eye/weak joint callbacks and umimusi_model1.btk material animation',
                            'seven-slot tongue (kamu_joint1..7) mouth geometry',
                            'attackNavi captain damage and mouth-slot geometry test',
                            'full action animation bank', 'cleanup/re-entry'],
                limitations=['Behavior fixture overrides the UmiMushi arena coordinate; '
                             'not production placement evidence.',
                             'P2 tongue swallow is resolved as an explicit P1-host capture '
                             'inside the source fp22=170 attack hit radius at the banked bite '
                             'event (attack1 frame 39, event 3) plus one kill at the banked Eat '
                             'swallow (eat1 animation end).',
                             'The source view-angle gate is treated as a full hemisphere and '
                             'target selection uses the single active Navi.'])


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
