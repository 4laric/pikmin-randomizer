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
MOVE_CLIPS = ('move1', 'move', 'move2', 'run1', 'walk')
ATTACK_CLIPS = ('attack1', 'attack', 'attack2', 'charge', 'hit_start')
CANONICAL_CLIPS = frozenset(WAIT_CLIPS + DEAD_CLIPS + MOVE_CLIPS + ATTACK_CLIPS)

CLIP_STEM_RE = re.compile(r'[A-Za-z0-9_]+')
PARAM_DIR_RE = re.compile(r'[a-z][a-z0-9_]{0,31}')

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


def _row_overrides(row, enum_name):
    """Resolve the optional data-driven row overrides for one extraction.

    ``row`` is ``None`` (roster defaults, the pre-existing callers) or a
    declaration/plan mapping carrying any of ``asset_dir`` (disc directory
    under ``enemy/data/`` holding ``model.szs``/``anim.szs`` when it is not
    the enum name), ``param_dir`` (lowercase prefix inside the enemy
    parameter archive when it is not ``enum.lower()``) and     ``clips``
    (``{canonical_output: source_stem}`` aliases; the aliased source clip
    is written under the canonical name and not under its own) and
    ``param_files`` (``{metadata_filename: prefix}`` per-file parameter
    prefixes for split families such as the dweevils, whose shared
    ``otakara/`` folder carries the anim mgr/collision/stone tables while
    each colour keeps its own ``<species>/enemyparm.txt``). Every
    violation fails closed with a clear ``ValueError``; registry
    membership of alias sources is checked later against the parsed
    registry so the error can name the species' actual stems.
    """
    asset_dir, param_dir, clips, param_files = None, None, {}, {}
    if row is None:
        return asset_dir, param_dir, clips, param_files
    if not isinstance(row, dict):
        raise ValueError(f'Proxy row overrides must be a mapping: {row!r}')
    if row.get('asset_dir') is not None:
        asset_dir = row['asset_dir']
        if not isinstance(asset_dir, str) or not ENUM_RE.fullmatch(asset_dir):
            raise ValueError(
                f'Proxy asset_dir invalid for {enum_name!r}: {asset_dir!r}')
    if row.get('param_dir') is not None:
        param_dir = row['param_dir']
        if not isinstance(param_dir, str) or not PARAM_DIR_RE.fullmatch(param_dir):
            raise ValueError(
                f'Proxy param_dir invalid for {enum_name!r}: {param_dir!r}')
    if row.get('clips'):
        raw = row['clips']
        if not isinstance(raw, dict) or not raw:
            raise ValueError(
                f'Proxy clips must be a non-empty object for {enum_name!r}')
        for canonical, source in raw.items():
            if canonical not in CANONICAL_CLIPS:
                raise ValueError(
                    f'Proxy clips key not a native clip name for {enum_name!r}: '
                    f'{canonical!r}')
            if not isinstance(source, str) or not CLIP_STEM_RE.fullmatch(source):
                raise ValueError(
                    f'Proxy clips source invalid for {enum_name!r}: {source!r}')
            if source == canonical:
                raise ValueError(
                    f'Proxy clips alias is a no-op for {enum_name!r}: '
                    f'{canonical!r}')
        if len(set(raw.values())) != len(raw):
            raise ValueError(
                f'Proxy clips sources must be distinct for {enum_name!r}')
        clips = dict(raw)
    if row.get('param_files'):
        raw_files = row['param_files']
        if not isinstance(raw_files, dict) or not raw_files:
            raise ValueError(
                f'Proxy param_files must be a non-empty object for {enum_name!r}')
        for filename, prefix in raw_files.items():
            if filename not in METADATA_FILES:
                raise ValueError(
                    f'Proxy param_files key not a metadata file for '
                    f'{enum_name!r}: {filename!r}')
            if not isinstance(prefix, str) or not PARAM_DIR_RE.fullmatch(prefix):
                raise ValueError(
                    f'Proxy param_files prefix invalid for {enum_name!r}: '
                    f'{prefix!r}')
        param_files = dict(raw_files)
    return asset_dir, param_dir, clips, param_files


