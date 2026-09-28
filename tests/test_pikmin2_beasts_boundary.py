import unittest
from experimental.pikmin2_beasts_boundary import boundary_text,validate_boundary
from experimental.pikmin2_beasts_witness_bridge import bound_checkpoint_witnesses
from tests import test_pikmin2_beasts_witness_bridge as bridge_fixture
from tests.test_pikmin2_beasts_witness_bridge import native_trace
from tests.test_pikmin2_beasts_generation import plan


def bound(log,token):
    return f'P2_BEASTS_BOUNDARY_BEGIN token={token}\n'+log.replace('PASS P2_BEASTS_',f'P2_BEASTS_BOUNDARY_END token={token}\nPASS P2_BEASTS_',1)


class BoundaryTests(unittest.TestCase):
    def test_token_validation(self):
        self.assertEqual(boundary_text('a'*64),'P2_BEASTS_BOUNDARY_1\n'+'a'*64+'\n')
        for token in (None,1,'a'*63,'A'*64,'a'*64+'\n'):
            with self.subTest(token=token),self.assertRaises(ValueError):boundary_text(token)
    def test_binding_and_wrong_missing_duplicate_reordered_markers(self):
        token='a'*64;log=bound(native_trace(),token)
        validate_boundary(log,token)
        first=log.splitlines()[0]+'\n'
        for bad in (native_trace(),log.replace(token,'b'*64),log+first,log.replace(first,'')+first):
            with self.subTest(log=bad),self.assertRaises(ValueError):validate_boundary(bad,token)
    def test_checkpoint_token_checked_before_mapping(self):
        fixture=bridge_fixture.BridgeTests();fixture.setUp()
        token=fixture.adapter.token(fixture.second)
        result=bound_checkpoint_witnesses(fixture.adapter,fixture.second,bound(native_trace(),token),plan(19))
        self.assertTrue(result['native_boundary_correlated'])
        self.assertFalse(result['native_handoff_authenticated'])
        with self.assertRaises(ValueError):bound_checkpoint_witnesses(fixture.adapter,fixture.second,bound(native_trace(),'b'*64),plan(19))
