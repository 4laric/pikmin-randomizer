"""Private original Impact Site arena: one Antenna Beetle actor plus P1 control.

Issue #245, arena/integration contract #186, modeled on
``pikmin2_aquatic_arena.py``. Original map/collision/routes are preserved
byte-identical, one explicit Antenna Beetle (Fuefuki 41) actor plus one
ordinary P1 control, generator IDs checked against the stage's existing
placements, full expected XYZ recorded, generator position plus offset is
translation only (zero offset), and source yaw is recorded as explicitly
unapplied metadata. The default generator scatter circle is zeroed by the
deterministic fixture override, an engineered choice, not production placement
evidence. The lane's real-GL runtime evidence (``P2_FUEFUKI_RT_*``) is bound
here as the gate record; no beetle actor, physical placement or gameplay run is
claimed for this stage.

P1 proxy: the closest Pikmin 1 analogue is TEKI_Napkid = 11, the Swooping
Snitchbug (``engine/include/teki.h``), the only P1 flying enemy that captures
and carries Pikmin away. It is a placement vehicle only: the source audit and
binding seam confirm there is no P1 follow-teki action, so the ACT_Teki follow
locomotion stays policy-fixture-only and the Fuefuki identity is NOT claimed.
The ordinary control is TEKI_Chappy = 3 (Dwarf Bulborb). Native registration
rides on the lane's ``pc_p2_fuefuki_binding.h`` seam (#186); no shared/native
edits here.
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
from experimental.pikmin2_fuefuki_install import (
    INSTALL_JSON, PROFILE_TXT, SEAM_VERSION, install, profile_text, sha)

# P1 teki types from engine/include/teki.h (GPVE01/GPIP01 symbols).
P1_NAPKID_TYPE = 11   # 11, Swooping Snitchbug (Fuefuki placement analogue)
P1_CHAPPY_TYPE = 3    # 3, Dwarf Bulborb (ordinary control)

SPECIES = ('Fuefuki', 'P1 Chappy')
IDS = (245001, 245002)
POSITIONS = ((-120., 30., 1850.), (120., 30., 1550.))
SOURCE_YAW = None
PROXY = {'Fuefuki': P1_NAPKID_TYPE, 'P1 Chappy': P1_CHAPPY_TYPE}
FAMILY = {P1_NAPKID_TYPE: 'Napkid (P1 Swooping Snitchbug)',
          P1_CHAPPY_TYPE: 'Chappy (P1 Dwarf Bulborb)'}

# Gate record consolidated from the lane's real-GL runtime evidence
# (native/tools/P2_FUEFUKI_RUNTIME_EVIDENCE.md). Items marked pass were executed
# against real pikiMgr/Navi objects; unresolved lane items stay blocked or
# untested and are never over-claimed.
GATES = (
    'native_identity', 'spawn_exact_xyz', 'control_undisturbed',
    'whistle_theft', 'interference_nonroute', 'follow_bookkeeping',
    'follow_locomotion', 'panic_release', 'panic_staging', 'reclaim',
    'brain_fallback', 'claim_persistence', 'carry_carcass',
    'motion_bank_staging')
GATE_STATES = {
    'native_identity': 'blocked: no Fuefuki actor exists in the P1 host; the '
                       'runtime anchor is policy-side (#186; flagged on #245)',
    'spawn_exact_xyz': 'untested: engineered arena coordinates; no actor spawns '
                       'until native registration, terrain/physical spawn unmeasured',
    'control_undisturbed': 'pass: P2_FUEFUKI_RT_NONROUTE held real Pikmin kept '
                           'their recorded free-roam mMode baseline (writes=0)',
    'whistle_theft': 'pass: P2_FUEFUKI_RT_SCAN claimed 3 real pikiMgr Pikmin '
                     'inside the retail 130.0 ring from the policy-side anchor',
    'interference_nonroute': 'pass: P2_FUEFUKI_RT_NONROUTE captain whistle, '
                             'switch and combine all refused on live held Pikmin (writes=0)',
    'follow_bookkeeping': 'pass: real claim/release and per-tick ping squad-timer '
                          'bookkeeping ran on real pikiMgr Pikmin (locomotion not)',
    'follow_locomotion': 'blocked: no P1 follow-teki action; actual follow movement '
                         'stays policy-fixture-only',
    'panic_release': 'pass: P2_FUEFUKI_RT_DEATH released 3 with reason=panic, '
                     'committed before followEnd callbacks',
    'panic_staging': 'blocked: P1 has no verified panic state; released followers '
                     'stay PIKISTATE_Normal (reclaim verified through the real whistle gather)',
    'reclaim': 'pass: real Navi::callPikis reclaim (LookAt transit, FormationMode '
               'join 20 frames later) with exactly one ownership write',
    'brain_fallback': 'blocked: suspend destination (Formation rejoin vs Free) '
                      'untraced in source; the seam exposes the release reason only',
    'claim_persistence': 'blocked: claim persistence across day/cave transitions '
                         'undefined; cancel-on-teardown is the safe default',
    'carry_carcass': 'pass: P2_FUEFUKI_RT_KILL delivered kill + carry_anim through '
                     'the seam at dead-anim END',
    'motion_bank_staging': 'blocked: the 10 FUEFUKIANIM clips are not converted or '
                           'staged (#128 converter/material work)',
}
if set(GATES) != set(GATE_STATES):
    raise ValueError('Gate contract mismatch')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster(assets):
    """Append the Antenna Beetle actor and P1 control to the practice records."""
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
            proxy = ('P1 Swooping Snitchbug placement vehicle only; no P1 '
                     'follow-teki action, species identity NOT claimed')
        placements.append(dict(generator=identity, species=kind,
                               native_family=FAMILY[teki_type],
                               native_teki_type=teki_type, proxy=proxy,
                               expected_xyz=list(validate_position(row, xyz)),
                               offset=[0, 0, 0], source_yaw=SOURCE_YAW,
                               source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def verify_profile(run):
    """Reload the installed Fuefuki profile/receipt and prove they match."""
    run = Path(run)
    data = profile_text().encode('utf-8')
    target = run / PROFILE_TXT
    receipt = run / INSTALL_JSON
    if not target.is_file() or target.read_bytes() != data:
        raise ValueError('Installed Fuefuki profile mismatch')
    if not receipt.is_file():
        raise ValueError('Installed Fuefuki receipt missing')
    payload = json.loads(receipt.read_text(encoding='utf-8'))
    if payload.get('profile_sha256') != sha(data) or payload.get('seam') != SEAM_VERSION:
        raise ValueError('Installed Fuefuki receipt mismatch')
    return {'verified': PROFILE_TXT, 'profile_sha256': payload['profile_sha256'],
            'seam': payload['seam'], 'status': payload.get('status')}


def prepare(assets, output):
    """Build a private arena run with the Fuefuki profile installed."""
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
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True, exist_ok=True)
    birth = deterministic_births(run / 'assets/dataDir/stages/chal0/default.gen',
                                 [a['generator'] for a in actors])
    receipt = install(run)
    verified = verify_profile(run)
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name, value in preserved.items():
        if digest(run / 'assets' / name) != value:
            raise ValueError('Original course changed')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=len(actors), control='P1 Chappy',
                  source_stage_sha256=digest(stage), preserved_course_sha256=preserved,
                  install=receipt, install_verified=verified, birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by deterministic fixture '
                          'override (PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not '
                          'production placement evidence',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn '
                                   'acceptance unmeasured',
                  gates=dict(GATE_STATES),
                  limitations=['Antenna Beetle (41) is staged as placement metadata only; '
                               'no beetle actor or visuals exist in the P1 host',
                               'P1 Swooping Snitchbug proxy captures Pikmin but has no '
                               'ACT_Teki follow; follow locomotion stays policy-fixture-only',
                               'Released followers have no verified P1 panic state and stay '
                               'PIKISTATE_Normal',
                               'No source yaw applied',
                               'FUEFUKIANIM motion bank (10 clips) and retail parms remain '
                               '#128 converter/material work',
                               'Native registration rides on pc_p2_fuefuki_binding.h (#186); '
                               'not installed here'])
    (run / 'arena.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.assets, args.output))
