"""Opt-in Bulblax MAT3 diagnosis and postconversion material profile; no bank mutation.

Source-cited per-species diagnosis for the #235 sampled display (#239):

- Queen (30): MAT3 material 0 (body, reached through the INF1 shape mapping
  for shape 1) is a three-stage TEV material. Stage 0 is the diffuse base:
  color arguments [15,8,10,15] (mix(ZERO,RASC,TEXC)) sampling texture slot 1
  (TEX1 index 2, CMPR 64x128) through texgen 1 (type 1, source 5 = TEX1 UVs,
  matrix 60 = identity). Stage 1 is a normal-mapped specular/environment
  stage: texgen 0 (type 1, source 1 = GX_TG_NRM, matrix 30 = TEXMTX0) samples
  texture slot 0 (TEX1 index 1, RGB565 64x64) with arguments
  [15,10,8,0] (mix(CPREV,TEXC,RASC) over the specular raster channel 5);
  TEXMTX0 is animated by ``queenchappy_model.btk`` (J3D1btk1/TTK1, 448 bytes,
  sha256 af0dde017624a5b30459b8ba55ed70a1d70de14f841ed58802b3b07565ef4eae,
  loaded at ``QueenMgr.cpp:12`` per docs/PIKMIN2 audit). Stage 2 blends konst
  colors C0/C1 by texture slot 3 (TEX1 index 4, 32x32).
  The converter's ``diffuse_slot`` (pikmin2_convert.py:57-74) only accepts a
  stage whose texgen is exactly [1,4,60] (TEX0); Queen's diffuse stage uses
  TEX1 UVs ([1,5,60]), so the match fails and the slot-0 fallback
  (pikmin2_convert.py:195-196) selects the envmap texture TEX1[1]. The
  single-stage writer (pikmin2_convert.py:263-280) then bakes that envmap as
  the shape's only texture -- the incorrect black/silver reflective body.
  The profile retargets the baked shape material to the actual diffuse base
  TEX1[2]. The base stage samples the TEX1 UV set in the source; the
  converter bakes UV0 only (attribute 14 is in ``discarded_attributes``), so
  reusing UV0 for this texture is an approximation and is recorded as such.
- Baby (31): one material, zero textures in TEX1 (all eight slots 65535).
  Stage 0 passes the lit raster color through ([10,15,15,15], no texture);
  channel 0 uses vertex colors (material_source 1, light mask 1). The baked
  pose carries the source vertex colors (255,247,198 warm-white ramp) but a
  lighting control of 0x1800 (vertex-color flag only, diffuse/specular bits
  clear), so the host renders the raw bright vertex color unlit -- the flat
  bright look. The profile restores lit diffuse/specular control bits
  (frog-profile 0x93 precedent) while preserving the 0x1800 vertex-color
  flag. Source material color is plain white, matching the bake.
- KingChappy (53): two single-stage diffuse materials already baked with the
  correct textures (TEX1[1] 128x128 CMPR body via mat 0, TEX1[0] 32x32 via
  mat 1); the converter picked the right slots. Source material 1 carries
  material color (204,204,204,255) which the bake replaced with white
  (pikmin2_convert.py:238 default material_colors); the profile restores the
  source gray. The sampled-display terrain intersection is a placement
  question (engineered display Y on P1 terrain), not a material or actor
  collision finding.

Everything not fixable lane-side is recorded as an explicit unsupported
request with the exact GX feature and source citation; nothing is guessed.

The profile is a hash-preserving, opt-in postconversion step: the verified
bank is never modified; profiled poses are new files with their own hashes
and provenance pointing at the original bank. Only the material chunk (48)
changes; every other chunk is byte-identical.

Issue #239 (parent #172); display #235; bank #234; converter policies #233.
"""
import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path

from experimental.pikmin2_convert import blocks, diffuse_slot, u16, u32
from experimental.pikmin2_bulblax_assets import SPECIES
from experimental.pikmin2_bulblax_bank import HEADER as BANK_HEADER
from experimental.pikmin2_bulblax_bank import parse_bank, validate_files
from experimental.pikmin2_frog_visual_audit import chunks, source_material

