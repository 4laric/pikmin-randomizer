import unittest
from experimental.pikmin2_floor2_fixture import instrument, validate


class FloorTwoFixtureTests(unittest.TestCase):
    def test_framing_and_no_direct_conversion(self):
        source='class RoomApp : public PlugPikiApp {\nif(!pc_p2_preview_ready() || !naviMgr || !pikiMgr || !tekiMgr)return result;\n        if(cargoCarryFixture(n))return result;'
        result=instrument(source)
        self.assertIn('pc_p2_preview_cargo_free_ready()',result)
        self.assertIn('n->throwPiki',result)
        self.assertNotIn('pc_p2_convert_violet(',result)
        self.assertNotIn('mP2Purple=true',result)
        with self.assertRaises(ValueError):instrument('changed')

    def test_evidence_rejects_rewards_and_missing_conversion(self):
        good='P2_ROOM_CARGO_FREE_READY cargo=0\nP2_PURPLE_READY\nPASS floor2 cargo-free:'
        self.assertEqual(validate(good)['pokos'],0)
        for bad in (good+'P2_POD_RECEIPT',good.replace('PASS floor2 cargo-free:','')):
            with self.assertRaises(ValueError):validate(bad)


if __name__=='__main__':unittest.main()
