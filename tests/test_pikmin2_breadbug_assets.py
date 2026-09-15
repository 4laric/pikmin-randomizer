import unittest
from experimental.pikmin2_breadbug_assets import parameter_blocks,collision_nodes,target_allowed,carry_strength
class BreadbugAssetsTests(unittest.TestCase):
    def test_parameter_duplicate_keys_remain_block_scoped(self):
        raw=b'{\n {ip01} 4 0\n {_eof}\n}\n{\n {ip01} 4 11\n {_eof}\n}'
        self.assertEqual(parameter_blocks(raw),[{'ip01':0},{'ip01':11}])
        with self.assertRaises(ValueError):parameter_blocks(b'{ {ip01} 4 1 {ip01} 4 2 {_eof} }')
    def test_collision_tree_preserves_joint_ids_and_radii(self):
        raw=b'1 30 {none} {____} 0 0 0 6 0 { 0 15 {body} {____} 0 0 0 6 0 }'
        nodes=collision_nodes(raw,7);self.assertEqual(nodes[1]['parent'],0);self.assertEqual(nodes[1]['radius'],15)
        for bad in (raw+b' 0',raw[:-1]):
            with self.assertRaises(ValueError):collision_nodes(bad,7)
        with self.assertRaises(ValueError):collision_nodes(raw,6)
    def test_source_thresholds_not_shared_size_rule(self):
        self.assertTrue(target_allowed('PanModoki',10,11));self.assertFalse(target_allowed('PanModoki',11,11))
        self.assertTrue(target_allowed('OoPanModoki',1,1))
        with self.assertRaises(ValueError):target_allowed('PanHouse',1,1)
        self.assertEqual(carry_strength(1,2),1.5)
        with self.assertRaises(ValueError):carry_strength(5,1)
