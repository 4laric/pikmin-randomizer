"""Private original Impact Site arena hosting the BigTreasure placement lane.

Issue #246 (Titan Dweevil / BigTreasure), arena/integration contract #186,
modeled on ``pikmin2_aquatic_arena.py`` (batch 2, #374) and the existing
``pikmin2_bigtreasure_install.py`` lane profile. BigTreasure has **no** P1
counterpart, so it uses the audited one-actor enemy template framing (native
type TEKI_Chappy 3) purely as a placement vehicle; species identity, FSM and
proxy mapping stay BLOCKED pending native-track work (#128) and root-owned
wiring (#186). One ordinary P1 Chappy is the control. Original map/collision/
routes are preserved byte-identical, generator position plus offset is
translation only (zero offset), and source yaw is recorded as unapplied
metadata.

Statuses are recorded honestly in ``STATUS``: the native ownership/teardown
suite and the per-element attack policies passed their standalone probes,
motion staging covered 2 of the 29 converted clips at runtime, and the native
identity/AI/FSM/combat/damage-receiver/model gates remain blocked. This is
engineered placement, not production placement evidence, and it ships no
assets: the existing ``pikmin2_bigtreasure_install`` host-seam profile is what
gets installed.
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
from experimental.pikmin2_bigtreasure_install import install

# P1 teki types from engine/include/teki.h (GPVE01/GPIP01 symbols).
P1_CHAPPY_TYPE = 3    # 3, Dwarf Bulborb (ordinary control / placement vehicle)

BIGTREASURE = ('BigTreasure', 'P1 Chappy')
IDS = (246001, 246002)
SPECIES = BIGTREASURE
POSITIONS = ((0., 30., 1850.), (240., 30., 1550.))
# No authored above-ground placement yaw was audited for this lane; recorded as
# unapplied metadata, never encoded as translation.
SOURCE_YAW = None
PROXY = {'BigTreasure': P1_CHAPPY_TYPE, 'P1 Chappy': P1_CHAPPY_TYPE}
FAMILY = {P1_CHAPPY_TYPE: 'Chappy (P1 Dwarf Bulborb)'}

# Acceptance gates for the arena slice. ``STATUS`` is the honest per-gate
# state; probe-verified entries point at the lane's standalone fixtures and
# runtime probes, partial entries state the covered subset, blocked entries
# name the missing native/engine work, and untested entries were never run.
GATES = ('native_identity', 'weapon_ownership_teardown', 'per_element_attacks',
         'motion_staging', 'natural_AI', 'fsm_host', 'combat', 'damage_receivers',
         'loozy_model', 'skeletal_playback', 'spawn', 'reload')
STATUS = {
    'native_identity': 'blocked: no native registration for BigTreasure/73 (integration lead #186)',
    'weapon_ownership_teardown': 'probe-verified: p2_bigtreasure_test ownership/teardown fixtures '
                                 'plus host-seam defeat ordering (pools first, weapons (0,100,0), Louie (0,150,0))',
    'per_element_attacks': 'probe-verified: p2_bigtreasure_attacks_test element policies plus '
                           'runtime elec-bounce/water-arc map probes',
    'motion_staging': 'partial: 2/29 clips runtime-staged (wait1, dead); 27 converted clips not staged',
    'natural_AI': 'blocked: source P2 12-state FSM not ported; Chappy placement vehicle only',
    'fsm_host': 'blocked: 12-state FSM host not wired (integration lead #186)',
    'combat': 'blocked: source attacks/damage receivers not registered',
    'damage_receivers': 'blocked: InteractFire/Gas/Bubble/Denki receivers are host concerns, not wired',
    'loozy_model': 'blocked: loozy shape matrix type 1 unsupported by the restricted converter',
    'skeletal_playback': 'blocked: baked per-frame poses only; no live skinning/IK',
    'spawn': 'untested: no runtime spawn-table registration / arena session',
    'reload': 'untested: save/resume reload not run',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    """Append the two-actor roster to the original practice stage records."""
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
        else:
            proxy = 'P1 Chappy placement vehicle only; native identity NOT claimed'
        placements.append(dict(generator=identity, species=kind,
                               native_family=FAMILY[teki_type], native_teki_type=teki_type,
                               proxy=proxy, expected_xyz=list(validate_position(row, xyz)),
                               offset=[0, 0, 0], source_yaw=SOURCE_YAW,
                               source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def prepare(assets, output):
    """Build a private arena run directory and install the BigTreasure host profile."""
    assets = assets.resolve()
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
    verified = install(run)
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  control='P1 Chappy', boss='BigTreasure (Titan Dweevil)',
                  source_stage_sha256=digest(stage), preserved_course_sha256=preserved,
                  profile_sha256=receipt['profile_sha256'],
                  install=receipt, install_verified=verified.get('status'),
                  birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by deterministic fixture '
                          'override (PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not '
                          'production placement evidence',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn '
                                   'acceptance unmeasured',
                  gates={key: STATUS.get(key, 'untested') for key in GATES},
                  limitations=['Host-seam profile only; no BigTreasure model/motion assets installed',
                               'BigTreasure has no P1 counterpart: Chappy placement vehicle only, '
                               'native identity NOT claimed',
                               'Ownership/teardown and per-element attacks are probe-verified, not '
                               'gameplay-accepted; damage receivers/FSM/combat blocked',
                               'Motion staging covers 2 of 29 converted clips',
                               'spawn/reload untested; no source yaw applied',
                               'Native registration/hook wiring pending integration lead (#186)'])
    (run / 'arena.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.output))
