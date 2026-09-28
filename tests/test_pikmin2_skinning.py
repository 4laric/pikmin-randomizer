import math
import struct
from pathlib import Path

import pytest

from experimental.pikmin2_convert import blocks
from experimental.pikmin2_skinning import draw_matrices


def _block(tag, payload):
    data = bytearray(payload)
    data[:4] = tag.encode()
    struct.pack_into(">I", data, 4, len(data))
    return bytes(data)


def _synthetic(envelope_weights=(0.5, 0.5), flags=(0, 1), refs=(0, 0)):
    # Two-joint root/child hierarchy.  JNT1 records are the same layout read
    # by pikmin2_rigid.joint_matrices: scale at +4, rotation at +16, translate
    # at +24, with the record table at +24.
    j = bytearray(24 + 128)
    struct.pack_into(">H", j, 8, 2)
    struct.pack_into(">I", j, 12, 24)
    for index, tx in enumerate((10.0, 2.0)):
        at = 24 + index * 64
        struct.pack_into(">3f", j, at + 4, 1.0, 1.0, 1.0)
        struct.pack_into(">3h", j, at + 16, 0, 0, 0)
        struct.pack_into(">3f", j, at + 24, tx, 0.0, 0.0)

    # INF1: open, joint 0, open, joint 1, close, close, end.
    h = bytearray(24 + 28)
    struct.pack_into(">I", h, 20, 24)
    struct.pack_into(">HHHHHHHHHHHHHH", h, 24,
                     1, 0, 0x10, 0, 1, 0, 0x10, 1, 2, 0, 2, 0, 0, 0)

    inverse_at = 29 + len(envelope_weights) * 6
    e = bytearray(inverse_at + 96)
    struct.pack_into(">H", e, 8, 1)
    struct.pack_into(">4I", e, 12, 28, 29, 29 + len(envelope_weights) * 2,
                     inverse_at)
    e[28] = len(envelope_weights)
    for i, joint in enumerate((0, 1)):
        struct.pack_into(">H", e, 29 + i * 2, joint)
    for i, weight in enumerate(envelope_weights):
        struct.pack_into(">f", e, 29 + len(envelope_weights) * 2 + i * 4, weight)
    for i, tx in enumerate((-10, -12)):
        struct.pack_into(">12f", e, inverse_at+i*48,
                         1, 0, 0, tx, 0, 1, 0, 0, 0, 0, 1, 0)

    d = bytearray(20 + len(flags) + len(refs) * 2)
    struct.pack_into(">H", d, 8, len(flags))
    struct.pack_into(">II", d, 12, 20, 20 + len(flags))
    d[20:20 + len(flags)] = bytes(flags)
    for i, ref in enumerate(refs):
        struct.pack_into(">H", d, 20 + len(flags) + i * 2, ref)
    return {"JNT1": _block("JNT1", j), "INF1": _block("INF1", h),
            "EVP1": _block("EVP1", e), "DRW1": _block("DRW1", d)}


def test_mixed_rigid_and_weighted_bind_pose_are_identity_envelopes():
    result = draw_matrices(_synthetic())
    assert result[0][0][3] == pytest.approx(10.0)
    assert result[1][0][3] == pytest.approx(0.0)


def test_weighted_matrix_uses_animated_times_inverse_bind():
    model = _synthetic()
    pose = [
        [[1, 0, 0, 20], [0, 1, 0, 0], [0, 0, 1, 0]],
        [[1, 0, 0, 7], [0, 1, 0, 0], [0, 0, 1, 0]],
    ]
    result = draw_matrices(model, pose)
    # Joint corrections: 20-10=10 and 27-12=15, weighted equally.
    assert result[0][0][3] == pytest.approx(20.0)
    assert result[1][0][3] == pytest.approx(12.5)


def test_authored_inverse_is_per_joint_before_blending_with_rotation():
    model = _synthetic()
    # Rotate the animated root +90 degrees, keep child translated locally.
    pose = [[[0,-1,0,20],[1,0,0,0],[0,0,1,0]],
            [[1,0,0,7],[0,1,0,0],[0,0,1,0]]]
    result = draw_matrices(model, pose)[1]
    # world0*inv0 translation=(20,-10); world1*inv1=(20,-5).
    assert result[0] == pytest.approx([0,-1,0,20])
    assert result[1] == pytest.approx([1,0,0,-7.5])
    # Deliberately change ONLY joint1's authored inverse, proving it is read
    # from EVP1 and not regenerated from JNT1 or indexed by envelope0.
    evp = bytearray(model['EVP1'])
    inverse_at = struct.unpack_from('>I', evp, 24)[0]
    struct.pack_into('>f', evp, inverse_at+48+12, -20)
    model['EVP1'] = evp
    assert draw_matrices(model, pose)[1][1][3] == pytest.approx(-11.5)


@pytest.mark.parametrize("mutation", ("sum", "truncated", "index", "nan", "kind"))
def test_rejects_malformed_skinning_tables(mutation):
    model = _synthetic()
    if mutation == "sum":
        model["EVP1"] = bytearray(model["EVP1"])
        struct.pack_into(">f", model["EVP1"], 39, 0.25)
    elif mutation == "truncated":
        model["EVP1"] = model["EVP1"][:-1]
    elif mutation == "index":
        model["EVP1"] = bytearray(model["EVP1"])
        struct.pack_into(">H", model["EVP1"], 29, 99)
    elif mutation == "nan":
        model["EVP1"] = bytearray(model["EVP1"])
        struct.pack_into(">I", model["EVP1"], 33, 0x7FC00000)
    else:
        model["DRW1"] = bytearray(model["DRW1"])
        model["DRW1"][20] = 2
    with pytest.raises(ValueError):
        draw_matrices(model)


def test_groink_model_has_weighted_draw_entries_and_valid_bind_table():
    source = Path("../groink-assets-02/MiniHoudai/enemy.bmd")
    if not source.exists():
        pytest.skip("Requires local Groink asset extraction")
    result = draw_matrices(blocks(source.read_bytes()))
    assert len(result) == 30
    assert all(len(row) == 3 and len(row[0]) == 4 for row in result)
    assert all(math.isfinite(value) for matrix in result for row in matrix for value in row)
