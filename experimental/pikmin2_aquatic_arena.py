"""Private original Impact Site arena: one aquatic actor per spawnable species plus control.

Batch 2 (#374, parent #167), modeled on ``pikmin2_kogane_arena.py`` and
``pikmin2_mamuta_arena.py`` per ``docs/PIKMIN2_ENEMY_ARENA.md``. Original
map/collision/routes are preserved byte-identical, one explicit actor per
spawnable species (Catfish 26, Tadpole 27, Jigumo 63, UmiMushi 71) plus one
ordinary P1 control, generator IDs checked against the stage's existing
placements, full expected XYZ recorded, generator position plus offset is
translation only (zero offset), and source yaw is recorded as unapplied
metadata. Visuals come from the batch-1 extraction via
``pikmin2_aquatic_install``.

Catfish and Tadpole have direct P1 ancestors (``teki.h``: TEKI_Namazu 30 Water
Dumple, TEKI_Otama 25 Wogpole) and use them as behavior/visual proxies. Jigumo
(Hermit Crawmad) and UmiMushi (Bloyster) have **no** P1 counterpart, so they use
the audited one-actor enemy template framing (native type TEKI_Chappy 3) purely
as a placement vehicle; their identity, FSM and proxy mapping stay BLOCKED
pending native-track work (#186, flagged on #374). This stage is engineered
placement, not production placement evidence.
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
from experimental.pikmin2_aquatic_install import install, verify_install

# P1 teki types from engine/include/teki.h (GPVE01/GPIP01 symbols).
P1_CHAPPY_TYPE = 3    # 3, Dwarf Bulborb (ordinary control)
P1_OTAMA_TYPE = 25    # 25, Wogpole (Tadpole proxy / native ancestor)
P1_NAMAZU_TYPE = 30   # 30, Water Dumple (Catfish proxy / native ancestor)

AQUATIC = ('Catfish', 'Tadpole', 'Jigumo', 'UmiMushi')
IDS = (374001, 374002, 374003, 374004, 374005)
SPECIES = AQUATIC + ('P1 Chappy',)
POSITIONS = ((-240., 30., 1850.), (-120., 30., 1850.), (0., 30., 1850.),
             (120., 30., 1850.), (240., 30., 1550.))
# No authored above-ground placement yaw was audited for this lane; recorded as
# unapplied metadata, never encoded as translation.
SOURCE_YAW = None
PROXY = {'Catfish': P1_NAMAZU_TYPE, 'Tadpole': P1_OTAMA_TYPE,
         'Jigumo': P1_CHAPPY_TYPE, 'UmiMushi': P1_CHAPPY_TYPE,
         'P1 Chappy': P1_CHAPPY_TYPE}
FAMILY = {P1_NAMAZU_TYPE: 'Namazu (P1 Water Dumple)',
          P1_OTAMA_TYPE: 'Otama (P1 Wogpole)',
          P1_CHAPPY_TYPE: 'Chappy (P1 Dwarf Bulborb)'}

# Common acceptance gates (docs/PIKMIN2_ENEMY_ARENA.md) plus the per-species
# native items the batch-1 handoff left open. BLOCKED entries are honest: the
# source P2 behavior is not ported and no shared native code is changed here.
GATES = ('native_identity', 'spawn_exact_xyz', 'control_undisturbed',
         'natural_AI', 'combat', 'death_corpse', 'carrier_recovery', 'reload',
         'catfish_kochappy_fsm', 'tadpole_waterbox_leap', 'jigumo_panhouse_nest',
         'umimushi_shared_mgr_blind', 'jigumo_proxy', 'umimushi_proxy')
BLOCKED = {
    'native_identity': 'blocked: no native registration for 26/27/63/71 (integration lead #186; flagged on #374)',
    'natural_AI': 'blocked: source P2 FSM not ported; P1 proxy or placement vehicle only',
    'combat': 'blocked: source attacks/damage receivers not registered',
    'death_corpse': 'blocked: source corpse/carry behavior not registered',
    'carrier_recovery': 'blocked: source corpse carry not registered',
    'catfish_kochappy_fsm': 'blocked: Catfish forwards onInit to KochappyBase shared FSM; native work pending',
    'tadpole_waterbox_leap': 'blocked: Tadpole Wait/Move/Escape leap depends on water-box presence; native water-box work pending',
    'jigumo_panhouse_nest': 'blocked: Jigumo owns PanHouse child (JigumoNest alias) with nest persistence/limits; native work pending',
    'umimushi_shared_mgr_blind': 'blocked: shared UmiMushi::Mgr base exclusion (100) and Blind (101) parameter split; native work pending',
    'jigumo_proxy': 'blocked: Hermit Crawmad has no P1 counterpart; Chappy placement vehicle only',
    'umimushi_proxy': 'blocked: Ranging/Toady Bloyster has no P1 counterpart; Chappy placement vehicle only',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    """Append the five-actor roster to the original practice stage records."""
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
        if kind == 'P1 Chappy':
            proxy = 'ordinary P1 control'
        elif teki_type == P1_CHAPPY_TYPE:
            proxy = 'P1 Chappy placement vehicle only; species identity NOT claimed'
        else:
            proxy = f'P1 {FAMILY[teki_type]} proxy; native ancestor, not source P2 FSM'
        placements.append(dict(generator=identity, species=kind,
                               native_family=FAMILY[teki_type], native_teki_type=teki_type,
                               proxy=proxy, expected_xyz=list(validate_position(row, xyz)),
                               offset=[0, 0, 0], source_yaw=SOURCE_YAW,
                               source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def prepare(assets, imported, output):
    """Build a private arena run directory with the aquatic visual bank installed."""
    assets = assets.resolve()
    imported = imported.resolve()
    data, actors = roster(assets)
    registered = [(a['generator'], a['species']) for a in actors if a['species'] in AQUATIC]
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
    receipt = install(imported, run, registered)
    verified = verify_install(imported, run, registered)
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=len(registered), control='P1 Chappy',
                  source_stage_sha256=digest(stage), preserved_course_sha256=preserved,
                  import_sha256=digest(imported / 'aquatic.json'),
                  install=receipt, install_verified=verified, birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by deterministic fixture '
                          'override (PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not '
                          'production placement evidence',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn '
                                   'acceptance unmeasured',
                  gates={key: BLOCKED.get(key, 'untested') for key in GATES},
                  limitations=['Source aquatic visuals only; no native behavior',
                               'Catfish/Tadpole use P1 Namazu/Otama ancestry proxies, not source P2 FSM',
                               'Jigumo/UmiMushi have no P1 counterpart: Chappy placement vehicle only, identity NOT claimed',
                               'No source yaw applied',
                               'Native registration/hook wiring pending integration lead (#186; flagged on #374)'])
    (run / 'arena.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.imported, args.output))
