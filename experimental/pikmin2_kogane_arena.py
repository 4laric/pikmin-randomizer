"""Private original Impact Site arena staging: Kogane/Wealthy/Fart plus P1 control.

Arena contract (docs/PIKMIN2_ENEMY_ARENA.md): original map/collision/routes
preserved byte-identical, one explicit actor per beetle species plus one
ordinary P1 control, generator IDs unique against the stage's existing
placements, full expected XYZ recorded. Generator position plus offset is
translation only (zero offset); source yaw is recorded as explicitly
unapplied metadata. The default generator scatter circle is zeroed by the
deterministic fixture override, which is an engineered choice, not production
placement evidence.

Beetle specific: the family has no Pikmin 1 counterpart (batch-1 audit,
docs/PIKMIN2_KOGANE_AUDIT.md section 6), so no P1 proxy species mapping is
decided in this lane. The roster reuses the audited one-actor enemy template
framing (native type = template's P1 dwarf bulborb) purely as a placement
vehicle; flip/drop, Fart gas, forced escape and cave relocation gates stay
BLOCKED until the native track registers pc_p2_kogane (flagged on #219).
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
from experimental.pikmin2_kogane_install import install

IDS = (219001, 219002, 219003, 219004)
SPECIES = ('kogane', 'wealthy', 'fart', 'P1 Chappy')
POSITIONS = ((-150., 30., 1850.), (-50., 30., 1850.), (50., 30., 1850.), (150., 30., 1550.))
# Source yaw: beetles burrow-emerge and wander with random headings
# (Kogane.cpp setTargetPosition); no authored above-ground placement yaw was
# audited. Kept as unapplied metadata, never in offsets.
SOURCE_YAW = None


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
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))] for n, a in enumerate(starts)]
    enemy = next(r for r in candidates if r[72:76] == b'iket')
    placements = []
    for identity, kind, xyz in zip(IDS, SPECIES, POSITIONS):
        if identity in used:
            raise ValueError('Arena generator ID collision')
        used.add(identity)
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, identity)
        row[16:48] = kind.encode('ascii').ljust(32, b'\0')
        write_position(row, xyz)
        entries.append(bytes(row))
        placements.append(dict(generator=identity, species=kind,
                               native_family='template P1 dwarf bulborb (placement vehicle only)',
                               expected_xyz=list(validate_position(row, xyz)), offset=[0, 0, 0],
                               source_yaw=SOURCE_YAW, source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def prepare(assets, bank, output):
    """Build a private arena run directory with the beetle visual bank installed."""
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
    receipt = install(Path(bank), run, [a['generator'] for a in actors if a['species'] != 'P1 Chappy'])
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=4, source_stage_sha256=digest(stage),
                  preserved_course_sha256=preserved,
                  install=receipt, birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by deterministic fixture override '
                          '(PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not production placement evidence',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn acceptance unmeasured',
                  gates={
                      'native_identity': 'blocked: no pc_p2_kogane native registration (native track; flagged on #219)',
                      'natural_AI': 'blocked: no P1 counterpart; proxy mapping undecided (integration lead)',
                      'flip_drop_cycle': 'blocked: P2-only FSM (damage.bca frame 7 createItem); needs native registration',
                      'fart_gas': 'blocked: P2-only InteractGas emitter; needs native registration',
                      'forced_escape_3_flips': 'blocked: P2-only FSM; needs native registration',
                      'cave_relocation': 'blocked: requires Cave::randMapMgr (P2 caves not in P1 engine)',
                      'reload': 'untested'},
                  limitations=['Source Kogane-bank visuals only; no native behavior',
                               'No source yaw applied', 'Native registration pending integration lead (#186/#219)',
                               'No P1 proxy species decided: family has no Pikmin 1 counterpart'])
    (run / 'arena.json').write_text(json.dumps(result, indent=2))
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'bank', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.bank, args.output))
