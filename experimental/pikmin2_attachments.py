"""Export bounded local-joint TRS banks for the shared attachment runtime (#358)."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

from experimental.pikmin2_convert import blocks
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_sheargrub_assets import joints
from experimental.pikmin2_animation import parse_bank
from experimental.pikmin2_assets import disc_files, archive_files


def parents(model):
    data = blocks(model)['INF1']
    at = struct.unpack_from('>I', data, 20)[0]
    stack, current, result = [], -1, {}
    while True:
        kind, index = struct.unpack_from('>HH', data, at)
        at += 4
        if kind == 0:
            break
        if kind == 1:
            stack.append(current)
        elif kind == 2:
            if not stack:
                raise ValueError('Unbalanced skeleton')
            current = stack.pop()
        elif kind == 0x10:
            if index in result:
                raise ValueError('Duplicate joint')
            result[index] = stack[-1] if stack else -1
            current = index
    if stack or set(result) != set(range(len(joints(model)))):
        raise ValueError('Incomplete skeleton')
    # The runtime evaluates parents first. Reject unsupported ordering explicitly.
    if any(parent >= index or parent < -1 for index, parent in result.items()):
        raise ValueError('Expected parent-first joint ordering')
    return [result[i] for i in range(len(result))]


def decompose(matrix):
    if not all(math.isfinite(v) for row in matrix for v in row):
        raise ValueError('Non-finite joint transform')
    scale = [math.sqrt(sum(matrix[r][c] ** 2 for r in range(3))) for c in range(3)]
    if not all(1e-6 <= v <= 1000 for v in scale):
        raise ValueError('Unsupported scale')
    m = [[matrix[r][c] / scale[c] for c in range(3)] for r in range(3)]
    det = (m[0][0] * (m[1][1]*m[2][2]-m[1][2]*m[2][1])
           - m[0][1] * (m[1][0]*m[2][2]-m[1][2]*m[2][0])
           + m[0][2] * (m[1][0]*m[2][1]-m[1][1]*m[2][0]))
    if abs(det - 1) > 1e-5 or any(abs(sum(m[r][a]*m[r][b] for r in range(3))) > 1e-5
                                 for a, b in ((0, 1), (0, 2), (1, 2))):
        raise ValueError('Local shear/reflection cannot be represented as positive TRS')
    trace = sum(m[i][i] for i in range(3))
    if trace > 0:
        s = math.sqrt(trace + 1) * 2
        q = [(m[2][1]-m[1][2])/s, (m[0][2]-m[2][0])/s, (m[1][0]-m[0][1])/s, s/4]
    else:
        i = max(range(3), key=lambda a: m[a][a])
        j, k = (i+1) % 3, (i+2) % 3
        s = math.sqrt(1+m[i][i]-m[j][j]-m[k][k]) * 2
        q = [0., 0., 0., (m[k][j]-m[j][k])/s]
        q[i], q[j], q[k] = s/4, (m[i][j]+m[j][i])/s, (m[i][k]+m[k][i])/s
    length = math.sqrt(sum(v*v for v in q))
    translation = [matrix[r][3] for r in range(3)]
    if any(abs(v) > 1e6 for v in translation):
        raise ValueError('Translation exceeds runtime bound')
    return translation + [v/length for v in q] + scale


def bank_text(model, animations, timing):
    """Generic BMD/BCA bank exporter; timing maps names to source frames/duration."""
    names, hierarchy = joints(model), parents(model)
    if not 1 <= len(names) <= 128 or not 1 <= len(timing) <= 64 or len(set(names)) != len(names):
        raise ValueError('Invalid skeleton or clip count')
    import re
    if any(not re.fullmatch('[A-Za-z0-9_]{1,63}', n) for n in [*names, *timing]):
        raise ValueError('Unsafe joint/clip name')
    rows = [f'P2_ATTACHMENTS_1 {len(names)} {len(timing)}']
    rows += [f'{name} {parent}' for name, parent in zip(names, hierarchy)]
    total = 0
    for name, info in timing.items():
        frames, duration = info['frames'], info['source_frames']
        if (not frames or len(frames) > 256 or not 1 <= duration <= 10000 or frames[0] != 0
                or frames[-1] != duration-1 or any(type(f) is not int for f in frames)
                or any(a >= b for a, b in zip(frames, frames[1:]))):
            raise ValueError('Invalid source sample mapping')
        total += len(frames) * len(names)
        if total > 32768:
            raise ValueError('Transform budget exceeded')
        rows += [f'{name} {duration} {len(frames)}', ' '.join(map(str, frames))]
        for frame in frames:
            actual_duration, pose = bca_pose(animations[name], frame, len(names), allow_scale=True)
            if actual_duration != duration:
                raise ValueError('Visual and attachment duration mismatch')
            rows += [' '.join(format(v, '.9g') for v in decompose(local)) for local in pose]
    text = '\n'.join(rows) + '\n'
    if len(text.encode()) > 4*1024*1024:
        raise ValueError('Byte budget exceeded')
    return text


def snow_bank(iso, snow, output):
    output.mkdir(parents=True, exist_ok=False)
    metadata = json.loads((snow/'snow.json').read_text())
    timing = parse_bank((snow/'p2-snow.txt').read_text())
    catalog = disc_files(iso)
    offset, size = catalog['enemy/data/Kochappy/anim.szs']
    with iso.open('rb') as stream:
        stream.seek(offset)
        archive = archive_files(stream.read(size))
    animations = {name: archive[name+'.bca'] for name in timing}
    for name, raw in animations.items():
        if (hashlib.sha256(raw).hexdigest() != metadata['motions'][name]['sha256']
                or timing[name]['frames'] != metadata['motions'][name]['frames']):
            raise ValueError('Source animation differs from the rendered bank')
    model = (snow/'snow.bmd').read_bytes()
    text = bank_text(model, animations, timing)
    (output/'attachments.txt').write_bytes(text.encode('ascii'))
    report = dict(model_sha256=hashlib.sha256(model).hexdigest(),
                  bank_sha256=hashlib.sha256(text.encode()).hexdigest(),
                  timing_sha256=hashlib.sha256((snow/'p2-snow.txt').read_bytes()).hexdigest(),
                  source_animation_sha256={n: hashlib.sha256(v).hexdigest() for n, v in animations.items()},
                  joints=joints(model), mouth='kamu', visual_bank=str(snow),
                  scope='Local TRS interpolation; runtime joint callbacks not included')
    (output/'attachments.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'snow', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(snow_bank(a.iso.resolve(), a.snow.resolve(), a.output.resolve()), indent=2))
