"""Data-driven campaign-proxy source pose assets; no native behavior substitution.

Species-agnostic version of :mod:`experimental.pikmin2_sokkuri_assets` for the
proxy family (issue #871). Reads one species' model/anim/parameter banks off
the US GPVE01 rev 0 disc, takes the clip list from that species'
``enemyanimmgr.txt``, and samples bounded rigid poses through the explicit
draw-matrix path into ``px_<Species>_<clip>_NN.mod`` pose meshes plus a
``proxy.json`` manifest (the Sokkuri manifest's information minus the
species-specific profile checks).

Output (``<output>/``, the identity-keyed ``<Enum>`` directory the proxy
installer reads):

* ``proxy.json``: schema-1 manifest (species ``<Enum>``, enemy_id
  ``<source_id>``) with per-clip ``file``/``events``/``source_frames``/
  ``sha256``/``status``, ``poses`` (``file``/``frame``/``bytes``/``sha256``)
  holding converted poses only under contiguous ``_00..`` slot names, and
  ``unsupported_frames`` listing sampled source frames the converter rejected.
* ``px_<Enum>_<clip>_%02d.mod``: sampled pose meshes, named exactly as the
  proxy bank loader opens them, plus a per-pose ``.json`` conversion record.
* ``enemy.bmd`` and the ``enemy*.txt`` metadata files found under the
  species' parameter prefix, preserved verbatim for audit.

Deterministic: hashed disc reads, fixed clip order, no timestamps. Nothing is
fabricated: a clip that fails to convert is recorded ``unsupported`` with its
reason, never replaced with a placeholder pose. Pose indices are contiguous
from zero, an unconvertible frame is recorded under ``unsupported_frames``
and never gets a slot, and every pose must share identical render resources.
"""

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_animation import resource_chunks, sample_frames
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_sheargrub_assets import animation_rows, joints
from experimental.pikmin2_skinning import draw_matrices

MANIFEST = 'proxy.json'
PARM_PATH = 'enemy/parm/enemyParms.szs'
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt',
                  'enemystoneinfo.txt')

ENUM_RE = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,31}')

# Generic proxy clip cover: the native side picks the clip from host state and
# falls back across these groups, so a bank with no wait or no dead clip
# cannot serve the proxy family.
WAIT_CLIPS = ('wait1', 'wait', 'wait2')
DEAD_CLIPS = ('dead', 'dead1', 'pdead1')

CLIP_BYTES = 512 * 1024
TOTAL_BYTES = 8 * 1024 * 1024

