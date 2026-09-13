"""Opt-in normal-tolerance modes for the J3D converter (#186).

Builds tiny synthetic J3D2bmd3 models in code (no disc assets) and checks the
missing_normals='error'|'compute'|'default' and
singular_normal='error'|'transpose-adjugate' decode/bake paths, including that
the strict defaults are unchanged.
"""
import math
import struct
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_convert import decode, write_model


def _block(tag, body):
    # ``body`` is the full block content with the first 8 bytes reserved for
    # the tag/size header, so offsets inside match the converter's view.
    assert len(body) >= 8
    body[:4] = tag
    struct.pack_into('>I', body, 4, len(body))
    return bytes(body)


def _inf1():
    body = bytearray(40)
    struct.pack_into('>I', body, 20, 24)  # hierarchy stream offset
    stream = [(0x10, 0), (0x11, 0), (0x12, 0), (0, 0)]  # joint 0, material 0, shape 0, end
    for i, (kind, index) in enumerate(stream):
        struct.pack_into('>HH', body, 24 + 4 * i, kind, index)
    return _block(b'INF1', body)


def _jnt1():
    body = bytearray(88)
    struct.pack_into('>H', body, 8, 1)      # one joint
    struct.pack_into('>II', body, 12, 24, 0)  # record at 24, no remap
    struct.pack_into('>3f', body, 24 + 4, 1.0, 1.0, 1.0)  # scale
    # rotation (24+16, 3h) and translation (24+24, 3f) stay zero
    return _block(b'JNT1', body)


def _drw1():
    body = bytearray(24)
    struct.pack_into('>H', body, 8, 1)      # one direct draw entry
    struct.pack_into('>II', body, 12, 20, 21)  # flags at 20, refs at 21 -> joint 0
    return _block(b'DRW1', body)


def _evp1():
    body = bytearray(12)
    return _block(b'EVP1', body)  # zero envelopes (u16 at 8 defaults to 0)


def _vtx1(positions, normals, uvs):
    """positions/normals/uvs: lists of float tuples; normals may be None."""
    body = bytearray(64)
    formats = [(9, 3, 4)]
    if normals is not None:
        formats.append((10, 3, 4))
    formats.append((13, 2, 4))
    at = 64
    entries = b''
    for attr, count, kind in formats:
        entries += struct.pack('>III', attr, count, kind) + bytes(4)
    entries += struct.pack('>III', 255, 0, 0) + bytes(4)
    body += entries
    at = len(body)
    arrays = {}
    for attr, values, dim in ((9, positions, 3), (10, normals, 3), (13, uvs, 2)):
        if values is None:
            continue
        arrays[attr] = at
        for v in values:
            body += struct.pack('>' + 'f' * dim, *v)
            at += 4 * dim
    struct.pack_into('>I', body, 8, 64)  # format table offset
    struct.pack_into('>I', body, 12, arrays[9])
    struct.pack_into('>I', body, 16, arrays.get(10, 0))
    struct.pack_into('>I', body, 32, arrays[13])
    return _block(b'VTX1', body)


def _shp1(vertex_count, with_normals, display_indices=None):
    attrs = [(0, 2), (9, 2)] + ([(10, 2)] if with_normals else []) + [(13, 2)]
    descriptor = b''.join(struct.pack('>II', a, k) for a, k in attrs) + struct.pack('>II', 255, 0)
    indices = display_indices if display_indices is not None else list(range(vertex_count))
    per_vertex = 2 + (1 if with_normals else 0) + 1
    dl = bytearray(struct.pack('>BH', 0x90, len(indices)))
    for i in indices:
        dl += bytes([0, i])  # matrix slot 0, position index
        if with_normals:
            dl += bytes([0])  # normal index 0
        dl += bytes([i if i < 3 else 0])  # uv index
    record = bytearray(40)
    struct.pack_into('>4H', record, 2, 1, 0, 0, 0)  # groups=1, desc=0, mi=0, di=0
    body = bytearray(48)
    struct.pack_into('>H', body, 8, 1)      # one shape
    struct.pack_into('>I', body, 12, 48)    # record base
    struct.pack_into('>I', body, 16, 88)    # remap table
    struct.pack_into('>I', body, 24, 90)    # attribute descriptors
    struct.pack_into('>I', body, 28, 90 + len(descriptor))  # matrix table
    struct.pack_into('>I', body, 36, 90 + len(descriptor) + 2)  # matrix group table
    struct.pack_into('>I', body, 40, 90 + len(descriptor) + 10)  # display group table
    struct.pack_into('>I', body, 32, 90 + len(descriptor) + 18)  # display list data
    body += record
    body += struct.pack('>H', 0)            # remap: shape 0
    body += descriptor
    body += struct.pack('>H', 0)            # matrix table: DRW1 entry 0
    body += struct.pack('>HHI', 0, 1, 0)    # one matrix slot, first=0
    body += struct.pack('>II', len(dl), 0)  # display group: size, offset
    body += bytes(dl)
    return _block(b'SHP1', body)


