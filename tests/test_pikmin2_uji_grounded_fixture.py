import unittest
import tempfile
import struct
from pathlib import Path
from experimental.pikmin2_uji_grounded_fixture import HOOK, instrument, validate, deterministic_births


class GroundedUjiTests(unittest.TestCase):
    def test_no_forced_death_or_relocation(self):
        self.assertNotIn('dieSoon',HOOK)
        self.assertNotRegex(HOOK,r'(mHealth|mStateID|mSRT\.t)\s*=(?!=)')
        self.assertIn('InteractAttack',HOOK);self.assertIn('born.y-y',HOOK)
        with self.assertRaises(ValueError):instrument('changed')

    def test_private_circle_override(self):
        block=b'cric0.0v'+bytes(12)+b'p00\x04'+struct.pack('>f',50)+b'\xff'*4
        row=bytearray(b'    0.0v'+bytes(72)+block)
        struct.pack_into('<I',row,8,61000)
        header=bytearray(b'1.0v'+bytes(20));struct.pack_into('>I',header,20,1)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'default.gen';original=bytes(header+row);p.write_bytes(original)
            report=deterministic_births(p,{61000})
            self.assertEqual(report['generator_ids'],[61000]);self.assertNotEqual(report['before_sha256'],report['after_sha256'])
            expected=original.replace(block,block[:24]+bytes(4)+block[28:])
            self.assertEqual(p.read_bytes(),expected)
            with self.assertRaises(ValueError):deterministic_births(p,{61000})
            self.assertEqual(p.read_bytes(),expected)
            p.write_bytes(original)
            with self.assertRaises(ValueError):deterministic_births(p,{61001})
            self.assertEqual(p.read_bytes(),original)

    def test_credits_and_all_identity_gates(self):
        log='PASS grounded Uji:\n'
        for i in range(61000,61010):
            for marker in ('P2_UJI_BIRTH id=','P2_UJI_GROUNDED id=','P2_UJI_GROUNDED_HIT id=','P2_UJI_GROUNDED_CROSS id='):log+=marker+str(i)+'\n'
            log+=f'P2_POD_RECEIPT id=corpse:uji:{i} value={2 if i<61004 else 1} new=1\n'
        self.assertEqual(validate(log)['corpse_pokos'],14)
        with self.assertRaises(ValueError):validate(log.replace('P2_UJI_GROUNDED_CROSS id=61009','missing'))


if __name__=='__main__':unittest.main()
