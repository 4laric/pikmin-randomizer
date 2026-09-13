"""Private original Impact Site arena: Titan Dweevil actor plus ordinary control (#246).

Pipeline section 4 staging for the BigTreasure lane, modeled on
``pikmin2_aquatic_arena.py`` and the P1 arena contract
(docs/PIKMIN2_ENEMY_ARENA.md). The original map/collision/routes are preserved
byte-identical, one explicit Titan Dweevil actor plus one ordinary P1 control
are appended to the practice record set, generator IDs are checked against the
stage's existing placements, full expected XYZ is recorded, the generator
offset stays zero (translation only) and source yaw is recorded as unapplied
metadata. The lane's opt-in install profile is installed into the same private
run and its bytes are re-checked.

Proxy choice: Titan Dweevil (``EnemyID_BigTreasure = 73``) has no Pikmin 1
counterpart, so the fair, audited choice is the neutral Chappy placement
vehicle - ``TEKI_Chappy = 3, // 3, Dwarf Bulborb`` at
``engine/include/teki.h:84`` - used for both the BigTreasure actor and the
ordinary control. The species identity, the 12-state FSM, the four captured
weapons and boss behavior are NOT claimed; the native seam
(``pc_p2_bigtreasure_host.h``) is opt-in only and registration is
integration-lead work (#186).

``STATUS`` consolidates the lane gates against the recorded runtime-probe
evidence: the standalone host seam verified weapon ownership/teardown and the
flat-floor/wall, elec-bounce and water-arc probes, and the reduced visual stage
ran two clips. Everything beyond that stays accurately blocked or untested.
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
from experimental.pikmin2_bigtreasure_install import (PROFILE_TXT, install,
                                                      profile_text)

# P1 teki type from engine/include/teki.h:84 (GPVE01/GPIP01 symbols):
#   TEKI_Chappy = 3, // 3, Dwarf Bulborb
# Neutral placement vehicle; BigTreasure has no P1 counterpart.
P1_CHAPPY_TYPE = 3

BIGTREASURE = 'BigTreasure'
CONTROL = 'P1 Chappy'
SPECIES = (BIGTREASURE, CONTROL)
IDS = (246001, 246002)
POSITIONS = ((0., 30., 1850.), (240., 30., 1550.))
# No authored above-ground placement yaw is audited for BigTreasure (the source
# Stay/Land emergence does not carry one); recorded as unapplied metadata, never
# encoded as translation.
SOURCE_YAW = None
PROXY = {BIGTREASURE: P1_CHAPPY_TYPE, CONTROL: P1_CHAPPY_TYPE}
FAMILY = {P1_CHAPPY_TYPE: 'Chappy (P1 Dwarf Bulborb)'}

# Consolidated lane gates: the six common arena gates
# (docs/PIKMIN2_ENEMY_ARENA.md) plus the BigTreasure/dependent-actor items the
# source audit, ownership/teardown contract, per-element attack policies and
# conversion slices left open. STATUS carries the recorded evidence for each.
GATES = ('native_identity', 'spawn_exact_xyz', 'control_undisturbed',
         'weapon_ownership_teardown', 'per_element_attacks', 'motion_staging',
         'natural_AI', 'fsm_host', 'combat', 'damage_receivers',
         'death_corpse', 'carrier_recovery', 'loozy_model',
         'skeletal_playback', 'arena_mixed_level_staging', 'reload')
STATUS = {
    'native_identity':
        'blocked: no native BigTreasure (EnemyID 73) registration in the production build; '
        'the lane seam is opt-in only (integration lead #186)',
    'spawn_exact_xyz':
        'untested: engineered arena coordinates; no native identity/XYZ spawn log for this roster',
    'control_undisturbed':
        'untested: no native run of this roster yet',
    'weapon_ownership_teardown':
        'probe-verified at the lane seam: setup captures 4 weapon pellets at 6000 HP plus Louie; '
        'defeat force-recycles the pools first, then releases weapons (0,100,0) and Louie '
        '(0,150,0) with no leak (P2_BIGTREASURE_HOST_SEAM_PASS ticks=361 events=5)',
    'per_element_attacks':
        'probe-verified at the lane seam: flat-floor/wall probes pass, elec settles after 10 '
        'first-contact bounces, water arc impacts the floor at tick 59 '
        '(P2_BIGTREASURE_ELEC_PROBE_PASS bounces=10, P2_BIGTREASURE_WATER_PROBE_PASS hits=1); '
        'real-map ballistics versus retail captures and damage application remain unmeasured',
    'motion_staging':
        'partial: only 2 of 29 converted clips are runtime-staged (wait1 frames=200, '
        'dead frames=332 keyevent100=320); the other 27 converted clips are unstaged; '
        '4 of 5 pellets staged because loozy is unconverted; baked poses, not playback',
    'natural_AI':
        'blocked: source P2 FSM not ported; Chappy placement vehicle only',
    'fsm_host':
        'blocked: the 12-state BigTreasure FSM host is not implemented; fixed seam only',
    'combat':
        'blocked: source attacks and damage receivers not registered',
    'damage_receivers':
        'blocked: InteractFire/Gas/Bubble/Denki and Pikmin/Navi damage application not registered',
    'death_corpse':
        'blocked: death sequence, throwupItem and releaseItemLoozy not wired natively',
    'carrier_recovery':
        'blocked: weapon/Louie pellet carry and delivery not registered',
    'loozy_model':
        'blocked: loozy (King of Bugs) model unconverted - the restricted converter rejects its '
        'shape matrix type 1; kept as a declared pellet_debug marker only',
    'skeletal_playback':
        'blocked: baked per-frame joint poses; no live skinning or IK',
    'arena_mixed_level_staging':
        'blocked: boss staged-phases gate - fixed placement first, mixed-level staging deferred (#186)',
    'reload':
        'untested: cleanup/re-entry and subsequent stage load not exercised',
}
# Aquatic-style compatibility view: the blocked subset only.
BLOCKED = {key: value for key, value in STATUS.items() if value.startswith('blocked')}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    """Append the Titan Dweevil actor plus the ordinary control to the practice records."""
    source = assets / 'dataDir/stages/practice/default.gen'
    header = source.read_bytes()[:24]
    practice = records(source)
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, a in enumerate(starts)]
    enemy = next(r for r in candidates if r[72:76] == b'iket')
    used = {struct.unpack_from('<I', r, 8)[0] for r in practice}
    entries = list(practice)
    placements = []
    for identity, kind, xyz in zip(IDS, SPECIES, POSITIONS):
        if identity in used:
            raise ValueError('Arena generator ID collision')
        used.add(identity)
        teki_type = PROXY[kind]
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, identity)
        row[16:48] = kind.encode('ascii').ljust(32, b'\0')
        row[80] = teki_type
        write_position(row, xyz)
        entries.append(bytes(row))
        if kind == CONTROL:
            proxy = 'ordinary P1 control'
        else:
            proxy = 'P1 Chappy placement vehicle only; Titan Dweevil identity NOT claimed'
        placements.append(dict(generator=identity, species=kind,
                               native_family=FAMILY[teki_type], native_teki_type=teki_type,
                               proxy=proxy, expected_xyz=list(validate_position(row, xyz)),
                               offset=[0, 0, 0], source_yaw=SOURCE_YAW,
                               source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def prepare(assets, imported, output):
    """Build a private arena run directory with the BigTreasure install profile applied."""
    assets = assets.resolve()
    imported = imported.resolve()
    report = json.loads((imported / 'bigtreasure.json').read_bytes())
    if report.get('policy') != 'P2_BIGTREASURE_IMPORT_1':
        raise ValueError('Expected a BigTreasure import report')
    data, actors = roster(assets)
    stage = assets / 'dataDir/stages/practice.ini'
    course = assets / 'dataDir/courses/practice'
    preserved = {str(path.relative_to(assets)).replace('\\', '/'): digest(path)
                 for path in course.rglob('*') if path.is_file()}
    if not preserved:
        raise ValueError('Original Impact Site course missing')
    run = output.resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': stage.read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/arena-private.txt': b'P1 original stage arena\n'}
    for path in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + path.name, empty)
    overlay(assets, run / 'assets', overrides)
    birth = deterministic_births(run / 'assets/dataDir/stages/chal0/default.gen',
                                 [a['generator'] for a in actors])
    receipt = install(run)
    if (run / PROFILE_TXT).read_bytes() != profile_text().encode('utf-8'):
        raise ValueError('Installed BigTreasure profile mismatch')
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=len(actors), control=CONTROL,
                  source_stage_sha256=digest(stage), preserved_course_sha256=preserved,
                  import_sha256=digest(imported / 'bigtreasure.json'),
                  install=receipt, birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by deterministic fixture '
                          'override (PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not '
                          'production placement evidence',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn '
                                   'acceptance unmeasured',
                  gates=dict(STATUS),
                  limitations=['Source BigTreasure visuals only; no native behavior',
                               'Titan Dweevil has no P1 counterpart: Chappy placement vehicle '
                               'only, identity NOT claimed',
                               'loozy (King of Bugs) model unconverted; 27 of 29 clips are not '
                               'runtime-staged and there is no skeletal playback',
                               'Fixed placement only (staged-phases gate); mixed-level staging deferred',
                               'No source yaw applied',
                               'Native registration/hook wiring pending integration lead (#186)'])
    (run / 'arena.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.imported, args.output))
