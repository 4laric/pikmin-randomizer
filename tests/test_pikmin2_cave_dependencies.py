import unittest
from experimental.pikmin2_cave_dependencies import enemy_registry,closure,floor_dependencies


def registry():
    return enemy_registry('''
{"Parent", EnemyTypeID::EnemyID_Parent, -1, 1, (EFlag_UseOwnID), "", "", "", "", "", "", "", -1, 0, BDT_Empty},
{"Helper", EnemyTypeID::EnemyID_Helper, -1, 1, (EFlag_CanBeSpawned | EFlag_HasNoInfo), "", "", "", "", "", "", "", -1, 0, BDT_Empty},
{"Variant", EnemyTypeID::EnemyID_Variant, EnemyTypeID::EnemyID_Parent, 1, (EFlag_CanBeSpawned), "Parent", "Parent", "Parent", "", "", "Parent", "Parent", EnemyTypeID::EnemyID_Helper, 1, BDT_Normal},
''')


class CaveDependenciesTests(unittest.TestCase):
    def test_alias_parent_helper_closure_and_nonspawnable(self):
        r=registry();rows={x['enemy_id']:x for x in closure(['Variant'],r)}
        self.assertEqual(set(rows),{'Variant','Parent','Helper'})
        self.assertEqual(rows['Variant']['resource_families']['texture'],'Variant')
        self.assertEqual(rows['Variant']['resource_families']['model'],'Parent')
        self.assertEqual(rows['Parent']['dependency_roles'],['parent_manager'])
        self.assertTrue(rows['Helper']['can_spawn']);self.assertTrue(rows['Helper']['has_no_info'])
        with self.assertRaises(ValueError):closure(['Parent'],r)
        with self.assertRaises(ValueError):closure(['Missing'],r)
        # Cyclic manager references terminate without dropping reasons.
        r['Parent']['helpers']=['Variant']
        self.assertEqual(len(closure(['Variant'],r)),3)

    def test_caps_and_held_cargo_have_stable_definition_identity(self):
        floor=dict(definition_index=0,first_floor=1,last_floor=2,parameters={'f008':'pool','f007':'1'},
                   enemies=[dict(enemy_id='Variant',carried_treasure='gem')],
                   caps=[dict(empty=True),dict(empty=False,enemy=dict(enemy_id='Helper',carried_treasure='gem'))],
                   treasures=[dict(treasure_id='gem')],gates=[dict(gate_id='gate')])
        cargo={'gem':dict(archive='gem.szs')};pools={'pool':dict(units=[dict(name='room')])}
        result=floor_dependencies('test',floor,registry(),cargo,pools)
        self.assertEqual(result,floor_dependencies('test',floor,registry(),cargo,pools))
        self.assertEqual(result['cargo'][0]['required_by'],['test:definition0:cap_enemy:1:held','test:definition0:enemy:0:held','test:definition0:treasure:0'])
        self.assertEqual(len(result['definitions']),4)
        self.assertFalse(result['selected_placements']);self.assertTrue(result['fixtures']['has_geyser'])
        with self.assertRaises(ValueError):floor_dependencies('test',floor,registry(),{},pools)
        with self.assertRaises(ValueError):floor_dependencies('test',floor,registry(),cargo,{})

    def test_malformed_registry_fails_closed(self):
        with self.assertRaises(ValueError):enemy_registry('unrecognized source format')
        with self.assertRaises(ValueError):enemy_registry('{"X", EnemyTypeID::EnemyID_X, -1, 1, (EFlag_CanBeSpawned), "bad"},')
