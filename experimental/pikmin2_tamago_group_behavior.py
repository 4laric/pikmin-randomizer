"""TamagoMushi (Mitite, EnemyID 68) bounded group-birth / leader-follow (#165/#407).

Private batch-2 ground arena staging a five-actor TamagoMushi cluster next to the
20-red fixture squad. The native ``pc_port/pc_p2_tamago.cpp`` binds the
smallest-generator actor as the group leader and the remaining four as followers
that emerge, follow the leader inside a bounded swarm leash and share the
collision Astonish receiver, printing ``P2_TAMAGO_{LEADER,GROUP,FOLLOW,ASTONISH,
HONEY}_*`` markers.

This is an explicit bounded approximation of the source manager-owned
``tamagoMushiMgr.cpp::createGroup`` birth (10 surface / 30 cave): no brand-new P1
Teki actors are born by the arena or the module, and the source birth offsets are
represented by engineered arena positions. ``validate()`` checks only the
``P2_TAMAGO_*`` markers; it makes no claim about production placement or runtime
execution.
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
SPECIES = tuple(CFG['arena_species'])
TAMAGO_INDEX = SPECIES.index('TamagoMushi')

# Five staged TamagoMushi generators; the smallest is the group leader.
GROUP_IDS = (346004, 346014, 346015, 346016, 346017)
LEADER_ID = GROUP_IDS[0]
FOLLOWER_IDS = GROUP_IDS[1:]
FOLLOWER_COUNT = len(FOLLOWER_IDS)
CONTROL_ID = 346007
GROUP_VALUE_COUNT = len(GROUP_IDS)

# Source group counts (generalEnemyMgr.cpp:436-443); recorded, not replayed.
SOURCE_SURFACE_COUNT = 10
SOURCE_CAVE_COUNT = 30

# Leader sits inside the starting squad; followers form the source-like cluster
# around it (engineered offsets, not replay of the manager's birthRadius * 45).
LEADER_POSITION = (-100.0, 30.0, 1850.0)
FOLLOWER_OFFSETS = ((-24.0, 0.0), (18.0, 0.0), (0.0, -30.0), (8.0, 30.0))
CONTROL_POSITION = (240.0, 30.0, 1500.0)

SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def group_positions():
    positions = [LEADER_POSITION]
    positions += [(LEADER_POSITION[0] + dx, LEADER_POSITION[1], LEADER_POSITION[2] + dz)
                  for dx, dz in FOLLOWER_OFFSETS]
    positions.append(CONTROL_POSITION)
    return tuple(positions)


def group_cfg():
    cfg = dict(CFG)
    cfg['arena_ids'] = GROUP_IDS + (CONTROL_ID,)
    cfg['arena_species'] = ('TamagoMushi',) * GROUP_VALUE_COUNT + ('P1 Chappy',)
    cfg['arena_positions'] = group_positions()
    return cfg


def position_override():
    positions = group_positions()
    return dict(group_count=GROUP_VALUE_COUNT, leader=LEADER_ID,
                followers=list(FOLLOWER_IDS), generators=list(GROUP_IDS),
                follower_offsets=[list(offset) for offset in FOLLOWER_OFFSETS],
                arena_default=[list(LEADER_POSITION)] * GROUP_VALUE_COUNT,
                behavior_fixture=[list(positions[index]) for index in range(GROUP_VALUE_COUNT)],
                reason='stage a five-actor TamagoMushi cluster near the starting squad so the '
                       'leader/follower binds, emerge cycle, follow motion and shared Astonish '
                       'receiver are observable without birthing new Teki actors',
                bounded_approximation='smallest-generator actor is leader; followers emerge and '
                                      'follow within the bounded leash; source manager createGroup '
                                      '(10 surface / 30 cave) and its birth offsets are not replayed',
                source_group=dict(surface=SOURCE_SURFACE_COUNT, cave=SOURCE_CAVE_COUNT,
                                  helper='tamagoMushiMgr.cpp::createGroup',
                                  revision='632af93787b9c95b63f0c13be32b161375ce3a96'),
                production_placement=False)


def prepare(assets, imported, output):
    cfg = group_cfg()
    # The shared core's prepare() calls installer(imported, run, actors) while
    # install()/verify_install() take cfg first; bind cfg here.
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    override = position_override()
    override['pose_name_normalization'] = normalize_pose_names(run)
    (run / 'tamago-group-override.json').write_text(json.dumps(override, indent=2) + '\n')
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
    (run_dir / 'tamago-group-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def _leader_bound(leader_markers):
    return len(leader_markers) >= 1 and int(leader_markers[0]) == LEADER_ID


def _group_binds(groups):
    followers = {int(follower) for _, follower in groups}
    return (len(groups) == FOLLOWER_COUNT
            and followers == set(FOLLOWER_IDS)
            and all(int(leader) == LEADER_ID for leader, _ in groups))


def _follow_samples(follows):
    """Per-follower position spread and the maximum leader/follower distance."""
    by_follower = {}
    max_distance = 0.0
    for generator, distance, x, z in follows:
        by_follower.setdefault(int(generator), []).append((x, z))
        max_distance = max(max_distance, distance)
    spread = 0.0
    for points in by_follower.values():
        if len(points) < 2:
            continue
        x0, z0 = points[0]
        spread = max(spread, max(abs(x - x0) + abs(z - z0) for x, z in points))
    return spread, max_distance


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    leader = re.findall(r'P2_TAMAGO_LEADER generator=(\d+)', text)
    groups = [(int(leader_id), int(follower))
              for leader_id, follower in re.findall(
                  r'P2_TAMAGO_GROUP leader=(\d+) follower=(\d+)', text)]
    follows = [(int(generator), float(distance), float(x), float(z))
               for generator, distance, x, z in re.findall(
                   r'P2_TAMAGO_FOLLOW generator=(\d+) leader=\d+ distance=([\d.]+) '
                   r'state=\w+ x=(-?[\d.]+) z=(-?[\d.]+)', text)]
    astonish = re.findall(r'P2_TAMAGO_ASTONISH generator=(\d+) pikmin=1', text)
    honey = re.findall(r'P2_TAMAGO_HONEY generator=(\d+) source_id=68', text)
    follow_spread, max_distance = _follow_samples(follows)
    follower_emerged = any(
        re.search(rf'P2_TAMAGO_STATE generator={follower} state=appear', text)
        for follower in FOLLOWER_IDS)
    checks = dict(
        identity=bool(re.search(r'P2_TAMAGO_BIND generator=(\d+) source_id=68 visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=TamagoMushi .*generator=346004 .*'
                             r'behavior=native .*source_FSM=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        leader_bound=_leader_bound(leader),
        group_binds=_group_binds(groups),
        follower_emerged=follower_emerged,
        follow_motion=len(follows) >= 2 and follow_spread > 5.0,
        swarm_bounded=bool(follows) and max_distance <= 200.0,
        astonish_receiver=len(astonish) >= 1,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(checks.values()), checks=checks, followers=len(groups),
                follow_samples=len(follows), follow_spread=follow_spread,
                max_distance=max_distance, astonish=len(astonish), honey=len(honey),
                exit_code=code,
                unmeasured=['true manager-owned createGroup birth of new P1 Teki actors',
                            'source birth offsets and velocities (birthRadius * 45 ground / -10 object)',
                            '10 surface / 30 cave count scaling',
                            'true InteractAstonish panic state (P1 has no Astonish)',
                            'honey reward (requires a death source in the run)'],
                limitations=['Behavior fixture overrides the TamagoMushi arena coordinates; not '
                             'production placement evidence.',
                             'Group is a bounded five-actor approximation; the module links staged '
                             'actors instead of birthing a manager-owned swarm.',
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
