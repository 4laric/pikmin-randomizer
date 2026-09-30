"""J3D Maya scale-compensate joints in experimental.pikmin2_rigid.joint_matrices (#996).

Source: JSystem J3DJoint.cpp J3DMtxCalcCalcTransformMaya::calcTransform. A joint
whose JNT1 scale-compensate byte is 1 divides the parent's local scale back out
of its own basis (rows of the 3x3), keeping the parent's scale on its
translation. Skitter Leaf (Sokkuri) appear1 frame 0 scales the body to ~0 while
the leaf joints keep full size; ignoring the flag collapsed the leaf.
"""
import struct
import unittest

from experimental.pikmin2_rigid import joint_matrices


def model(maya, compensate):
    jnt = bytearray(12 + 4 + 4 + 2 * 64)
    struct.pack_into('>H', jnt, 8, 2)
    struct.pack_into('>I', jnt, 12, 20)
    struct.pack_into('>I', jnt, 16, 0)
    for i, comp in enumerate((0, compensate)):
        at = 20 + 64 * i
        struct.pack_into('>HB', jnt, at, 1, comp)
        struct.pack_into('>3f', jnt, at + 4, 1.0, 1.0, 1.0)
    inf = bytearray(24 + 5 * 4)
    struct.pack_into('>H', inf, 8, 2 if maya else 0)
    struct.pack_into('>I', inf, 20, 24)
    at = 24
    for kind, index in ((0x10, 0), (1, 0), (0x10, 1), (2, 0), (0, 0)):
        struct.pack_into('>HH', inf, at, kind, index)
        at += 4
    return {'JNT1': bytes(jnt), 'INF1': bytes(inf)}


def pose(root_scale):
    root = [[root_scale, 0, 0, 0], [0, root_scale, 0, 0], [0, 0, root_scale, 0]]
    child = [[1, 0, 0, 10], [0, 1, 0, 0], [0, 0, 1, 0]]
    return [root, child]


class RigidScaleCompensate(unittest.TestCase):
    def test_maya_compensate_keeps_child_unscaled(self):
        world = joint_matrices(model(True, 1), pose(0.01))
        self.assertAlmostEqual(world[1][0][0], 1.0, places=5)
        self.assertAlmostEqual(world[1][1][1], 1.0, places=5)
        self.assertAlmostEqual(world[1][2][2], 1.0, places=5)
        # The parent's scale still applies to the child's translation.
        self.assertAlmostEqual(world[1][0][3], 0.1, places=5)

    def test_uncompensated_child_inherits_parent_scale(self):
        world = joint_matrices(model(True, 0), pose(0.01))
        self.assertAlmostEqual(world[1][0][0], 0.01, places=6)
        self.assertAlmostEqual(world[1][0][3], 0.1, places=5)

    def test_non_maya_models_are_unchanged(self):
        world = joint_matrices(model(False, 1), pose(0.01))
        self.assertAlmostEqual(world[1][0][0], 0.01, places=6)

    def test_unit_scale_is_identity_either_way(self):
        a = joint_matrices(model(True, 1), pose(1.0))
        b = joint_matrices(model(True, 0), pose(1.0))
        self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main()