POLICY = 'P2_BULBLAX_MATERIAL_1'
# Full hashes bind this profile to the audited #217/#234 source models.
SOURCES = {'Queen': 'e4904b223fa388e53092dc67c80a3668782a314b6e7683bd2284f7413cfb4414',
           'Baby': '4813630c8681b4e15c5f66d449515fe71d964ef00e7ea03bfd64bd05b0a4c5e0',
           'KingChappy': '44934adcd74e4b352d7de29a63a642d278290f4d991ea0f2b42861fdde4ba6e4'}

# Lit control follows the Frog profile precedent (0x93 lit / 0 unlit); the
# 0x1800 vertex-color flag emitted by the converter writer
# (pikmin2_convert.py:274) is preserved when a pose carries vertex colors.
LIT = 0x93
VERTEX_COLOR_FLAG = 0x1800
CONTROLS = (0, LIT, VERTEX_COLOR_FLAG, LIT | VERTEX_COLOR_FLAG)

CONVERTER_REFS = {'diffuse_slot': 'experimental/pikmin2_convert.py:57-74',
                  'slot_fallback': 'experimental/pikmin2_convert.py:195-196',
                  'single_stage_writer': 'experimental/pikmin2_convert.py:263-280',
                  'default_material_colors': 'experimental/pikmin2_convert.py:238',
                  'discarded_uv_attributes': 'experimental/pikmin2_convert.py:108,301'}

# Exact unsupported native requests, with source citations. Anything not in
# this list is either fixed by the profile or was already correct.
UNSUPPORTED = {
    'Queen': [
        'Normal-source environment/specular TEV stage: MAT3 mat0 texgen 0 (type 1, source 1 = GX_TG_NRM, matrix 30 = TEXMTX0) + stage 1 order [0,0,5], args [15,10,8,0] (mix(CPREV,TEXC,RASC) over specular raster channel 5, light mask 128). Needs native multi-stage TEV + normal texgen; the profile only stops the envmap texture (TEX1[1]) from being misused as the diffuse base.',
        'BTK texture-matrix animation: queenchappy_model.btk (J3D1btk1, TTK1, 448 bytes, sha256 af0dde017624a5b30459b8ba55ed70a1d70de14f841ed58802b3b07565ef4eae; loaded at src/plugProjectNishimuraU/QueenMgr.cpp:12) animates TEXMTX0 for the specular stage. Needs native BTK playback; no skeletal/BTK playback exists lane-side.',
        'Konst-color blend layer: MAT3 mat0 stage 2 order [3,3,4], args [15,8,2,0] (mix(CPREV,C0,TEXC) with TEX1[4]). Needs native konst color registers + a third TEV stage.',
        'Base diffuse stage samples the TEX1 UV set (MAT3 mat0 texgen 1 = [1,5,60]); the converter bakes UV0 only (attribute 14 discarded, see converter refs). The profile reuses UV0 for TEX1[2]; UV1-accurate mapping needs converter/native support for a second UV set.',
    ],
    'Baby': [
        'Source GX lighting parity: MAT3 mat0 channel 0 (enabled, material_source 1 = vertex color, light_mask 1, diffuse_function 2, attenuation_function 1) vs the host P1 ambient/PVW light environment; also specular channel 2 (light_mask 128). The profile restores lit control bits but cannot reproduce the source light rig.',
        'Alpha/konst blend: MAT3 mat0 stage 1 order [255,255,5], args [15,10,14,0] (mix(CPREV,KONST,RASC)). Needs native konst alpha register + a second TEV stage.',
    ],
    'KingChappy': [
        'Host lighting remains the P1 PVW environment (source MAT3 light masks/diffuse functions are not reproduced); no material-layer feature beyond the frog-profile lighting approximation is required.',
    ],
}

LIMITS = ['PVW lighting control follows the Frog profile precedent (0x93 lit / 0 unlit); host PVW control-bit semantics are approximate, not source-verified.',
          'Queen diffuse base texture is retargeted but sampled with UV0 instead of the source TEX1 UV set (approximation; UV arrays differ).',
          'Queen (both materials) and KingChappy material 0 source diffuse stages use TEV scale 1 (x2; MAT3 stage 0 scale byte); the baked single stage uses scale 0, so the profiled base is half source intensity under equal lighting.',
          'Ambient/light environment remains P1; no source lighting parity claimed.',
          'KingChappy display terrain intersection is a placement question (engineered display Y on original P1 terrain), not a material finding and not actor collision.']


