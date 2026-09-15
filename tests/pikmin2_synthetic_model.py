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


def _jnt1(scale=(1.0, 1.0, 1.0), translation=(0.0, 0.0, 0.0)):
    body = bytearray(88)
    struct.pack_into('>H', body, 8, 1)      # one joint
    struct.pack_into('>II', body, 12, 24, 0)  # record at 24, no remap
    struct.pack_into('>3f', body, 24 + 4, *scale)  # scale
    # rotation (24+16, 3h) stays zero
    struct.pack_into('>3f', body, 24 + 24, *translation)  # translation
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


def _shp1(vertex_count, with_normals, display_indices=None, matrix_type=0):
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
    record[0] = matrix_type  # SHP1 shape matrix type (0 Base, 1 BBoard, ...)
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


def build_model(positions, normals, uvs, display_indices=None, display_normals=True,
                matrix_type=0, joint_scale=(1.0, 1.0, 1.0), joint_translation=(0.0, 0.0, 0.0)):
    """One-shape rigid model. ``normals`` populates the VTX1 normal array;
    ``display_normals=False`` drops the normal attribute from the shape
    display list (the KingChappy pattern). ``matrix_type`` selects the SHP1
    shape matrix type (0 Base, 1 BBoard, ...). ``joint_scale``/``joint_translation``
    place the single rigid joint."""
    parts = [_inf1(), _vtx1(positions, normals, uvs), _shp1(len(positions), display_normals, display_indices,
             matrix_type),
             _jnt1(joint_scale, joint_translation), _drw1(), _evp1(), _mat3(), _tex1()]
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
