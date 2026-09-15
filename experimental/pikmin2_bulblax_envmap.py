"""Opt-in Bulblax Queen body environment stage; additive, no shared converter edits.

The converter's single-stage writer (``experimental/pikmin2_convert.py``
``write_model``, material chunk 48) bakes only the diffuse base of the Queen
(MAT3 material 0) body shape. The source material's second TEV stage is a
normal-texgen specular/environment stage:

- MAT3 mat0 stage 1: texgen 0 = (type 1, source 1 = ``GX_TG_NRM``, matrix 30 =
  ``TEXMTX0``); TEV order ``[0, 0, 5]``; RGB arguments ``[15, 10, 8, 0]``;
  samples texture slot 0 = TEX1 index 1 (RGB565 64x64 envmap); ``TEXMTX0`` is
  animated by ``queenchappy_model.btk`` (``J3D1btk1``/TTK1, 448 bytes,
  sha256 af0dde017624a5b30459b8ba55ed70a1d70de14f841ed58802b3b07565ef4eae).
  Source bytes (``p234-import/Queen/enemy.bmd`` MAT3 material 0 stage 1, raw 20):
  ``[255, 15, 10, 8, 0, 0, 0, 0, 1, 0, 4, 7, 6, 0, 0, 0, 0, 0, 0, 255]``.

The host engine is already able to consume this stage without new native code
(``engine/src/sysDolphin/dgxGraphics.cpp``):
- ``PVWTevInfo::mTevStageCount`` drives ``GXSetNumTevStages`` and each
  ``PVWTevStage`` is applied verbatim through ``GXSetTevColorIn``/``GXSetTevOrder``.
- ``DGXGraphics::setMatMatrices`` treats a ``PVWTextureData`` whose serialized
  ``_UNUSED10`` byte is ``0xE6`` and whose texgen ``mTexGenSrc`` is
  ``GX_TG_NRM`` (1) as the opt-in marker: it sets ``mP2Envmap`` and feeds
  ``mP2EnvSRT``; ``DGXGraphics::useMatrixQuick`` then builds the texture matrix
  through ``engine/pc_port/pc_p2_envmap.h``. Abort guards require exactly one
  marked stage per material, ``mAnimationFactor != 255``,
  ``mTotalFrameCount == 0`` and ``mRotationZ == 0``.

This module appends that second stage to one already-generated pose without
touching any shared converter function or default. It rewrites only MOD chunk
48 (material): the target shape's ``PVWTevInfo`` grows from one to two stages,
and the target material grows one `PVWTextureData` (normal texgen + envmap
attribute) plus one texgen entry. Every other chunk is byte-identical.

Intended pipeline order: bank build -> Bulblax material profile (which rebinds
the body base from the envmap TEX1[1] to the diffuse base TEX1[2],
``pikmin2_bulblax_material.py``) -> this envmap stage (which re-references
TEX1[1] as the second, normal-texgen input). Applying this before the material
profile would make both inputs the same texture.

``TEXMTX0`` is still static here: ``queenchappy_model.btk`` sampling is exposed
but not fed into ``mP2EnvSRT`` (see docs/PIKMIN2_BULBLAX_ENVMAP.md). No native
build is performed by this slice.

Issue #416 (parent #239); source import #234/#223; material profile #235.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

from experimental.pikmin2_convert import Writer, u32
from experimental.pikmin2_frog_visual_audit import chunks

POLICY = 'P2_BULBLAX_ENVMAP_1'

# Anchor for the material profile whose output this stage layers on.
MATERIAL_POLICY = 'P2_BULBLAX_MATERIAL_1'

# Generated single-stage record sizes (see write_model, pikmin2_convert.py:263-280).
TEV_INFO_SIZE = 124          # PVWTevInfo with one PVWTevStage
TEV_STAGE_OFF = 92           # first PVWTevStage inside a PVWTevInfo
TEV_STAGE_COUNT_OFF = 88     # PVWTevInfo::mTevStageCount
TEV_STAGE_SIZE = 32          # serialized PVWTevStage
TEXGEN_COUNT_OFF = 76        # Material::mTextureInfo.mTexGenDataCount
TEXGEN_OFF = 80              # first PVWTexGenData
TEXGEN_SIZE = 4
TEXTURE_DATA_SIZE = 64       # serialized PVWTextureData
TEXTURE_DATA_COUNT_EXTRA = 4

# Serialized PVWTextureData fields used by the engine envmap marker.
TD_SOURCE_ATTR_OFF = 0       # mSourceAttrIndex (TexAttr index == TEX1 index)
TD_MARKER_OFF = 8            # serialized _UNUSED10
TD_TEV_FLAG_OFF = 9          # serialized _UNUSED11 (counted into mTevStageCount)
TD_ANIM_FACTOR_OFF = 12      # mAnimationFactor
TD_TOTAL_FRAME_OFF = 16      # mTotalFrameCount
TD_ANIM_SPEED_OFF = 20       # mAnimSpeed
TD_SCALE_X_OFF = 24
TD_SCALE_Y_OFF = 28
TD_ROTATION_OFF = 32
TD_TRANSLATION_X_OFF = 36
TD_TRANSLATION_Y_OFF = 40
TD_PIVOT_X_OFF = 44
TD_PIVOT_Y_OFF = 48

ENVMAP_MARKER = 0xE6         # dgxGraphics.cpp:1005 explicit source-export marker
TEV_FLAG = 2                 # dgxGraphics.cpp:522 mTevStageCount marker
ANIMATION_FACTOR = 0         # 0xFF is rejected by the engine marker path

# Queen body: INF1 shape 1 maps to MAT3 material 0
# (pikmin2_bulblax_material.py:_shape_mapping / profile).
QUEEN_BODY_SHAPE = 1
QUEEN_ENVMAP_TEXTURE = 1     # TEX1[1], the 64x64 RGB565 envmap

# Exact source stage 1, mapped onto the generated layout. The source order is
# [texcoord 0, texmap 0, channel 5]; the converter's baked base already occupies
# generated texcoord/map 0, so the environment stage takes generated 1/1.
QUEEN_BODY = {
    'shape': QUEEN_BODY_SHAPE,
    'texture': QUEEN_ENVMAP_TEXTURE,
    'tex_coord_id': 1,
    'tex_map_id': 1,
    'channel_id': 5,
    'k_color_sel': 0,
    'k_alpha_sel': 0,
    # source rgb args [15, 10, 8, 0], op/bias/scale/clamp/register [0,0,0,1,0]
    'color_combiner': (15, 10, 8, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    # source alpha args [4, 7, 6, 0], op/bias/scale/clamp/register [0,0,0,0,0]
    'alpha_combiner': (4, 7, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    # source texgen (type 1, GX_TG_NRM, matrix 30 = TEXMTX0)
    'texgen': (1, 1, 30),
    # static SRT sampled from queenchappy_model.btk; identity until native BTK.
    'srt': (1.0, 1.0, 0.0, 0.0, 0.0, 0.0),
    'marker': ENVMAP_MARKER,
    'tev_flag': TEV_FLAG,
    'animation_factor': ANIMATION_FACTOR,
}

_SRT_KEYS = ('scale_x', 'scale_y', 'pivot_x', 'pivot_y', 'translation_x', 'translation_y')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _chunk_offsets(raw):
    """(offset, tag, end) for every MOD chunk, in file order."""
    result = []
    at = 0
    while at + 8 <= len(raw):
        tag, size = struct.unpack_from('>II', raw, at)
        end = at + 8 + size
        _require(end <= len(raw), 'Invalid MOD chunk')
        result.append((at, tag, end))
        at = end
        if tag == 65535:
            break
    _require(result and result[-1][1] == 65535 and result[-1][2] == len(raw),
             'Expected a complete generated MOD without a source footer')
    return result


def _parse_tev_infos(chunk, count):
    """Parse generated PVWTevInfo blocks; one or more stages each (read-back)."""
    infos = []
    at = 32
    for _ in range(count):
        _require(at + TEV_INFO_SIZE <= len(chunk), 'Truncated generated TEV block')
        stage_count = u32(chunk, TEV_STAGE_COUNT_OFF + at)
        _require(1 <= stage_count <= 8, 'Invalid generated TEV stage count')
        length = TEV_INFO_SIZE + TEV_STAGE_SIZE * (stage_count - 1)
        _require(at + length <= len(chunk), 'Truncated generated TEV block')
        infos.append(bytes(chunk[at:at + length]))
        at += length
    return infos, at


def _parse_materials(chunk, count, at):
    """Parse generated material records; one or more texgen/texture inputs each."""
    records = []
    for _ in range(count):
        _require(at + 84 <= len(chunk), 'Truncated generated material')
        flags = u32(chunk, at)
        texture = struct.unpack_from('>i', chunk, at + 4)[0]
        _require(flags & 1 and u32(chunk, at + 20) == 0, 'Expected static generated PVW material')
        n = u32(chunk, at + TEXGEN_COUNT_OFF)
        if texture >= 0:
            _require(1 <= n <= 8, 'Invalid generated texgen count')
            tdc = u32(chunk, at + TEXGEN_OFF + TEXGEN_SIZE * n)
            _require(1 <= tdc <= 8, 'Invalid generated texture input count')
            length = 84 + TEXGEN_SIZE * n + TEXTURE_DATA_SIZE * tdc
        else:
            _require(n == 0, 'Expected textureless generated material')
            length = 84
        _require(at + length <= len(chunk), 'Truncated generated material')
        records.append(bytes(chunk[at:at + length]))
        at += length
    _require(all(byte == 0 for byte in chunk[at:]), 'Unexpected generated material padding')
    return records


def _material_chunk(raw):
    offsets = _chunk_offsets(raw)
    material = [(at, end) for at, tag, end in offsets if tag == 48]
    _require(len(material) == 1, 'Expected exactly one material chunk')
    at, end = material[0]
    chunk = raw[at:end]
    count = u32(chunk, 8)
    tev_count = u32(chunk, 12)
    _require(1 <= count <= 32 and tev_count == count, 'Expected generated material layout')
    infos, at_after_tev = _parse_tev_infos(chunk, tev_count)
    records = _parse_materials(chunk, count, at_after_tev)
    return dict(raw=raw, at=at, end=end, chunk=chunk, count=count,
                tev_count=tev_count, tev=infos, materials=records)


def _byte(value, name):
    _require(type(value) is int and 0 <= value <= 255, f'Invalid {name}')
    return value


def _combiner(values, name):
    _require(isinstance(values, (tuple, list)) and len(values) == 12, f'Invalid {name}')
    return bytes(_byte(value, name) for value in values)


def _validate(spec):
    _require(isinstance(spec, dict), 'Environment stage spec must be a mapping')
    required = {'shape', 'texture', 'tex_coord_id', 'tex_map_id', 'channel_id',
                'k_color_sel', 'k_alpha_sel', 'color_combiner', 'alpha_combiner',
                'texgen', 'srt', 'marker', 'tev_flag', 'animation_factor'}
    _require(required <= set(spec), 'Environment stage spec is missing fields')
    _require(type(spec['shape']) is int and spec['shape'] >= 0, 'Invalid target shape')
    _require(type(spec['texture']) is int and spec['texture'] >= 0, 'Invalid environment texture')
    for key in ('tex_coord_id', 'tex_map_id', 'channel_id', 'k_color_sel', 'k_alpha_sel'):
        _byte(spec[key], key)
    _require(isinstance(spec['texgen'], (tuple, list)) and len(spec['texgen']) == 3,
             'Invalid environment texgen')
    for value in spec['texgen']:
        _byte(value, 'texgen')
    _require(isinstance(spec['srt'], (tuple, list)) and len(spec['srt']) == 6
             and all(math.isfinite(value) for value in spec['srt']), 'Invalid environment SRT')
    _byte(spec['marker'], 'marker')
    _byte(spec['tev_flag'], 'tev_flag')
    _byte(spec['animation_factor'], 'animation_factor')
    _combiner(spec['color_combiner'], 'color_combiner')
    _combiner(spec['alpha_combiner'], 'alpha_combiner')


def _stage_bytes(spec):
    return bytes([0, spec['tex_coord_id'], spec['tex_map_id'], spec['channel_id'],
                  spec['k_color_sel'], spec['k_alpha_sel'], 0, 0]) \
        + _combiner(spec['color_combiner'], 'color_combiner') \
        + _combiner(spec['alpha_combiner'], 'alpha_combiner')


def _texgen_bytes(spec):
    texgen_type, texgen_source, matrix_type = spec['texgen']
    return bytes([spec['tex_coord_id'], texgen_type, texgen_source, matrix_type])


def _texture_data(spec):
    scale_x, scale_y, pivot_x, pivot_y, translation_x, translation_y = spec['srt']
    data = bytearray(TEXTURE_DATA_SIZE)
    struct.pack_into('>I', data, TD_SOURCE_ATTR_OFF, spec['texture'])
    data[TD_MARKER_OFF] = spec['marker']
    data[TD_TEV_FLAG_OFF] = spec['tev_flag']
    struct.pack_into('>I', data, TD_ANIM_FACTOR_OFF, spec['animation_factor'])
    struct.pack_into('>I', data, TD_TOTAL_FRAME_OFF, 0)
    struct.pack_into('>f', data, TD_ANIM_SPEED_OFF, 0.0)
    for offset, value in ((TD_SCALE_X_OFF, scale_x), (TD_SCALE_Y_OFF, scale_y),
                          (TD_ROTATION_OFF, 0.0), (TD_TRANSLATION_X_OFF, translation_x),
                          (TD_TRANSLATION_Y_OFF, translation_y), (TD_PIVOT_X_OFF, pivot_x),
                          (TD_PIVOT_Y_OFF, pivot_y)):
        struct.pack_into('>f', data, offset, value)
    return bytes(data)


def _inject_tev(info, spec):
    _require(len(info) == TEV_INFO_SIZE and u32(info, TEV_STAGE_COUNT_OFF) == 1,
             'Expected single-stage generated TEV')
    return info[:TEV_STAGE_COUNT_OFF] + struct.pack('>I', 2) \
        + info[TEV_STAGE_OFF:TEV_INFO_SIZE] + _stage_bytes(spec)


def _inject_material(record, spec):
    texture = struct.unpack_from('>i', record, 4)[0]
    _require(texture >= 0, 'Target shape has no generated texture')
    n = u32(record, TEXGEN_COUNT_OFF)
    _require(n == 1, 'Expected one generated texgen')
    texture_data_off = TEXGEN_OFF + TEXGEN_SIZE * n
    _require(u32(record, texture_data_off) == 1, 'Expected one generated texture input')
    _require(len(record) == texture_data_off + TEXTURE_DATA_COUNT_EXTRA + TEXTURE_DATA_SIZE,
             'Unexpected generated material length')
    return record[:TEXGEN_COUNT_OFF] + struct.pack('>I', 2) \
        + record[TEXGEN_OFF:texture_data_off] + _texgen_bytes(spec) \
        + struct.pack('>I', 2) + record[texture_data_off + TEXTURE_DATA_COUNT_EXTRA:] \
        + _texture_data(spec)


def add_stage(raw, spec):
    """Append one normal-texgen environment stage to ``spec['shape']``.

    Returns ``(bytes, report)``; the input is never modified and every MOD chunk
    other than 48 is byte-identical. Refuses anything that is not a generated
    single-stage material (tamper, double application, unknown shape or texture).
    """
    _validate(spec)
    parsed = _material_chunk(raw)
    count = parsed['count']
    shape = spec['shape']
    _require(0 <= shape < count, 'Target shape out of range')
    texture_chunks = [(at, end) for at, tag, end in _chunk_offsets(raw) if tag == 32]
    _require(len(texture_chunks) == 1, 'Expected exactly one texture chunk')
    texture_count = u32(raw[texture_chunks[0][0]:texture_chunks[0][1]], 8)
    _require(spec['texture'] < texture_count, 'Environment texture index out of range')
    _require(struct.unpack_from('>i', parsed['materials'][shape], 4)[0] >= 0,
             'Target shape is textureless')

    tev = list(parsed['tev'])
    tev[shape] = _inject_tev(tev[shape], spec)
    materials = list(parsed['materials'])
    materials[shape] = _inject_material(materials[shape], spec)

    writer = Writer()
    writer.begin(48, count, len(tev))
    writer.pad()
    for info in tev:
        writer.data += info
    for record in materials:
        writer.data += record
    writer.end()
    result = raw[:parsed['at']] + bytes(writer.data) + raw[parsed['end']:]

    before = chunks(raw)
    after = chunks(result)
    if any(before[tag] != after[tag] for tag in before if tag != 48):
        raise AssertionError('Nonmaterial bytes changed')
    report = dict(policy=POLICY, shape=shape, texture=spec['texture'],
                  added_tev_stage=True, added_texgen=True, added_texture_data=True,
                  source_sha256=hashlib.sha256(raw).hexdigest(),
                  output_sha256=hashlib.sha256(result).hexdigest())
    return result, report


def apply(raw, spec=None):
    """Opt-in entry point. ``spec=None`` returns ``raw`` unchanged (no-op)."""
    if spec is None:
        return raw
    result, _ = add_stage(raw, spec)
    return result


def apply_queen_body(raw):
    """Emit the Queen body environment stage; convenience family wrapper."""
    return apply(raw, QUEEN_BODY)


def tev_infos(raw):
    """Per-shape generated TEV view (engine-mirroring, read-only)."""
    parsed = _material_chunk(raw)
    result = []
    for info in parsed['tev']:
        stages = []
        for i in range(u32(info, TEV_STAGE_COUNT_OFF)):
            stage = info[TEV_STAGE_OFF + TEV_STAGE_SIZE * i:TEV_STAGE_OFF + TEV_STAGE_SIZE * (i + 1)]
            stages.append(dict(tex_coord_id=stage[1], tex_map_id=stage[2], channel_id=stage[3],
                               k_color_sel=stage[4], k_alpha_sel=stage[5],
                               color_combiner=list(stage[8:20]), alpha_combiner=list(stage[20:32])))
        result.append(dict(stage_count=u32(info, TEV_STAGE_COUNT_OFF), stages=stages))
    return result


def material_records(raw):
    """Per-shape generated material view (engine-mirroring, read-only)."""
    parsed = _material_chunk(raw)
    result = []
    for record in parsed['materials']:
        texture = struct.unpack_from('>i', record, 4)[0]
        n = u32(record, TEXGEN_COUNT_OFF)
        texgens = [list(record[TEXGEN_OFF + TEXGEN_SIZE * i:TEXGEN_OFF + TEXGEN_SIZE * (i + 1)])
                   for i in range(n)]
        td_off = TEXGEN_OFF + TEXGEN_SIZE * n
        tdc = u32(record, td_off) if texture >= 0 else 0
        datas = []
        for i in range(tdc):
            td = record[td_off + TEXTURE_DATA_COUNT_EXTRA + TEXTURE_DATA_SIZE * i:
                        td_off + TEXTURE_DATA_COUNT_EXTRA + TEXTURE_DATA_SIZE * (i + 1)]
            datas.append(dict(source_attr=u32(td, TD_SOURCE_ATTR_OFF), marker=td[TD_MARKER_OFF],
                              tev_flag=td[TD_TEV_FLAG_OFF],
                              animation_factor=u32(td, TD_ANIM_FACTOR_OFF),
                              total_frame=u32(td, TD_TOTAL_FRAME_OFF),
                              scale_x=struct.unpack_from('>f', td, TD_SCALE_X_OFF)[0],
                              scale_y=struct.unpack_from('>f', td, TD_SCALE_Y_OFF)[0],
                              rotation=struct.unpack_from('>f', td, TD_ROTATION_OFF)[0]))
        result.append(dict(flags=u32(record, 0), texture=texture,
                           tev_info_index=u32(record, 12), texgen_count=n, texgens=texgens,
                           texture_data=datas))
    return result


def prepare(bank, output):
    """Apply the Queen body environment stage to a profiled Bulblax bank.

    Writes a new directory; the input bank is untouched. Requires the material
    profile (base rebound to TEX1[2]) so the environment stage can re-reference
    TEX1[1] as its own input.
    """
    bank = Path(bank)
    output = Path(output)
    if output.exists():
        raise ValueError('Refusing existing envmap output')
    report = json.loads((bank / 'bulblax-bank.json').read_text())
    profile = report.get('material_profile')
    if report.get('schema') != 1 or not isinstance(profile, dict) \
            or profile.get('policy') != MATERIAL_POLICY or not profile.get('applied'):
        raise ValueError('Expected a Bulblax material-profile bank')
    queen = sorted((bank / 'Queen').glob('bulblax_Queen_*.mod'))
    if not queen:
        raise ValueError('No Queen poses in bank')
    applied = {}
    files = []
    for path in queen:
        result, info = add_stage(path.read_bytes(), QUEEN_BODY)
        applied[path.name] = info['output_sha256']
        files.append((path.name, result))
    output.mkdir(parents=True)
    for path in sorted(bank.rglob('*')):
        if path.is_file():
            target = output / path.relative_to(bank)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    (output / 'Queen').mkdir(exist_ok=True)
    for name, data in files:
        (output / 'Queen' / name).write_bytes(data)
    updated = dict(report)
    updated['file_sha256'] = dict(report.get('file_sha256', {}))
    for name, digest in applied.items():
        updated['file_sha256'][name] = digest
    updated['envmap_profile'] = dict(
        policy=POLICY, applied=True, shape=QUEEN_BODY['shape'],
        texture=QUEEN_BODY['texture'], marker=QUEEN_BODY['marker'],
        source_material_profile=profile.get('policy'),
        source_bank_json_sha256=hashlib.sha256(
            (bank / 'bulblax-bank.json').read_bytes()).hexdigest(),
        queen_poses=len(applied),
        stage=dict(tex_coord_id=QUEEN_BODY['tex_coord_id'],
                   tex_map_id=QUEEN_BODY['tex_map_id'],
                   channel_id=QUEEN_BODY['channel_id'],
                   color_combiner=list(QUEEN_BODY['color_combiner']),
                   alpha_combiner=list(QUEEN_BODY['alpha_combiner']),
                   texgen=list(QUEEN_BODY['texgen']), srt=list(QUEEN_BODY['srt'])),
        btk='queenchappy_model.btk animates TEXMTX0; native mP2EnvSRT is static here',
        limitations=['Static TEXMTX0 SRT; no native BTK playback.',
                     'Requires the material profile; the base diffuse stage keeps its UV0 approximation.'])
    (output / 'bulblax-bank.json').write_bytes((json.dumps(updated, indent=2) + '\n').encode())
    return updated['envmap_profile']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('stage')
    s.add_argument('--pose', type=Path, required=True)
    s.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--bank', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'stage':
        if args.output.exists():
            raise ValueError('Refusing existing stage output')
        data, info = add_stage(args.pose.read_bytes(), QUEEN_BODY)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
        print(json.dumps(info, indent=2))
    else:
        print(json.dumps(prepare(args.bank, args.output), indent=2))