def _mat3():
    body = bytearray(464)
    struct.pack_into('>H', body, 8, 1)      # one material
    struct.pack_into('>I', body, 12, 132)   # record base
    struct.pack_into('>I', body, 16, 464)   # remap table
    struct.pack_into('>I', body, 88, 466)   # texgen-count byte
    struct.pack_into('>I', body, 108, 468)  # alpha compare (unused; pixel_state reads it)
    struct.pack_into('>I', body, 112, 476 - 8)  # placeholder, fixed below
    struct.pack_into('>I', body, 116, 476 - 4)  # placeholder, fixed below
    r = 132
    body[r] = 1                              # draw category 1
    struct.pack_into('>H', body, r + 132, 0xFFFF)  # no texture
    struct.pack_into('>HH', body, r + 0x146, 0, 0)  # alpha/blend table indices
    body += struct.pack('>H', 0)             # 464: remap -> material record 0
    body += bytes([0])                       # 466: zero texgens -> diffuse slot 0
    body += bytes(1)                         # 467: pad
    body += bytes([4, 128, 0, 3, 240, 255, 255, 255])  # 468: alpha compare
    body += bytes([1, 4, 5, 3])              # 476: blend mode
    body += bytes([1, 3, 0, 255])            # 480: z mode
    struct.pack_into('>I', body, 112, 476)
    struct.pack_into('>I', body, 116, 480)
    return _block(b'MAT3', body)


def _tex1():
    body = bytearray(12)
    return _block(b'TEX1', body)  # zero textures (u16 at 8 defaults to 0)


def build_model(positions, normals, uvs, display_indices=None, display_normals=True):
    """One-shape rigid model. ``normals`` populates the VTX1 normal array;
    ``display_normals=False`` drops the normal attribute from the shape
    display list (the KingChappy pattern)."""
    parts = [_inf1(), _vtx1(positions, normals, uvs), _shp1(len(positions), display_normals, display_indices),
             _jnt1(), _drw1(), _evp1(), _mat3(), _tex1()]
    data = bytearray(32)
    data[:8] = b'J3D2bmd3'
    struct.pack_into('>I', data, 12, len(parts))
    data += b''.join(parts)
    struct.pack_into('>I', data, 8, len(data))
    return bytes(data)


TRIANGLE = [(0., 0., 0.), (1., 0., 0.), (0., 0., 1.)]
UVS = [(0., 0.), (1., 0.), (0., 1.)]


def normalless_model():
    # KingChappy pattern: VTX1 carries a normal array, shape display list omits it.
    return build_model(TRIANGLE, [(0., 0., 1.)], UVS, display_normals=False)


def normal_model():
    return build_model(TRIANGLE, [(0., 1., 0.)], UVS)


