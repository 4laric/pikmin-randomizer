"""Private original Impact Site arena for the ShijimiChou native slice (#166).

Stages a small plant-origin Unmarked Spectralids group on the private P1 Chappy
placement vehicle plus one ordinary P1 control. The original map/collision/routes
are preserved byte-identical; the starting 20-red squad is added by
``scripts/preview_pikmin2_room.overlay`` -> ``ensure_pikmin_squad`` (it does not
disable extinction). Generator position plus offset is translation only (zero
offset); source yaw is explicitly unapplied. Engineered coordinates, not
production placement evidence.
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
from experimental.pikmin2_shijimi_install import SOURCE_ID, install, verify_install

P1_CHAPPY_TYPE = 3            # tekimgr.cpp "chappy" (Dwarf Bulborb placement vehicle)
CONTROL_GENERATOR = 204999    # ordinary P1 Chappy control
SHIJIMI_GENERATORS = (204001, 204002)
SHIJIMI_POSITIONS = ((-150.0, 30.0, 1850.0), (-100.0, 30.0, 1850.0))
CONTROL_POSITION = (150.0, 30.0, 1550.0)

GATES = ('native_identity', 'natural_AI', 'receiver', 'death_corpse',
         'transport_reward', 'cleanup_reentry')
GATE_STATES = {
    'native_identity': 'untested: pc_p2_shijimi registration staged here',
    'natural_AI': 'untested: Wait/Fly/Leave source FSM, no fixture injection',
    'receiver': 'source-backed N/A: source damageCallBack returns false',
    'death_corpse': 'untested: Fall/Dead runs only on natural health <= 0',
    'transport_reward': 'blocked: genItem nectar is lane 06 owned; marker only',
    'cleanup_reentry': 'blocked: #397 lifecycle',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    source = assets / 'dataDir/stages/practice/default.gen'
    header = source.read_bytes()[:24]
    practice = list(records(source))
    used = {struct.unpack_from('<I', record, 8)[0] for record in practice}
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, a in enumerate(starts)]
    enemy = next(record for record in candidates if record[72:76] == b'iket')
    entries = list(practice)
    placements = []
    rows = [(gen, 'P2 ShijimiChou', SHIJIMI_POSITIONS[i], P1_CHAPPY_TYPE)
            for i, gen in enumerate(SHIJIMI_GENERATORS)]
    rows.append((CONTROL_GENERATOR, 'P1 Chappy control', CONTROL_POSITION, P1_CHAPPY_TYPE))
    for identity, kind, xyz, teki_type in rows:
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
            generator=identity, species=kind, source_species='ShijimiChou' if identity != CONTROL_GENERATOR else None,
            source_enemy_id=SOURCE_ID if identity != CONTROL_GENERATOR else None,
            native_family='Chappy', native_teki_type=teki_type,
            position=list(validate_position(row, xyz)), offset=[0, 0, 0],
            source_yaw=None, source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def prepare(assets, imported, output):
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
    overrides = {
        'dataDir/stages/chal0.ini': stage.read_bytes(),
        'dataDir/stages/chal0/default.gen': data,
        'dataDir/courses/pikmin2room/arena-private.txt': b'P1 original stage arena\n',
    }
    for path in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + path.name, empty)
    overlay(assets, run / 'assets', overrides)
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True, exist_ok=True)
    birth = deterministic_births(run / 'assets/dataDir/stages/chal0/default.gen',
                                 [actor['generator'] for actor in actors])
    receipt = install(imported, run, list(SHIJIMI_GENERATORS))
    verified = verify_install(imported, run, list(SHIJIMI_GENERATORS))
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    if set(GATES) != set(GATE_STATES):
        raise ValueError('Gate contract mismatch')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=len(actors), source_id=SOURCE_ID,
                  source_stage_sha256=digest(stage), preserved_course_sha256=preserved,
                  flying_manifest_sha256=digest(imported / 'flying.json'),
                  install=receipt, install_verified=verified, birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by the deterministic fixture override',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn acceptance unmeasured',
                  gates=dict(GATE_STATES),
                  limitations=['P1 Chappy placement vehicle; not source P2 group factory',
                               'Cluster is 2 actors, not the source 25-member group',
                               'No source yaw applied',
                               'Reward is a marker/scene item only; lane 06 owns reward semantics'])
    (run / 'arena.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.imported, args.output))
