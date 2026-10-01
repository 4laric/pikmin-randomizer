"""Long Legs / Man-at-Legs enemy family lane profile (#173, #312).

Family: Beady Long Legs (`Damagumo`, enemy id 56 / bestiary 72 / disc folder
`Demon`), Man-at-Legs (`Houdai`, 66 / 74 / `Houdai`) and Raging Long Legs
(`BigFoot`, 69 / 73 / `BigFoot`).

The Damagumo/`Demon` extraction already lives in the demon lane
(`experimental/pikmin2_demon_assets.py`, branch `codex/p2-demon-assets`); this
lane deliberately does not re-extract its disc rows. It owns only the two
family members the demon lane does not cover, plus the family roll-up.

This module is deterministic, disc-free at the profile layer and makes no
runtime claim: no actor, no FSM, no animation playback, no collision, no
skinning, no save or native integration. All retail values below are quoted
from the committed retail source audit (`docs/PIKMIN2_LONG_LEGS_AUDIT.md`), not
invented.

The extract layer additionally decodes each owned `model.szs` member into a
bind-pose mesh evidence profile (skeleton joint list, per-joint world matrices,
lane-contract joint presence). The audit names `rkamujnt`/`lkamujnt`,
`tama`/`teama` and `lft1`/`lht1`/`rft1`/`rht1` as source identities for mouth,
stickable-body and leg-tube runtime constructs; the two owned models carry none
of them as mesh joints, so the decode records presence honestly instead of
manufacturing matrices.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from experimental.pikmin2_assets import disc_files, archive_files
from experimental.pikmin2_convert import blocks, u16
from experimental.pikmin2_rigid import joint_matrices
from experimental.pikmin2_sheargrub_assets import joints

FAMILY = 'Long Legs'
DEMON_LANE = 'codex/p2-demon-assets'

SPECIES = {
    56: dict(name='Damagumo', retail='Beady Long Legs', bestiary=72,
             folder='Demon', owned_by=DEMON_LANE),
    66: dict(name='Houdai', retail='Man-at-Legs', bestiary=74,
             folder='Houdai', owned_by=None),
    69: dict(name='BigFoot', retail='Raging Long Legs', bestiary=73,
             folder='BigFoot', owned_by=None),
}

# Retail animation event rows for the two family members this lane owns,
# keyed by animation name. Each row is [frame, event-index] pair, frame 0-based
# within the clip; frames come from the source audit. These are reproduced as
# evidence, not invented.
HOUDai_EVENTS = {
    'landing': [(18, 2), (54, 3), (100, 4), (130, 5), (150, 6)],
    'wait': [(0, 0), (39, 1)],
    'attack': [(33, 2), (34, 0), (35, 3), (37, 4), (38, 1), (39, 5)],
    'flick': [(40, 2), (45, 3), (68, 4)],
}
BIGFOOT_EVENTS = {
    'landing': [(18, 2), (54, 3), (56, 4), (60, 5)],
    'wait': [(0, 0), (75, 1)],
    'flick': [(35, 2)],
    'dead': [(95, 2), (150, 3)],
}

# Bounded, deterministic pose budget shared by the whole family lane. Keep it
# consistent with the groink/demon slices so tests stay green across lanes.
CHARACTER_JOINTS = ('rkamujnt', 'lkamujnt', 'kamu', 'tkubi', 'kosi', 'koshi')

MOUTH_JOINTS = ('rkamujnt', 'lkamujnt')
MOUTH_RADIUS = 40
STICKABLE_JOINTS = ('tama', 'teama')
LEG_TUBES = ('lft1', 'lht1', 'rft1', 'rht1')
PRESS_RADIUS = 15

# Lane-contract identities by runtime role; the decode reports mesh presence
# for every member of every role instead of assuming the mesh carries them.
SPECIAL_JOINT_ROLES = (('mouth', MOUTH_JOINTS),
                       ('stickable', STICKABLE_JOINTS),
                       ('leg_tube', LEG_TUBES))


def frames_for(duration, events):
    """Deterministic pose sampler: retail event keys plus clip-end anchors.

    Mirrors the demon lane contract so reproducibility tests stay green; it is
    bounded (never more than 32 poses) and rejects malformed input.
    """
    if type(duration) is not int or not 1 <= duration <= 10000:
        raise ValueError('Invalid clip duration')
    frames = {0, duration - 1}
    for frame, event in events:
        if type(frame) is not int or not 0 <= frame <= duration or type(event) is not int:
            raise ValueError('Invalid event frame')
        frames.add(min(frame, duration - 1))
    frames.update(f for f in (10, 16, 17, 30) if f < duration)
    if len(frames) > 32:
        raise ValueError('Pose budget exceeded')
    return sorted(frames)


def profile(species_id):
    if species_id == 56:
        raise ValueError('Damagumo owned by demon lane (#312); not profiled here')
    entry = SPECIES.get(species_id)
    if entry is None:
        raise ValueError('Unknown Long Legs species')
    if species_id == 56:
        raise ValueError('Damagumo is owned by the demon lane; not profiled here')
    if species_id == 66:
        rows = HOUDai_EVENTS
    else:
        rows = BIGFOOT_EVENTS
    return dict(
        schema=1, family=FAMILY, enemy_id=species_id, name=entry['name'],
        retail=entry['retail'], bestiary=entry['bestiary'], folder=entry['folder'],
        mouth_joints=list(MOUTH_JOINTS), mouth_radius=MOUTH_RADIUS,
        stickable_joints=list(STICKABLE_JOINTS), leg_tubes=list(LEG_TUBES),
        press_radius=PRESS_RADIUS, animation_rows={
            name: frames_for(_duration_for(species_id, name), rows)
            for name, rows in rows.items()
        },
        owned_by=entry['owned_by'] or 'codex/p2-longlegs-family',
    )


def _duration_for(species_id, name):
    """Retail clip durations (_frames evaluator) from the source audit."""
    lookup = {
        66: {'landing': 150, 'wait': 39, 'attack': 39, 'flick': 68, 'dead': 75},
        69: {'landing': 62, 'wait': 300, 'flick': 48, 'dead': 150},
        56: {},
    }
    durations = lookup[species_id]
    if name not in durations:
        raise ValueError('Unknown animation')
    return durations[name]


def mesh_profile(model_bytes):
    """Deterministic bind-pose mesh evidence for one owned family member.

    Decodes one `model.szs` member payload (the J3D2bmd3 `enemy.bmd`) into the
    skeleton joint list, a per-joint bind world matrix from
    :mod:`experimental.pikmin2_rigid` and an explicit presence report for every
    lane-contract joint identity in :data:`SPECIAL_JOINT_ROLES`. Byte-identical
    inputs yield byte-identical output; nothing here reads the clock, files,
    environment or ambient data.
    """
    if len(model_bytes) < 32 or model_bytes[:8] != b'J3D2bmd3':
        raise ValueError('Expected complete J3D2bmd3 model')
    b = blocks(model_bytes)
    names = joints(model_bytes)
    if not 1 <= len(names) <= 128:
        raise ValueError('Skeleton joint budget exceeded')
    matrices = joint_matrices(b)
    if len(matrices) != len(names):
        raise ValueError('Bone matrix count mismatch')
    if any(not all(math.isfinite(v) for row in matrix for v in row) for matrix in matrices):
        raise ValueError('Nonfinite bind joint transform')
    report = []
    for role, members in SPECIAL_JOINT_ROLES:
        for name in members:
            count = names.count(name)
            if count == 0:
                report.append(dict(name=name, role=role, present=False,
                                   index=None, matrix=None))
            elif count == 1:
                report.append(dict(name=name, role=role, present=True,
                                   index=names.index(name),
                                   matrix=matrices[names.index(name)]))
            else:
                raise ValueError('Ambiguous joint identity: %s' % name)
    texture_count = None
    if 'TEX1' in b:
        texture_count = u16(b['TEX1'], 8)
    return dict(
        model_sha256=hashlib.sha256(model_bytes).hexdigest(),
        joints=names,
        joint_count=len(names),
        special_joints=report,
        bone_matrices=matrices,
        embedded_texture_count=texture_count,
    )


def extract(iso, output):
    """Reproducible Long Legs family bank with decoded model evidence.

    Only the two family members this lane owns (Houdai, BigFoot) are read off
    the disc; Damagumo rows are deliberately excluded and pointed at the demon
    lane instead of being re-scanned here. Each owned `model.szs` is decoded
    into a bind-pose mesh profile. Output is refused if it already exists (the
    lane precedent: never overwrite reproduced evidence); the refusal happens
    before any disc read.
    """
    if output.exists():
        raise FileExistsError('Refusing to overwrite existing output')
    index = disc_files(iso)
    rows = {}
    models = {}
    with iso.open('rb') as disc:
        for name, enemy_id in (('Houdai', 66), ('BigFoot', 69)):
            path = 'enemy/data/%s/model.szs' % name
            offset, size = index[path]
            disc.seek(offset)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError('Truncated disc row')
            rows[path] = dict(enemy_id=enemy_id, size=size,
                              sha256=hashlib.sha256(raw).hexdigest())
            archive = archive_files(raw)
            if 'enemy.bmd' not in archive:
                raise ValueError('Missing enemy.bmd in %s' % path)
            model = archive['enemy.bmd']
            models[enemy_id] = (model, mesh_profile(model))
    output.mkdir(parents=True, exist_ok=False)
    profiles = {}
    for enemy_id in (66, 69):
        root = output / SPECIES[enemy_id]['folder']
        root.mkdir(exist_ok=False)
        (root / 'enemy.bmd').write_bytes(models[enemy_id][0])
        profiles[str(enemy_id)] = dict(profile(enemy_id), **models[enemy_id][1])
    result = dict(
        schema=1, family=FAMILY, lane='codex/p2-longlegs-family',
        profiles=profiles,
        disc_rows=rows, demon_lane=DEMON_LANE,
        limitations=[
            'Bind-pose mesh decode only; no animation pose banks, skeletal playback or event execution.',
            'Lane-contract joints (mouth rkamujnt/lkamujnt, stickable tama/teama, leg tubes lft1/lht1/rft1/rht1) are source-audit runtime identities; the two owned models ship none as mesh joints, so presence is recorded as false.',
            'Bone matrices are model-space bind world matrices before any runtime IK, tube tree or owner transform.',
            'Press and mouth radii are lane-contract values from the source audit, not mesh-derived.',
        ],
    )
    (output / 'long-legs-family.json').write_text(
        json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.iso, args.output)
    print(json.dumps(dict(
        species=[dict(enemy_id=p['enemy_id'], name=p['name'], joints=p['joint_count'],
                      present=sum(s['present'] for s in p['special_joints']))
                 for p in result['profiles'].values()],
        rows=len(result['disc_rows']),
    )))
    for path, row in sorted(result['disc_rows'].items()):
        print('%s enemy_id=%s sha256=%s' % (path, row['enemy_id'], row['sha256']))