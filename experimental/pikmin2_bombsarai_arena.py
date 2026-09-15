"""Private original Impact Site arena: one BombSarai actor plus one P1 control.

Lane #244 (Careening Dirigibug, enemy ID 58), modeled on
``pikmin2_aquatic_arena.py`` and ``pikmin2_flying_arena.py`` per
``docs/PIKMIN2_ENEMY_ARENA.md``. Original map/collision/routes are preserved
byte-identical, one explicit BombSarai actor plus one ordinary P1 control,
generator IDs checked against the stage's existing placements, full expected XYZ
recorded, generator position plus offset is translation only (zero offset), and
source yaw is recorded as unapplied metadata. Visuals come from the lane import
via ``pikmin2_bombsarai_install``.

BombSarai is a flyer with a direct P1 ancestor: the P1 Puffy Blowhog
(``engine/include/teki.h:97``, ``TEKI_Mar = 16``) is the behavior/visual proxy.
The source BombSarai FSM is not ported here; this is an engineered placement
vehicle, not production placement evidence. Gate statuses are recorded honestly
from ``docs/PIKMIN2_BOMBSARAI_RUNTIME_EVIDENCE.md`` and
``docs/PIKMIN2_BOMBSARAI_FSM.md``: the standalone policy/FSM fixtures and the
retail-asset runtime probes pass, most integration gates are partial, and native
identity/registration is blocked pending the integration lead (#186, flagged on
#244).
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
from experimental.pikmin2_bombsarai_install import install, verify_install

# P1 teki types from engine/include/teki.h (GPVE01/GPIP01 symbols).
P1_MAR_TYPE = 16      # 16, Puffy Blowhog (BombSarai proxy / native ancestor)
P1_CHAPPY_TYPE = 3    # 3, Dwarf Bulborb (ordinary P1 control)

BOMBSARAI = ('BombSarai',)
IDS = (244001, 244002)
SPECIES = BOMBSARAI + ('P1 Chappy',)
POSITIONS = ((-150., 30., 1850.), (150., 30., 1550.))
# No authored above-ground placement yaw was audited for this lane; recorded as
# unapplied metadata, never encoded as translation.
SOURCE_YAW = None
PROXY = {'BombSarai': P1_MAR_TYPE, 'P1 Chappy': P1_CHAPPY_TYPE}
FAMILY = {P1_MAR_TYPE: 'Mar (P1 Puffy Blowhog)',
          P1_CHAPPY_TYPE: 'Chappy (P1 Dwarf Bulborb)'}

# Gate statuses transcribed from the BombSarai runtime evidence (#244). PASS /
# PARTIAL entries are backed by the executed standalone fixtures and the
# retail-asset runtime probes; BLOCKED entries are honest integration gaps.
GATES = ('native_identity', 'terrain_floor_probe', 'terrain_wall_probe',
         'supply_birth', 'release_lob', 'fall_eject', 'death_drop',
         'fuse_detonation', 'blast_routing', 'airborne_immunity',
         'carrier_fsm', 'purple_forced_fall', 'dead_carrier_fallback',
         'pool_exhaustion', 'visual_assets', 'walk_to_target',
         'flick_effect_routing', 'retail_keyframe_timings',
         'animated_capture_joint', 'multi_carrier_pool', 'induction_ip02',
         'save_resume')
# The fixture reads one arena profile per scenario from its cwd (see
# ``output/lane01-native/tools/p2_bombsarai_runtime.cpp`` kScenarios and the
# ``P2_BOMBSARAI_ARENA_1`` parser in ``pc_p2_bombsarai_arena.cpp``). Content is
# the audited retail-asset profile: pinned carrier/token, a body-relative
# kamu_jnt1 stand-in joint (the payload rides the moving carrier, not a static
# point), hover and bomb values from the retail tables, and the four static
# receivers; the purple/death scenarios add the tick-indexed host-event script.
# These are emitted into the run directory so the fixture's cwd is complete.
SCENARIO_FILES = ('p2-bombsarai-arena.txt', 'p2-bombsarai-arena-purple.txt',
                  'p2-bombsarai-arena-death.txt')
SCENARIO_LINES = {
    'p2-bombsarai-arena.txt': (
        'P2_BOMBSARAI_ARENA_1',
        'carrier 0 120 0 0 9001',
        'joint 0 -40 0',
        'hover 70 2.5 20 1.5 1.0',
        'bomb 18.666667 4.5 30 15 90 50 500 10',
        'receivers 4',
        'receiver 501 teki 20 15 0 1 0',
        'receiver 502 navi 30 15 0 1 0',
        'receiver 503 piki 0 15 -40 1 0',
        'receiver 504 teki 10 15 0 0 1'),
    'p2-bombsarai-arena-purple.txt': (
        'P2_BOMBSARAI_ARENA_1',
        'carrier 0 120 0 0 9001',
        'joint 0 -40 0',
        'hover 70 2.5 20 1.5 1.0',
        'bomb 18.666667 4.5 30 15 90 50 500 10',
        'receivers 4',
        'receiver 501 teki 20 15 119 1 0',
        'receiver 502 navi 30 15 119 1 0',
        'receiver 503 piki 0 15 150 1 0',
        'receiver 504 teki 10 15 119 0 1',
        'events 2',
        'event 50 stuck 0 1',
        'event 90 stuck 0 0'),
    'p2-bombsarai-arena-death.txt': (
        'P2_BOMBSARAI_ARENA_1',
        'carrier 0 120 0 0 9001',
        'joint 0 -40 0',
        'hover 70 2.5 20 1.5 1.0',
        'bomb 18.666667 4.5 30 15 90 50 500 10',
        'receivers 4',
        'receiver 501 teki 20 15 0 1 0',
        'receiver 502 navi 30 15 0 1 0',
        'receiver 503 piki 0 15 -40 1 0',
        'receiver 504 teki 10 15 0 0 1',
        'events 1',
        'event 45 kill'),
}


def scenario_payloads():
    """Return scenario-filename -> exact fixture profile bytes (CRLF, as shipped)."""
    return {name: ('\r\n'.join(SCENARIO_LINES[name]) + '\r\n').encode('ascii')
            for name in SCENARIO_FILES}


GATE_STATES = {
    'native_identity': 'blocked: no BombSarai/Bomb native registration (integration lead #186; flagged on #244)',
    'terrain_floor_probe': 'pass: P2_BOMBSARAI_FLOOR_PROBE floor=1 (runtime evidence)',
    'terrain_wall_probe': 'pass: P2_BOMBSARAI_WALL_PROBE_PASS (runtime evidence)',
    'supply_birth': 'pass: Supply state-entry birth at source tick 30 (FSM approach)',
    'release_lob': 'pass: Release KEYEVENT_2 fixed lob (50,100) thrown (FSM approach)',
    'fall_eject': 'pass: Fall KEYEVENT_2 skyward eject (100,300) thrown (FSM purple)',
    'death_drop': 'pass: unconditional zero-velocity Death drop (FSM death)',
    'fuse_detonation': 'pass: floor-armed fuse with fixed 10-tick delay; blast at tick 209/201',
    'blast_routing': 'partial: routed to instrumented receivers, not live P1 creatures',
    'airborne_immunity': 'pass: airborne-immune receiver 504 skipped (runtime evidence)',
    'carrier_fsm': 'pass: 13-state lane FSM drives all three runtime scenarios',
    'purple_forced_fall': 'pass: scripted Purple stick forces Fall through the height gate (FSM purple)',
    'dead_carrier_fallback': 'pass: dead-carrier blast attributes navi/piki hits to the bomb (self=1 token=0)',
    'pool_exhaustion': 'partial: fixture pool cap 2; real shared Bomb manager limit open',
    'visual_assets': 'blocked: debug markers only; converted BMD/BCK assets not wired (#128)',
    'walk_to_target': 'blocked: horizontal walkToTarget not integrated; carrier is pinned',
    'flick_effect_routing': 'blocked: flickStickPikmin knockback/damage host-owned, not routed',
    'retail_keyframe_timings': 'partial: profile timing stand-ins, not retail .bca durations (#128)',
    'animated_capture_joint': 'partial: unit-level followJoint/yaw transform; runtime P2_BOMBSARAI_JOINT_FOLLOW not yet observed',
    'multi_carrier_pool': 'blocked: shared Bomb manager limit under concurrent carriers open',
    'induction_ip02': 'blocked: bomb-on-bomb induction (ip02=15) not modeled',
    'save_resume': 'blocked: no BombSarai/Bomb serialization; carried/in-flight/armed persistence open',
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
            proxy = (f'P1 {FAMILY[teki_type]} proxy; native ancestor, '
                     'not source BombSarai FSM')
        placements.append(dict(generator=identity, species=kind,
                               native_family=FAMILY[teki_type], native_teki_type=teki_type,
                               proxy=proxy, expected_xyz=list(validate_position(row, xyz)),
                               offset=[0, 0, 0], source_yaw=SOURCE_YAW,
                               source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def prepare(assets, imported, output):
    """Build a private arena run directory with the BombSarai visual bank installed."""
    assets = assets.resolve()
    imported = imported.resolve()
    data, actors = roster(assets)
    registered = [(a['generator'], a['species']) for a in actors if a['species'] in BOMBSARAI]
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
    if set(GATES) != set(GATE_STATES):
        raise ValueError('Gate contract mismatch')
    scenarios = scenario_payloads()
    for name, payload in scenarios.items():
        (run / name).write_bytes(payload)
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=len(registered), control='P1 Chappy',
                  source_stage_sha256=digest(stage), preserved_course_sha256=preserved,
                  bombsarai_manifest_sha256=digest(imported / 'bombsarai.json'),
                  install=receipt, install_verified=verified, birth_policy=birth,
                  scenarios={name: {'sha256': hashlib.sha256(payload).hexdigest(),
                                    'bytes': len(payload)}
                             for name, payload in sorted(scenarios.items())},
                  scatter='Default generator scatter circle zeroed by deterministic fixture '
                          'override (PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not '
                          'production placement evidence',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn '
                                   'acceptance unmeasured',
                  gates=dict(GATE_STATES),
                  limitations=['P1 Puffy Blowhog proxy placement; not source BombSarai FSM',
                               'Source BombSarai FSM/projectile policy not registered natively',
                               'No source yaw applied',
                               'Visual bank optional; absent .mod files preserve the baseline',
                               'Native registration pending integration lead (#186; flagged on #244)'])
    (run / 'arena.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.imported, args.output))
