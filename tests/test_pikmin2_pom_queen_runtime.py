"""Tests for experimental/pikmin2_pom_queen_runtime.py (#448)."""
import unittest

from experimental import pikmin2_pom_queen_runtime as qr

PASS_TEXT = (
    'P2_POM_READY generator=240013 species=RandPom source_id=8 colour=0 budget=1 queen=1 engine=1 x=-25.00 y=30.00 z=1850.00\n'
    'P2_POM_INVULNERABLE generator=240013 invulnerable_after_landing=1\n'
    'P2_POM_QUEEN_COLOUR generator=240013 colour=1 met=7\n'
    'P2_POM_QUEEN_COLOUR generator=240013 colour=2 met=7\n'
    'P2_CANDYPOP_WITNESS generator=240013 species=RandPom input=red refund=0\n'
    'P2_CANDYPOP_CONVERT generator=240013 species=RandPom converted=1 used=1 refunds=0\n'
    'P2_CANDYPOP_SPROUTS generator=240013 species=RandPom sprouts=9 multiplier=9\n'
    'P2_POM_QUEEN_STATE initial=2 sprouts=9 alive=1\n'
    'PASS P2_POM_QUEEN cycle_and_multiplier\n'
)


class ProtocolTests(unittest.TestCase):
    def test_sidecar(self):
        self.assertEqual(qr.queen_sidecar().decode('ascii'), 'P2_POM_1 1\n240013 RandPom -25.0 30.0 1790.0\n')

    def test_validate_pass(self):
        good = qr.validate(PASS_TEXT, 0)
        self.assertTrue(good['passed'], good['failed'])
        self.assertEqual(good['cycle_colours'], ['1', '2'])

    def test_validate_requires_cycle(self):
        single = PASS_TEXT.replace('P2_POM_QUEEN_COLOUR generator=240013 colour=1 met=7\n', '')
        self.assertFalse(qr.validate(single, 0)['passed'])

    def test_validate_requires_multiplier(self):
        wrong = PASS_TEXT.replace('sprouts=9 multiplier=9', 'sprouts=1 multiplier=9')
        self.assertFalse(qr.validate(wrong, 0)['passed'])
        lost = PASS_TEXT.replace('P2_CANDYPOP_SPROUTS generator=240013 species=RandPom sprouts=9 multiplier=9\n', '')
        self.assertFalse(qr.validate(lost, 0)['passed'])

    def test_validate_requires_conversion_and_completion(self):
        corrupted = PASS_TEXT.replace('converted=1 used=1 refunds=0', 'converted=0 used=0 refunds=0')
        self.assertFalse(qr.validate(corrupted, 0)['passed'])
        self.assertFalse(qr.validate(PASS_TEXT, 1)['passed'])

    def test_instrument_replaces_room_app(self):
        source = 'prefix\nclass RoomApp : public PlugPikiApp {\n int idle() override { return 0; }\n};\nint main(int, char**) { return 0; }\n'
        out = qr.instrument(source)
        self.assertIn('PASS P2_POM_QUEEN', out)
        self.assertIn('int main(', out)


if __name__ == '__main__':
    unittest.main()
