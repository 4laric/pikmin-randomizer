import struct
import unittest
from experimental.pikmin2_generator_pose import write_position,validate_position


class GeneratorPoseTests(unittest.TestCase):
    def test_native_effective_position_is_position_plus_offset(self):
        for position,yaw in [((-55,0,75),215),((75,0,-95),45),((1020,25,0),300)]:
            with self.subTest(position=position):
                row=bytearray(100)
                struct.pack_into('>6f',row,48,*position,0,yaw,0)
                with self.assertRaises(ValueError):validate_position(row,position)
                write_position(row,position)
                p=struct.unpack_from('>3f',row,48);offset=struct.unpack_from('>3f',row,60)
                self.assertEqual(tuple(a+b for a,b in zip(p,offset)),position)
                self.assertEqual(offset,(0,0,0))

    def test_nonfinite_and_wrong_position_rejected(self):
        row=bytearray(100)
        for pos in ([float('nan'),0,0],[0,float('inf'),0],[0,0]):
            with self.assertRaises(ValueError):write_position(row,pos)
        write_position(row,[1,2,3])
        with self.assertRaises(ValueError):validate_position(row,[1,3,3])


if __name__=='__main__':unittest.main()
