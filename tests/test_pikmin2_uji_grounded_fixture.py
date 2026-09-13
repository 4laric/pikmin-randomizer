import unittest
from experimental.pikmin2_uji_grounded_fixture import HOOK, instrument, validate


class GroundedUjiTests(unittest.TestCase):
    def test_no_forced_death_or_relocation(self):
        self.assertNotIn('dieSoon',HOOK)
        self.assertNotRegex(HOOK,r'(mHealth|mStateID|mSRT\.t)\s*=(?!=)')
        self.assertIn('InteractAttack',HOOK);self.assertIn('mSRT.t.y-y',HOOK)
        with self.assertRaises(ValueError):instrument('changed')

    def test_credits_and_all_identity_gates(self):
        log='PASS grounded Uji:\n'
        for i in range(61000,61010):
            for marker in ('P2_UJI_GROUNDED id=','P2_UJI_GROUNDED_HIT id=','P2_UJI_GROUNDED_CROSS id='):log+=marker+str(i)+'\n'
            log+=f'P2_POD_RECEIPT id=corpse:uji:{i} value={2 if i<61004 else 1} new=1\n'
        self.assertEqual(validate(log)['corpse_pokos'],14)
        with self.assertRaises(ValueError):validate(log.replace('P2_UJI_GROUNDED_CROSS id=61009','missing'))


if __name__=='__main__':unittest.main()
