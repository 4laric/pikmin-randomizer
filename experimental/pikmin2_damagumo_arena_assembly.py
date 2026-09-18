"""Damagumo (Beady Long Legs, source 56) arena runtime assembly (issue #798).

Recovery assembly for the stranded gen-9 gap in
``shard-enemies-3-damagumo56-observer`` (#173): no staged Damagumo arena and no
built preview-room executable existed to run the guarded game path. This lane
consumes the pinned, already-landed converter artifacts read-only and stages a
private arena slot 312004 that the committed ``#632``-guarded room harness can
run:

* ``damagumo-family.json`` (``f9ec5030...``) - converted 56 profile/mesh facts
  (``damagumo-profile-convert``), canonical LF.
* ``Demon/enemy.bmd`` (``8fc0ac7f...``) - the retail Damagumo bind-pose mesh.
* ``damagumo-slot-312004.json`` (``61019a39...``) - the slot/provider row
  (``damagumo-converter-artifact-landing``, #685), canonical LF.
* ``longlegs_Damagumo_bind_00.mod`` (``c5642cc9...``, 104640 bytes) - the
  converted bind shape from ``damagumo-bind-mod-conversion-native`` (#727).

The module stages slot 312004 (actors config + mesh + bind mod) into a private
run using the shared engine-free overlay/roster machinery, records exact
receipt hashes, and fails closed on any missing, malformed or hash-drifting
input, an unsafe actor identity, an existing/conflicting installation, or a
changed original course. It performs no engine edits, no gameplay claim, no
ledger write and no ADMIT; the native harness/room-app membership is reused
read-only by the separate leased build.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

LANE = 'shard-enemies-3-damagumo56-arena-assembly'
ISSUE = 798
SLOT = 312004
SPECIES = 'Damagumo'
ENEMY_ID = 56
FOLDER = 'Demon'
MESH_NAME = 'Demon/enemy.bmd'
BIND_MOD = 'longlegs_Damagumo_bind_00.mod'
BIND_MOD_BYTES = 104640
FAMILY_MANIFEST = 'damagumo-family.json'
SLOT_PROFILE = 'damagumo-slot-312004.json'
GUARD_SHA256 = 'd2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474'
P1_CHAPPY_TYPE = 3  # neutral placement vehicle; Damagumo identity comes from the host species row
ACTORS_TXT = 'p2-long-legs-actors.txt'
INSTALL_JSON = 'damagumo-arena-assembly.json'
CONTROL = 'P1 Chappy'

# canonical LF hash for text JSON, raw hash for binary blobs
PINNED = {
    FAMILY_MANIFEST: ('f9ec5030890d72fba0c890b41407aa8788b6fac53223dd62f231a3259f68ef94', True),
    SLOT_PROFILE: ('61019a39bf255442e49cd5d03db6f16581ab5370ab401a346341f8d077c4e37c', True),
    MESH_NAME: ('8fc0ac7fd6c7585113cf10da12ecd7faccf807896d2d642ab0f80019fff2a961', False),
    BIND_MOD: ('c5642cc97a292210b1556465125685963c8403134b438398c9739a9f64827dc2', False),
}


class AssemblyRejected(ValueError):
    """Raised when inputs or the staged layout violate the contract."""


def canonical_sha(data, text):
    """SHA-256 of canonical LF bytes (text) or raw bytes (binary)."""
    if text:
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _read(path, text):
    try:
        return path.read_bytes()
    except OSError as exc:
        raise AssemblyRejected('Missing input: %s (%s)' % (path, exc))


def verify_inputs(inputs_dir):
    """Load and hash-verify the four pinned converter artifacts (read-only)."""
    inputs_dir = Path(inputs_dir)
    loaded = {}
    for name, (digest, text) in PINNED.items():
        path = inputs_dir / name
        data = _read(path, text)
        actual = canonical_sha(data, text)
        if actual != digest:
            raise AssemblyRejected('Input hash drift for %s: %s' % (name, actual))
        loaded[name] = data
    family = _load_json(loaded[FAMILY_MANIFEST])
    slot = _load_json(loaded[SLOT_PROFILE])
    _validate_family(family)
    _validate_slot(slot)
    if len(loaded[BIND_MOD]) != BIND_MOD_BYTES:
        raise AssemblyRejected('Bind mod size mismatch: %d' % len(loaded[BIND_MOD]))
    return dict(family=family, slot=slot, mesh=loaded[MESH_NAME], bind_mod=loaded[BIND_MOD],
                hashes={name: canonical_sha(loaded[name], text)
                        for name, (_, text) in PINNED.items()})


def _load_json(data):
    try:
        value = json.loads(data.decode('utf-8-sig'))
    except (UnicodeDecodeError, ValueError) as exc:
        raise AssemblyRejected('Malformed JSON input: %s' % exc)
    if not isinstance(value, dict):
        raise AssemblyRejected('JSON input must be an object')
    return value


def _validate_family(family):
    if family.get('schema') != 1 or family.get('family') != 'Long Legs':
        raise AssemblyRejected('Unsupported family manifest')
    profile = family.get('profiles', {}).get(str(ENEMY_ID))
    if not isinstance(profile, dict) or profile.get('enemy_id') != ENEMY_ID:
        raise AssemblyRejected('Damagumo profile missing from family manifest')
    if profile.get('folder') != FOLDER or profile.get('name') != SPECIES:
        raise AssemblyRejected('Damagumo folder/name mismatch')
    rows = profile.get('animation_rows', {})
    for anchor in ('wait', 'flick', 'landing'):
        if not rows.get(anchor):
            raise AssemblyRejected('Missing Damagumo source anchor: ' + anchor)
    if not profile.get('model_sha256'):
        raise AssemblyRejected('Missing Damagumo model hash')


def _validate_slot(slot):
    if slot.get('schema') != 1 or slot.get('slot') != SLOT or slot.get('source_id') != ENEMY_ID:
        raise AssemblyRejected('Slot profile is not Damagumo slot %d' % SLOT)
    if slot.get('species') != SPECIES or slot.get('mesh') != MESH_NAME:
        raise AssemblyRejected('Slot species/mesh mismatch')


def actors_text(actors):
    """Canonical LF actor bindings in the engine's P2_LONG_LEGS_ACTORS_1 grammar."""
    actors = list(actors)
    if not 1 <= len(actors) <= 100:
        raise AssemblyRejected('Expected 1..100 actors')
    seen = set()
    for generator, species in actors:
        if type(generator) is not int or not 0 <= generator <= 0xFFFFFFFF or generator in seen:
            raise AssemblyRejected('Invalid/duplicate actor identity')
        if not isinstance(species, str) or not species:
            raise AssemblyRejected('Invalid actor species')
        seen.add(generator)
    rows = ['P2_LONG_LEGS_ACTORS_1', str(len(actors))]
    rows += ['%d %s' % (generator, species) for generator, species in actors]
    return ('\n'.join(rows) + '\n').encode('ascii')


