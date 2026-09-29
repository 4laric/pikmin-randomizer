"""Loop-seam audit of retail P2 enemy animations (#895).

For every BCA clip of the given species (``enemy/data/<Species>/anim.szs`` on
the supplied GPVE01 disc) compare the local joint transforms of

* frame 0 with frame ``duration-1`` (the loop seam: J3D repeat playback steps
  from the last frame straight back to frame 0), and
* adjacent frames at the start and end of the clip (an ordinary one-frame
  step).

The metric is the largest absolute difference over every joint's local 3x4
matrix (rotation terms are unitless, translations in model units), so only
the RATIO ``seam / step`` is meaningful. ``seam_ratio`` near 1 means the clip
is authored so that ``duration-1 -> 0`` is one more ordinary step (the last
frame is NOT a copy of frame 0); a large ratio means the seam jumps (one-shot
acts, root-motion flights). The native draw path mirrors this with
``p2motion::seamContinuous`` on the baked poses and blends a P1 loop wrap only
across a discontinuous seam.

Usage: ``py -3.12 scripts/p2_loop_seam_audit.py --iso <GPVE01.iso> [--json out] Species...``
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_assets import archive_files, disc_files  # noqa: E402
from experimental.pikmin2_purple import bca_pose  # noqa: E402

DEFAULT_ISO = Path('C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso')
# The 35-species campaign pool plus the Groink identities (78/97 share MiniHoudai).
DEFAULT_SPECIES = (
    'Armor', 'BigFoot', 'Chappy', 'Damagumo', 'DangoMushi', 'ElecBug', 'ElecOtakara', 'FireChappy',
    'FireOtakara', 'Frog', 'GasOtakara', 'Imomushi', 'Jigumo', 'Kabuto', 'KingChappy', 'KumaChappy',
    'KumaKochappy', 'LeafChappy', 'MaroFrog', 'MiniHoudai', 'Miulin', 'Sarai', 'SnakeCrow', 'SnakeWhole',
    'Sokkuri', 'TamagoMushi', 'Tank', 'Tobi', 'UjiA', 'UjiB', 'UmiMushi', 'WaterOtakara', 'Wtank',
    'YellowChappy')
CONTINUOUS_RATIO = 3.0  # matches p2motion::seamContinuous(factor=3)


def delta(a, b):
    return max(abs(x - y) for ma, mb in zip(a, b) for ra, rb in zip(ma, mb) for x, y in zip(ra, rb))


def audit(iso, species):
    index = disc_files(iso)
    out = {}
    with Path(iso).open('rb') as disc:
        def read(path):
            at, size = index[path]
            disc.seek(at)
            return disc.read(size)
        for name in species:
            key = f'enemy/data/{name}/anim.szs'
            if key not in index:
                out[name] = {'note': 'no anim.szs (shares another species\' animation or has none)'}
                continue
            rows = {}
            for clip, raw in sorted(archive_files(read(key)).items()):
                if not clip.lower().endswith('.bca'):
                    continue
                try:
                    joints = struct.unpack_from('>H', raw, 32 + 12)[0]
                    duration, first = bca_pose(raw, 0, joints, allow_scale=True, singular_scale='allow')
                    if duration < 3:
                        rows[clip] = {'duration': duration, 'note': 'trivial'}
                        continue
                    last = bca_pose(raw, duration - 1, joints, allow_scale=True, singular_scale='allow')[1]
                    before = bca_pose(raw, duration - 2, joints, allow_scale=True, singular_scale='allow')[1]
                    second = bca_pose(raw, 1, joints, allow_scale=True, singular_scale='allow')[1]
                    seam = delta(first, last)
                    step = max(delta(before, last), delta(first, second), 1e-9)
                    rows[clip] = dict(duration=duration, loop_attribute=raw[40], seam=round(seam, 5),
                                      step=round(step, 5), seam_ratio=round(seam / step, 3),
                                      last_equals_first=seam < 1e-4,
                                      continuous=seam <= CONTINUOUS_RATIO * step or seam < 0.05)
                except (ValueError, KeyError, struct.error) as error:
                    rows[clip] = {'error': f'{type(error).__name__}: {error}'}
            out[name] = rows
    return out


def summary(result):
    clips = [r for rows in result.values() for r in rows.values() if isinstance(r, dict) and 'seam' in r]
    return dict(clips=len(clips),
                last_equals_first=sum(r['last_equals_first'] for r in clips),
                continuous=sum(r['continuous'] for r in clips),
                discontinuous=sum(not r['continuous'] for r in clips))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--iso', type=Path, default=DEFAULT_ISO)
    parser.add_argument('--json', type=Path, default=None)
    parser.add_argument('species', nargs='*', default=list(DEFAULT_SPECIES))
    args = parser.parse_args(argv)
    result = audit(args.iso, args.species)
    report = dict(summary=summary(result), species=result)
    if args.json:
        args.json.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(report['summary']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
