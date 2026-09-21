"""MiniHoudai (Gatling Groink, enemy ID 78) source pose assets; no native behavior substitution.

Single-species ISO extractor modeled on
:mod:`experimental.pikmin2_sokkuri_assets` (hashed disc reads, GPVE01 check,
fail-closed registry validation, deterministic sampled poses) reusing the
audited Groink source contract (:mod:`experimental.pikmin2_groink_assets`:
general parameter ``profile``, ``kuti`` muzzle ``muzzle``). Reads the retail
MiniHoudai model/anim/parameter banks off the US GPVE01 rev 0 disc and samples
bounded rigid poses through the explicit draw-matrix path.

Output (``<output>/``, the identity-keyed ``MiniHoudai`` directory the family
installer pre-flights via ``_read_identity_source(source, 78, 'MiniHoudai')``):

* ``identity.json`` (schema 1, source_id 78, enum_name ``MiniHoudai``): the
  family installer's pre-flight identity source.
* ``minihoudai.json``: schema-1 manifest (species ``MiniHoudai``, enemy_id 78)
  with per-clip ``file``/``events``/``source_frames``/``sha256``/``status``,
  ``poses`` (``file``/``frame``/``sha256``) holding converted poses only under
  contiguous ``_00..`` slot names, ``muzzle_samples`` (model-space ``kuti``
  muzzle basis before the runtime aim callback) and ``unsupported_frames``
  listing sampled source frames the converter rejected.
* ``minihoudai_<clip>_<ii:02>.mod``: sampled pose meshes, plus a per-pose
  ``.json`` conversion record. Pose meshes are data-only: the current
  MiniHoudai adapter (``experimental.pikmin2_family_install._adapt_minihoudai``)
  stages only the ``p2-groink-teki.txt`` actor sidecar, so no native loader
  opens them yet; names are chosen not to collide with any staged bank.
* ``enemy.bmd`` and the four ``minihoudai/enemy*.txt`` metadata files, plus
  ``fixed-enemyparm.txt`` (the ``fminihoudai`` pedestal variant's parameters,
  preserved verbatim for audit; only the roaming MiniHoudai identity's values
  are profiled here), preserved verbatim for audit.

Deterministic: hashed disc reads, fixed clip order, no timestamps. Nothing is
fabricated: a clip that fails to convert is recorded ``unsupported`` with its
reason, never replaced with a placeholder pose.
"""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_animation import sample_frames
from experimental.pikmin2_breadbug_assets import collision_nodes, parameter_blocks, sha
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_groink_assets import muzzle, profile
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import joint_matrices
from experimental.pikmin2_sheargrub_assets import animation_rows, joints
from experimental.pikmin2_skinning import draw_matrices

SPECIES = 'MiniHoudai'
ENEMY_ID = 78
ENUM_NAME = 'MiniHoudai'
MANIFEST = 'minihoudai.json'
IDENTITY = 'identity.json'
MODEL_PATH = 'enemy/data/MiniHoudai/model.szs'
ANIM_PATH = 'enemy/data/MiniHoudai/anim.szs'
PARM_PATH = 'enemy/parm/enemyParms.szs'
PARM_PREFIX = 'minihoudai/'
FIXED_PARM_ENTRY = 'fminihoudai/enemyparm.txt'
METADATA_FILES = ('enemyparm.txt', 'enemycoll.txt', 'enemyanimmgr.txt',
                  'enemystoneinfo.txt')
MUZZLE_JOINT = 'kuti'

LIMITATIONS = [
    'Sampled rigid poses with approximate materials; no skeletal playback or event execution.',
    'Muzzle transforms precede the runtime vertical aim callback and owner world transform.',
    'Pose meshes are data-only; the MiniHoudai adapter stages only the p2-groink-teki.txt actor sidecar.',
    'No native runtime, AI/FSM, carcass delivery or revival is provided by this module.',
]


def pose_name(clip, number):
    """Deterministic pose mesh filename for one sampled pose."""
    return f'minihoudai_{clip}_{number:02}.mod'


