import unittest
from experimental.pikmin2_violet_diagnostic import instrument, PROBE


class VioletDiagnosticTests(unittest.TestCase):
    def test_read_only_diagnostics_keep_input_driver(self):
        source='class RoomApp : public PlugPikiApp {\nif(!pc_p2_preview_ready() || !naviMgr || !pikiMgr || !tekiMgr)return result;\n        if(cargoCarryFixture(n))return result;'
        text=instrument(source)
        self.assertIn('VIOLET_DIAG flower=',text);self.assertIn('VIOLET_PIKI index=',text)
        for forbidden in ('transit(', 'throwPiki(', 'mP2Purple=', 'resetPosition(', 'setCurrentState('):self.assertNotIn(forbidden,PROBE)
        with self.assertRaises(ValueError):instrument('changed')


if __name__=='__main__':unittest.main()
