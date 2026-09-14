"""Private original Impact Site arena: Fuefuki (Antenna Beetle) proxy plus control.

Issue #245, arena/integration contract #186, modeled on
``pikmin2_dwarf_bear_arena.py`` and ``pikmin2_aquatic_arena.py`` per
``docs/PIKMIN2_ENEMY_ARENA.md``. Original map/collision/routes are preserved
byte-identical, one explicit actor for the Fuefuki lane plus one ordinary P1
control, generator IDs checked against the stage's existing placements, full
expected XYZ recorded, generator position plus offset is translation only
(zero offset), and source yaw is recorded as unapplied metadata.

Fuefuki has no P1 ancestor; native type ``TEKI_Napkid`` 11 (Swooping Snitchbug)
is the audited placement vehicle only — its identity, FSM and whistle
interference stay BLOCKED pending native actor registration (#186). The estate
profile from ``pikmin2_fuefuki_install.py`` is the only asset this arena ships;
no motion bank, no shared/native edits. Gate statuses are recorded honestly from
the real-GL runtime evidence in ``native/tools/P2_FUEFUKI_RUNTIME_EVIDENCE.md``:
the whistle-theft, interference, reclaim, carry and pinned-spawn paths passed
against retail assets; follow locomotion, panic staging, brain fallback, claim
persistence and native identity remain blocked.
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
from experimental.pikmin2_fuefuki_install import install

# P1 teki types from engine/include/teki.h (GPVE01/GPIP01 symbols).
P1_CHAPPY_TYPE = 3    # 3, Dwarf Bulborb (ordinary control)
P1_NAPKID_TYPE = 11   # 11, Swooping Snitchbug (placement vehicle only)

IDS = (245001, 245002)
SPECIES = ('Fuefuki', 'P1 Chappy')
POSITIONS = ((-150., 30., 1850.), (150., 30., 1550.))
# No authored above-ground placement yaw was audited for this lane; recorded as
# unapplied metadata, never encoded as translation.
SOURCE_YAW = None
PROXY = {'Fuefuki': P1_NAPKID_TYPE, 'P1 Chappy': P1_CHAPPY_TYPE}
FAMILY = {P1_NAPKID_TYPE: 'Napkid (P1 Swooping Snitchbug)',
          P1_CHAPPY_TYPE: 'Chappy (P1 Dwarf Bulborb)'}

# Lane acceptance gates. PASS/BLOCKED strings quote the real-GL evidence in
# native/tools/P2_FUEFUKI_RUNTIME_EVIDENCE.md. Nothing here claims gameplay
# acceptance.
GATES = ('native_identity', 'spawn', 'whistle_theft', 'interference', 'reclaim',
         'carry', 'follow_locomotion', 'panic_staging', 'brain_fallback',
         'claim_persistence')
PASSED = {
    'whistle_theft': 'pass: real-GL run claimed exactly the 3 in-ring of 6 real pikiMgr Pikmin, none outside (P2_FUEFUKI_RT_SCAN)',
    'interference': 'pass: real-GL run refused captain whistle/switch/combine on held Pikmin with zero ownership writes (P2_FUEFUKI_RT_NONROUTE)',
    'reclaim': 'pass: real Navi::callPikis reclaim, PIKISTATE_LookAt then real FormationMode join (P2_FUEFUKI_RT_RECLAIM, P2_FUEFUKI_RT_FORMJOIN)',
    'carry': 'pass: dead-anim END delivered kill with carry_anim carcass flag (P2_FUEFUKI_RT_KILL)',
    'spawn': 'pass: both pinned actors birthed through the real generator path at exact XYZ, generator_delta=0.000 born_delta=0.000 (P2_FUEFUKI_ARENA_SPAWN); placement vehicle only, native identity still blocked',
}
BLOCKED = {
    'native_identity': 'blocked: no native Fuefuki (41) registration; Napkid 11 is a placement vehicle only (#186)',
    'follow_locomotion': 'blocked: P1 has no follow-teki action; follow movement stays policy-fixture-only',
    'panic_staging': 'blocked: P1 has no verified panic state; released followers stay PIKISTATE_Normal',
    'brain_fallback': 'blocked: suspend destination (Formation rejoin vs Free) untraced in source',
    'claim_persistence': 'blocked: claim persistence across day/cave transitions undefined',
}
STATUS = {key: PASSED.get(key, BLOCKED.get(key, 'untested')) for key in GATES}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    """Append the two-actor Fuefuki roster to the original practice stage records."""
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
            proxy = 'P1 Napkid 11 placement vehicle only; species identity NOT claimed'
        placements.append(dict(generator=identity, species=kind,
                               native_family=FAMILY[teki_type], native_teki_type=teki_type,
                               proxy=proxy, expected_xyz=list(validate_position(row, xyz)),
                               offset=[0, 0, 0], source_yaw=SOURCE_YAW,
                               source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def prepare(assets, output):
    """Build a private arena run directory with the Fuefuki seam profile installed."""
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
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=len(actors), control='P1 Chappy',
                  source_stage_sha256=digest(stage), preserved_course_sha256=preserved,
                  install=receipt, birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by deterministic fixture '
                          'override (PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not '
                          'production placement evidence',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn '
                                   'acceptance unmeasured',
                  gates=STATUS,
                  limitations=['Seam profile only; no Fuefuki visual/audio assets or motion bank (#128)',
                               'P1 Napkid 11 is a placement vehicle; Fuefuki identity and FSM NOT claimed',
                               'Follow locomotion, panic staging, brain fallback and claim persistence blocked',
                               'No source yaw applied',
                               'Native actor registration pending integration lead (#186)'])
    (run / 'arena.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.output))
