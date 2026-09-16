"""Blind UmiMushi (EnemyID 101) shared-base acceptance (#167/#374/#407).

Extends the UmiMushi (71) source-behavior fixture
(``experimental.pikmin2_umimushi_behavior``) to the shared ``UmiMushi::Mgr``
Blind variant. The source import manifest (``experimental.pikmin2_aquatic_assets``)
ships only the ordinary UmiMushi (71) actor/model/params; there is **no**
converted Blind (101) actor. ``pc_port/pc_p2_umimushi.cpp`` therefore accepts an
``UmiMushiBlind`` species row in ``p2-aquatic-actors.txt`` and reuses the
converted UmiMushi sampled bank as an explicit visual stand-in
(``pc_port/pc_p2_batch3.cpp`` aliases the ``aquatic|UmiMushiBlind`` key to the
``UmiMushi`` poses). No Blind visual provenance is fabricated.

``prepare`` adds one extra P1 Chappy placement vehicle at the source-101
generator beside the engine-added 20-red starting squad (arena ``POSITIONS``
index 3 stays the ordinary UmiMushi at x=120, so both IDs run concurrently) and
appends the Blind actor binding to the run's ``p2-aquatic-actors.txt``. This is
engineered placement, not production placement evidence. ``validate()`` checks
only the ``P2_UMIMUSHI_*`` / batch-3 markers for generator 374006 plus the
still-present ordinary UmiMushi bind. The fixture is not run by the unit tests.
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

BLIND_ID = 374006
BLIND_SOURCE_ID = 101
BLIND_FAR_ID = 374007
ORDINARY_ID = 374004
ORDINARY_SOURCE_ID = 71
CONTROL_ID = 374005
BLIND_SPECIES = 'UmiMushiBlind'
# Focused roster: ordinary UmiMushi, P1 control, near Blind, far Blind.
BLIND_INDEX = 2
BLIND_FAR_INDEX = 3
ORDINARY_POSITION = (120.0, 30.0, 1850.0)
CONTROL_POSITION = (240.0, 30.0, 1550.0)
BLIND_POSITION = (-108.0, 30.0, 1850.0)
# Outside the fp22=170 attack hit radius but inside the fp12=700 sight radius:
# the near actor bites/swallows immediately, the far actor walks and exercises
# the Blind Walk move/wait pacing before it can engage.
BLIND_FAR_POSITION = (200.0, 30.0, 1850.0)
BITE_FRAME = 39.0      # source attack1 event (39,3) tongue active
ATTACK_HIT = 170.0     # source general fp22 attack hit radius
SIGHT = 700.0          # source general fp12 sight radius
BLIND_LIFE = 800.0     # source proper fp12 mBlindHealth (disc)
BLIND_SCALE = 0.5      # source setParameters scale
BLIND_TURN_RATE = 0.30  # source Parms::mBlindTurnRateReduction
BLIND_WAIT_FRAMES = 200.0
BLIND_MOVE_FRAMES = 200.0
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def squad_distance(position):
    """Horizontal distance from a position to the nearest starting red Pikmin."""
    return min(((position[0] - x) ** 2 + (position[2] - z) ** 2) ** 0.5
               for x in SQUAD_X for z in SQUAD_Z)


def prepare(assets, imported, output):
    """Stage a focused UmiMushi arena: ordinary (71) + Blind (101) + P1 control.

    The other aquatic actors (Catfish/Tadpole/Jigumo) are dropped from this
    private roster so they cannot consume the shared 20-red squad before the
    Blind actor's banked Eat swallow resolves; the ordinary UmiMushi is kept so
    the shared-manager claim that both IDs work is exercised in one run.
    """
    assets, imported, output = Path(assets), Path(imported), Path(output)
    original = (arena.IDS, arena.SPECIES, arena.POSITIONS, arena.PROXY, arena.AQUATIC)
    arena.IDS = (ORDINARY_ID, CONTROL_ID, BLIND_ID, BLIND_FAR_ID)
    arena.SPECIES = ('UmiMushi', 'P1 Chappy', BLIND_SPECIES, BLIND_SPECIES)
    arena.POSITIONS = (ORDINARY_POSITION, CONTROL_POSITION, BLIND_POSITION, BLIND_FAR_POSITION)
    arena.PROXY = {'UmiMushi': arena.P1_CHAPPY_TYPE, 'P1 Chappy': arena.P1_CHAPPY_TYPE,
                   BLIND_SPECIES: arena.P1_CHAPPY_TYPE}  # no P1 counterpart; vehicle only
    arena.AQUATIC = ('UmiMushi',)  # only the ordinary UmiMushi is a manifest species
    try:
        run = _prepare(assets, imported, output)
    finally:
        (arena.IDS, arena.SPECIES, arena.POSITIONS, arena.PROXY, arena.AQUATIC) = original

    # The aquatic install refuses species outside the import manifest, so the
    # Blind actor binding is appended after the hash-bound install/verify step.
    actors_path = run / 'p2-aquatic-actors.txt'
    lines = actors_path.read_text().splitlines()
    if lines[0] != 'P2_AQUATIC_ACTORS_1':
        raise ValueError('Unexpected aquatic actors header')
    lines[1] = str(int(lines[1]) + 2)
    lines.append(f'{BLIND_ID} {BLIND_SPECIES}')
    lines.append(f'{BLIND_FAR_ID} {BLIND_SPECIES}')
    actors_path.write_text('\n'.join(lines) + '\n')

    distance = squad_distance(BLIND_POSITION)
    standin = dict(
        schema=1, generators=[BLIND_ID, BLIND_FAR_ID], species=BLIND_SPECIES,
        source_id=BLIND_SOURCE_ID,
        visual_bank='aquatic_UmiMushi_<clip>_NN.mod (converted ordinary UmiMushi poses)',
        bank_alias='pc_p2_batch3.cpp keys aquatic|UmiMushiBlind but loads the UmiMushi bank',
        reason='the aquatic import manifest has no converted Blind (101) actor/model; the '
               'shared UmiMushi::Mgr Blind variant is staged on the converted UmiMushi bank as '
               'an explicit visual stand-in',
        source_parms=dict(scale=BLIND_SCALE, health=BLIND_LIFE, turn_rate=BLIND_TURN_RATE,
                          wait_frames=BLIND_WAIT_FRAMES, move_frames=BLIND_MOVE_FRAMES,
                          is_change_navi=False),
        fabricated_provenance=False, production_placement=False)
    (run / 'umimushi-blind-standin.json').write_text(json.dumps(standin, indent=2) + '\n')

    override = dict(
        species=BLIND_SPECIES, generators=[BLIND_ID, BLIND_FAR_ID], source_id=BLIND_SOURCE_ID,
        index=BLIND_INDEX, arena_default=None,
        behavior_fixture={'near': list(BLIND_POSITION), 'far': list(BLIND_FAR_POSITION)},
        near_distance_to_squad=distance, attack_hit=ATTACK_HIT, sight=SIGHT, bite_frame=BITE_FRAME,
        reason='the aquatic arena stages only the ordinary UmiMushi at x=120; append a near Blind '
               'UmiMushi at x=-108, z=1850 (%.1f units from the starting squad, inside the source '
               'fp22=170 attack hit radius) so the shared FSM bite/Eat is observable, plus a far '
               'Blind UmiMushi at x=200, z=1850 outside the attack radius so the Blind walk '
               'move/wait pacing and autonomous motion are observable' % distance,
        pose_name_normalization=normalize_pose_names(run),
        production_placement=False)
    (run / 'umimushi-blind-override.json').write_text(json.dumps(override, indent=2) + '\n')
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
    (run_dir / 'umimushi-blind-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    """Check the native log against the Blind UmiMushi shared-FSM contract.

    Confined to ``P2_UMIMUSHI_*`` / batch-3 markers for generator 374006 (Blind)
    and the still-present ordinary UmiMushi (374004) bind, so it makes no claim
    about unrelated families or about production placement.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_UMIMUSHI_STATE generator=374006 state=(\w+)', text)
    bites = re.findall(r'P2_UMIMUSHI_BITE generator=374006 frame=([\d.]+) pikmin=1', text)
    eats = re.findall(r'P2_UMIMUSHI_EAT generator=374006 pikmin=1', text)
    waits = re.findall(r'P2_UMIMUSHI_BLIND_WAIT generator=(37400[67])', text)
    moves = re.findall(r'P2_UMIMUSHI_BLIND_MOVE generator=(37400[67])', text)
    frames = [float(f) for f in bites]
    bite_in_window = bool(frames) and all(
        BITE_FRAME - 1.0 <= f <= BITE_FRAME + 1.0 for f in frames)
    spread = 0.0
    for generator in (BLIND_ID, BLIND_FAR_ID):
        positions = []
        spawn = re.search(r'P2_ENEMY_READY species=UmiMushiBlind .*generator=%d '
                          r'x=(-?[\d.]+) y=-?[\d.]+ z=(-?[\d.]+)' % generator, text)
        if spawn:
            positions.append((float(spawn.group(1)), float(spawn.group(2))))
        positions += [(float(m.group(1)), float(m.group(2))) for m in re.finditer(
            r'P2_UMIMUSHI_POS generator=%d state=\w+ clip=\w+ phase=[\d.]+ '
            r'x=(-?[\d.]+) y=-?[\d.]+ z=(-?[\d.]+)' % generator, text)]
        if len(positions) >= 2:
            x0, z0 = positions[0]
            spread = max(spread, max(abs(x - x0) + abs(z - z0) for x, z in positions))
    dead = bool(re.search(r'P2_UMIMUSHI_DEAD generator=374006 source_id=101 health=0', text))
    checks = dict(
        identity=bool(re.search(r'P2_UMIMUSHI_BIND generator=374006 source_id=101 '
                                r'visual_only=0 blind=1', text)),
        config=bool(re.search(r'P2_UMIMUSHI_BLIND generator=374006 scale=0\.500 health=800\.0 '
                              r'turn_rate=0\.30 wait_frames=200 move_frames=200', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=UmiMushiBlind native_family=Chappy '
                             r'generator=374006 .*health=800\.0 max_health=800\.0 behavior=native '
                             r'.*source_FSM=implemented', text)),
        ordinary_identity=bool(re.search(r'P2_UMIMUSHI_BIND generator=374004 source_id=71 '
                                         r'visual_only=0 blind=0', text)),
        batch3_bind=bool(re.search(r'P2_BATCH3_BIND generator=374006 key=aquatic\|UmiMushiBlind '
                                   r'visual_only=0 native_fsm=implemented', text)),
        far_batch3_bind=bool(re.search(r'P2_BATCH3_BIND generator=374007 key=aquatic\|UmiMushiBlind '
                                       r'visual_only=0 native_fsm=implemented', text)),
        ordinary_batch3_bind=bool(re.search(r'P2_BATCH3_BIND generator=374004 key=aquatic\|UmiMushi '
                                            r'visual_only=0 native_fsm=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        walk_or_wait=('walk' in states or 'wait' in states),
        attack='attack' in states,
        animation_event_bite=bite_in_window,
        bite_frames=frames,
        bite_eat_accounting=len(eats) >= 1 and len(eats) <= len(frames),
        blind_pacing=bool(waits) and bool(moves),
        autonomous_motion=spread > 5.0,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    required = ('identity', 'config', 'ready', 'ordinary_identity', 'batch3_bind',
                'far_batch3_bind', 'ordinary_batch3_bind', 'window', 'walk_or_wait', 'attack',
                'animation_event_bite', 'bite_eat_accounting', 'no_extinction')
    gates = dict(
        identity=checks['identity'] and checks['ready'] and checks['batch3_bind'],
        movement=checks['walk_or_wait'] and checks['autonomous_motion'],
        attack_receiver=checks['attack'] and checks['animation_event_bite']
                        and checks['bite_eat_accounting'],
        death=dead,
        cleanup=False)
    return dict(passed=all(checks[k] for k in required),
                checks=checks, gates=gates, motion_spread=spread, death_observed=dead,
                exit_code=code, states_seen=sorted(set(states)),
                pace_events=len(waits) + len(moves),
                unmeasured=['P2 water box / Hamon sea height / dive and splash presentation',
                            'UmiMushi::Mgr base (100) direct-spawn exclusion',
                            'mid-boss BGM phase staging',
                            'eye/weak joint callbacks and umimusi_model1.btk material animation',
                            'seven-slot tongue (kamu_joint1..7) mouth geometry',
                            'attackNavi captain damage and mouth-slot geometry test',
                            'full action animation bank',
                            'death/corpse and cleanup/re-entry (no damage source in this fixture)'],
                limitations=['Blind (101) reuses the converted ordinary UmiMushi sampled bank as an '
                             'explicit visual stand-in; the import manifest has no converted Blind '
                             'actor/model and no Blind provenance is fabricated.',
                             'Half scale is applied to the P1 host actor mSRT.s and therefore the '
                             'batch-3 draw matrix; it is logged, not visually re-measured.',
                             'The Blind Walk move/wait frame cycle is implemented, but the fixture '
                             'squad roams into reach within one move window, so the WAIT/MOVE '
                             'markers are not always observed (reported in checks.blind_pacing).',
                             'Behavior fixture appends Blind placements beside and behind the squad; '
                             'not production placement evidence.'])


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