def roster(assets, imported):
    """Append slot 312004 Damagumo + an ordinary control to the practice stage."""
    from scripts.preview_pikmin2_room import generator, records
    from experimental.pikmin2_generator_pose import validate_position, write_position
    assets = Path(assets)
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
    for generator_id, kind, xyz in ((SLOT, SPECIES, (-120.0, 30.0, 1850.0)),
                                    (SLOT + 1, CONTROL, (120.0, 30.0, 1850.0))):
        if generator_id in used:
            raise AssemblyRejected('Arena generator ID collision: %d' % generator_id)
        used.add(generator_id)
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, generator_id)
        row[16:48] = kind.encode('ascii').ljust(32, b'\0')
        row[80] = P1_CHAPPY_TYPE
        write_position(row, xyz)
        entries.append(bytes(row))
        placements.append(dict(generator=generator_id, species=kind,
                               native_teki_type=P1_CHAPPY_TYPE,
                               expected_xyz=list(validate_position(row, xyz))))
    data = header[:20] + struct.pack('>I', len(entries)) + b''.join(entries)
    return data, placements


def stage_arena(assets, inputs_dir, output):
    """Stage a private slot-312004 arena; returns the run dir and receipt."""
    from scripts.preview_pikmin2_room import overlay
    assets = Path(assets).resolve()
    inputs = verify_inputs(inputs_dir)
    data, placements = roster(assets, inputs_dir)
    stage = assets / 'dataDir/stages/practice.ini'
    course = assets / 'dataDir/courses/practice'
    preserved = {str(path.relative_to(assets)).replace('\\', '/'): sha(path.read_bytes())
                 for path in course.rglob('*') if path.is_file()}
    if not preserved:
        raise AssemblyRejected('Original Impact Site course missing')
    output = Path(output).resolve()
    if output.exists():
        raise AssemblyRejected('Refusing existing output directory')
    run = output / ('damagumo-' + hashlib.sha256(data).hexdigest()[:16])
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': stage.read_bytes(),
                 'dataDir/stages/chal0/default.gen': data}
    for path in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + path.name, empty)
    overlay(assets, run / 'assets', overrides)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if not room.is_dir():
        raise AssemblyRejected('Staged room directory missing')
    actors = [(SLOT, SPECIES), (SLOT + 1, CONTROL)]
    bind_target = room / BIND_MOD
    mesh_target = room / 'Damagumo_enemy.bmd'
    for target in (bind_target, mesh_target, run / ACTORS_TXT, run / INSTALL_JSON):
        if target.exists() or target.is_symlink():
            raise AssemblyRejected('Refusing existing installation: ' + target.name)
    bind_target.write_bytes(inputs['bind_mod'])
    mesh_target.write_bytes(inputs['mesh'])
    actors_payload = actors_text(actors)
    (run / ACTORS_TXT).write_bytes(actors_payload)
    for name, value in preserved.items():
        if sha((run / 'assets' / name).read_bytes()) != value:
            raise AssemblyRejected('Original course changed: ' + name)
    receipt = dict(schema=1, lane=LANE, issue=ISSUE, slot=SLOT, species=SPECIES,
                   enemy_id=ENEMY_ID, folder=FOLDER, actors=actors,
                   input_hashes=inputs['hashes'],
                   actors_config_sha256=sha(actors_payload),
                   bind_mod_sha256=sha(inputs['bind_mod']),
                   mesh_sha256=sha(inputs['mesh']),
                   guard_sha256=GUARD_SHA256,
                   source_stage_sha256=sha(stage.read_bytes()),
                   placements=placements,
                   preserved_course_sha256=preserved,
                   identity_proxy='P1 Chappy placement vehicle (teki type %d); Damagumo '
                                  'identity comes from the host species row' % P1_CHAPPY_TYPE,
                   native_ready=True,
                   native_registration='existing long-legs host reuses Damagumo SPECIES row (#638/#173)',
                   gameplay_events_executed=False,
                   native_registration_note='no source duplication; harness membership reused read-only')
    (run / INSTALL_JSON).write_bytes(
        (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode('ascii'))
    return run, receipt


def verify_staged(run, inputs_dir):
    """Reload a staged run and prove every artifact matches the pinned inputs."""
    run = Path(run)
    inputs = verify_inputs(inputs_dir)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (room / BIND_MOD).read_bytes() != inputs['bind_mod']:
        raise AssemblyRejected('Staged bind mod mismatch')
    if (room / 'Damagumo_enemy.bmd').read_bytes() != inputs['mesh']:
        raise AssemblyRejected('Staged mesh mismatch')
    expected = actors_text([(SLOT, SPECIES), (SLOT + 1, CONTROL)])
    if (run / ACTORS_TXT).read_bytes() != expected:
        raise AssemblyRejected('Staged actors config mismatch')
    receipt = json.loads((run / INSTALL_JSON).read_text())
    if receipt.get('bind_mod_sha256') != sha(inputs['bind_mod']):
        raise AssemblyRejected('Receipt bind-mod hash mismatch')
    return {'verified': True, 'slot': receipt.get('slot'), 'actors': receipt.get('actors')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    run, receipt = stage_arena(args.assets, args.inputs, args.output)
    print(json.dumps({'run': str(run), 'receipt': receipt}, sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
