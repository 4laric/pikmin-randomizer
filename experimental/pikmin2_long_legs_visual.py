"""Long Legs family bind-pose visual conversion (#312, parent #173).

The lane install (:mod:`experimental.pikmin2_long_legs_install`) stages the two
owned bind-pose meshes (``Houdai_enemy.bmd`` / ``BigFoot_enemy.bmd``). This
family-owned module turns each staged mesh into a single static engine ``.mod``
so the native Long Legs draw path can display the bind pose. It is deliberately
a single bind shape per species, not a sampled ``.mod`` pose bank: the source
carries no converted animation bank for these two models.

Two converter capabilities are opted in for this family only (strict defaults
elsewhere, per #186):

- ``approximate_materials=True`` — Houdai's ``MAT3`` materials are multi-stage,
  which the strict converter rejects.
- an explicit bind ``draw_matrices`` table from
  :func:`experimental.pikmin2_skinning.draw_matrices` — BigFoot carries four
  ``EVP1`` matrix envelopes (weighted skinning), which the strict rigid path
  rejects. The table is the authored inverse-bind blend at the bind pose.

A rigid (envelope-free) mesh, i.e. Houdai, also gets a rigid skin sidecar
(``longlegs_<species>_skin_00.txt``, ``P2_LONG_LEGS_SKIN_1``): every joint's
bind matrix and, per baked position/normal, its owning joint and joint-local
value. The native draw re-poses the twelve leg joints with the ported source
IKSystemMgr so the legs walk (#173); everything else stays at the bind pose.

Output is deterministic (no clock, no environment), refuses to overwrite, and
records every source/output SHA-256. No disc assets, generated models or
receipts are committed; evidence stays under private ``output/``.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_skinning import draw_matrices

SPECIES = {'Houdai': 66, 'BigFoot': 69}
MESH = '{species}_enemy.bmd'
MOD = 'longlegs_{species}_bind_00.mod'
SKIN = 'longlegs_{species}_skin_00.txt'
SKIN_HEADER = 'P2_LONG_LEGS_SKIN_1'
RECEIPT = 'long-legs-visual.json'
SCHEMA = 1
FAMILY = 'Long Legs'
MAX_MOD_BYTES = 4 * 1024 * 1024
BIND_POSE = 'bind'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _private_room(room):
    room = Path(room)
    if (not room.is_dir() or room.is_symlink() or room.is_junction()
            or room.resolve() != room.absolute()):
        raise ValueError('Expected private non-junction room directory')
    return room


def _conversion(model):
    """Decode one bind-pose ``enemy.bmd`` into a static ``.mod`` byte string."""
    if len(model) < 32 or model[:8] != b'J3D2bmd3':
        raise ValueError('Expected complete J3D2bmd3 model')
    model_blocks = blocks(model)
    envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
    draw = None
    if envelopes:
        draw = draw_matrices(model_blocks)
    bindings = {} if not envelopes else None
    decoded = decode(model, True, bake_rigid=True, draw_matrices=draw, bindings=bindings)
    # write_model writes a path-bearing sidecar next to the .mod; write into a
    # throwaway path then capture the bytes so no sidecar is left in the room.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / 'bind.mod'
        report = write_model(decoded, target, 'enemy.bmd')
        data = target.read_bytes()
    report.pop('output', None)
    report['envelopes'] = envelopes
    report['bind_draw_matrices'] = len(draw or [])
    if len(data) > MAX_MOD_BYTES:
        raise ValueError('Converted bind mesh exceeds budget')
    if bindings is not None:
        # Rigid mesh: every baked vertex follows exactly one joint, so the
        # native IK leg draw can re-pose it (#173 walk animation).
        report['skin_text'] = skin_text(model_blocks, bindings)
    return data, report


def joint_names(model_blocks):
    """JNT1 name table, in joint index order."""
    j = model_blocks['JNT1']
    count = struct.unpack_from('>H', j, 8)[0]
    table = struct.unpack_from('>I', j, 20)[0]
    if struct.unpack_from('>H', j, table)[0] != count:
        raise ValueError('Joint name table count mismatch')
    names = []
    for i in range(count):
        offset = struct.unpack_from('>H', j, table + 4 + 4 * i + 2)[0]
        start = table + offset
        end = j.index(b'\0', start)
        names.append(j[start:end].decode('ascii'))
    return names


def skin_text(model_blocks, bindings):
    """Rigid skin sidecar for the native Long Legs IK draw (#173).

    One row per joint (its bind model-space 3x4 matrix, the matrix the bind
    bake used) and one row per baked ``.mod`` position/normal in ``.mod``
    order: the owning joint and the joint-local value. The native draw
    evaluates ``matrix[joint] * local`` per vertex, so the bind matrices
    reproduce the bind ``.mod`` exactly and IK-posed leg joints move only
    the vertices they own.
    """
    from experimental.pikmin2_rigid import joint_matrices
    names = joint_names(model_blocks)
    matrices = joint_matrices(model_blocks)
    if len(names) != len(matrices):
        raise ValueError('Joint name/matrix count mismatch')

    def f(v):
        return format(float(v), '.9g')

    rows = [SKIN_HEADER, f'joints {len(matrices)}']
    for index, (name, matrix) in enumerate(zip(names, matrices)):
        if not name or any(c.isspace() for c in name):
            raise ValueError('Unsupported joint name')
        rows.append(f'j {index} {name} ' + ' '.join(f(v) for row in matrix for v in row))
    for label, attr in (('positions', 9), ('normals', 10)):
        entries = bindings[attr]
        rows.append(f'{label} {len(entries)}')
        for joint, value in entries:
            if not 0 <= joint < len(matrices):
                raise ValueError('Skin joint out of range')
            rows.append(f'{joint} ' + ' '.join(f(v) for v in value))
    rows.append('end')
    return ('\n'.join(rows) + '\n').encode('ascii')


def plan(room):
    room = _private_room(room)
    present = [(name, identity) for name, identity in SPECIES.items()
               if (room / MESH.format(species=name)).is_file()]
    stray = sorted(p.name for p in room.glob('*_enemy.bmd')
                   if p.name not in {MESH.format(species=n) for n in SPECIES})
    if stray:
        raise ValueError('Unexpected Long Legs mesh: ' + ', '.join(stray))
    if not present:
        return room, {}, []
    return room, {name: identity for name, identity in present}, present


def convert(room):
    room, wanted, order = plan(room)
    if not wanted:
        return dict(schema=SCHEMA, family=FAMILY, visuals='absent_baseline_preserved',
                    species={}, files={})
    targets = [room / MOD.format(species=name) for name in wanted]
    targets += [room / SKIN.format(species=name) for name in wanted]
    if any(target.exists() or target.is_symlink() for target in targets):
        raise ValueError('Refusing existing/conflicting Long Legs visual conversion')
    if (room / RECEIPT).exists():
        raise ValueError('Refusing existing Long Legs visual receipt')
    files = {}
    for name in wanted:
        source = (room / MESH.format(species=name)).read_bytes()
        data, report = _conversion(source)
        skin = report.pop('skin_text', None)
        (room / MOD.format(species=name)).write_bytes(data)
        if skin is not None:
            (room / SKIN.format(species=name)).write_bytes(skin)
        files[name] = dict(
            enemy_id=SPECIES[name], mesh=MESH.format(species=name),
            model='bind', output=MOD.format(species=name),
            source_bytes=len(source), source_sha256=sha(source),
            bytes=len(data), sha256=sha(data),
            vertices=report['vertices'], triangles=report['triangles'],
            shapes=report['shapes'], textures=report['textures'],
            envelopes=report['envelopes'], bind_draw_matrices=report['bind_draw_matrices'],
            discarded_attributes=report.get('discarded_attributes', []),
            discarded_texture_matrix_attributes=report.get(
                'discarded_texture_matrix_attributes', []))
        if skin is not None:
            files[name].update(skin=SKIN.format(species=name), skin_bytes=len(skin),
                               skin_sha256=sha(skin))
    skinned = sorted(name for name, row in files.items() if 'skin' in row)
    receipt = dict(schema=SCHEMA, family=FAMILY, visual='bind_pose_static',
                   pose_bank=False, skeletal_playback=False,
                   **({'ik_leg_skin': skinned} if skinned else {}),
                   species={name: SPECIES[name] for name in wanted}, files=files)
    (room / RECEIPT).write_bytes(
        (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode('ascii'))
    return receipt


def verify(room):
    room, wanted, order = plan(room)
    if not wanted:
        return dict(verified=[], visuals='absent_baseline_preserved')
    if not (room / RECEIPT).is_file():
        raise ValueError('Long Legs visual receipt missing')
    receipt = json.loads((room / RECEIPT).read_text())
    if receipt.get('schema') != SCHEMA or receipt.get('family') != FAMILY:
        raise ValueError('Unsupported Long Legs visual receipt')
    for name in wanted:
        row = receipt['files'].get(name)
        if row is None:
            raise ValueError('Receipt missing species: ' + name)
        target = room / MOD.format(species=name)
        if not target.is_file():
            raise ValueError('Installed bind mod missing: ' + name)
        data = target.read_bytes()
        if sha(data) != row['sha256'] or len(data) != row['bytes']:
            raise ValueError('Installed bind mod mismatch: ' + name)
        source = (room / MESH.format(species=name)).read_bytes()
        if sha(source) != row['source_sha256']:
            raise ValueError('Staged mesh changed: ' + name)
        if 'skin' in row:
            skin = room / row['skin']
            if not skin.is_file():
                raise ValueError('Installed skin sidecar missing: ' + name)
            skin_data = skin.read_bytes()
            if sha(skin_data) != row['skin_sha256'] or len(skin_data) != row['skin_bytes']:
                raise ValueError('Installed skin sidecar mismatch: ' + name)
    return dict(verified=sorted(wanted), receipt=RECEIPT, visuals='installed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--room', type=Path, required=True,
                        help='private run room assets/dataDir/courses/pikmin2room')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = verify(args.room) if args.verify else convert(args.room)
    print(json.dumps(result, sort_keys=True, indent=2))
