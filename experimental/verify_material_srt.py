"""Compare native sample probe output to an independent JMA source-equation oracle.

Consumes a locally exported material-srt.json and sample_p2_material_srt stdout.
No retail assets or keys are embedded. The oracle follows the floating-point
JMA instruction order algebraically, not the runtime's four Hermite basis terms.
This verifies numerical equations, not bit-exact PowerPC rounding or rendering.
"""
import argparse
import json
import math
from pathlib import Path


def source_curve(keys, frame):
    if frame <= keys[0][0]: return keys[0][1]
    if frame >= keys[-1][0]: return keys[-1][1]
    a, b = next((a, b) for a, b in zip(keys, keys[1:]) if a[0] <= frame < b[0])
    distance = frame-a[0]
    fraction = distance/(b[0]-a[0])
    square = fraction*fraction
    difference = square-fraction
    base = (2*fraction*difference-square)*(a[1]-b[1])+a[1]
    tangent = fraction*a[3]-(a[3]*difference+a[3]+b[2]*difference)
    return base-distance*tangent


def verify(report, lines):
    maximum = 0.0; count = 0
    expected_rows = [(i, step/8) for i in range(len(report['tracks'])) for step in range(report['duration']*8+1)]
    rows = [list(map(float, line.split())) for line in lines if line.strip()]
    if len(rows) != len(expected_rows): raise ValueError('Missing or extra native samples')
    for row, (index, frame) in zip(rows, expected_rows):
        if len(row) != 13 or row[:2] != [index, frame]: raise ValueError('Native frame ordering/shape mismatch')
        track = report['tracks'][index]
        sx, sy, rotation, tx, ty = [source_curve(keys, frame) for keys in track['curves']]
        rotation = math.trunc(rotation)*(1 << report['rotation_shift'])
        rotation = (rotation+32768)%65536-32768
        angle = ((rotation%65536) >> 5)*math.tau/2048
        sn, cs = math.sin(angle), math.cos(angle)
        cx, cy, _ = track['center']
        expected = [sx, sy, rotation, tx, ty, sx*cs, -sx*sn,
                    sx*(-cs*cx+sn*cy)+cx+tx, sy*sn, sy*cs,
                    sy*(-sn*cx-cs*cy)+cy+ty]
        for actual, reference in zip(row[2:], expected):
            error = abs(actual-reference)
            if not math.isfinite(actual) or error > 2e-6: raise ValueError(f'Mismatch at track {index}, frame {frame}: {actual} vs {reference}')
            maximum = max(maximum, error)
        count += 1
    return dict(samples=count, max_absolute_error=maximum, tolerance=2e-6, source_sha256=report['source_sha256'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--samples', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(verify(json.loads(args.report.read_text(encoding='utf-8')), args.samples.read_text(encoding='utf-8').splitlines()), indent=2))