class MissingNormalsTests(unittest.TestCase):
    def test_error_is_the_default_and_raises_keyerror(self):
        model = normalless_model()
        with self.assertRaises(KeyError) as ctx:
            decode(model, True, bake_rigid=True)
        self.assertEqual(ctx.exception.args, (10,))
        with self.assertRaises(KeyError):
            decode(model, True, bake_rigid=True, missing_normals='error')

    def test_invalid_modes_rejected(self):
        model = normal_model()
        for kw in ({'missing_normals': 'bogus'}, {'singular_normal': 'bogus'}):
            with self.assertRaises(ValueError, msg=kw):
                decode(model, True, bake_rigid=True, **kw)

    def test_default_mode_substitutes_unit_y(self):
        _, arrays, shapes, _ = decode(normalless_model(), True, bake_rigid=True,
                                      missing_normals='default')
        self.assertEqual(arrays[10], [(0., 1., 0.)])
        for tri in shapes[0]:
            for vertex in tri:
                self.assertEqual(vertex[10], 0)

    def test_compute_mode_derives_face_normal(self):
        _, arrays, shapes, _ = decode(normalless_model(), True, bake_rigid=True,
                                      missing_normals='compute')
        # Triangle (0,0,0),(1,0,0),(0,0,1): cross((1,0,0),(0,0,1)) = (0,-1,0).
        # One derived normal per baked position.
        for tri in shapes[0]:
            for vertex in tri:
                # Each vertex points at its baked position's derived normal.
                self.assertEqual(arrays[10][vertex[10]], (0., -1., 0.))

    def test_compute_mode_area_weights_shared_vertices(self):
        # Two triangles sharing position 0: (0,0,4) and (0,-1,0) face normals.
        positions = [(0., 0., 0.), (2., 0., 0.), (0., 2., 0.), (1., 0., 0.), (0., 0., 1.)]
        uvs = UVS + [(0., 0.), (0., 0.)]
        model = build_model(positions, [(0., 0., 1.)], uvs,
                            display_indices=[0, 1, 2, 0, 3, 4], display_normals=False)
        _, arrays, shapes, _ = decode(model, True, bake_rigid=True, missing_normals='compute')
        root = math.sqrt(17.0)
        expected = {(0., 0., 1.): {1, 2}, (0., -1. / root, 4. / root): {0}}
        seen = {}
        for tri in shapes[0]:
            for vertex in tri:
                seen.setdefault(arrays[10][vertex[10]], set()).add(vertex[9])
        for normal, positions_used in expected.items():
            matched = [p for n, p in seen.items()
                       if all(math.isclose(a, b, abs_tol=1e-7) for a, b in zip(n, normal))]
            self.assertEqual(len(matched), 1, (normal, seen))
            self.assertEqual(matched[0], positions_used)

    def test_write_model_records_mode_only_when_opted_in(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'pose.mod'
            report = write_model(decode(normalless_model(), True, bake_rigid=True,
                                        missing_normals='compute'), path, 'synthetic.bmd')
            self.assertEqual(report['missing_normals'], 'compute')
            self.assertNotIn('singular_normal', report)
            strict = write_model(decode(normal_model(), True, bake_rigid=True),
                                 Path(d) / 'strict.mod', 'synthetic.bmd')
            self.assertNotIn('missing_normals', strict)
            self.assertNotIn('singular_normal', strict)


class SingularNormalTests(unittest.TestCase):
    ZERO_POSE = [[[0., 0., 0., 0.], [0., 0., 0., 0.], [0., 0., 0., 0.]]]
    FLAT_Y_POSE = [[[1., 0., 0., 0.], [0., 0., 0., 0.], [0., 0., 1., 0.]]]

    def test_error_is_the_default_and_raises(self):
        with self.assertRaisesRegex(ValueError, 'Singular normal transform'):
            decode(normal_model(), True, bake_rigid=True, pose=self.ZERO_POSE)
        with self.assertRaisesRegex(ValueError, 'Singular normal transform'):
            decode(normal_model(), True, bake_rigid=True, pose=self.ZERO_POSE,
                   singular_normal='error')

    def test_transpose_adjugate_bakes_cofactor_normal(self):
        # diag(1,0,1) collapses the Y axis; the cofactor matrix maps (0,1,0)
        # to itself, so the authored +Y normal survives normalized.
        _, arrays, _, _ = decode(normal_model(), True, bake_rigid=True, pose=self.FLAT_Y_POSE,
                                 singular_normal='transpose-adjugate')
        self.assertEqual(arrays[10], [(0., 1., 0.)])
        for x, y, z in arrays[9]:
            self.assertEqual(y, 0.)

    def test_transpose_adjugate_report_records_mode(self):
        with tempfile.TemporaryDirectory() as d:
            report = write_model(decode(normal_model(), True, bake_rigid=True, pose=self.FLAT_Y_POSE,
                                        singular_normal='transpose-adjugate'),
                                 Path(d) / 'pose.mod', 'synthetic.bmd')
            self.assertEqual(report['singular_normal'], 'transpose-adjugate')
            self.assertNotIn('missing_normals', report)


class StrictDefaultTests(unittest.TestCase):
    def test_normal_model_bakes_unchanged(self):
        _, arrays, shapes, _ = decode(normal_model(), True, bake_rigid=True)
        self.assertEqual(arrays[9], TRIANGLE)
        self.assertEqual(arrays[10], [(0., 1., 0.)])
        self.assertEqual(sum(map(len, shapes)), 1)


if __name__ == '__main__':
    unittest.main()