LIMITATIONS = [
    'Sampled rigid poses with approximate materials; no skeletal playback or event execution.',
    'Animation key events and parameter text are preserved as data only; no damage, death, movement or carry behavior executes.',
    'No native runtime, AI/FSM, install or arena placement is provided by this module; see experimental.pikmin2_proxy_content for staging.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pose_name(species, clip, number):
    """Native bank filename for one sampled pose (proxy ``loadPose`` grammar)."""
    return f'px_{species}_{clip}_{number:02}.mod'


def _roster_entry(source_id):
    """Return the (enum_name, assets) roster entry for one source id."""
    path = Path(__file__).resolve().parents[1] / 'docs' / 'PIKMIN2_ENEMY_ROSTER.json'
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ValueError(f'Proxy roster unreadable: {path}: {error}') from error
    for entry in payload.get('entries', []):
        if isinstance(entry, dict) and entry.get('source_id') == source_id:
            return entry.get('enum_name'), entry.get('assets', {})
    raise ValueError(f'Proxy source id {source_id!r} unknown to the roster')


def _asset_names(enum_name, assets):
    """Derive disc names from the roster assets block, falling back to the enum."""
    if not isinstance(assets, dict):
        assets = {}
    model = assets.get('model') or enum_name
    anim = assets.get('anim') or enum_name
    param = assets.get('param') or enum_name
    if not all(isinstance(name, str) and name for name in (model, anim, param)):
        raise ValueError(f'Proxy assets block unusable for {enum_name!r}')
    return model, anim, param.lower()


def extract(iso, enum_name, source_id, output, pose_limit=4):
    if not isinstance(enum_name, str) or not ENUM_RE.fullmatch(enum_name):
        raise ValueError(f'Proxy enum name invalid: {enum_name!r}')
    if type(source_id) is not int or isinstance(source_id, bool):
        raise ValueError(f'Proxy source id must be an int: {source_id!r}')
    if type(pose_limit) is not int or not 2 <= pose_limit <= 8:
        raise ValueError(f'Pose limit must be 2..8: {pose_limit!r}')
    roster_enum, roster_assets = _roster_entry(source_id)
    if roster_enum != enum_name:
        raise ValueError(
            f'Proxy enum mismatch for source {source_id}: '
            f'{enum_name!r} != roster {roster_enum!r}')
    model_name, anim_name, param_dir = _asset_names(enum_name, roster_assets)
    model_path = f'enemy/data/{model_name}/model.szs'
    anim_path = f'enemy/data/{anim_name}/anim.szs'
    parm_prefix = f'{param_dir}/'
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
            model = archive_files(read(disc, model_path))['enemy.bmd']
        except KeyError:
            raise ValueError(f'{enum_name} model missing enemy.bmd') from None
        motions = archive_files(read(disc, anim_path))
        params = archive_files(read(disc, PARM_PATH))
    names = joints(model)
    if not names:
        raise ValueError(f'{enum_name} model carries no joints')
    model_blocks = blocks(model)
    try:
        envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
        draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
    except (KeyError, struct.error) as error:
        raise ValueError(f'Invalid {enum_name} model skinning blocks: {error}') from None

    metadata = {}
    for filename in METADATA_FILES:
        try:
            raw = params[parm_prefix + filename]
        except KeyError:
            raise ValueError(
                f'{enum_name} parameter entry missing: {parm_prefix + filename}') from None
        metadata[filename] = sha(raw)
        (output / filename).write_bytes(raw)
    (output / 'enemy.bmd').write_bytes(model)

    rows = animation_rows(params[parm_prefix + 'enemyanimmgr.txt'].decode('shift_jis'))
    if not 1 <= len(rows) <= 32:
        raise ValueError(f'{enum_name} clip budget exceeded: {len(rows)}')

    clips = []
    reference = None
    total_pose_bytes = 0
    for row in rows:
        stem = Path(row['file']).stem
        try:
            raw = motions[row['file']]
        except KeyError:
            raise ValueError(f'{enum_name} motion missing: {row["file"]}') from None
        (output / row['file']).write_bytes(raw)
        duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
        clip = dict(file=row['file'], events=[list(event) for event in row['events']],
                    source_frames=duration, sha256=sha(raw),
                    poses=[], unsupported_frames=[], status='unsupported')
        # Bank slots are assigned to converted poses only, contiguously from
        # zero: an unconvertible sampled frame is recorded under
        # unsupported_frames (never replaced with a placeholder) and never
        # occupies a slot.
        for frame in sample_frames(duration, pose_limit):
            try:
                _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                matrices = draw_matrices(model_blocks, pose)
                decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices)
                name = pose_name(enum_name, stem, len(clip['poses']))
                conversion = write_model(decoded, output / name, 'enemy.bmd')
                conversion.update(source='enemy.bmd', output=name,
                                  weighted_pose_baked=envelopes > 0,
                                  source_frame=frame)
                data = (output / name).read_bytes()
                resources = resource_chunks(data)
                if reference is not None and resources != reference:
                    raise ValueError(
                        f'{enum_name} pose changes immutable render resources')
                reference = resources
                total_pose_bytes += len(data)
                clip['poses'].append(dict(file=name, frame=frame, bytes=len(data),
                                          sha256=sha(data)))
                (output / Path(name).with_suffix('.json')).write_text(
                    json.dumps(conversion, sort_keys=True, indent=2) + '\n',
                    encoding='utf-8')
            except (ValueError, KeyError, ArithmeticError) as error:
                clip['unsupported_frames'].append(frame)
        if clip['poses']:
            clip['status'] = 'converted'
        else:
            clip['unsupported_reason'] = 'no sampled frames converted'
        clips.append(clip)

    converted_stems = {Path(clip['file']).stem for clip in clips
                       if clip['status'] == 'converted'}
    if not converted_stems & set(WAIT_CLIPS):
        raise ValueError(
            f'{enum_name} bank has none of the wait clips {list(WAIT_CLIPS)}')
    if not converted_stems & set(DEAD_CLIPS):
        raise ValueError(
            f'{enum_name} bank has none of the dead clips {list(DEAD_CLIPS)}')
    for clip in clips:
        clip_bytes = sum(pose['bytes'] for pose in clip['poses'])
        if clip_bytes > CLIP_BYTES:
            raise ValueError(
                f'{enum_name} clip {clip["file"]} exceeds 512 KiB of pose bytes '
                f'({clip_bytes} bytes); lower pose_limit (now {pose_limit})')
    if total_pose_bytes > TOTAL_BYTES:
        raise ValueError(
            f'{enum_name} bank exceeds 8 MiB of pose bytes '
            f'({total_pose_bytes} bytes); lower pose_limit (now {pose_limit})')

    result = dict(
        schema=1, species=enum_name, enemy_id=source_id,
        disc_id=header[:6].decode(), disc_revision=header[7],
        source_sha256=hashes, model_sha256=sha(model), joints=names,
        pose_limit=pose_limit,
        metadata_sha256=metadata,
        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                      weighted_baking=envelopes > 0,
                      self_contained_resources=draws > 0),
        clips=clips, total_pose_bytes=total_pose_bytes,
        limitations=list(LIMITATIONS))
    (output / MANIFEST).write_text(
        json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--enum', required=True)
    parser.add_argument('--source-id', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=4)
    args = parser.parse_args()
    summary = extract(args.iso, args.enum, args.source_id, args.output,
                      args.pose_limit)
    print(json.dumps({
        'species': summary['species'],
        'clips': len(summary['clips']),
        'converted': sum(c['status'] == 'converted' for c in summary['clips']),
        'poses': sum(len(c['poses']) for c in summary['clips']),
        'pose_bytes': summary['total_pose_bytes'],
    }, indent=2))
