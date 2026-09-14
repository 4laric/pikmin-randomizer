import unittest
from scripts.test_pikmin2_mamuta_native import validate

GOOD='''P2_MAMUTA_FIXTURE_BIRTH id=221001 type=24 xyz=-150.000,30.000,1850.000 control=221002
P2_MAMUTA_DRAW generator=221001 anchor=wait poses=3 animated=1
PASS P2_MAMUTA_RUNTIME identity control reset P1_proxy_static_anchors
'''
class MamutaRuntimeTests(unittest.TestCase):
    def test_honest_scope(self):
        result=validate(GOOD)
        self.assertFalse(result['planting_verified'])
        self.assertFalse(result['corpse_verified'])
    def test_missing_corrupt_or_incomplete_evidence(self):
        for text in (GOOD.replace('anchor=wait','anchor=attack1'),GOOD.replace('30.000','0.000'),GOOD.replace('type=24','type=3'),GOOD+'[PC GX] DESYNC',GOOD.replace('PASS','FAIL')):
            with self.assertRaises(ValueError):validate(text)
