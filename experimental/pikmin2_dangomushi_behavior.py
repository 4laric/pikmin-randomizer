"""DangoMushi (Segmented Crawbster, EnemyID 94) source-behavior acceptance (#174/#376/#407).

Builds the private batch-3 snagret arena via
`experimental.pikmin2_snagret_arena.prepare` (SnakeCrow + SnakeWhole +
DangoMushi + P1 control). The native `pc_port/pc_p2_dangomushi.cpp` drives the
standalone source DangoMushiState.cpp roller FSM -- Stay -> Appear (fly) ->
Wait/Move wander -> Attack (ball roll, single InteractFlick contact) -> Turn
(territory crash) -> Recover -> Flick (attack_2 arm sweep) -> Wait, plus Dead --
and prints `P2_DANGOMUSHI_*` markers. `validate()` checks only those markers
plus the batch-3 bind/ready lines and the source roll frame window.

The arena stages DangoMushi at (50, 30, 1850). That is 121.7 units from the
nearest starting red Pikmin (x in [-140, -68]), inside the source fp11=150 Stay
private radius and fp12=500 sight radius, so no behavior-fixture position
override is needed; `plan_positions` applies one only if the actor would sit
outside the private radius. The bank file `p2-snagret-bank.txt` is materialized
from the batch-1 `snagret.json` manifest because the snagret install stores the
actor config/poses but not the clip listing the native bank loader consumes.
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_snagret_arena import prepare as _prepare

DANGO_ID = 376003
DANGO_INDEX = 2
SPECIES = 'DangoMushi'
SOURCE_ID = 94
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))
ARENA_POSITION = (50.0, 30.0, 1850.0)
BEHAVIOR_POSITION = (-20.0, 30.0, 1850.0)
PRIVATE_RADIUS = 150.0
SIGHT = 500.0
ROLL_START_FRAME = 23.0
ROLL_END_FRAME = 100.0
BANK_TXT = 'p2-snagret-bank.txt'
POSITIONS = (DANGO_INDEX, ARENA_POSITION)


def squad_distance(position):
    """Horizontal distance from a position to the nearest starting red Pikmin."""
    return min(((position[0] - x) ** 2 + (position[2] - z) ** 2) ** 0.5
               for x in SQUAD_X for z in SQUAD_Z)


def plan_positions(positions):
    """Move DangoMushi next to the fixture squad only if the arena default is
    outside the source fp11 private wake radius. Returns (positions, override)."""
    positions = list(positions)
    index, _ = POSITIONS
    current = tuple(positions[index])
    if squad_distance(current) < PRIVATE_RADIUS:
        return tuple(positions), None
    positions[index] = BEHAVIOR_POSITION
    return tuple(positions), dict(
        index=index, species=SPECIES, generator=DANGO_ID,
        arena_default=list(current), behavior_fixture=list(BEHAVIOR_POSITION),
        reason='arena default is outside the source fp11=150 Stay wake radius; move '
               'DangoMushi beside the starting squad so the roller FSM is observable',
        production_placement=False)


def bank_text(manifest):
    """Canonical `P2_SNAGRET_BANK_1` listing the native loader consumes."""
    rows = ['P2_SNAGRET_BANK_1']
    for name in ('SnakeCrow', 'SnakeWhole', SPECIES):
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
    positions, override = plan_positions(original)
    arena.POSITIONS = positions
    try:
        run = _prepare(assets, imported, output)
    finally:
        arena.POSITIONS = original
    _ensure_bank(run, imported)
    record = dict(species=SPECIES, generator=DANGO_ID, source_id=SOURCE_ID,
                  arena_default=list(ARENA_POSITION),
                  distance_to_squad=squad_distance(ARENA_POSITION),
                  private_radius=PRIVATE_RADIUS, sight=SIGHT,
                  behavior_fixture=None if override is None else list(BEHAVIOR_POSITION),
                  override_applied=override is not None, override=override,
                  reason='arena default already inside the source fp11=150 Stay wake '
                         'radius of the starting squad; no override applied'
                  if override is None else override['reason'],
                  production_placement=False)
    (run / 'dangomushi-override.json').write_text(json.dumps(record, indent=2) + '\n')
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
    (run_dir / 'dangomushi-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_DANGOMUSHI_STATE generator=376003 state=(\w+)', text)
    hits = [int(n) for n in re.findall(
        r'P2_DANGOMUSHI_HIT generator=376003 pikmin=(\d+)', text)]
    rolls = [float(f) for f in re.findall(
        r'P2_DANGOMUSHI_ROLL generator=376003 frame=([\d.]+)', text)]
    positions = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(
        r'P2_DANGOMUSHI_POS generator=376003 state=\w+ clip=\w+ phase=[\d.]+ '
        r'x=(-?[\d.]+) z=(-?[\d.]+)', text)]
    spread = 0.0
    if len(positions) >= 2:
        x0, z0 = positions[0]
        spread = max(abs(x - x0) + abs(z - z0) for x, z in positions)
    # Lane-25 hazard policy markers (#376): the Turn stickable window and the
    # Rock/Egg rain decisions. Frame 32 is the turn clip loop-start key and 108
    # is key 3 (docs/PIKMIN2_SNAGRET_CRAWBSTER_AUDIT.md).
    windows = [(float(f), int(s), int(i)) for f, s, i in re.findall(
        r'P2_DANGOMUSHI_TURN_WINDOW generator=376003 frame=([\d.]+) '
        r'stickable=(\d) invulnerable=(\d)', text)]
    hazards = [(int(r), float(l), int(e)) for r, l, e in re.findall(
        r'P2_DANGOMUSHI_HAZARD generator=376003 rocks=(\d+) lifetime=([\d.]+) '
        r'egg=(\d)', text)]
    window_open = any(s == 1 and i == 0 and 31.0 <= f <= 35.0 for f, s, i in windows)
    window_close = any(s == 0 and i == 1 and 106.0 <= f <= 112.0 for f, s, i in windows)
    # Applied damage gate (#174/#376): pc_p2_dangomushi_invulnerable rejects an
    # attack/bomb outside the stickable window and admits it inside. A rejected
    # line proves the window is applied, not merely observed.
    rejects = re.findall(
        r'P2_DANGOMUSHI_DAMAGE_REJECTED generator=376003 stickable=0 invulnerable=1', text)
    accepts = re.findall(
        r'P2_DANGOMUSHI_DAMAGE_ACCEPTED generator=376003 stickable=1', text)
    # Realized children (#174/#376): the hazard rain hosts the lane-20 Rock/Egg
    # policies, so a decision now produces a real falling Rock and a real Egg
    # whose break births real P1 pellets/nectar.
    rock_births = [(int(r), int(real)) for r, real in re.findall(
        r'P2_DANGOMUSHI_ROCK_BIRTH generator=376003 requested=(\d+) real=(\d+)', text)]
    egg_births = [int(real) for real in re.findall(
        r'P2_DANGOMUSHI_EGG_BIRTH generator=376003 real=(\d)', text)]
    egg_items = [(int(kind), int(real), item) for kind, real, item in re.findall(
        r'P2_DANGOMUSHI_EGG_ITEM generator=376003 index=\d+ kind=(\d+) real=(\d) '
        r'fallback=\d item=(\w+)', text)]
    rock_strikes = re.findall(r'P2_DANGOMUSHI_ROCK_STRIKE generator=376003', text)
    rock_birth = bool(rock_births) and any(real > 0 for _, real in rock_births)
    hazard_rain = bool(hazards) and all(1 <= r <= 10 for r, _, _ in hazards) \
        and all(28.0 <= l <= 32.0 for _, l, _ in hazards)
    # The source roll window: the attack clip KEYEVENT_4 roll gate is frame 23 and
    # a HIT is only valid while the ball roll is active.
    roll_in_window = bool(rolls) and all(
        ROLL_START_FRAME - 1.0 <= frame <= ROLL_START_FRAME + 1.0 for frame in rolls)
    rolling = False
    hit_in_roll = True
    for match in re.finditer(
            r'P2_DANGOMUSHI_STATE generator=376003 state=(\w+)'
            r'|P2_DANGOMUSHI_ROLL generator=376003 frame=[\d.]+'
            r'|P2_DANGOMUSHI_HIT generator=376003 pikmin=1', text):
        token = match.group(0)
        if token.startswith('P2_DANGOMUSHI_STATE'):
            rolling = match.group(1) == 'attack'
        elif token.startswith('P2_DANGOMUSHI_ROLL'):
            rolling = True
        elif not rolling:
            hit_in_roll = False
    checks = dict(
        identity=bool(re.search(r'P2_DANGOMUSHI_BIND generator=376003 source_id=94 visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=DangoMushi native_family=Chappy '
                             r'generator=376003 .*behavior=native .*source_FSM=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        stay='stay' in states,
        wait='wait' in states,
        move='move' in states,
        attack='attack' in states,
        turn='turn' in states,
        flick='flick' in states,
        roll_event=roll_in_window,
        roll_frames=rolls,
        hit=bool(hits) and all(n >= 1 for n in hits),
        hit_pikmin=(hits[0] if hits else 0),
        hit_bounded=0 < len(hits) <= max(1, len(rolls)),
        hit_in_roll_window=hit_in_roll,
        turn_window=window_open and window_close,
        damage_rejected=bool(rejects),
        damage_accepted=bool(accepts),
        window_applied=bool(rejects),
        rock_birth=rock_birth,
        egg_birth=bool(egg_births) and any(real > 0 for real in egg_births),
        egg_item_birth=(not egg_items) or any(real > 0 and item in ('pellet', 'nectar')
                                              for _, real, item in egg_items),
        rock_strike=bool(rock_strikes),
        hazard_rain=hazard_rain,
        hazard_egg=(any(e == 1 for _, _, e in hazards) if hazards else False),
        autonomous_motion=spread > 5.0,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(v for k, v in checks.items()
                           if k not in ('roll_frames', 'hit_pikmin', 'hazard_egg',
                                        'damage_accepted', 'egg_birth', 'egg_item_birth',
                                        'rock_strike')),
                checks=checks, motion_spread=spread, exit_code=code,
                unmeasured=['dangomushi.brk material loop',
                            'P2 InteractPress roll crush (mapped to InteractFlick)',
                            'source wallCallback crash trigger (mapped to territory/crash)',
                            'full action animation bank', 'cleanup/re-entry'],
                limitations=['Batch-3 snagret arena placement is engineered fixture evidence, '
                             'not production placement evidence.',
                             'Roll contact is a single InteractFlick knockback+damage at the '
                             'first receiver inside the source fp22=100 hit radius, once per roll; '
                             'the P1 engine has no InteractPress collision callback.',
                             'The Turn stickable window is now applied: the host damage gate '
                             '(pc_p2_dangomushi_invulnerable, wired through InteractAttack and '
                             'InteractBomb) rejects attack/bomb damage outside the window and '
                             'admits it inside. Acceptance still needs a real run showing '
                             'DAMAGE_REJECTED and, when an attack lands in-window, DAMAGE_ACCEPTED.',
                             'The Rock/Egg rain is now hosted lane-side using the lane-20 '
                             'P2RockHazard / P2Egg policies: a decision births real falling '
                             'Rocks that apply real InteractPress/InteractAttack, and a real Egg '
                             'whose break births real P1 pellets/nectar. Rock fall/scale values '
                             'are the documented fixture host parms; the Egg drop table uses the '
                              'disc chances. Runtime observation of the births and strikes is still '
                              'required.',
                              'The Egg birth gate is probabilistic: eggRequested uses the source '
                              'probability formationPikis/allPikis (DangoMushi.cpp:732-748), so it '
                              'fires only while the captain has Pikmin in formation when the Turn '
                              'decision is evaluated; a real birth was observed on a fresh run '
                              '(P2_DANGOMUSHI_EGG_BIRTH real=1 + EGG_ITEM item=nectar), but other runs '
                              'may roll egg=0. Rock births and strikes remain real births.'])


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
