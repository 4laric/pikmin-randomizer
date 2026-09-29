"""Before/after pose-playback evidence for #895, rendered from staged pose banks.

Native draws a P2 actor by bracketing the baked poses around the current
source frame and writing the (lerped) vertex positions into a private Shape.
This tool replays exactly that, offline, from two staged run directories
(``scripts/p2_pose_density_audit.py`` output: the audit JSON plus the pose MODs
under ``assets/dataDir/courses/pikmin2room/``), one source frame per 30 fps
display frame, and renders each displayed geometry (triangles parsed from the
MOD display lists, flat shaded, orthographic 3/4 view).

Per clip it writes

* ``<case>.gif``: side-by-side playback, two loops, of
  - BEFORE nearest: the baseline bake drawn with the nearest pose (what the
    dedicated family paths did),
  - BEFORE lerp: the baseline bake with vertex lerp (what batch2/batch3 did),
  - AFTER: the dense bake with lerp (this branch);
* ``<case>-motion.png``: per displayed frame, the largest vertex displacement
  from the previous frame (a pop is a spike; steady motion is a smooth curve)
  and the projected path of the most-moving vertex (sparse lerp cuts corners
  along straight chords; the dense bake follows the source arc);
* a JSON summary with the pop metric (max / median per-frame displacement).

Nothing here touches the game or the retail disc; it only reads the staged
MODs and bank rows.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOM = Path('assets/dataDir/courses/pikmin2room')


def chunks(data):
    at, out = 0, {}
    while at + 8 <= len(data):
        tag, size = struct.unpack_from('>II', data, at)
        out[tag] = (at + 8, size)
        if tag == 0xFFFF:
            break
        at += 8 + size
    return out


def positions(data):
    start, _ = chunks(data)[16]
    count = struct.unpack_from('>I', data, start)[0]
    base = start - 8 + 32
    return [struct.unpack_from('>3f', data, base + 12 * i) for i in range(count)]


def triangles(data):
    start, size = chunks(data)[80]
    shapes = struct.unpack_from('>I', data, start)[0]
    at = start + 4
    at += (-at) % 32
    tris = []
    for _ in range(shapes):
        flags = struct.unpack_from('>I', data, at + 4)[0]
        dl_len = struct.unpack_from('>I', data, at + 30)[0]
        at += 34
        at += (-at) % 32
        dl = at
        op, n = struct.unpack_from('>BH', data, dl)
        if op != 0x90:
            raise ValueError('expected GX_TRIANGLES')
        stride = 5 + (2 if flags & 4 else 0) + (2 if flags & 8 else 0)
        idx = [struct.unpack_from('>H', data, dl + 3 + i * stride + 1)[0] for i in range(n)]
        tris.extend(tuple(idx[i:i + 3]) for i in range(0, n - 2, 3))
        at = dl + dl_len
    return tris


def bracket(frames, f):
    if f <= frames[0]:
        return 0, 0, 0.0
    if f >= frames[-1]:
        return len(frames) - 1, len(frames) - 1, 0.0
    for i in range(1, len(frames)):
        if frames[i] >= f:
            if frames[i] == f:
                return i, i, 0.0
            return i - 1, i, (f - frames[i - 1]) / (frames[i] - frames[i - 1])
    return len(frames) - 1, len(frames) - 1, 0.0


def extent(pose):
    lo = [min(v[k] for v in pose) for k in range(3)]
    hi = [max(v[k] for v in pose) for k in range(3)]
    return math.dist(lo, hi)


def hold_frame(poses, frames, fraction=0.2):
    """Native p2motion::visibleEnd: the last pose not collapsed to a point."""
    sizes = [extent(p) for p in poses]
    for i in range(len(poses) - 1, -1, -1):
        if sizes[i] >= fraction * max(sizes):
            return frames[i]
    return frames[-1]


def is_death(clip):
    return clip.startswith('dead') or clip.startswith('pdead') or clip == 'kagebozu_dead'


def displayed(poses, frames, f, lerp):
    a, b, w = bracket(frames, f)
    if not lerp:
        k = a if w < 0.5 else b
        return poses[k]
    pa, pb = poses[a], poses[b]
    return [(x0 + (x1 - x0) * w, y0 + (y1 - y0) * w, z0 + (z1 - z0) * w)
            for (x0, y0, z0), (x1, y1, z1) in zip(pa, pb)]


YAW, PITCH = math.radians(35), math.radians(-20)


def project(p):
    x, y, z = p
    cy, sy = math.cos(YAW), math.sin(YAW)
    x, z = cy * x + sy * z, -sy * x + cy * z
    cp, sp = math.cos(PITCH), math.sin(PITCH)
    y, z = cp * y - sp * z, sp * y + cp * z
    return x, y, z


def render(geom, tris, box, size, label, font):
    img = Image.new('RGB', (size, size + 18), (24, 26, 30))
    draw = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    scale = (size - 16) / max(x1 - x0, y1 - y0, 1e-6)
    pts = [project(p) for p in geom]
    faces = []
    for a, b, c in tris:
        pa, pb, pc = pts[a], pts[b], pts[c]
        ux, uy, uz = pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]
        vx, vy, vz = pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length < 1e-12:
            continue
        shade = abs(0.35 * nx + 0.8 * ny - 0.5 * nz) / length
        depth = (pa[2] + pb[2] + pc[2]) / 3
        faces.append((depth, shade, (pa, pb, pc)))
    faces.sort(key=lambda f: -f[0])
    for _, shade, tri in faces:
        c = int(60 + 170 * shade)
        poly = [(8 + (p[0] - x0) * scale, 18 + size - 8 - (p[1] - y0) * scale) for p in tri]
        draw.polygon(poly, fill=(int(c * 0.78), int(c * 0.9), c))
    draw.text((6, 3), label, fill=(235, 235, 235), font=font)
    return img


def load_clip(run, clip):
    room = Path(run) / ROOM
    if 'models' in clip:
        files = [room / m for m in clip['models']]
    else:
        files = [room / f"{clip['stem']}_{i:02}.mod" for i in range(clip['poses'])]
    datas = [f.read_bytes() for f in files]
    return [positions(d) for d in datas], triangles(datas[0]), clip['frames']


def find(audit, family, species, clip):
    for c in audit['clips']:
        if c['family'] == family and c['species'] == species and c['clip'] == clip:
            return c
    raise KeyError(f'{family} {species} {clip} not in audit')


def metric(seq):
    steps = [max(math.dist(p, q) for p, q in zip(a, b)) for a, b in zip(seq, seq[1:])]
    return steps


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--before-run', type=Path, required=True)
    parser.add_argument('--before-audit', type=Path, required=True)
    parser.add_argument('--after-run', type=Path, required=True)
    parser.add_argument('--after-audit', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--case', action='append', required=True,
                        help='name:bankfile:species:clip[:baseline=nearest|lerp]')
    parser.add_argument('--size', type=int, default=220)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    before_audit = json.loads(args.before_audit.read_text())
    after_audit = json.loads(args.after_audit.read_text())
    font = ImageFont.load_default()
    summary = {}
    for case in args.case:
        parts = case.split(':')
        name, family, species, clip = parts[:4]
        baseline = parts[4] if len(parts) > 4 else 'nearest'
        b = find(before_audit, family, species, clip)
        a = find(after_audit, family, species, clip)
        b_poses, tris, b_frames = load_clip(args.before_run, b)
        a_poses, a_tris, a_frames = load_clip(args.after_run, a)
        duration = a['source_frames']
        # Loops play twice; a death clip plays once and then holds (the corpse).
        timeline = list(range(duration)) * 2 if not is_death(clip) else list(range(duration)) + [duration - 1] * 20
        # Death clips stop at their last visible pose, as native does.
        b_hold = hold_frame(b_poses, b_frames) if is_death(clip) else duration
        a_hold = hold_frame(a_poses, a_frames) if is_death(clip) else duration
        seqs = {
            'before_nearest': [displayed(b_poses, b_frames, min(f, b_hold), False) for f in timeline],
            'before_lerp': [displayed(b_poses, b_frames, min(f, b_hold), True) for f in timeline],
            'after_lerp': [displayed(a_poses, a_frames, min(f, a_hold), True) for f in timeline],
        }
        allpts = [project(p) for seq in seqs.values() for g in seq[:duration] for p in g]
        box = (min(p[0] for p in allpts), min(p[1] for p in allpts),
               max(p[0] for p in allpts), max(p[1] for p in allpts))
        labels = {
            'before_nearest': f'BEFORE {len(b_frames)} poses, nearest' + (' (was drawn)' if baseline == 'nearest' else ''),
            'before_lerp': f'BEFORE {len(b_frames)} poses, lerp' + (' (was drawn)' if baseline == 'lerp' else ''),
            'after_lerp': f'AFTER {len(a_frames)} poses, lerp',
        }
        frames = []
        for i in range(len(timeline)):
            panels = [render(seqs[k][i], tris, box, args.size, labels[k], font) for k in seqs]
            canvas = Image.new('RGB', (args.size * 3, args.size + 36), (16, 17, 20))
            for j, panel in enumerate(panels):
                canvas.paste(panel, (j * args.size, 0))
            ImageDraw.Draw(canvas).text(
                (6, args.size + 20), f'{name}: {species} {clip}  source frame {timeline[i]}/{duration - 1}',
                fill=(200, 200, 200), font=font)
            frames.append(canvas)
        frames[0].save(args.out / f'{name}.gif', save_all=True, append_images=frames[1:], duration=33, loop=0,
                       optimize=True)
        # Motion plot.
        steps = {k: metric(v[:duration + 1]) for k, v in seqs.items()}
        W, H = 900, 520
        plot = Image.new('RGB', (W, H), (250, 250, 250))
        d = ImageDraw.Draw(plot)
        colors = {'before_nearest': (214, 96, 77), 'before_lerp': (230, 171, 2), 'after_lerp': (27, 120, 180)}
        top = max(max(v) for v in steps.values()) or 1
        d.text((10, 6), f'{name} {species} {clip}: largest vertex move per displayed frame (30 fps)', fill=(0, 0, 0),
               font=font)
        for k, v in steps.items():
            pts = [(40 + i * (W - 60) / max(1, len(v) - 1), 230 - 200 * s / top) for i, s in enumerate(v)]
            d.line(pts, fill=colors[k], width=2)
        d.line([(40, 230), (W - 20, 230)], fill=(120, 120, 120))
        # Most-moving vertex path (after bake defines it), projected.
        seq = seqs['after_lerp'][:duration]
        vid = max(range(len(seq[0])), key=lambda i: max(math.dist(g[i], seq[0][i]) for g in seq))
        paths = {k: [project(g[vid])[:2] for g in v[:duration]] for k, v in seqs.items()}
        px = [p[0] for v in paths.values() for p in v]
        py = [p[1] for v in paths.values() for p in v]
        sx = (W / 2 - 60) / max(max(px) - min(px), 1e-6)
        sy = (H - 290) / max(max(py) - min(py), 1e-6)
        s = min(sx, sy)
        d.text((10, 250), f'projected path of the most-moving vertex (#{vid}) over one loop', fill=(0, 0, 0), font=font)
        for k, v in paths.items():
            pts = [(W / 4 + (x - min(px)) * s, H - 20 - (y - min(py)) * s) for x, y in v]
            d.line(pts, fill=colors[k], width=2)
        for j, (k, label) in enumerate(labels.items()):
            d.rectangle([W - 330, 262 + 18 * j, W - 318, 274 + 18 * j], fill=colors[k])
            d.text((W - 312, 262 + 18 * j), label, fill=(0, 0, 0), font=font)
        plot.save(args.out / f'{name}-motion.png')
        summary[name] = {k: dict(poses=len(b_frames if k.startswith('before') else a_frames),
                                 max_step=round(max(v), 4), median_step=round(sorted(v)[len(v) // 2], 4),
                                 still_frames=sum(1 for x in v if x < 1e-6), frames=len(v))
                         for k, v in steps.items()}
        summary[name].update(species=species, clip=clip, source_frames=duration, baseline_drawn=baseline)
        print(name, json.dumps(summary[name]))
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
