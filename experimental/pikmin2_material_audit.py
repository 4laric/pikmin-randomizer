"""Read-only P1/P2 material lighting audit (issue #895).

Parses the MOD material chunk (48) the way ``Material::read`` /
``ShapeBase`` read it, so retail Pikmin 1 teki MODs and converted P2 pose MODs
can be compared field for field: PVW lighting control word, material colour
and TEV stage colour arguments/scale. It also reports the texel-mean
luminance of each MOD texture, and audits a prepared P2 content root against
the source MAT3 channel control of every ``enemy.bmd`` it contains.

    py -3.12 -m experimental.pikmin2_material_audit mods <file.mod>...
    py -3.12 -m experimental.pikmin2_material_audit content <content-root> [--json out.json]

Nothing is written except the optional JSON report.
"""
import argparse
import json
import struct
import sys
from pathlib import Path

from experimental.pikmin2_convert import (MAT_SRC_ALPHA0_VERTEX, MAT_SRC_COLOR0_VERTEX,
                                          P1_LIT_CONTROL, blocks, source_lighting, u16, u32)

VERTEX_BITS = MAT_SRC_COLOR0_VERTEX | MAT_SRC_ALPHA0_VERTEX


class _Reader:
    def __init__(self, data, at):
        self.data = data
        self.at = at

    def i(self):
        value = struct.unpack_from('>I', self.data, self.at)[0]
        self.at += 4
        return value

    def f(self):
        value = struct.unpack_from('>f', self.data, self.at)[0]
        self.at += 4
        return value

    def raw(self, n):
        if self.at + n > len(self.data):
            raise ValueError('Truncated MOD material chunk')
        value = self.data[self.at:self.at + n]
        self.at += n
        return value

    def skip_keys(self, key_size, triple):
        # PVWKeyInfo tables: a count, then count keys of 4 + key_size*(3|1).
        count = self.i()
        self.at += count * (4 + key_size * (3 if triple else 1))


def mod_chunks(raw):
    """Top-level MOD chunks as {tag: (start, body_start, end)}; retail footers are ignored."""
    result = {}
    at = 0
    while at + 8 <= len(raw):
        tag, size = struct.unpack_from('>II', raw, at)
        end = at + 8 + size
        if end > len(raw):
            raise ValueError('Invalid MOD chunk length')
        result.setdefault(tag, (at, at + 8, end))
        at = end
        if tag == 0xFFFF:
            break
    if 0xFFFF not in result:
        raise ValueError('Incomplete MOD')
    return result


def mod_materials(raw):
    """Material list of a MOD: lighting control, colour and TEV stage summary."""
    _, body, _ = mod_chunks(raw)[48]
    r = _Reader(raw, body)
    material_count = r.i()
    tev_count = r.i()
    r.at = (r.at + 31) & ~31
    tevs = []
    for _ in range(tev_count):
        for _ in range(3):
            r.raw(8)
            r.i()
            r.f()
            r.skip_keys(12, True)
            r.skip_keys(12, False)
        r.raw(16)
        stages = []
        for _ in range(r.i()):
            stage = r.raw(32)
            stages.append(dict(color=list(stage[8:12]), scale=stage[14]))
        tevs.append(stages)
    result = []
    for _ in range(material_count):
        flags = r.i()
        texture = r.i()
        rgba = list(r.raw(4))
        material = dict(flags=flags, texture=texture, rgba=rgba)
        if flags & 1:
            material['tev'] = r.i()
            r.raw(4)
            r.i()
            r.f()
            r.skip_keys(12, True)
            r.skip_keys(12, False)
            material['control'] = r.i()
            r.f()
            r.raw(16)
            r.i()
            r.raw(12)
            r.raw(4 * r.i())
            for _ in range(r.i()):
                r.raw(52)
                r.skip_keys(12, True)
                r.skip_keys(12, True)
                r.skip_keys(12, True)
            material['stages'] = tevs[material['tev']] if material['tev'] < len(tevs) else []
        result.append(material)
    return result


def _luma(r, g, b):
    return 0.299 * r + 0.587 * g + 0.114 * b


