"""Private original Impact Site arena: one Careening Dirigibug actor plus control.

Issue #244 (Careening Dirigibug lane: bomb-lob flight, projectile lifecycle),
arena/integration contract #186, modeled on ``pikmin2_aquatic_arena.py`` (#374)
and ``pikmin2_fuefuki_arena.py`` (#245). Original map/collision/routes are
preserved byte-identical, one explicit BombSarai actor plus one ordinary P1
control, generator IDs checked against the stage's existing placements, full
expected XYZ recorded, generator position plus offset is translation only (zero
offset), and source yaw is recorded as explicitly unapplied metadata. Visuals
come from the lane extraction via ``pikmin2_bombsarai_install``.

Proxy choice: Pikmin 2's Careening Dirigibug is a flying enemy that hovers,
carries a bomb-rock payload and lobs it. Pikmin 1 has no bomb-lobbing flyer, so
the closest placement vehicle is ``TEKI_Mar = 16``, the Puffy Blowhog
(``engine/include/teki.h:97``), the same aerial hoverer the flying-enemy lane
(#375) stages on. It is a placement vehicle only: the source hover/bomb FSM is
host-owned policy and the BombSarai identity is NOT claimed. The ordinary
control is ``TEKI_Chappy = 3`` (Dwarf Bulborb). Native registration rides on the
lane's opt-in ``P2_BOMBSARAI_ARENA_1`` seam (#186); no shared/native edits here.

Gate status is consolidated from the lane's executed runtime evidence
(``docs/PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md``,
``PIKMIN2_BOMBSARAI_HOST_ADAPTER.md``, ``PIKMIN2_BOMBSARAI_RUNTIME_EVIDENCE.md``,
``PIKMIN2_BOMBSARAI_FSM.md``). Items marked ``pass`` were executed against real
room geometry or real instrumented receivers; native-dependent items stay
``blocked`` or ``untested`` and are never over-claimed. No BombSarai actor,
visual bank or gameplay run is claimed for this Python stage.
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
P1_PUFFY_TYPE = 16   # 16, Puffy Blowhog (aerial placement vehicle for BombSarai)
P1_CHAPPY_TYPE = 3   # 3, Dwarf Bulborb (ordinary control)

BOMBSARAI = ('BombSarai',)
SPECIES = ('BombSarai', 'P1 Chappy')
IDS = (244001, 244002)
POSITIONS = ((-150., 30., 1850.), (150., 30., 1550.))
# No authored above-ground placement yaw was audited for this lane; recorded as
# unapplied metadata, never encoded as translation.
SOURCE_YAW = None
PROXY = {'BombSarai': P1_PUFFY_TYPE, 'P1 Chappy': P1_CHAPPY_TYPE}
FAMILY = {P1_PUFFY_TYPE: 'Mar (P1 Puffy Blowhog)',
          P1_CHAPPY_TYPE: 'Chappy (P1 Dwarf Bulborb)'}

# Common acceptance gates (docs/PIKMIN2_ENEMY_ARENA.md) plus the BombSarai
# bomb-lob/projectile-lifecycle items the lane evidence covers. Native
# registration and real-creature damage routing are integration-lead work and
# stay blocked; no shared native code is changed here.
GATES = ('native_identity', 'spawn_exact_xyz', 'control_undisturbed', 'natural_AI',
         'combat', 'death_corpse', 'carrier_recovery', 'reload',
         'bomb_lob_flight', 'projectile_lifecycle', 'hover_flight', 'blast_routing',
         'carrier_fsm', 'death_drop', 'bitter_purple_interrupt', 'pool_exhaustion',
         'kamu_joint_capture', 'multi_projectile_induction', 'persistence_reload',
         'visual_fidelity')
GATE_STATES = {
    'native_identity': 'blocked: no native BombSarai actor/registry; the lane is an opt-in '
                       'policy seam only (integration lead #186; flagged on #244)',
    'spawn_exact_xyz': 'untested: engineered arena coordinates; no actor spawns until native '
                       'registration and terrain/physical spawn is unmeasured',
    'control_undisturbed': 'untested: staged control placement recorded; no gameplay run',
    'natural_AI': 'partial: lane-owned 13-state carrier FSM policy passes standalone fixtures '
                  'and three runtime scenarios; no engine-registered AI perception',
    'combat': 'partial: blast routing policy + runtime routed hits pass against instrumented '
              'receivers; real InteractBomb creature stimulation is not wired',
    'death_corpse': 'partial: unconditional zero-velocity Death drop and dead-carrier '
                    'attribution fallback pass in fixtures/runtime; corpse/carry not registered',
    'carrier_recovery': 'partial: Purple-forced Fall and TakeOff1/2 recovery pass in the FSM '
                        'runtime; no native corpse carry',
    'reload': 'blocked: save/resume and cave/day transition semantics unresolved '
              '(audit persistence caveat)',
    'bomb_lob_flight': 'pass: fixed Release (50,100) and Fall (100,300) lob velocities pass in '
                       'the standalone bomb fixture and the runtime scenario',
    'projectile_lifecycle': 'pass: captured/in-flight/armed/burning/despawn policy passes the '
                            'standalone fixture; host trace is bound to the P1 static map in '
                            'the private runtime',
    'hover_flight': 'pass: hover vertical-control policy passes fixtures over adapter height '
                    'samples; engine registration pending',
    'blast_routing': 'pass: volume/vertical-gate/attribution policy passes the blast fixture and '
                     'the runtime routed three hits (teki 500 self, navi/piki 10 with carrier '
                     'token) against instrumented receivers',
    'carrier_fsm': 'pass: 13-state FSM fixture plus approach/purple/death runtime scenarios '
                   'pass; not engine-registered',
    'death_drop': 'pass: zero-velocity Death drop from a carrying state and dead-carrier '
                  'bomb-self attribution pass in the fixture and the death runtime scenario',
    'bitter_purple_interrupt': 'partial: bitter and Purple-forced Fall covered in the FSM fixture '
                               'and Purple at runtime; flick knockback/effect routing not wired',
    'pool_exhaustion': 'pass: one live bomb per carrier token and capacity-2 pool exhaustion '
                       'return nullptr without state change in the fixture',
    'kamu_joint_capture': 'blocked: kamu_jnt1 index 14 identified; the retail joint transform is '
                          'not plumbed and a static offset is used (#128)',
    'multi_projectile_induction': 'blocked: multi-carrier shared Bomb manager limit and ip02 '
                                  'bomb-on-bomb induction are not modeled/routed',
    'persistence_reload': 'blocked: carried/in-flight/armed bomb save-resume semantics '
                          'unresolved (audit persistence caveat)',
    'visual_fidelity': 'blocked: debug markers only; no converted BombSarai/Bomb visual bank '
                       'exists (#128 converter/material work)',
}
if set(GATES) != set(GATE_STATES):
    raise ValueError('Gate contract mismatch')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    """Append the BombSarai actor and P1 control to the original practice records."""
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
            proxy = ('P1 Puffy Blowhog aerial placement vehicle only; no P1 bomb-lob '
                     'action, species identity NOT claimed')
        placements.append(dict(generator=identity, species=kind,
                               native_family=FAMILY[teki_type],
                               native_teki_type=teki_type, proxy=proxy,
                               expected_xyz=list(validate_position(row, xyz)),
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
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True, exist_ok=True)
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
                  import_sha256=digest(imported / 'bombsarai.json'),
                  install=receipt, install_verified=verified, birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by deterministic fixture '
                          'override (PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not '
                          'production placement evidence',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn '
                                   'acceptance unmeasured',
                  gates=dict(GATE_STATES),
                  limitations=['P1 Puffy Blowhog (TEKI_Mar 16) aerial placement vehicle only; '
                               'no P1 bomb-lob action and the BombSarai identity is NOT claimed',
                               'Source hover/bomb behavior is lane-owned policy, not an '
                               'engine-registered actor (native registration #186; flagged on #244)',
                               'No source yaw applied',
                               'kamu_jnt1 capture transform and the converted visual bank remain '
                               '#128 converter work; debug markers only',
                               'Save/resume and multi-projectile pool behavior remain open '
                               '(audit persistence caveat)'])
    (run / 'arena.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.imported, args.output))
