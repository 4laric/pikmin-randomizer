"""UjiA/UjiB/Tobi (Sheargrubs + Shearwig, enemy IDs 12/13/14) source pose assets.

Single-family ISO extractor modeled on :mod:`experimental.pikmin2_sokkuri_assets`
and the UjiA/UjiB importer :mod:`experimental.pikmin2_sheargrub_assets`. Reads
the retail model/anim/parameter banks off the US GPVE01 rev 0 disc, validates
them against the audited disc registries below, and samples bounded rigid poses
through the explicit draw-matrix path. Tobi (Shearwig, source 14) has no prior
extractor; its layout mirrors the sheargrub pattern exactly:

* model ``enemy/data/Tobi/model.szs`` (``enemy.bmd``),
* motions ``enemy/data/Tobi/anim.szs`` (Tobi owns its archive, unlike UjiB),
* params ``enemy/parm/enemyParms.szs`` entries ``tobi/enemy*.txt``.

UjiB owns no animation archive: its registry shares the UjiA animations
(``enemyInfo.cpp:31``; see docs/PIKMIN2_GROUND_INVERTEBRATE_AUDIT.md), so UjiB
clips are read from ``enemy/data/UjiA/anim.szs`` while the model and params
come from the UjiB entries. Verified against the retail disc 2026-09-25:

* ``enemy/data/{UjiA,UjiB}/model.szs``, ``enemy/data/UjiA/anim.szs``,
  ``enemy/data/Tobi/{model,anim}.szs`` all present; no ``UjiB/anim.szs``.
* Registries (order = AnimID enum order): UjiA 7 clips
  (dead, dead_p, appear, dive, move, attack1, type5); UjiB 9 clips (the UjiA
  seven plus attack2, eat); Tobi 10 clips (the UjiB nine plus fly). Key events
  are recorded in EXPECTED_EVENTS below.

Output (``<output>/`` with one subdir per species):

* ``<Species>/uji.json``: schema-1 manifest (species ``<Species>``, matching
  enemy_id) with per-clip ``file``/``events``/``source_frames``/``sha256``/
  ``status``, ``poses`` (``file``/``frame``/``bytes``/``sha256``) holding
  converted poses only under contiguous ``_00..`` slot names, and
  ``unsupported_frames`` listing sampled source frames the converter rejected.
* ``<Species>/uji_<Species>_<clip>_%02d.mod``: sampled pose meshes, named
  exactly as the campaign-identity Uji loader opens them (``uji`` prefix +
  species + clip + zero-padded slot, mirroring the batch-2 ``loadPose`` grammar
  ``engine/pc_port/pc_p2_batch2.cpp:95-120`` and the proxy-visual precedent
  ``engine/pc_port/pc_p2_sheargrub.cpp:34``), plus a per-pose ``.json``
  conversion record.
* ``<Species>/enemy.bmd`` and the four ``<sp>/enemy*.txt`` metadata files,
  preserved verbatim for audit (params under the ``ujia/``, ``ujib/`` and
  ``tobi/`` prefixes of ``enemyParms.szs``).

Deterministic: hashed disc reads, fixed clip order, no timestamps. Nothing is
fabricated: a clip that fails to convert is recorded ``unsupported`` with its
reason, never replaced with a placeholder pose.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_animation import resource_chunks, sample_frames
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_ground_inverts_assets import LOOPS
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_sheargrub_assets import animation_rows, joints
from experimental.pikmin2_skinning import draw_matrices

SPECIES = {'UjiA': 12, 'UjiB': 13, 'Tobi': 14}
MANIFEST = 'uji.json'
MODEL_PATH = 'enemy/data/{species}/model.szs'
# UjiB shares the UjiA animation archive (enemyInfo.cpp:31); Tobi owns its own.
ANIM_ARCHIVE = {'UjiA': 'UjiA', 'UjiB': 'UjiA', 'Tobi': 'Tobi'}
ANIM_PATH = 'enemy/data/{archive}/anim.szs'
PARM_PATH = 'enemy/parm/enemyParms.szs'
PARM_PREFIX = {'UjiA': 'ujia/', 'UjiB': 'ujib/', 'Tobi': 'tobi/'}
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt',
                  'enemystoneinfo.txt')

# Registry order per species, read off the US GPVE01 rev 0 disc 2026-09-25
# (matches the native clip order in engine/pc_port/pc_p2_uji_animation.h:10-11
# for UjiA/UjiB; Tobi inserts fly before attack1).
CLIPS = {
    'UjiA': ('dead', 'dead_p', 'appear', 'dive', 'move', 'attack1', 'type5'),
    'UjiB': ('dead', 'dead_p', 'appear', 'dive', 'move', 'attack1',
             'attack2', 'eat', 'type5'),
    'Tobi': ('dead', 'dead_p', 'appear', 'dive', 'move', 'fly', 'attack1',
             'attack2', 'eat', 'type5'),
}

# Exact (frame, type) key events read from each species' enemyanimmgr.txt on
# the US GPVE01 rev 0 disc 2026-09-25. Types: 0 = KEYEVENT_LOOP_START, 1 =
# KEYEVENT_LOOP_END, 2+ = state hooks (bridge gnaw, bite, swallow).
EXPECTED_EVENTS = {
    'UjiA': {
        'dead': [], 'dead_p': [], 'appear': [], 'dive': [],
        'move': [[0, 0], [19, 1]],
        'attack1': [[15, 2]],
        'type5': [[10, 0], [29, 1]],
    },
    'UjiB': {
        'dead': [], 'dead_p': [], 'appear': [], 'dive': [],
        'move': [[0, 0], [19, 1]],
        'attack1': [[15, 2]],
        'attack2': [[5, 2], [12, 3], [14, 4]],
        'eat': [[53, 2]],
        'type5': [[10, 0], [29, 1]],
    },
    'Tobi': {
        'dead': [], 'dead_p': [], 'appear': [], 'dive': [],
        'move': [[0, 0], [19, 1]],
        'fly': [[46, 0], [65, 1]],
        'attack1': [[15, 2]],
        'attack2': [[5, 2], [12, 3], [14, 4]],
        'eat': [[53, 2]],
        'type5': [[10, 0], [29, 1]],
    },
}

LIMITATIONS = [
    'Sampled rigid poses with approximate materials; no skeletal playback or event execution.',
    'Animation key events and parameter text are preserved as data only; bridge gnaw, bite/capture, swallow, burrow cycle, flight and lifecycle behavior do not execute.',
    'No native runtime, AI/FSM, install or arena placement is provided by this module; see experimental.pikmin2_uji_content for staging.',
    'UjiB shares the UjiA animation archive (enemyInfo.cpp:31); its clips are sampled from enemy/data/UjiA/anim.szs against the UjiB model.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pose_name(species, clip, number):
    """Native bank filename for one sampled pose (``uji`` prefix grammar)."""
    return f'uji_{species}_{clip}_{number:02}.mod'


def extract(iso, output, pose_limit=4):
    if type(pose_limit) is not int or not 2 <= pose_limit <= 8:
        raise ValueError(f'Pose limit must be 2..8: {pose_limit!r}')
    iso, output = Path(iso), Path(output)
    if not iso.is_file():
        raise ValueError(f'ISO not found: {iso}')
    if output.exists():
        raise ValueError(f'Output already exists: {output}')
    output.mkdir(parents=True, exist_ok=False)
    index = disc_files(iso)
    hashes = {}

    def read(disc, path):
        try:
            at, size = index[path]
        except KeyError:
            raise ValueError(f'Disc entry missing: {path}') from None
        disc.seek(at)
        raw = disc.read(size)
        if len(raw) != size:
            raise ValueError(f'Truncated disc entry: {path}')
        hashes[path] = sha(raw)
        return raw

    with iso.open('rb') as disc:
        header = disc.read(8)
        if header[:6] != b'GPVE01':
            raise ValueError('Expected supplied US GPVE01 disc')
        try:
            params = archive_files(read(disc, PARM_PATH))
        except KeyError:
            raise ValueError('Uji parameter archive missing enemyParms.szs') from None
        models, motions, registries = {}, {}, {}
        for species in SPECIES:
            try:
                models[species] = archive_files(
                    read(disc, MODEL_PATH.format(species=species)))['enemy.bmd']
            except KeyError:
                raise ValueError(f'{species} model missing enemy.bmd') from None
            archive = ANIM_ARCHIVE[species]
            if archive not in motions:
                try:
                    motions[archive] = archive_files(
                        read(disc, ANIM_PATH.format(archive=archive)))
                except KeyError:
                    raise ValueError(f'{species} motions missing anim.szs') from None
            prefix = PARM_PREFIX[species]
            try:
                registries[species] = params[prefix + 'enemyanimmgr.txt']
            except KeyError:
                raise ValueError(
                    f'{species} parameter entry missing: {prefix}enemyanimmgr.txt') from None

    for species, identity in SPECIES.items():
        root = output / species
        root.mkdir()
        model = models[species]
        motions_archive = motions[ANIM_ARCHIVE[species]]
        names = joints(model)
        if not names:
            raise ValueError(f'{species} model carries no joints')
        model_blocks = blocks(model)
        try:
            envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
            draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
        except (KeyError, struct.error) as error:
            raise ValueError(f'Invalid {species} model skinning blocks: {error}') from None

        metadata = {}
        prefix = PARM_PREFIX[species]
        for filename in METADATA_FILES:
            try:
                raw = params[prefix + filename]
            except KeyError:
                raise ValueError(
                    f'{species} parameter entry missing: {prefix + filename}') from None
            metadata[filename] = sha(raw)
            (root / filename).write_bytes(raw)
        (root / 'enemy.bmd').write_bytes(model)

        rows = animation_rows(registries[species].decode('shift_jis'))
        order = tuple(Path(row['file']).stem for row in rows)
        if order != CLIPS[species]:
            raise ValueError(f'Unexpected {species} clip registry: {order}')

        clips = []
        reference = None
        total_pose_bytes = 0
        for row in rows:
            stem = Path(row['file']).stem
            try:
                raw = motions_archive[row['file']]
            except KeyError:
                raise ValueError(f'{species} motion missing: {row["file"]}') from None
            (root / row['file']).write_bytes(raw)
            duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
            if raw[40] not in LOOPS:
                raise ValueError(f'Unsupported {species} loop attribute: {row["file"]}')
            clip = dict(file=row['file'], events=[list(event) for event in row['events']],
                        source_frames=duration, sha256=sha(raw),
                        loop_attribute=raw[40], loop_semantics=LOOPS[raw[40]],
                        poses=[], unsupported_frames=[], status='unsupported')
            if row['events'] != EXPECTED_EVENTS[species][stem]:
                raise ValueError(f'{species} clip {stem} key events mismatch')
            # Bank slots are assigned to converted poses only, contiguously
            # from zero: the native loader opens indices 0..N-1 and aborts on
            # a gap, so an unconvertible sampled frame is recorded under
            # unsupported_frames (never replaced with a placeholder) and never
            # occupies a slot.
            for frame in sample_frames(duration, pose_limit):
                try:
                    _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                    matrices = draw_matrices(model_blocks, pose)
                    decoded = decode(model, True, bake_rigid=True,
                                     draw_matrices=matrices)
                    name = pose_name(species, stem, len(clip['poses']))
                    conversion = write_model(decoded, root / name, 'enemy.bmd')
                    conversion.update(source='enemy.bmd', output=name,
                                      weighted_pose_baked=envelopes > 0,
                                      source_frame=frame)
                    data = (root / name).read_bytes()
                    resources = resource_chunks(data)
                    if reference is not None and resources != reference:
                        raise ValueError(
                            f'{species} pose changes immutable render resources')
                    reference = resources
                    total_pose_bytes += len(data)
                    clip['poses'].append(dict(file=name, frame=frame, bytes=len(data),
                                              sha256=sha(data)))
                    (root / Path(name).with_suffix('.json')).write_text(
                        json.dumps(conversion, sort_keys=True, indent=2) + '\n',
                        encoding='utf-8')
                except (ValueError, KeyError, ArithmeticError) as error:
                    clip['unsupported_frames'].append(frame)
            if clip['poses']:
                clip['status'] = 'converted'
            else:
                clip['unsupported_reason'] = 'no sampled frames'
            clips.append(clip)

        result = dict(
            schema=1, species=species, enemy_id=identity,
            disc_id=header[:6].decode(), disc_revision=header[7],
            source_sha256={k: v for k, v in hashes.items()
                           if species in k or ANIM_ARCHIVE[species] in k
                           or 'enemyParms' in k},
            model_sha256=sha(model), joints=names,
            metadata_sha256=metadata,
            skinning=dict(envelopes=envelopes, draw_matrices=draws,
                          weighted_baking=envelopes > 0,
                          self_contained_resources=draws > 0),
            clips=clips, total_pose_bytes=total_pose_bytes,
            limitations=list(LIMITATIONS))
        (root / MANIFEST).write_text(
            json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return {'species': dict(SPECIES)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=4)
    args = parser.parse_args()
    summary = extract(args.iso, args.output, args.pose_limit)
    print(json.dumps(summary, indent=2))