def _materials_source(model, species):
    """Parse audited source MAT3 materials; hash-bound to the #234 import."""
    if species not in SOURCES or hashlib.sha256(model).hexdigest() != SOURCES[species]:
        raise ValueError('Unrecognized Bulblax source model')
    return source_material(model)


def _shape_mapping(model):
    """INF1 shape->material mapping in shape order (frog-profile traversal)."""
    hierarchy = blocks(model)['INF1']
    at = u32(hierarchy, 20)
    current = None
    mapping = {}
    while True:
        kind, index = struct.unpack_from('>HH', hierarchy, at)
        at += 4
        if kind == 0:
            break
        if kind == 0x11:
            current = index
        if kind == 0x12:
            if index in mapping or current is None:
                raise ValueError('Invalid source shape/material mapping')
            mapping[index] = current
    if sorted(mapping) != list(range(len(mapping))):
        raise ValueError('Noncontiguous source shapes')
    return [mapping[i] for i in range(len(mapping))]


def _diffuse_texture(m, r, metadata):
    """Select the source diffuse texture for one MAT3 material.

    Generalizes the converter's diffuse_slot (pikmin2_convert.py:57-74):
    accepts the two known texture-times-raster color patterns on a stage
    whose texgen is a plain 2D UV mapping (type 1, source 4 = TEX0 or
    source 5 = TEX1, matrix 60 = identity), preferring TEX0. Returns
    (TEX1 texture index, uv_source) or (-1, None) for genuinely textureless
    materials (all eight slots empty, e.g. Baby).
    """
    slots = [u16(m, r + 132 + 2 * k) for k in range(8)]
    if all(s == 65535 for s in slots):
        if metadata['tev_stage_count'] < 1:
            raise ValueError('Material with no TEV stages')
        return -1, None, None
    best = None
    for i in range(metadata['tev_stage_count']):
        stage = u32(m, 92) + u16(m, r + 0xe4 + 2 * i) * 20
        color = list(m[stage + 1:stage + 10])
        # Accept the texture-times-raster patterns at TEV scale 0 or 1; the
        # converter (pikmin2_convert.py:68) only accepts scale 0, which is why
        # Queen's scale-1 diffuse stage is missed. The scale factor is not
        # reproduced by the bake and is recorded as a host limit.
        if color[:5] not in ([15, 10, 8, 15, 0], [15, 8, 10, 15, 0]) or color[6] not in (0, 1) or color[7] != 1 or color[8] != 0:
            continue
        order = u32(m, 76) + u16(m, r + 0xbc + 2 * i) * 4
        coord, slot = m[order:order + 2]
        if coord >= 8 or slot >= 8 or slots[slot] == 65535:
            continue
        gen = u32(m, 56) + u16(m, r + 0x28 + 2 * coord) * 4
        if list(m[gen:gen + 3]) in ([1, 4, 60], [1, 5, 60]):
            uv = 'TEX0' if m[gen + 1] == 4 else 'TEX1'
            if best is None or uv == 'TEX0':
                best = (slot, uv, color[6])
    if best is None:
        raise ValueError('No identifiable diffuse stage; refusing to guess a texture')
    slot, uv, scale = best
    texture = u16(m, u32(m, 72) + slots[slot] * 2)
    return texture, uv, scale


