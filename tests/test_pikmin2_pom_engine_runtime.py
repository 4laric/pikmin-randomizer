"""Tests for experimental/pikmin2_pom_engine_runtime.py (#448).

Protocol and validation checks always run; the real GL fixture is run by the
serialized lane harness, not here.
"""
import unittest

from experimental import pikmin2_pom_engine_runtime as er

SPECS = [dict(generator=er.REDPOM, species='RedPom', x=-25.0, y=30.0, z=1850.0),
         dict(generator=er.BLUEPOM, species='BluePom', x=25.0, y=30.0, z=1850.0),
         dict(generator=er.BASEPOM, species='Pom', x=0.0, y=30.0, z=1850.0)]

PASS_TEXT = (
    'P2_POM_READY generator=240011 species=RedPom source_id=4 colour=1 budget=5 queen=0 engine=1 x=-25.00 y=30.00 z=1850.00\n'
    'P2_POM_READY generator=240012 species=BluePom source_id=3 colour=0 budget=5 queen=0 engine=1 x=25.00 y=30.00 z=1850.00\n'
    'P2_POM_BASE_REJECTED generator=240013 species=Pom source_id=82 reason=nonspawnable_base\n'
    'P2_CANDYPOP_WITNESS generator=240011 species=RedPom input=red refund=1\n'
    'P2_CANDYPOP_WITNESS generator=240011 species=RedPom input=red refund=1\n'
    'P2_CANDYPOP_WITNESS generator=240011 species=RedPom input=blue refund=0\n'
    'P2_CANDYPOP_WITNESS generator=240011 species=RedPom input=blue refund=0\n'
    'P2_CANDYPOP_WITNESS generator=240011 species=RedPom input=blue refund=0\n'
    'P2_CANDYPOP_CONVERT generator=240011 species=RedPom converted=5 used=3 refunds=2\n'
    'P2_CANDYPOP_WITNESS generator=240012 species=BluePom input=blue refund=1\n'
    'P2_CANDYPOP_WITNESS generator=240012 species=BluePom input=blue refund=1\n'
    'P2_CANDYPOP_WITNESS generator=240012 species=BluePom input=red refund=0\n'
    'P2_CANDYPOP_WITNESS generator=240012 species=BluePom input=red refund=0\n'
    'P2_CANDYPOP_WITNESS generator=240012 species=BluePom input=red refund=0\n'
    'P2_CANDYPOP_CONVERT generator=240012 species=BluePom converted=5 used=3 refunds=2\n'
    'P2_POM_ENGINE_STATE initial=12 sprouts=10 alive=2\n'
    'PASS P2_POM_ENGINE real_conversion_refund_conservation\n'
)


class ProtocolTests(unittest.TestCase):
    def test_sidecar_round_trip(self):
        text = er.engine_sidecar(SPECS).decode('ascii')
        lines = text.splitlines()
        self.assertEqual(lines[0], 'P2_POM_1 3')
        self.assertEqual(lines[1], '240011 RedPom -25.0 30.0 1850.0')
        self.assertEqual(lines[2], '240012 BluePom 25.0 30.0 1850.0')
        self.assertEqual(lines[3], '240013 Pom 0.0 30.0 1850.0')

    def test_sidecar_rejections(self):
        def reject(specs):
            with self.assertRaises(ValueError):
                er.engine_sidecar(specs)
        reject([])
        reject(SPECS + [dict(SPECS[0])])                                      # duplicate generator
        reject([dict(SPECS[0], generator=1 << 32)])                           # id overflow
        reject([dict(SPECS[0], species='GreenPom')])                          # unknown species
        reject([dict(SPECS[0], x=float('nan'))])                              # non-finite position
        reject([dict(SPECS[0], z=100001)])                                    # position bound

    def test_validate_pass(self):
        good = er.validate(PASS_TEXT, 0)
        self.assertTrue(good['passed'], good['failed'])

    def test_validate_requires_refund_and_conservation(self):
        no_refund = PASS_TEXT.replace('P2_CANDYPOP_WITNESS generator=240011 species=RedPom input=red refund=1\n', '')
        self.assertFalse(er.validate(no_refund, 0)['passed'])
        # Overwriting an own-colour refund with a used slot breaks the batch total.
        swapped = PASS_TEXT.replace('P2_CANDYPOP_WITNESS generator=240012 species=BluePom input=blue refund=1',
                                    'P2_CANDYPOP_WITNESS generator=240012 species=BluePom input=blue refund=0')
        self.assertFalse(er.validate(swapped, 0)['passed'])
        dropped = PASS_TEXT.replace('P2_POM_ENGINE_STATE initial=12 sprouts=10 alive=2\n', '')
        self.assertFalse(er.validate(dropped, 0)['passed'])
        lost = PASS_TEXT.replace('P2_POM_ENGINE_STATE initial=12 sprouts=10 alive=2',
                                 'P2_POM_ENGINE_STATE initial=12 sprouts=10 alive=0')
        self.assertFalse(er.validate(lost, 0)['passed'])

    def test_validate_requires_engine_binding_and_completion(self):
        legacy_ready = PASS_TEXT.replace('engine=1', 'engine=0')
        self.assertFalse(er.validate(legacy_ready, 0)['passed'])
        self.assertFalse(er.validate(PASS_TEXT, 1)['passed'])

    def test_instrument_replaces_room_app(self):
        source = 'prefix\nclass RoomApp : public PlugPikiApp {\n int idle() override { return 0; }\n};\nint main(int, char**) { return 0; }\n'
        out = er.instrument(source)
        self.assertIn('PASS P2_POM_ENGINE', out)
        self.assertIn('int main(', out)


if __name__ == '__main__':
    unittest.main()
