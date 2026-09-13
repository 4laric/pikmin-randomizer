"""Private original Impact Site arena staging: Mar + Hanachirashi plus P1 control.

Batch 2 (#375, parent #166) per docs/PIKMIN2_ENEMY_ARENA.md. Original
map/collision/routes are preserved byte-identical, one explicit actor per
spawnable flying species plus one ordinary P1 control, generator IDs unique
against the stage's existing placements, full expected XYZ recorded. Generator
position plus offset is translation only (zero offset); source yaw is recorded
as explicitly unapplied metadata. The default generator scatter circle is zeroed
by the deterministic fixture override, which is an engineered choice, not
production placement evidence.

ShijimiChou (77) is helper-only for this lane and is deliberately NOT spawned
and NOT installed as a lane visual; it is recorded as helper/reward metadata in
the arena manifest while runtime ownership stays with its family owner. Mar and
Hanachirashi stage on the P1 Puffy Blowhog proxy (tekimgr.cpp tekiNames[16]
"mar", the direct P1 ancestor); the withering Hanachirashi variant has no P1
counterpart, so its behavior is a proxy only. Native registration is blocked
until the native track registers pc_p2_flying (flagged on #375 / #186).
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
from experimental.pikmin2_flying_assets import (
    HELPER_SPECIES, SHIJIMICHOU_GROUP_COUNT, SPECIES as ENEMY_IDS)
from experimental.pikmin2_flying_install import install, verify_install

IDS = (375001, 375002, 375003)
POSITIONS = ((-150., 30., 1850.), (-50., 30., 1850.), (150., 30., 1550.))
P1_PUFFY_TYPE = 16   # tekimgr.cpp tekiNames[16] "mar" (P1 Puffy Blowhog)
P1_CHAPPY_TYPE = 3   # control actor, ordinary P1 combat enemy (Dwarf Bulborb)
SOURCE_YAW = None

GATES = ('native_identity', 'natural_AI', 'wind_attack', 'flick_shakeoff',
         'death_corpse', 'day_floor_reset', 'save_load', 'piklopedia_observation',
         'helper_group_ownership')
GATE_STATES = {
    'native_identity': 'blocked: no pc_p2_flying native registration (native track; flagged on #375)',
    'natural_AI': 'blocked: no P2 blowhog FSM registered in the P1 engine (integration lead)',
    'wind_attack': 'blocked: P2-only InteractWind/InteractHanaChirashi emitters; needs native registration',
    'flick_shakeoff': 'blocked: P2-only Mar/Hanachirashi FSM; needs native registration',
    'death_corpse': 'blocked: P2-only EnemyBase::onKill reward metadata; needs native registration',
    'day_floor_reset': 'blocked: P2-only manager reset/reentry; needs native registration',
    'save_load': 'blocked: P2-only Creature::save/doSave; needs native registration',
    'piklopedia_observation': 'blocked: P2-only discovery counters; needs native registration',
    'helper_group_ownership': ('blocked: ShijimiChou runtime ownership stays with its family '
                               'owner (Tanpopo/Ooinu_l/Magaret/Damagumo/Mamuta/plant nodes)'),
}

HELPER_METADATA = dict(species=HELPER_SPECIES[0], enemy_id=ENEMY_IDS[HELPER_SPECIES[0]],
                       helper_only=True, spawned=False, installed_visuals=False,
                       group_count=SHIJIMICHOU_GROUP_COUNT,
                       runtime_owner=('family owners (Tanpopo, Ooinu_l, Magaret, '
                                      'Damagumo, Mamuta, plant nodes)'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    """Append the three-actor roster to the original practice stage records."""
    source = assets / 'dataDir/stages/practice/default.gen'
    header = source.read_bytes()[:24]
    entries = list(records(source))
    used = {struct.unpack_from('<I', record, 8)[0] for record in entries}
    # Reuse the audited one-actor enemy template framing, never its placement.
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[start:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, start in enumerate(starts)]
    enemy = next(record for record in candidates if record[72:76] == b'iket')
    actors = ((IDS[0], 'P2 Mar', 'Mar', P1_PUFFY_TYPE, POSITIONS[0]),
              (IDS[1], 'P2 Hanachirashi', 'Hanachirashi', P1_PUFFY_TYPE, POSITIONS[1]),
              (IDS[2], 'P1 Chappy control', None, P1_CHAPPY_TYPE, POSITIONS[2]))
    placements = []
    for identity, kind, source_species, teki_type, xyz in actors:
        if identity in used:
            raise ValueError('Arena generator ID collision')
        used.add(identity)
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, identity)
        row[16:48] = kind.encode('ascii').ljust(32, b'\0')
        row[80] = teki_type
        write_position(row, xyz)
        entries.append(bytes(row))
        placements.append(dict(
            generator=identity, species=kind,
            source_species=source_species,
            source_enemy_id=ENEMY_IDS[source_species] if source_species else None,
            native_family=('Puffy Blowhog' if teki_type == P1_PUFFY_TYPE else 'Chappy'),
            native_teki_type=teki_type,
            expected_xyz=list(validate_position(row, xyz)), offset=[0, 0, 0],
            source_yaw=SOURCE_YAW, source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def prepare(assets, imported, output):
    """Build a private arena run directory with the flying visual bank installed."""
    assets = assets.resolve()
    imported = imported.resolve()
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
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True, exist_ok=True)
    spawnable = [(actor['generator'], actor['source_species'])
                 for actor in actors if actor['source_species']]
    birth = deterministic_births(run / 'assets/dataDir/stages/chal0/default.gen',
                                 [actor['generator'] for actor in actors])
    receipt = install(imported, run, spawnable)
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    verified = verify_install(imported, run, spawnable)
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    if set(GATES) != set(GATE_STATES):
        raise ValueError('Gate contract mismatch')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=len(actors), helper=HELPER_METADATA,
                  source_stage_sha256=digest(stage),
                  preserved_course_sha256=preserved,
                  flying_manifest_sha256=digest(imported / 'flying.json'),
                  install=receipt, install_verified=verified, birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by deterministic fixture '
                          'override (PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not '
                          'production placement evidence',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn '
                                   'acceptance unmeasured',
                  gates=dict(GATE_STATES),
                  limitations=['P1 Puffy Blowhog proxy placement; not source P2 Mar/'
                               'Hanachirashi FSM',
                               'Hanachirashi (withering variant) has no P1 counterpart; '
                               'P1 Puffy Blowhog behavior is a proxy only',
                               'No source yaw applied',
                               'ShijimiChou (77) helper-only: not spawned, not installed as '
                               'a lane visual; runtime ownership stays with its family owner',
                               'Native registration pending integration lead (#186/#375)'])
    (run / 'arena.json').write_text(json.dumps(result, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.imported, args.output))
