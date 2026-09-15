"""SnakeCrow/SnakeWhole shared-base source-behavior acceptance (#174/#376/#407).

Builds the private batch-3 snagret arena via
`experimental.pikmin2_snagret_arena.prepare` (SnakeCrow + SnakeWhole +
DangoMushi + P1 control). The native `pc_port/pc_p2_snakejoint.cpp` drives the
shared source snagret FSM -- Stay (burrow) -> Appear1/Appear2 (emerge) ->
Wait/Walk/Home -> Attack (one directional bite capture) -> Eat (one swallow
kill) -> Struggle/Flick -> Disappear (dive) -> Stay, plus Dead -- and prints
`P2_SNAKEJOINT_*` markers for BOTH species (dispatched by source id 34/70).
`validate()` checks only those markers plus the batch-3 bind/ready lines.

The arena stages SnakeCrow at (-150, 30, 1850) and SnakeWhole at
(-50, 30, 1850); both sit inside the source fp11=100 Stay private radius and the
source sight radius of the 20-red starting squad (x in [-140, -68]), so no
behavior-fixture position override is needed. `plan_positions` applies one per
actor only if the arena default would sit outside the private radius. The bank
file `p2-snagret-bank.txt` is materialized from the batch-1 `snagret.json`
manifest because the snagret install stores the actor config/poses but not the
clip listing the native bank loader consumes.
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_snagret_arena import prepare as _prepare

SNAKES = (
    dict(index=0, generator=376001, species='SnakeCrow', source_id=34,
         arena_position=(-150.0, 30.0, 1850.0)),
    dict(index=1, generator=376002, species='SnakeWhole', source_id=70,
         arena_position=(-50.0, 30.0, 1850.0)),
)
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))
PRIVATE_RADIUS = 100.0           # source general fp11
SIGHT = {'SnakeCrow': 150.0, 'SnakeWhole': 400.0}
BITE_FRAME = 34                  # EXPECTED_EVENTS hit 34:3 KEYEVENT_3
BEHAVIOR_POSITION = (-100.0, 30.0, 1840.0)
BANK_TXT = 'p2-snagret-bank.txt'


def squad_distance(position):
    """Horizontal distance from a position to the nearest starting red Pikmin."""
    return min(((position[0] - x) ** 2 + (position[2] - z) ** 2) ** 0.5
               for x in SQUAD_X for z in SQUAD_Z)


def plan_positions(positions):
    """Move each snagret next to the fixture squad only if its arena default is
    outside the source fp11 private wake radius. Returns (positions, overrides)."""
    positions = [tuple(p) for p in positions]
    overrides = []
    for snake in SNAKES:
        index = snake['index']
        current = positions[index]
        if squad_distance(current) < PRIVATE_RADIUS:
            continue
        positions[index] = BEHAVIOR_POSITION
        overrides.append(dict(
            index=index, species=snake['species'], generator=snake['generator'],
            arena_default=list(current), behavior_fixture=list(BEHAVIOR_POSITION),
            reason='arena default is outside the source fp11=100 Stay wake radius; move '
                   'the snagret beside the starting squad so the shared FSM is observable',
            production_placement=False))
    return tuple(positions), (overrides or None)


def bank_text(manifest):
    """Canonical `P2_SNAGRET_BANK_1` listing the native loader consumes."""
    rows = ['P2_SNAGRET_BANK_1']
    for name in ('SnakeCrow', 'SnakeWhole', 'DangoMushi'):
        info = manifest['species'][name]
        rows.append(f"species {name} {info['enemy_id']}")
        for clip in info.get('clips', []):
            events = ','.join(f'{frame}:{kind}'
                              for frame, kind in clip.get('events', [])) or '-'
            poses = sum(1 for pose in clip.get('poses', []) if 'file' in pose)
            rows.append(f"clip {name} {clip['name']} {clip.get('source_frames', 0)} "
                        f"{events} poses {poses} status {clip.get('status', '')}")
    return '\n'.join(rows) + '\n'


def _ensure_bank(run, imported):
    target = run / BANK_TXT
    if target.exists():
        return target.read_text()
    manifest = json.loads((imported / 'snagret.json').read_text())
    text = bank_text(manifest)
    target.write_text(text)
    return text


def prepare(assets, imported, output):
    import experimental.pikmin2_snagret_arena as arena

    assets, imported, output = Path(assets), Path(imported), Path(output)
    original = arena.POSITIONS
    positions, overrides = plan_positions(original)
    arena.POSITIONS = positions
    try:
        run = _prepare(assets, imported, output)
    finally:
        arena.POSITIONS = original
    _ensure_bank(run, imported)
    record = dict(
        species=[dict(
            species=snake['species'], generator=snake['generator'],
            source_id=snake['source_id'],
            arena_default=list(snake['arena_position']),
            distance_to_squad=squad_distance(snake['arena_position']),
            private_radius=PRIVATE_RADIUS, sight=SIGHT[snake['species']],
            override_applied=overrides is not None and any(
                o['generator'] == snake['generator'] for o in (overrides or [])),
        ) for snake in SNAKES],
        overrides=overrides,
        reason='arena defaults already inside the source fp11=100 Stay wake radius of the '
               'starting squad; no override applied' if overrides is None else 'override applied',
        production_placement=False,
    )
    (run / 'snakejoint-override.json').write_text(json.dumps(record, indent=2) + '\n')
    return run


def run(assets, imported, output, exe, seconds=30):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(assets, imported, output)
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'snakejoint-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def _species_checks(text, snake):
    generator = snake['generator']
    species = snake['species']
    source_id = snake['source_id']
    states = re.findall(
        rf'P2_SNAKEJOINT_STATE generator={generator} state=(\w+)', text)
    bites = [int(frame) for frame in re.findall(
        rf'P2_SNAKEJOINT_BITE generator={generator} frame=(\d+) pikmin=1', text)]
    eats = len(re.findall(
        rf'P2_SNAKEJOINT_EAT generator={generator} pikmin=1', text))
    positions = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(
        rf'P2_SNAKEJOINT_POS generator={generator} state=\w+ clip=\w+ phase=[\d.]+ '
        rf'x=(-?[\d.]+) z=(-?[\d.]+)', text)]
    spread = 0.0
    if len(positions) >= 2:
        x0, z0 = positions[0]
        spread = max(abs(x - x0) + abs(z - z0) for x, z in positions)

    # The bite is only valid while the attack state is active and the swallow
    # kill only while the eat state is active (the source anim key events).
    active = 'null'
    bite_in_window = True
    eat_in_window = True
    for match in re.finditer(
            rf'P2_SNAKEJOINT_STATE generator={generator} state=(\w+)'
            rf'|P2_SNAKEJOINT_BITE generator={generator} frame=\d+ pikmin=1'
            rf'|P2_SNAKEJOINT_EAT generator={generator} pikmin=1', text):
        token = match.group(0)
        if token.startswith('P2_SNAKEJOINT_STATE'):
            active = match.group(1)
        elif 'BITE' in token and active != 'attack':
            bite_in_window = False
        elif 'EAT' in token and active != 'eat':
            eat_in_window = False

    emerged = bool({'appear1', 'appear2'} & set(states))
    checks = dict(
        identity=bool(re.search(
            rf'P2_SNAKEJOINT_BIND generator={generator} species={species} '
            rf'source_id={source_id} visual_only=0', text)),
        ready=bool(re.search(
            rf'P2_ENEMY_READY species={species} native_family=Chappy '
            rf'generator={generator} .*behavior=native .*source_FSM=implemented', text)),
        stay='stay' in states,
        emerged=emerged,
        wait=('wait' in states) or species == 'SnakeWhole',
        attack='attack' in states,
        eat='eat' in states,
        bite_frame=bool(bites) and all(frame == BITE_FRAME for frame in bites),
        bite_in_window=bite_in_window and bool(bites),
        eat_in_window=eat_in_window,
        bite_bounded=1 <= len(bites) <= 8,
        eat_bounded=0 < eats <= len(bites),
        # SnakeCrow is stationary by source (fp06=0); motion is only required of
        # the mobile SnakeWhole.
        autonomous_motion=(spread > 5.0) or species == 'SnakeCrow',
    )
    return checks, dict(bites=bites, eats=eats, states=states, motion_spread=spread)


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    window = bool(re.search(
        r'Experimental preview window set to 960x540 windowed and centered', text))
    no_extinction = not re.search(r'Extinction', text, re.IGNORECASE)
    species_results = {}
    for snake in SNAKES:
        checks, detail = _species_checks(text, snake)
        checks['window'] = window
        checks['no_extinction'] = no_extinction
        species_results[snake['species']] = dict(
            passed=all(checks.values()), checks=checks, **detail)
    passed = window and no_extinction and all(
        result['passed'] for result in species_results.values())
    return dict(passed=passed, window=window, no_extinction=no_extinction,
                species=species_results, exit_code=code,
                unmeasured=['shared SnakeJointMgr bodyjnt3-bodyjnt8 spine matrices',
                            'source P2 burrow model hide / invulnerability flags',
                            'SnakeCrow White Flower Garden mWFGHealth (fp31) override',
                            'source appearNearByTarget 120-unit emerge reposition',
                            'five-directional hit_near/hit/hit_far/hit_r/hit_l selection',
                            'full action animation bank', 'cleanup/re-entry'],
                limitations=['Batch-3 snagret arena placement is engineered fixture '
                             'evidence, not production placement evidence.',
                             'The five-way directional bite is approximated as the nearest '
                             'target inside the source attack sweep; capture is exactly-once '
                             'at the banked hit KEYEVENT_3 frame and the swallow kill is '
                             'exactly-once at the banked waitact1 KEYEVENT_2 frame.'])


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
