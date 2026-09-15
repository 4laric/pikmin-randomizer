"""Private original Impact Site arena: Snagret pair + standalone DangoMushi + P1 control.

Arena contract (docs/PIKMIN2_ENEMY_ARENA.md, issue #376, parent #174): the
original map/collision/routes are preserved byte-identical, one explicit actor
is placed per species plus one ordinary P1 control, generator IDs are unique
against the stage's existing placements, and the full expected XYZ is recorded.
Generator position plus offset is translation only (zero offset); source yaw is
recorded as explicitly unapplied metadata. The default generator scatter circle
is zeroed by the deterministic fixture override (an engineered choice, not
production placement evidence).

Species-specific: SnakeCrow and SnakeWhole are the shared-base snagret pair
(`Game::SnakeJointMgr` over bodyjnt3-bodyjnt8); DangoMushi is the standalone
segmented `EnemyBase`/`EnemyBlendAnimatorBase` Crawbster. Neither family has a
Pikmin 1 counterpart, so the three P2 actors reuse the audited one-actor enemy
template (native type = template's P1 dwarf bulborb) purely as a placement
vehicle. Native registration belongs to the integration lead (#186) and is
flagged on #376; every native-dependent gate is BLOCKED, not over-claimed.
"""
import argparse
import hashlib
import json
import struct
import uuid
from pathlib import Path

from scripts.preview_pikmin2_room import generator, overlay, records
from experimental.pikmin2_generator_pose import validate_position, write_position
from experimental.pikmin2_uji_grounded_fixture import deterministic_births
from experimental.pikmin2_snagret_assets import SPECIES as SOURCE_SPECIES
from experimental.pikmin2_snagret_install import install, verify_install

P1_CHAPPY_TYPE = 3          # ordinary P1 combat enemy control
P1_TEMPLATE_ENEMY_TYPE = 3  # P1 dwarf bulborb placement template (vehicle only)
IDS = (376001, 376002, 376003, 376004)
ACTORS = (('SnakeCrow', 376001), ('SnakeWhole', 376002), ('DangoMushi', 376003),
          ('P1 Chappy', 376004))
POSITIONS = ((-150., 30., 1850.), (-50., 30., 1850.), (50., 30., 1850.),
             (150., 30., 1550.))
# Source yaw: snagrets emerge from burrows and DangoMushi falls/rolls with
# runtime headings; no authored above-ground placement yaw was audited. Kept
# as unapplied metadata, never encoded as translation.
SOURCE_YAW = None
GATES = ('native_identity', 'shared_snake_joint_spine', 'natural_AI',
         'appear_burrow', 'directional_bite', 'run1_jump', 'segmented_roll_turn',
         'attack2_flick', 'falling_helpers', 'brk_material_loop', 'death_corpse',
         'day_floor_reset', 'save_load', 'piklopedia_observation')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    """Append the four-actor roster to the original practice stage records."""
    source = assets / 'dataDir/stages/practice/default.gen'
    header = source.read_bytes()[:24]
    entries = list(records(source))
    used = {struct.unpack_from('<I', r, 8)[0] for r in entries}
    # Reuse the audited one-actor enemy template framing, never its placement.
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, a in enumerate(starts)]
    enemy = next(r for r in candidates if r[72:76] == b'iket')
    placements = []
    for (species, identity), xyz in zip(ACTORS, POSITIONS):
        if identity in used:
            raise ValueError('Arena generator ID collision')
        used.add(identity)
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, identity)
        row[16:48] = species.encode('ascii').ljust(32, b'\0')
        source_species = species in SOURCE_SPECIES
        if not source_species:
            row[80] = P1_CHAPPY_TYPE
        write_position(row, xyz)
        entries.append(bytes(row))
        placements.append(dict(
            generator=identity, species=species,
            native_family='template P1 dwarf bulborb (placement vehicle only)'
            if source_species else 'Chappy (ordinary P1 control)',
            native_teki_type=None if source_species else P1_CHAPPY_TYPE,
            proxy_behavior='unregistered P2 species; no P1 counterpart (batch-1 audit)'
            if source_species else None,
            expected_xyz=list(validate_position(row, xyz)), offset=[0, 0, 0],
            source_yaw=SOURCE_YAW, source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def prepare(assets, imported, output):
    """Build a private arena run directory with the snagret visual bank installed."""
    assets = assets.resolve()
    imported = imported.resolve()
    data, actors = roster(assets)
    stage = assets / 'dataDir/stages/practice.ini'
    course = assets / 'dataDir/courses/practice'
    preserved = {str(p.relative_to(assets)).replace('\\', '/'): digest(p)
                 for p in course.rglob('*') if p.is_file()}
    if not preserved:
        raise ValueError('Original Impact Site course missing')
    run = output.resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': stage.read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/arena-private.txt': b'P1 original stage arena\n'}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True, exist_ok=True)
    birth = deterministic_births(run / 'assets/dataDir/stages/chal0/default.gen',
                                 [a['generator'] for a in actors])
    family = [(a['generator'], a['species']) for a in actors
              if a['species'] in SOURCE_SPECIES]
    installed = install(imported, run, family)
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    verified = verify_install(imported, run, family)
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    result = dict(
        schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
        enemy_count=4, source_stage_sha256=digest(stage),
        preserved_course_sha256=preserved,
        import_sha256=digest(imported / 'snagret.json'),
        installed=installed, install_verified=verified, birth_policy=birth,
        scatter='Default generator scatter circle zeroed by deterministic fixture override '
                '(PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not production placement evidence',
        command=['nectar.exe', '--experimental-pikmin2-room'],
        placement_choice='Engineered arena coordinates; terrain/physical spawn acceptance unmeasured',
        gates={
            'native_identity': 'blocked: no native registration for SnakeCrow/SnakeWhole/DangoMushi '
                               '(integration lead #186; flagged on #376)',
            'shared_snake_joint_spine': 'blocked: SnakeJointMgr bodyjnt3-bodyjnt8 callback unregistered',
            'natural_AI': 'blocked: no P1 counterpart; proxy mapping undecided (integration lead)',
            'appear_burrow': 'blocked: source P2 burrow-emerge FSM not executable in P1 engine',
            'directional_bite': 'blocked: hit_near/hit/hit_far/hit_r/hit_l selection needs native anim bank',
            'run1_jump': 'blocked: SnakeWhole run1 leap is P2-only (SnakeWhole.h:236-241)',
            'segmented_roll_turn': 'blocked: DangoMushi ball roll / wall-crash turn is P2-only',
            'attack2_flick': 'blocked: DangoMushi attack_2 flick is P2-only',
            'falling_helpers': 'blocked: DangoMushi Rock/Egg child spawner not reproduced',
            'brk_material_loop': 'blocked: dangomushi.brk material loop needs native animator',
            'death_corpse': 'blocked: source death/corpse path needs native registration',
            'day_floor_reset': 'untested: native day reset behavior not measured',
            'save_load': 'untested: save/load round-trip not measured',
            'piklopedia_observation': 'blocked: P2 Piklopedia not present in P1 engine'},
        limitations=['Source Snagret/Crawbster visuals only; no native behavior',
                     'No source yaw applied',
                     'SnakeCrow+SnakeWhole share SnakeJointMgr; DangoMushi stays standalone',
                     'Native registration pending integration lead (#186/#376)',
                     'P2 actors use the P1 dwarf bulborb placement template; no P1 proxy species decided'])
    (run / 'arena.json').write_text(json.dumps(result, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.imported, args.output))
