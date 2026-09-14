"""ShijimiChou (Unmarked Spectralids, EnemyID 77) source-behavior acceptance
(#407/#166).

Builds the private ShijimiChou arena via
`experimental.pikmin2_shijimi_arena.prepare` (three plant-origin Yellow
Spectralids on P1 Chappy placement vehicles). The native
`pc_port/pc_p2_shijimi.cpp` drives the bounded source shijimiChouState.cpp FSM
Wait -> Fly -> Leave (or Fall -> Dead), the source group-leader convention, and
the source genItem nectar reward, printing `P2_SHIJIMI_*` markers. `validate()`
checks only those markers plus the batch-3 bind/ready lines, and makes no claim
about other families. Death is triggered by a fixture-only lethal injection
(`p2-shijimi-fixture.txt`) because the unattended 20-red squad never receives
attack orders.
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_shijimi_arena import IDS, LEADER_ID, prepare

SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))
SIGHT = 275.0


def squad_distance(position):
    return min(((position[0] - x) ** 2 + (position[2] - z) ** 2) ** 0.5
               for x in SQUAD_X for z in SQUAD_Z)


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
    (run_dir / 'shijimi-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_SHIJIMI_STATE generator=\d+ state=(\w+)', text)
    positions = [(m.group(1), m.group(2), float(m.group(3)), float(m.group(4)), float(m.group(5)))
                 for m in re.finditer(
        r'P2_SHIJIMI_POS generator=\d+ state=(\w+) clip=(\w+) phase=([\d.]+) '
        r'x=(-?[\d.]+) z=(-?[\d.]+)', text)]
    spread = 0.0
    if len(positions) >= 2:
        x0, z0 = positions[0][3], positions[0][4]
        spread = max(abs(x - x0) + abs(z - z0) for _, _, _, x, z in positions)
    clips_seen = {p[1] for p in positions}
    honey = re.findall(r'P2_SHIJIMI_HONEY generator=(\d+) source_id=77', text)
    kills = re.findall(r'P2_SHIJIMI_KILL generator=(\d+) source_id=77', text)
    corpses = re.findall(r'P2_BATCH3_DRAW corpse=1 key=flying\|ShijimiChou', text)
    corpse_native = re.findall(r'P2_SHIJIMI_CORPSE generator=(\d+) source_id=77 native=\w+', text)
    leader_ready = re.search(r'P2_ENEMY_READY species=ShijimiChou native_family=Chappy '
                             r'generator=%d .*behavior=native .*source_FSM=implemented'
                             % LEADER_ID, text)
    checks = dict(
        identity=bool(re.search(r'P2_SHIJIMI_BIND generator=%d source_id=77 visual_only=0'
                                % LEADER_ID, text)),
        batch3_bind=bool(re.search(r'P2_BATCH3_BIND generator=%d key=flying\|ShijimiChou '
                                   r'visual_only=0 native_fsm=implemented' % LEADER_ID, text)),
        ready=bool(leader_ready),
        group_leader=bool(re.search(r'P2_ENEMY_READY species=ShijimiChou .*group_leader=1',
                                    text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered',
                              text)),
        wait='wait' in states,
        fly='fly' in states,
        fall='fall' in states,
        dead='dead' in states,
        state_fsm={'wait', 'fly'} <= set(states),
        autonomous_motion=spread > 5.0,
        animation=bool(clips_seen),
        death=bool(re.search(r'P2_SHIJIMI_DEAD generator=\d+ source_id=77 health=0', text)),
        nectar=bool(honey),
        corpse=bool(corpse_native) or bool(corpses),
        kill=bool(kills),
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(checks.values()),
                checks=checks, motion_spread=spread, states_seen=sorted(set(states)),
                clips_seen=sorted(clips_seen), honey_events=honey, kills=kills,
                corpses=len(corpse_native), batch3_corpse_draws=len(corpses),
                sampled_positions=len(positions), exit_code=code,
                unmeasured=['source Piklopedia/Zukan mode', 'Red/Purple colour gates and '
                            'first-spray demo flags', 'fp02=0.2 nectar roll (plant origin '
                            'short-circuits it in this fixture)',
                            'full 25-member group, sound cluster and mEfxDown feather effect',
                            'Leave-state culling distance (bounded host cleanup instead)',
                            're-entry/day-floor respawn'],
                limitations=['Three staged Chappy vehicles approximate the source group; '
                             'lowest generator leads and members trace the live leader.',
                             'Death is fixture-injected (p2-shijimi-fixture.txt) because the '
                             'unattended squad never attacks; Fall begins at the health '
                             'endpoint, not a real Pikmin latch.',
                             'genItem is source plant-origin Yellow; the drop is exactly-once '
                             'and births a P1 OBJTYPE_Water nectar item.'])


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
        run_dir, meta, result = run(args.assets, args.imported, args.output,
                                    args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