def profile(model, species, has_vertex_colors):
    """Per-shape profile entries for one species' baked poses.

    Each entry: material (source MAT3 index), texture (emitted TEX1 index to
    bind, -1 for none), replace_texture (the index the converter emitted;
    rewrite refuses anything else), rgba, control, uv_source and notes.
    """
    metadata = _materials_source(model, species)
    m = blocks(model)['MAT3']
    materials = []
    for i, info in enumerate(metadata):
        r = u32(m, 12) + u16(m, u32(m, 16) + 2 * i) * 332
        texture, uv, scale = _diffuse_texture(m, r, info)
        # Reproduce the converter's slot choice/fallback (pikmin2_convert.py:195-196):
        # what the bake actually carries for this material.
        slot = diffuse_slot(m, r)
        raw = u16(m, r + 132 + 2 * slot)
        converter_texture = -1 if raw == 65535 else u16(m, u32(m, 72) + raw * 2)
        rgba = info['material_rgba'][0]
        if rgba is None or len(rgba) != 4:
            raise ValueError('Source material color missing')
        lit = bool(info['channels'][0] and info['channels'][0]['enabled'])
        control = (LIT if lit else 0) | (VERTEX_COLOR_FLAG if has_vertex_colors else 0)
        materials.append(dict(material=i, texture=texture, replace_texture=converter_texture,
                              rgba=list(rgba), control=control, uv_source=uv,
                              tev_scale=scale,
                              texgen_retargeted=texture != converter_texture))
    mapping = _shape_mapping(model)
    if any(idx >= len(materials) for idx in mapping):
        raise ValueError('Shape references unknown source material')
    return [materials[idx] for idx in mapping]


def _chunk48(raw):
    found = chunks(raw)
    return found, bytearray(found[48])


def _record_walk(block):
    """Yield (record_offset, tex, length) for each emitted material record."""
    count = u32(block, 8)
    if not 1 <= count <= 32 or u32(block, 12) != count:
        raise ValueError('Expected generated material layout')
    for i in range(count):
        if u32(block, 120 + 124 * i) != 1:
            raise ValueError('Expected single-stage generated TEV')
    r = 32 + 124 * count
    for _ in range(count):
        if u32(block, r) & 1 == 0 or u32(block, r + 20) != 0:
            raise ValueError('Expected static generated PVW material')
        tex = struct.unpack_from('>i', block, r + 4)[0]
        if tex >= 0:
            if u32(block, r + 76) != 1 or u32(block, r + 84) != 1 or len(block) < r + 152:
                raise ValueError('Expected one texture per generated material')
            yield r, tex, 152
            r += 152
        else:
            if tex != -1 or u32(block, r + 76) != 0 or len(block) < r + 84:
                raise ValueError('Expected textureless generated material')
            yield r, tex, 84
            r += 84
    if r > len(block):
        raise ValueError('Truncated generated material')


def _chunk_offsets(raw):
    """(offset, tag, end) for every MOD chunk, in file order."""
    result = []
    at = 0
    while at + 8 <= len(raw):
        tag, size = struct.unpack_from('>II', raw, at)
        end = at + 8 + size
        if end > len(raw):
            raise ValueError('Invalid MOD chunk')
        result.append((at, tag, end))
        at = end
        if tag == 65535:
            break
    return result


def rewrite(raw, materials):
    """Apply profile entries to one baked pose; only chunk 48 fields change.

    Refuses: material-count mismatch, unexpected record layout, a texture
    reference outside the pose's texture table, controls outside the bounded
    set, and any pose whose current texture differs from the recorded
    converter output (tamper or double application).
    """
    found, block = _chunk48(raw)
    records = list(_record_walk(block))
    if len(materials) != len(records):
        raise ValueError('Profile/pose shape count mismatch')
    texture_count = u32(found[32], 8)
    for (r, tex, length), entry in zip(records, materials):
        control = entry['control']
        rgba = entry['rgba']
        target = entry['texture']
        if control not in CONTROLS or len(rgba) != 4 or any(type(v) is not int or not 0 <= v <= 255 for v in rgba):
            raise ValueError('Unsupported Bulblax material profile entry')
        if tex != entry['replace_texture']:
            raise ValueError('Pose material differs from recorded converter output')
        if target != tex:
            if tex < 0 or target < 0 or target >= texture_count:
                raise ValueError('Profile texture retarget out of range')
            struct.pack_into('>i', block, r + 4, target)
            struct.pack_into('>i', block, r + 88, target)
        # Only static material and lighting fields change; preserve pixel/texture state.
        block[r + 8:r + 12] = bytes(rgba)
        block[r + 16:r + 20] = bytes(rgba)
        struct.pack_into('>I', block, r + 36, control)
    offsets = [(at, end) for at, tag, end in _chunk_offsets(raw) if tag == 48]
    if len(offsets) != 1:
        raise ValueError('Expected exactly one material chunk')
    at, end = offsets[0]
    result = raw[:at] + bytes(block) + raw[end:]
    after = chunks(result)
    if any(found[t] != after[t] for t in found if t != 48):
        raise AssertionError('Nonmaterial bytes changed')
    if len(found[48]) != len(after[48]):
        raise AssertionError('Material chunk size changed')
    return result


