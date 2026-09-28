import unittest
from experimental.pikmin2_tank_heap_diagnostic import system_probe,graphics_probe,once
class TankHeapProbeTests(unittest.TestCase):
    def test_exact_anchors_required(self):
        for s in ('','x x'):
            with self.assertRaises(ValueError):once(s,'x','y')
    def test_system_load_and_reset_preserved(self):
        raw='void reset(){mHeaps[heapIdx].reset(flag);}\nShape* StdSystem::loadShape(){addGfxObject(newInfo);}\nAnimData* StdSystem::findAnimation(){}'
        out=system_probe(raw)
        self.assertIn('addGfxObject(newInfo);',out);self.assertIn('tank_diag_register(result, modelPath, getHeapNum());',out)
        self.assertIn('tank_diag_reset(heapIdx);\n    mHeaps[heapIdx].reset(flag);',out)
    def test_draw_probe_preserves_submission(self):
        out=graphics_probe('GXCallDisplayList(list.mData, list.mDataLength);')
        self.assertIn('tank_diag_submit(model, list.mData, list.mDataLength);',out)
        self.assertEqual(out.count('GXCallDisplayList(list.mData, list.mDataLength);'),1)
    def test_changed_bytes_are_reported_without_causal_claim(self):
        from experimental.pikmin2_tank_heap_diagnostic import analyze_heap
        r=analyze_heap('TANK_HEAP_DRAW row=1 shape=abc list=def size=32 original=1234 now=5678 reset=1 name=test.mod\n[PC GX] DESYNC #1 bad')
        self.assertTrue(r['changed_draws'][0]['changed']);self.assertEqual(r['warnings'][0]['preceding_probe']['name'],'test.mod')
