"""Minimal reproducer for the Bulblax converter blockers (handoff to #186 integration lead).

Run from the repo root after the #217 import:

    python -m experimental.pikmin2_kingchappy_normalless_repro --imported output/bulblax-run1

Demonstrates, without modifying any shared converter code:

1. KingChappy (enemy 53): shape 0's display list carries no normal attribute
   (GX attr 10 / VA_NORMAL) even though the VTX1 block contains a populated
   normal array. ``decode(..., bake_rigid=True, draw_matrices=...)`` then fails
   inside the bake with ``KeyError: 10`` for every sampled frame of all 14
   clips, so the bank enumerates them as ``blocked`` rather than fabricating
   poses.

2. Queen (enemy 30): ``dead`` frames 83/111/139 and every ``carry`` frame
   produce ``ValueError: Singular normal transform`` from
   ``pikmin2_rigid.normal_matrices`` (the animated joint normal matrix has a
   near-zero determinant), so those frames are recorded ``unsupported``.

Requested converter interface (either is acceptable; the bank module needs no
other changes to adopt it):

- Preferred: ``decode(..., bake_rigid=True, pose=pose, missing_normals='compute')``
  where ``missing_normals`` is ``'error'`` (default, current behavior),
  ``'compute'`` (derive per-vertex normals from baked triangle geometry, e.g.
  area-weighted face-normal accumulation), or ``'default'`` (supply a unit
  +Y normal). This unblocks KingChappy shapes whose display list omits the
  normal attribute while VTX1 still carries the array.
- Additionally/optionally: tolerate near-singular normal matrices via a
  documented fallback (e.g. ``singular_normal='transpose-adjugate'``) instead
  of raising, so Queen dead/carry frames can bake; the adjugate-transpose is
  the standard inverse-transpose generalization for singular matrices.

Both knobs must stay opt-in so existing callers keep the strict behavior.
"""
import argparse
import json
import struct
import sys
from pathlib import Path

from experimental.pikmin2_convert import blocks, decode, u16, u32
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import sample_frames

GX_ATTR_NAMES = {0: 'VA_POSMTXIDX', 9: 'VA_POS', 10: 'VA_NRM', 11: 'VA_CLR0', 12: 'VA_CLR1',
                 13: 'VA_TEX0', **{14 + i: f'VA_TEX{1 + i}' for i in range(7)},
                 **{1 + i: f'VA_TEX{i}MTXIDX' for i in range(8)}, 25: 'VA_NULL'}


def vtx1_attributes(model_blocks):
    v = model_blocks['VTX1']
    attrs = {}
    at = u32(v, 8)
    while u32(v, at) != 255:
        attr, count, kind = struct.unpack_from('>III', v, at)
        attrs[attr] = {'components': count, 'storage': kind, 'shift': v[at + 12]}
        at += 16
    return attrs


def shape_attributes(model_blocks, shape_index):
    s = model_blocks['SHP1']
    rec = u32(s, 12) + u16(s, u32(s, 16) + 2 * shape_index) * 40
    desc = u16(s, rec + 4)
    attrs = []
    at = u32(s, 24) + desc
    while u32(s, at) != 255:
        attr, kind = struct.unpack_from('>II', s, at)
        attrs.append(attr)
        at += 8
    return attrs


def show_attributes(model_blocks, label):
    vtx = vtx1_attributes(model_blocks)
    shape0 = shape_attributes(model_blocks, 0)
    print(f'{label} VTX1 arrays: {sorted((GX_ATTR_NAMES.get(a, a) for a in vtx), key=str)}')
    print(f'{label} shape 0 display-list attributes: {[GX_ATTR_NAMES.get(a, a) for a in shape0]}')
    print(f'{label} VTX1 has normal array (VA_NRM): {10 in vtx}; '
          f'shape 0 references normals: {10 in shape0}')
    return 10 in vtx, 10 in shape0


def kingchappy(imported):
    print('--- KingChappy: display list without normal attribute ---')
    model = (imported / 'KingChappy' / 'enemy.bmd').read_bytes()
    model_blocks = blocks(model)
    joints = u16(model_blocks['JNT1'], 8)
    has_vtx_normals, shape_uses_normals = show_attributes(model_blocks, 'KingChappy')
    clip = (imported / 'KingChappy' / 'attack.bca').read_bytes()
    duration, pose = bca_pose(clip, 0, joints, allow_scale=True)
    print(f'attack.bca duration {duration}; attempting weighted bake of frame 0 ...')
    matrices = draw_matrices(model_blocks, pose)
    try:
        decode(model, True, bake_rigid=True, draw_matrices=matrices)
        print('UNEXPECTED: bake succeeded')
        return False
    except KeyError as error:
        print(f'exact failure: KeyError: {error} (missing normal attribute index in baked vertex)')
    ok = has_vtx_normals and not shape_uses_normals
    print(f'reproducer confirmed: {ok}')
    return ok


def queen(imported):
    print('--- Queen: singular normal transform on dead/carry frames ---')
    model = (imported / 'Queen' / 'enemy.bmd').read_bytes()
    model_blocks = blocks(model)
    joints = u16(model_blocks['JNT1'], 8)
    failures = {}
    for name, frames in (('dead', (83, 111, 139)), ('carry', None)):
        clip = (imported / 'Queen' / f'{name}.bca').read_bytes()
        duration, _ = bca_pose(clip, 0, joints, allow_scale=True)
        targets = frames if frames is not None else sample_frames(duration, 6)
        bad = []
        for frame in targets:
            _, pose = bca_pose(clip, frame, joints, allow_scale=True)
            matrices = draw_matrices(model_blocks, pose)
            try:
                decode(model, True, bake_rigid=True, draw_matrices=matrices)
            except ValueError as error:
                bad.append((frame, str(error)))
        failures[name] = bad
        print(f'{name}: {len(bad)}/{len(targets)} sampled frames failed: '
              + json.dumps(bad[:4]))
    expected = [f for f, _ in failures['dead']] == [83, 111, 139] and failures['carry']
    print(f'reproducer confirmed: {bool(expected)}')
    return bool(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported', type=Path, required=True,
                        help='existing #217 import directory (e.g. output/bulblax-run1)')
    args = parser.parse_args()
    if not (args.imported / 'bulblax.json').exists():
        parser.error('expected a #217 Bulblax import directory')
    ok = kingchappy(args.imported) & queen(args.imported)
    print(__doc__.split('Requested converter interface', 1)[1].split('Both knobs', 1)[0].strip()
          if ok else 'reproducer did not confirm the recorded failures')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