def describe(materials):
    return [dict(shape=i, **m) for i, m in enumerate(materials)]


def _verified_import(imported):
    report = json.loads((imported / 'bulblax.json').read_bytes())
    if report.get('schema') != 1 or report.get('policy') != 'P2_BULBLAX_IMPORT_1':
        raise ValueError('Expected Bulblax reference import')
    if set(report.get('species', {})) != set(SPECIES):
        raise ValueError('Incomplete Bulblax reference import')
    return report


def _pose_has_vertex_colors(raw):
    return 19 in chunks(raw)


def mapping_table(parsed_bank):
    """Explicit clip -> pose index -> source frame table per species."""
    return {species: {name: [{'pose': i, 'source_frame': frame}
                             for i, frame in enumerate(info['frames'])]
                      for name, info in clips.items()}
            for species, clips in parsed_bank.items()}


def emitted_material_records(raw):
    """Per-shape emitted material record summary for one baked pose."""
    _, block = _chunk48(raw)
    return [dict(shape=i, texture=tex,
                 rgba=list(block[r + 8:r + 12]),
                 control=u32(block, r + 36))
            for i, (r, tex, length) in enumerate(_record_walk(block))]


def audit_bank(bank):
    """Sampled-pose audit over a #234 bank build; read-only.

    Resource consistency across every pose (per species), the explicit
    clip->source-frame mapping table, and per-pose emitted material records
    with any deviation from the species reference flagged.
    """
    bank = Path(bank)
    report = json.loads((bank / 'bulblax-bank.json').read_text())
    if report.get('schema') != 1 or report.get('bank') != BANK_HEADER:
        raise ValueError('Expected a P2 Bulblax bank build')
    parsed = parse_bank((bank / 'p2-bulblax-bank.txt').read_text())
    strict = None
    try:
        _, strict_total = validate_files(bank, parsed)
    except ValueError as error:
        strict = str(error)
    from experimental.pikmin2_animation import resource_chunks
    species = {}
    total = 0
    for name in SPECIES:
        reference = None
        material_reference = None
        poses = []
        deviating = []
        for clip, info in parsed.get(name, {}).items():
            for index in range(info['poses']):
                path = bank / name / f'bulblax_{name}_{clip}_{index:02}.mod'
                raw = path.read_bytes()
                total += len(raw)
                resources = resource_chunks(raw)
                if reference is None:
                    reference = resources
                records = emitted_material_records(raw)
                if material_reference is None:
                    material_reference = records
                deviation = None
                if resources != reference:
                    deviation = 'resource_chunks differ from species reference'
                elif records != material_reference:
                    deviation = 'material record differs from species reference'
                poses.append(dict(file=path.name, clip=clip, pose=index,
                                  source_frame=info['frames'][index],
                                  bytes=len(raw), materials=records))
                if deviation:
                    deviating.append(dict(file=path.name, clip=clip, pose=index, reason=deviation))
        species[name] = dict(poses=poses, pose_count=len(poses),
                             reference_resources_sha256=hashlib.sha256(reference).hexdigest() if reference else None,
                             deviating_poses=deviating)
    return dict(schema=1, bank=BANK_HEADER,
                strict_validation=strict or 'passed',
                poses=sum(s['pose_count'] for s in species.values()),
                mod_bytes=total,
                mapping_table=mapping_table(parsed),
                species={s: {k: v for k, v in info.items() if k != 'poses'}
                         for s, info in species.items()},
                pose_materials={s: info['poses'] for s, info in species.items()})


