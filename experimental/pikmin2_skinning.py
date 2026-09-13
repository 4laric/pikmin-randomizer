"""Bounded J3D matrix-envelope support for the Groink prototype.

The native renderer builds one matrix per DRW1 entry: direct entries use a
joint's animated world matrix, while envelope entries blend animated-world
times inverse-bind matrices.  This module exposes that same draw-matrix table
so the local converter can explicitly bake sampled poses. The source is
J3DModelLoader::readEnvelop and J3DMtxBuffer::calcWeightEnvelopeMtx: inverse
matrices are indexed by joint INSIDE the influence loop, not by envelope.
"""
import math
import struct

from experimental.pikmin2_rigid import joint_matrices


def _u16(data, at):
    if at < 0 or at + 2 > len(data):
        raise ValueError("Truncated J3D table")
    return struct.unpack_from(">H", data, at)[0]


def _u32(data, at):
    if at < 0 or at + 4 > len(data):
        raise ValueError("Truncated J3D table")
    return struct.unpack_from(">I", data, at)[0]


def _f32(data, at):
    if at < 0 or at + 4 > len(data):
        raise ValueError("Truncated J3D envelope")
    value = struct.unpack_from(">f", data, at)[0]
    if not math.isfinite(value):
        raise ValueError("Non-finite J3D envelope weight")
    return value


def _check_range(data, start, size, label):
    if start < 0 or size < 0 or start + size > len(data):
        raise ValueError("Truncated J3D " + label)


def _mul(left, right):
    """Multiply two row-major affine 3x4 matrices."""
    return [[sum(left[r][k] * right[k][c] for k in range(3)) +
             (left[r][3] if c == 3 else 0.0) for c in range(4)]
            for r in range(3)]


def _envelopes(block, joint_count):
    count = _u16(block, 8)
    if count == 0:
        return [], []
    counts_at = _u32(block, 12)
    indices_at = _u32(block, 16)
    weights_at = _u32(block, 20)
    inverse_at = _u32(block, 24)
    if min(counts_at, indices_at, weights_at, inverse_at) < 28:
        raise ValueError('Invalid EVP1 table offset')
    _check_range(block, counts_at, count, "envelope counts")
    counts = list(block[counts_at:counts_at + count])
    total = sum(counts)
    _check_range(block, indices_at, total * 2, "envelope indices")
    _check_range(block, weights_at, total * 4, "envelope weights")
    _check_range(block, inverse_at, joint_count * 48, "joint inverse matrices")
    result = []
    cursor = 0
    for influence_count in counts:
        if influence_count == 0:
            raise ValueError("Empty J3D envelope")
        influences = []
        weight_sum = 0.0
        for _ in range(influence_count):
            joint = _u16(block, indices_at + cursor * 2)
            if joint >= joint_count:
                raise ValueError('EVP1 joint reference out of range')
            weight = _f32(block, weights_at + cursor * 4)
            if weight < 0.0:
                raise ValueError("Negative J3D envelope weight")
            influences.append((joint, weight))
            weight_sum += weight
            cursor += 1
        if not math.isfinite(weight_sum) or abs(weight_sum - 1.0) > 1e-4:
            raise ValueError("J3D envelope weights are not normalized")
        result.append(influences)
    inverse = []
    for index in range(joint_count):
        values = [_f32(block, inverse_at + index * 48 + i * 4) for i in range(12)]
        inverse.append([values[0:4], values[4:8], values[8:12]])
    return result, inverse


def draw_matrices(model_blocks, pose=None):
    """Return the animated 3x4 matrix for every DRW1 draw entry.

    ``pose`` is the optional list of local animated joint matrices accepted by
    :func:`experimental.pikmin2_rigid.joint_matrices`. Each influence uses its
    authored EVP1 inverse matrix: sum(weight * animatedJoint * inverseJoint).
    This follows Pikmin 2 J3DMtxBuffer.cpp:376, not a reconstructed bind pose.
    """
    try:
        jnt = model_blocks["JNT1"]
        drw = model_blocks["DRW1"]
        evp = model_blocks["EVP1"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Missing J3D skinning block") from exc

    joint_count = _u16(jnt, 8)
    envelopes, inverse_joints = _envelopes(evp, joint_count)
    if pose is None:
        animated = joint_matrices(model_blocks)
    else:
        if len(pose) != joint_count:
            raise ValueError("Pose joint count does not match JNT1")
        if any(len(m) != 3 or any(len(row) != 4 or not all(math.isfinite(v) for v in row) for row in m) for m in pose):
            raise ValueError('Invalid animated joint matrix')
        animated = joint_matrices(model_blocks, local_overrides=pose)
    draw_count = _u16(drw, 8)
    flags_at = _u32(drw, 12)
    refs_at = _u32(drw, 16)
    if draw_count == 0 or min(flags_at, refs_at) < 20:
        raise ValueError('Invalid DRW1 table offset/count')
    _check_range(drw, flags_at, draw_count, "draw flags")
    _check_range(drw, refs_at, draw_count * 2, "draw references")
    result = []
    for draw in range(draw_count):
        kind = drw[flags_at + draw]
        ref = _u16(drw, refs_at + draw * 2)
        if kind == 0:
            if ref >= joint_count:
                raise ValueError("DRW1 joint reference out of range")
            result.append([row[:] for row in animated[ref]])
        elif kind == 1:
            if ref >= len(envelopes):
                raise ValueError("DRW1 envelope reference out of range")
            blended = [[0.0] * 4 for _ in range(3)]
            for joint, weight in envelopes[ref]:
                matrix = _mul(animated[joint], inverse_joints[joint])
                for r in range(3):
                    for c in range(4):
                        blended[r][c] += matrix[r][c] * weight
            result.append(blended)
        else:
            raise ValueError("Unsupported DRW1 matrix kind")
    if not all(math.isfinite(value) for matrix in result for row in matrix for value in row):
        raise ValueError('Nonfinite draw matrix')
    return result
