import unittest
from experimental.pikmin2_beasts_transfer import transfer_party,checkpoint_payload
from tests import test_pikmin2_beasts_witness_bridge as fixtures
from tests.test_pikmin2_beasts_boundary import bound
from tests.test_pikmin2_beasts_generation import plan


class TransferTests(unittest.TestCase):
    def test_native_species_health_and_edge(self):
        token='a'*64
        text=f'P2_BEASTS_TRANSFER_1\n{token}\n2 3 0.625 2\n1 2\n3 1\n'
        self.assertEqual(transfer_party(text,token),dict(health=.625,squad=[dict(species='red',maturity=2),dict(species='purple',maturity=1)]))
        self.assertEqual(transfer_party(f'P2_BEASTS_TRANSFER_1\n{token}\n2 3 0 0\n',token),dict(health=0,squad=[]))
        for old,new in [('2 3 0.625','2 2 0.625'),('2 3 0.625','1 3 0.625'),
                        ('0.625','nan'),('0.625','0'),('1 2','1 3'),('0.625 2','0.625 3'),
                        ('P2_BEASTS_TRANSFER_1','P2_CAVE_TRANSFER_1'),('a'*64,'b'*64)]:
            with self.subTest(old=old),self.assertRaises(ValueError):transfer_party(text.replace(old,new),token)
    def test_bound_hole_payload(self):
        fixture=fixtures.BridgeTests();fixture.setUp();token=fixture.adapter.token(fixture.second)
        log=bound(fixtures.native_trace(),token).replace('P2_BEASTS_PARTY health=',
            'P2_BEASTS_EXIT_REMOTE_REJECTED\nP2_BEASTS_EXIT_TRANSFER_WRITTEN\nP2_BEASTS_PARTY health=',1)
        text=f'P2_BEASTS_TRANSFER_1\n{token}\n2 3 0.875 20\n'+''.join(f'{1 if i<10 else 3} {i%3}\n' for i in range(20))
        payload=checkpoint_payload(fixture.adapter,fixture.second,log,plan(19),text)
        third=fixture.adapter.apply(fixture.second,token,**payload)
        self.assertEqual(third['floor'],3)
        for bad in (text.replace('0.875','1'),text.replace('3 1','1 1')):
            with self.assertRaises(ValueError):checkpoint_payload(fixture.adapter,fixture.second,log,plan(19),bad)
        with self.assertRaises(ValueError):checkpoint_payload(fixture.adapter,fixture.second,log.replace('P2_BEASTS_EXIT_REMOTE_REJECTED','missing'),plan(19),text)