def prepare(imported, bank, output):
    """Build the profiled bank as NEW files; the verified bank is untouched."""
    imported = Path(imported)
    bank = Path(bank)
    output = Path(output)
    if output.exists():
        raise ValueError('Refusing existing profile output')
    reference = _verified_import(imported)
    bank_report_bytes = (bank / 'bulblax-bank.json').read_bytes()
    bank_report = json.loads(bank_report_bytes)
    if bank_report.get('schema') != 1 or bank_report.get('bank') != BANK_HEADER:
        raise ValueError('Expected a P2 Bulblax bank build')
    if bank_report.get('reference_sha256') != hashlib.sha256((imported / 'bulblax.json').read_bytes()).hexdigest():
        raise ValueError('Bank/import reference mismatch')
    parsed = parse_bank((bank / 'p2-bulblax-bank.txt').read_text())
    paths, _ = validate_files(bank, parsed)
    for path in paths:
        if bank_report.get('file_sha256', {}).get(path.name) != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('Bank report/file hash mismatch: ' + path.name)
    profiles = {}
    files = []
    for species in SPECIES:
        model = (imported / species / 'enemy.bmd').read_bytes()
        if hashlib.sha256(model).hexdigest() != reference['species'][species]['model_sha256']:
            raise ValueError(f'{species} reference model hash mismatch')
        sample = None
        for clip, info in parsed.get(species, {}).items():
            if info['poses']:
                sample = (bank / species / f'bulblax_{species}_{clip}_00.mod').read_bytes()
                break
        if sample is None:
            raise ValueError(f'{species} has no converted poses')
        materials = profile(model, species, _pose_has_vertex_colors(sample))
        profiles[species] = materials
        for clip, info in parsed[species].items():
            for index in range(info['poses']):
                name = f'bulblax_{species}_{clip}_{index:02}.mod'
                before = (bank / species / name).read_bytes()
                after = rewrite(before, materials)
                files.append((species, name, after))
                sidecar = (bank / species / name).with_suffix('.json')
                if sidecar.is_file():
                    files.append((species, sidecar.name, sidecar.read_bytes()))
    report = copy.deepcopy(bank_report)
    report['file_sha256'] = {name: hashlib.sha256(data).hexdigest()
                             for _, name, data in files if name.endswith('.mod')}
    report['material_profile'] = dict(
        policy=POLICY,
        source_bank_sha256=hashlib.sha256(bank_report_bytes).hexdigest(),
        source_import_sha256=hashlib.sha256((imported / 'bulblax.json').read_bytes()).hexdigest(),
        applied=True,
        fixes={
            'Queen': 'Body shape rebound from the envmap texture TEX1[1] (converter slot-0 fallback, pikmin2_convert.py:195-196) to the diffuse base TEX1[2]; unlit control 0 -> 0x93 on lit channels.',
            'Baby': 'Lighting control 0x1800 -> 0x1893: diffuse/specular bits restored (frog-profile precedent) with the vertex-color flag preserved; source vertex colors and white material color unchanged.',
            'KingChappy': 'Material color restored to source (204,204,204,255) on material 1 (converter default white, pikmin2_convert.py:238); lit control 0 -> 0x93 on material 0.',
        },
        unsupported={s: list(u) for s, u in UNSUPPORTED.items()},
        converter_refs=dict(CONVERTER_REFS),
        geometry_unchanged=True,
        host_limits=list(LIMITS),
        shapes={s: describe(m) for s, m in profiles.items()},
        mapping_table=mapping_table(parsed))
    output.mkdir(parents=True)
    for species, name, data in files:
        target = output / species / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(data)
    (output / 'bulblax-bank.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
    (output / 'p2-bulblax-bank.txt').write_bytes((bank / 'p2-bulblax-bank.txt').read_bytes())
    (output / 'p2-bulblax.txt').write_bytes((imported / 'p2-bulblax.txt').read_bytes())
    # The profiled bank must still satisfy the bank validators on its own.
    validate_files(output, parse_bank((output / 'p2-bulblax-bank.txt').read_text()))
    return report['material_profile']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    for key in ('imported', 'bank', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    a = sub.add_parser('audit')
    a.add_argument('--bank', type=Path, required=True)
    a.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        print(json.dumps(prepare(args.imported, args.bank, args.output), indent=2))
    else:
        if args.output.exists():
            raise ValueError('Refusing existing audit output')
        result = audit_bank(args.bank)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes((json.dumps(result, indent=2) + '\n').encode())
        print(json.dumps({'poses': result['poses'],
                          'deviating': {s: len(v['deviating_poses']) for s, v in result['species'].items()}}, indent=2))
