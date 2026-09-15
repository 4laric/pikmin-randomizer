"""Private original Impact Site arena staging: one Dwarf Orange Bulborb plus P1 control.

Arena contract (docs/PIKMIN2_ENEMY_ARENA.md): original map/collision/routes
preserved byte-identical, one explicit family actor plus one ordinary P1
control, generator IDs unique against the stage's existing placements, full
expected XYZ recorded. Generator position plus offset is translation only
(zero offset); source yaw is recorded as explicitly unapplied metadata. The
default generator scatter circle is zeroed by the deterministic fixture
override, which is an engineered choice, not production placement evidence.
Native identity/lifecycle gates remain untested until the integration lead
(#186) registers the actor and a fixed build runs.
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
from experimental.pikmin2_dwarf_orange_install import install

IDS = (211001, 211002)
POSITIONS = ((-150., 30., 1850.), (150., 30., 1550.))
SPECIES = ('BlueKochappy', 'P1 Chappy')
# Source yaw: no authored above-ground source placement yaw was audited for
# BlueKochappy (P2 cave spawn); kept as unapplied metadata, never in offsets.
SOURCE_YAW = None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    """Append the two-actor roster to the original practice stage records."""
    source = assets / 'dataDir/stages/practice/default.gen'
    header = source.read_bytes()[:24]
    entries = list(records(source))
    used = {struct.unpack_from('<I', r, 8)[0] for r in entries}
    # Reuse the audited one-actor enemy template framing, never its placement.
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))] for n, a in enumerate(starts)]
    enemy = next(r for r in candidates if r[72:76] == b'iket')
    placements = []
    for identity, kind, xyz in zip(IDS, SPECIES, POSITIONS):
        if identity in used:
            raise ValueError('Arena generator ID collision')
        used.add(identity)
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, identity)
        # lane-03 (#439): mark both arena actors save-eligible so the day-end
        # generator-cache loop selects them (GENCARRY_SaveGenerator = 1 << 0).
        struct.pack_into('>I', row, 12, 1)
        row[16:48] = kind.encode('ascii').ljust(32, b'\0')
        write_position(row, xyz)
        entries.append(bytes(row))
        placements.append(dict(generator=identity, species=kind, native_family='Chappy',
                               expected_xyz=list(validate_position(row, xyz)), offset=[0, 0, 0],
                               source_yaw=SOURCE_YAW, source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def prepare(assets, bank, profile, output):
    """Build a private arena run directory with the family visual installed."""
    assets = assets.resolve()
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
    birth = deterministic_births(run / 'assets/dataDir/stages/chal0/default.gen',
                                 [a['generator'] for a in actors])
    receipt = install(Path(bank), Path(profile), run, [actors[0]['generator']])
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=2, source_stage_sha256=digest(stage),
                  preserved_course_sha256=preserved,
                  install=receipt, birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by deterministic fixture override '
                          '(PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not production placement evidence',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn acceptance unmeasured',
                  gates={key: 'untested' for key in
                         ('native_identity', 'natural_AI', 'combat', 'death', 'delivery', 'reload')},
                  limitations=['Source BlueKochappy visuals and health only; proxy P1 AI, not P2 FSM',
                               'No source yaw applied', 'Native registration pending integration lead (#186)',
                               'No Pod reward binding; native P1 corpse behavior retained'])
    (run / 'arena.json').write_text(json.dumps(result, indent=2))
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'bank', 'profile', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.bank, args.profile, args.output))
