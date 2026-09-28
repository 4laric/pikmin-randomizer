"""Private original Impact Site arena staging for ShijimiChou (Unmarked
Spectralids, EnemyID 77) on independent P1 Chappy placement vehicles.

The shared flying arena (#375) deliberately excludes ShijimiChou: it is
helper-only there and is never spawned. This private arena stages it itself, a
small plant-origin Yellow group of three actors near the 20-red fixture squad,
so the source group-leader convention (first actor leads, members trace) and the
source genItem nectar reward are observable. Generator IDs 375004/375005/375006
are unique against the stage's existing placements. Original map/collision/
routes are preserved byte-identical; generator position plus offset is
translation only (zero offset) and source yaw is recorded as explicitly
unapplied metadata. The default scatter circle is zeroed by the deterministic
fixture override, which is an engineered choice, not production placement
evidence.

The converted ShijimiChou poses already exist in the flying import manifest
(`output/p2-lane-verify/flying/flying.json`, clip status `converted`); the lane
install excludes them because it refuses helper visuals. This arena copies the
exact manifest-listed `fly_ShijimiChou_<clip>_NN.mod` bytes into the private
room and writes the `P2_FLYING_ACTORS_1` / `p2-flying-bank.txt` pair the native
`pc_p2_batch3` loader consumes. No converter change is required.
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
from experimental.pikmin2_flying_assets import SPECIES as ENEMY_IDS
from experimental.pikmin2_flying_install import bank_text

LEADER_ID = 375004
MEMBER_IDS = (375005, 375006)
IDS = (LEADER_ID,) + MEMBER_IDS
SPECIES = 'ShijimiChou'
SOURCE_ID = ENEMY_IDS[SPECIES]
P1_CHAPPY_TYPE = 3   # tekimgr.cpp tekiNames[3] "chap" (P1 Dwarf Bulborb)
MANIFEST = 'flying.json'
ACTORS_TXT = 'p2-flying-actors.txt'
BANK_TXT = 'p2-flying-bank.txt'
FIXTURE_TXT = 'p2-shijimi-fixture.txt'

# Leader and two members beside the fixture squad (x in [-140,-68],
# z in [1812,1820], y=30). All start inside the source fp12=275 sight and the
# 180-unit wake radius so the leader leaves Wait.
POSITIONS = ((LEADER_ID, (-104.0, 30.0, 1832.0)),
             (MEMBER_IDS[0], (-100.0, 30.0, 1842.0)),
             (MEMBER_IDS[1], (-110.0, 30.0, 1842.0)))
# Fixture-only lethal injection seconds (staggered after the leader has flown).
LETHAL = {LEADER_ID: 5.0, MEMBER_IDS[0]: 5.5, MEMBER_IDS[1]: 6.0}
SOURCE_YAW = None

GATES = ('native_identity', 'group_leader', 'movement_animation', 'nectar_reward',
         'death_corpse', 'cleanup_reentry')
GATE_STATES = {
    'native_identity': 'PASS: pc_p2_shijimi registers on TEKI_Chappy and logs P2_SHIJIMI_BIND',
    'group_leader': 'PASS(approx): lowest generator leads; members trace the live leader',
    'movement_animation': 'PASS: Wait -> Fly with move clip phase and POS spread',
    'nectar_reward': 'PASS: source genItem OBJTYPE_Water Honey at Dead end, exactly-once',
    'death_corpse': 'PASS: Fall -> Dead -> actor->die() host corpse handoff; dead-shape draw observed',
    'cleanup_reentry': 'PARTIAL: teki forget/reset wired; re-entry/day-floor respawn untested',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    """Append the ShijimiChou cluster to the original practice stage records."""
    source = assets / 'dataDir/stages/practice/default.gen'
    header = source.read_bytes()[:24]
    entries = list(records(source))
    used = {struct.unpack_from('<I', record, 8)[0] for record in entries}
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[start:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, start in enumerate(starts)]
    enemy = next(record for record in candidates if record[72:76] == b'iket')
    placements = []
    for generator_id, xyz in POSITIONS:
        if generator_id in used:
            raise ValueError('Arena generator ID collision')
        used.add(generator_id)
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, generator_id)
        row[16:48] = f'P2 ShijimiChou {generator_id}'.encode('ascii').ljust(32, b'\0')
        row[80] = P1_CHAPPY_TYPE
        write_position(row, xyz)
        entries.append(bytes(row))
        placements.append(dict(
            generator=generator_id, species=SPECIES, source_species=SPECIES,
            source_enemy_id=SOURCE_ID, native_family='Chappy',
            native_teki_type=P1_CHAPPY_TYPE, role=('leader' if generator_id == LEADER_ID
                                                   else 'member'),
            expected_xyz=list(validate_position(row, xyz)), offset=[0, 0, 0],
            source_yaw=SOURCE_YAW, source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def pose_bytes(imported):
    """Exact manifest-listed ShijimiChou pose bytes, hash-checked."""
    metadata = json.loads((imported / MANIFEST).read_text())
    info = metadata['species'][SPECIES]
    files = {}
    for clip in info.get('clips', []):
        for pose in clip.get('poses', []):
            name = pose.get('file')
            if not name:
                continue
            if Path(name).name != name or not name.endswith('.mod'):
                raise ValueError('Unsafe ShijimiChou pose filename')
            data = (imported / SPECIES / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != pose.get('sha256'):
                raise ValueError('ShijimiChou pose hash mismatch: ' + name)
            files[name] = data
    if not files:
        raise ValueError('Flying import manifest carries no ShijimiChou poses; '
                         'the converter must add them')
    helper = metadata['species'][SPECIES]
    if not helper.get('helper_only'):
        raise ValueError('Expected helper-only ShijimiChou metadata')
    return files, bank_text(metadata), metadata


def prepare(assets, imported, output):
    """Build a private arena run with the ShijimiChou cluster and visual bank."""
    assets = assets.resolve()
    imported = imported.resolve()
    data, actors = roster(assets)
    stage = assets / 'dataDir/stages/practice.ini'
    course = assets / 'dataDir/courses/practice'
    preserved = {str(path.relative_to(assets)).replace('\\', '/'): digest(path)
                 for path in course.rglob('*') if path.is_file()}
    if not preserved:
        raise ValueError('Original Impact Site course missing')
    files, bank, metadata = pose_bytes(imported)
    run = output.resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': stage.read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/arena-private.txt': b'P1 ShijimiChou arena\n'}
    for path in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + path.name, empty)
    overlay(assets, run / 'assets', overrides)
    room = run / 'assets/dataDir/courses/pikmin2room'
    room.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        (room / name).write_bytes(payload)
    (run / BANK_TXT).write_bytes(bank.encode('ascii'))
    actors_text = 'P2_FLYING_ACTORS_1 %d\n' % len(IDS) + ''.join(
        f'{generator_id} {SPECIES}\n' for generator_id in IDS)
    (run / ACTORS_TXT).write_bytes(actors_text.encode('ascii'))
    (run / FIXTURE_TXT).write_bytes(
        ('P2_SHIJIMI_FIXTURE_1\nsource plants\n' + ''.join(
            f'lethal {generator_id} {seconds}\n'
            for generator_id, seconds in LETHAL.items())).encode('ascii'))
    birth = deterministic_births(run / 'assets/dataDir/stages/chal0/default.gen',
                                 [actor['generator'] for actor in actors])
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    if set(GATES) != set(GATE_STATES):
        raise ValueError('Gate contract mismatch')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=len(actors), species=SPECIES, enemy_id=SOURCE_ID,
                  source_stage_sha256=digest(stage),
                  preserved_course_sha256=preserved,
                  flying_manifest_sha256=digest(imported / MANIFEST),
                  pose_sha256={name: digest(room / name) for name in files},
                  source='plants', spec_type='yellow',
                  nectar_rate=0.2, group_count=3,
                  birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by deterministic '
                          'fixture override (PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered '
                          'choice, not production placement evidence',
                  fixture=dict(path=FIXTURE_TXT, source='plants',
                               lethal={str(k): v for k, v in LETHAL.items()},
                               note='fixture-only lethal injection; the unattended 20-red '
                                    'squad never receives attack orders'),
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates near the 20-red fixture '
                                   'squad; terrain/physical spawn acceptance unmeasured',
                  gates=dict(GATE_STATES),
                  limitations=['P1 Chappy placement vehicle; not a source Spectralid group '
                               'factory',
                               'Three-actor cluster approximates the source group; the '
                               'full 25-member group, sound cluster and mEfxDown feather '
                               'effect are not ported',
                               'Plants-origin Yellow group chosen so the source genItem '
                               'rule is deterministic; the fp02=0.2 nectar roll and the '
                               'Red/Purple demo-flag gates are implemented but not '
                               'exercised here',
                               'No source yaw applied',
                               'Native registration stays on #186/#407'])
    (run / 'arena.json').write_text(json.dumps(result, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.imported, args.output))
