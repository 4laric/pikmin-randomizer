"""Private original Impact Site arena: one source-visual Mamuta proxy and one P1 control.

Batch 2 (#221). Proxy behavior is native P1 Miurin (TEKI_Miurin 24, 'tkmr'),
the direct ancestor of P2 Miulin; visuals come from the batch-1 extraction via
pikmin2_mamuta_install. Engineered arena coordinates; gates start UNTESTED and
require a native runtime pass.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import uuid

from scripts.preview_pikmin2_room import records, generator, overlay
from experimental.pikmin2_generator_pose import write_position, validate_position
from experimental.pikmin2_uji_grounded_fixture import deterministic_births
from experimental.pikmin2_mamuta_install import install, verify_install

P1_MIURIN_TYPE = 24  # tekimgr.cpp tekiNames[24] = "miurin", Mamuta
P1_CHAPPY_TYPE = 3   # control actor, ordinary P1 combat enemy
GATES = ('native_identity', 'natural_AI', 'bury_attack', 'flick_collateral',
         'territory_watchdog', 'death_corpse', 'day_floor_reset', 'save_load',
         'piklopedia_observation')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
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
    actors = [(221001, 'P2 Mamuta', P1_MIURIN_TYPE, (-150., 30., 1850.)),
              (221002, 'P1 Chappy control', P1_CHAPPY_TYPE, (150., 30., 1550.))]
    for identity, kind, teki_type, xyz in actors:
        if identity in used:
            raise ValueError('Arena generator ID collision')
        used.add(identity)
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, identity)
        row[16:48] = kind.encode('ascii').ljust(32, b'\0')
        row[80] = teki_type
        write_position(row, xyz)
        entries.append(bytes(row))
        placements.append(dict(generator=identity, species=kind,
                               native_family='Miurin' if teki_type == P1_MIURIN_TYPE else 'Chappy',
                               native_teki_type=teki_type,
                               position=list(validate_position(row, xyz)),
                               offset=[0, 0, 0], source_yaw=None, source_yaw_applied=False))
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
    overrides = {'dataDir/stages/chal0.ini': stage.read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/arena-private.txt': b'P1 original stage arena\n'}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True, exist_ok=True)
    birth = deterministic_births(run / 'assets/dataDir/stages/chal0/default.gen',
                                 [a['generator'] for a in actors])
    installed = install(imported, run, [(a['generator'], 'Miulin') for a in actors
                                        if a['native_family'] == 'Miurin'])
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    verified = verify_install(imported, run, [(a['generator'], 'Miulin') for a in actors
                                              if a['native_family'] == 'Miurin'])
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=2, source_stage_sha256=digest(stage),
                  preserved_course_sha256=preserved,
                  import_sha256=digest(imported / 'mamuta.json'),
                  installed=installed, install_verified=verified,
                  birth_policy=birth,
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn acceptance unmeasured',
                  gates={key: 'untested' for key in GATES},
                  limitations=['P1 Miurin proxy behavior; not source P2 Miulin FSM',
                               'P1 bury semantics differ: in-place flowering, no 99 cap (see PIKMIN2_MAMUTA_BEHAVIOR.md)',
                               'No source yaw applied',
                               'Native fixture hooks for bury/cap/Piklopedia observation are integration-lead work, flagged in #221'])
    (run / 'arena.json').write_text(json.dumps(result, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    print(prepare(a.assets, a.imported, a.output))