def extract(iso, output, pose_limit=3):
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
            model = archive_files(read(disc, MODEL_PATH))['enemy.bmd']
        except KeyError:
            raise ValueError('MiniHoudai model missing enemy.bmd') from None
        motions = archive_files(read(disc, ANIM_PATH))
        params = archive_files(read(disc, PARM_PATH))
    disc_id = header[:6].decode()
    disc_revision = header[7]
    names = joints(model)
    if names.count(MUZZLE_JOINT) != 1:
        raise ValueError('Expected exactly one kuti muzzle joint')
    muzzle_index = names.index(MUZZLE_JOINT)
    model_blocks = blocks(model)

    metadata = {}
    for filename in METADATA_FILES:
        try:
            raw = params[PARM_PREFIX + filename]
        except KeyError:
            raise ValueError(
                f'MiniHoudai parameter entry missing: {PARM_PREFIX + filename}') from None
        metadata[filename] = sha(raw)
        (output / filename).write_bytes(raw)
    try:
        fixed = params[FIXED_PARM_ENTRY]
    except KeyError:
        raise ValueError(
            f'MiniHoudai parameter entry missing: {FIXED_PARM_ENTRY}') from None
    (output / 'fixed-enemyparm.txt').write_bytes(fixed)
    (output / 'enemy.bmd').write_bytes(model)

    # General parameter profile of the roaming MiniHoudai identity (raises on
    # duplicate/missing general blocks or nonphysical values).
    general = profile(params[PARM_PREFIX + 'enemyparm.txt'])
    rows = animation_rows(params[PARM_PREFIX + 'enemyanimmgr.txt'].decode('shift_jis'))
    if not 1 <= len(rows) <= 32:
        raise ValueError('Clip budget exceeded')

    clips = []
    for row in rows:
        stem = Path(row['file']).stem
        try:
            raw = motions[row['file']]
        except KeyError:
            raise ValueError(f'MiniHoudai motion missing: {row["file"]}') from None
        (output / row['file']).write_bytes(raw)
        duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
        clip = dict(file=row['file'], events=[list(event) for event in row['events']],
                    source_frames=duration, sha256=sha(raw),
                    poses=[], muzzle_samples=[], unsupported_frames=[],
                    status='unsupported')
        # Poses occupy contiguous _00.. slots: the sampled frames that fail to
        # convert are recorded under unsupported_frames (never replaced with a
        # placeholder) and never occupy a slot.
        for frame in sample_frames(duration, pose_limit):
            try:
                _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                transform = muzzle(joint_matrices(model_blocks, pose)[muzzle_index])
                matrices = draw_matrices(model_blocks, pose)
                decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices)
                name = pose_name(stem, len(clip['poses']))
                conversion = write_model(decoded, output / name, 'enemy.bmd')
                conversion.update(source='enemy.bmd', output=name,
                                  weighted_pose_baked=True, source_frame=frame)
                data = (output / name).read_bytes()
                clip['poses'].append(dict(file=name, frame=frame,
                                          sha256=hashlib.sha256(data).hexdigest()))
                clip['muzzle_samples'].append(dict(frame=frame, **transform))
                (output / Path(name).with_suffix('.json')).write_text(
                    json.dumps(conversion, sort_keys=True, indent=2) + '\n',
                    encoding='utf-8')
            except (ValueError, KeyError, ArithmeticError) as error:
                clip['unsupported_frames'].append(frame)
                clip.setdefault('unsupported_reasons', []).append(str(error))
        if clip['poses'] and len(clip['poses']) == len(clip['muzzle_samples']):
            clip['status'] = 'converted'
        elif not clip['poses']:
            clip['unsupported_reason'] = 'no sampled frames converted'
        else:
            clip['unsupported_reason'] = 'muzzle/pose slot mismatch'
        clips.append(clip)

    result = dict(
        schema=1, species=SPECIES, enemy_id=ENEMY_ID, enum_name=ENUM_NAME,
        native_ready=False,
        disc_id=disc_id, disc_revision=disc_revision,
        source_sha256=hashes, model_sha256=sha(model), joints=names,
        muzzle_joint=muzzle_index,
        parameters=general['parameter_blocks'], general=general['general'],
        fixed_variant=dict(enemy_id=97,
                           parameter_sha256=sha(fixed)),
        metadata_sha256=metadata,
        clips=clips,
        collision=collision_nodes(params[PARM_PREFIX + 'enemycoll.txt'], len(names)),
        limitations=list(LIMITATIONS))
    (output / MANIFEST).write_text(
        json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    (output / IDENTITY).write_text(
        json.dumps(dict(schema=1, source_id=ENEMY_ID, enum_name=ENUM_NAME),
                   indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=3)
    args = parser.parse_args()
    summary = extract(args.iso, args.output, args.pose_limit)
    print(json.dumps({
        'clips': len(summary['clips']),
        'converted': sum(c['status'] == 'converted' for c in summary['clips']),
        'poses': sum(len(c['poses']) for c in summary['clips']),
        'joints': len(summary['joints']),
    }, indent=2))