def extract(iso, enum_name, source_id, output, pose_limit=4, row=None):
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
    row_asset, row_param, aliases, param_files = _row_overrides(row, enum_name)
    if row_asset is not None:
        # A row override names the disc directory directly (verified
        # against the ISO listing per species); the roster assets block is
        # the fallback for rows that predate the override fields.
        model_name = anim_name = row_asset
    if row_param is not None:
        param_dir = row_param
    model_path = f'enemy/data/{model_name}/model.szs'
    anim_path = f'enemy/data/{anim_name}/anim.szs'
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
    missing_metadata = []
    for filename in METADATA_FILES:
        prefix = param_files.get(filename, param_dir)
        try:
            raw = params[f'{prefix}/{filename}']
        except KeyError:
            if filename == 'enemystoneinfo.txt':
                # Optional metadata: absent from the disc for Qurione.
                missing_metadata.append(filename)
                continue
            raise ValueError(
                f'{enum_name} parameter entry missing: {prefix}/{filename}') from None
        metadata[filename] = sha(raw)
        (output / filename).write_bytes(raw)
    (output / 'enemy.bmd').write_bytes(model)

    registry_notes = []
    animmgr_prefix = param_files.get('enemyanimmgr.txt', param_dir)
    rows = animation_rows(params[f'{animmgr_prefix}/enemyanimmgr.txt'].decode('shift_jis'),
                          allow_uppercase=True, dedupe_duplicates=True,
                          allow_braceless=True, notes=registry_notes)
    if not 1 <= len(rows) <= 32:
        raise ValueError(f'{enum_name} clip budget exceeded: {len(rows)}')
    registry_stems = {Path(item['file']).stem for item in rows}
    by_source = {}
    for canonical, source in aliases.items():
        if source not in registry_stems:
            raise ValueError(
                f'{enum_name} clips source {source!r} not in the species '
                f'registry: {sorted(registry_stems)}')
        by_source[source] = canonical
    native_stems = registry_stems - set(by_source)
    for canonical in aliases:
        if canonical in native_stems:
            raise ValueError(
                f'{enum_name} clips output {canonical!r} collides with a '
                f'native registry clip')
    lower_motions = {}
    for key in motions:
        lowered = key.lower()
        if lowered in lower_motions and lower_motions[lowered] != key:
            raise ValueError(
                f'{enum_name} motion archive has case-ambiguous entries: '
                f'{key!r}')
        lower_motions[lowered] = key

    clips = []
    unsupported_clips = []
    case_resolved = []
    reference = None
    total_pose_bytes = 0
    for row in rows:
        stem = Path(row['file']).stem
        out_stem = by_source.get(stem, stem)
        out_file = f'{out_stem}.bca'
        try:
            raw = motions[row['file']]
        except KeyError:
            actual = lower_motions.get(row['file'].lower())
            if actual is None:
                raise ValueError(f'{enum_name} motion missing: {row["file"]}') from None
            raw = motions[actual]
            case_resolved.append(f'{row["file"]}->{actual}')
        (output / out_file).write_bytes(raw)
        try:
            duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
        except (ValueError, KeyError, ArithmeticError) as error:
            # A clip whose sampling raises is skipped with its error
            # recorded instead of aborting the species, as long as wait +
            # dead cover survives on the remaining clips.
            unsupported_clips.append(dict(file=row['file'], out_file=out_file,
                                          error=f'{type(error).__name__}: {error}',
                                          sha256=sha(raw)))
            continue
        clip = dict(file=out_file, events=[list(event) for event in row['events']],
                    source_frames=duration, sha256=sha(raw),
                    poses=[], unsupported_frames=[], status='unsupported')
        if out_stem != stem:
            clip['source_file'] = row['file']
        # Bank slots are assigned to converted poses only, contiguously from
        # zero: an unconvertible sampled frame is recorded under
        # unsupported_frames (never replaced with a placeholder) and never
        # occupies a slot.
        for frame in sample_frames(duration, pose_limit):
            try:
                _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                matrices = draw_matrices(model_blocks, pose)
                decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices)
                name = pose_name(enum_name, out_stem, len(clip['poses']))
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

    if case_resolved:
        registry_notes.append(
            f'case-insensitive motion lookup for {len(case_resolved)} clips '
            f'(e.g. {case_resolved[0]})')
    result = dict(
        schema=1, species=enum_name, enemy_id=source_id,
        disc_id=header[:6].decode(), disc_revision=header[7],
        source_sha256=hashes, model_sha256=sha(model), joints=names,
        pose_limit=pose_limit,
        asset_dir=model_name, param_dir=param_dir,
        clips_alias=dict(aliases), param_files=dict(param_files),
        metadata_sha256=metadata,
        missing_metadata=list(missing_metadata),
        registry_notes=list(registry_notes),
        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                      weighted_baking=envelopes > 0,
                      self_contained_resources=draws > 0),
        clips=clips, unsupported_clips=unsupported_clips,
        total_pose_bytes=total_pose_bytes,
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