def _rgb565(v):
    return ((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31


def _texels(fmt, data):
    """Yield (luma, alpha) per texel. Tiling is irrelevant to a mean."""
    if fmt == 0:
        for i in range(0, len(data) - 1, 2):
            yield _luma(*_rgb565(struct.unpack_from('>H', data, i)[0])), 255
    elif fmt == 1:
        for i in range(0, len(data) - 7, 8):
            c0, c1 = struct.unpack_from('>HH', data, i)
            a, b = _rgb565(c0), _rgb565(c1)
            if c0 > c1:
                palette = [(a, 255), (b, 255),
                           (tuple((2 * x + y) // 3 for x, y in zip(a, b)), 255),
                           (tuple((x + 2 * y) // 3 for x, y in zip(a, b)), 255)]
            else:
                palette = [(a, 255), (b, 255), (tuple((x + y) // 2 for x, y in zip(a, b)), 255), ((0, 0, 0), 0)]
            bits = struct.unpack_from('>I', data, i + 4)[0]
            for k in range(16):
                colour, alpha = palette[(bits >> (30 - 2 * k)) & 3]
                yield _luma(*colour), alpha
    elif fmt == 2:
        for i in range(0, len(data) - 1, 2):
            v = struct.unpack_from('>H', data, i)[0]
            if v & 0x8000:
                yield _luma(((v >> 10) & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, (v & 31) * 255 // 31), 255
            else:
                yield _luma(((v >> 8) & 15) * 17, ((v >> 4) & 15) * 17, (v & 15) * 17), ((v >> 12) & 7) * 255 // 7
    elif fmt == 3:
        for byte in data:
            yield (byte >> 4) * 17, 255
            yield (byte & 15) * 17, 255
    elif fmt == 4:
        for byte in data:
            yield byte, 255
    elif fmt == 5:
        for byte in data:
            yield (byte & 15) * 17, (byte >> 4) * 17
    elif fmt == 6:
        for i in range(0, len(data) - 1, 2):
            yield data[i + 1], data[i]
    elif fmt == 7:
        for tile in range(0, len(data) - 63, 64):
            for k in range(16):
                a, r = data[tile + 2 * k], data[tile + 2 * k + 1]
                g, b = data[tile + 32 + 2 * k], data[tile + 33 + 2 * k]
                yield _luma(r, g, b), a
    else:
        raise ValueError('Unsupported MOD texture format %d' % fmt)


def mod_textures(raw):
    """Per texture: size, MOD format and alpha-weighted mean luma (0-255)."""
    chunk = mod_chunks(raw).get(32)
    if chunk is None:
        return []
    _, body, end = chunk
    count = u32(raw, body)
    at = (body + 4 + 31) & ~31
    result = []
    for _ in range(count):
        width, height, fmt = struct.unpack_from('>HHI', raw, at)
        size = u32(raw, at + 28)
        data = raw[at + 32:at + 32 + size]
        if at + 32 + size > end:
            raise ValueError('Truncated MOD texture')
        total = weight = 0.0
        for luma, alpha in _texels(fmt, data):
            total += luma * alpha
            weight += alpha
        result.append(dict(width=width, height=height, format=fmt,
                           mean_luma=round(total / weight, 1) if weight else None))
        at += 32 + size
    return result


def source_table(model):
    """Per source material: COLOR0 lighting, vertex sources, colour and stage scales."""
    m = blocks(model)['MAT3']
    table = []
    for i in range(u16(m, 8)):
        r = u32(m, 12) + u16(m, u32(m, 16) + 2 * i) * 332
        info = source_lighting(m, r)
        scales = [m[u32(m, 92) + u16(m, r + 0xe4 + 2 * s) * 20 + 7]
                  for s in range(m[u32(m, 88) + m[r + 4]])]
        table.append(dict(info, rgba=list(info['rgba']), tev_scales=scales))
    return table


def shape_materials(model):
    """INF1 shape -> source material index, in shape order."""
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
            mapping[index] = current
    return [mapping[i] for i in range(len(mapping))]


def expected_control(source):
    """Lit/unlit base word and the vertex bits the source allows."""
    allowed = (MAT_SRC_COLOR0_VERTEX if source['color_vertex'] else 0) | \
              (MAT_SRC_ALPHA0_VERTEX if source['alpha_vertex'] else 0)
    return (P1_LIT_CONTROL if source['lit'] else 0), allowed


def check_pose(raw, source, mapping):
    """List of mismatch strings for one converted pose against its source."""
    problems = []
    materials = mod_materials(raw)
    if len(materials) != len(mapping):
        return ['material count %d != source shapes %d' % (len(materials), len(mapping))]
    for shape, (material, index) in enumerate(zip(materials, mapping)):
        base, allowed = expected_control(source[index])
        control = material.get('control')
        if control is None or control & ~VERTEX_BITS != base or control & VERTEX_BITS & ~allowed:
            problems.append('shape %d control %s expected %#x (+%#x vertex bits)' %
                            (shape, None if control is None else hex(control), base, allowed))
        if material['rgba'] != source[index]['rgba']:
            problems.append('shape %d rgba %s expected %s' % (shape, material['rgba'], source[index]['rgba']))
    return problems


def audit_content(root):
    """Audit every pose MOD beside each enemy.bmd under a prepared content root."""
    root = Path(root)
    report = dict(schema=1, root=str(root), models={}, poses=0, mismatched_poses=0, controls={})
    for model_path in sorted(root.rglob('enemy.bmd')):
        model = model_path.read_bytes()
        source = source_table(model)
        mapping = shape_materials(model)
        entry = dict(source=source, shapes=mapping, poses=0, problems={})
        for pose in sorted(model_path.parent.glob('*.mod')):
            raw = pose.read_bytes()
            entry['poses'] += 1
            report['poses'] += 1
            for material in mod_materials(raw):
                key = hex(material.get('control', -1))
                report['controls'][key] = report['controls'].get(key, 0) + 1
            problems = check_pose(raw, source, mapping)
            if problems:
                entry['problems'][pose.name] = problems
                report['mismatched_poses'] += 1
        report['models'][str(model_path.parent.relative_to(root)).replace('\\', '/')] = entry
    # Pose banks staged without a sibling source model (e.g. BlueKochappy/bank,
    # Sarai) are counted but cannot be checked against MAT3.
    unsourced = {}
    for folder in sorted({p.parent for p in root.rglob('*.mod')}):
        if (folder / 'enemy.bmd').is_file():
            continue
        counts = {}
        for pose in sorted(folder.glob('*.mod')):
            for material in mod_materials(pose.read_bytes()):
                key = hex(material.get('control', -1))
                counts[key] = counts.get(key, 0) + 1
        unsourced[str(folder.relative_to(root)).replace('\\', '/')] = counts
    report['unsourced'] = unsourced
    return report


def describe_mod(path):
    raw = Path(path).read_bytes()
    return dict(path=str(path),
                materials=[dict(control=hex(m['control']) if 'control' in m else None, rgba=m['rgba'],
                                stages=[dict(color=s['color'], scale=s['scale']) for s in m.get('stages', [])])
                           for m in mod_materials(raw)],
                textures=mod_textures(raw))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    mods = sub.add_parser('mods')
    mods.add_argument('paths', nargs='+', type=Path)
    content = sub.add_parser('content')
    content.add_argument('root', type=Path)
    for p in (mods, content):
        p.add_argument('--json', type=Path)
    args = parser.parse_args(argv)
    if args.command == 'mods':
        result = [describe_mod(p) for p in args.paths]
    else:
        result = audit_content(args.root)
    text = json.dumps(result, indent=1)
    if args.json:
        args.json.write_text(text + '\n', encoding='utf-8')
    if args.command == 'content':
        summary = dict(poses=result['poses'], mismatched_poses=result['mismatched_poses'], controls=result['controls'])
        print(json.dumps(summary, indent=1))
    else:
        print(text)
    return 0 if args.command == 'mods' or not result['mismatched_poses'] else 1


if __name__ == '__main__':
    sys.exit(main())
