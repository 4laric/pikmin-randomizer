import copy, unittest
from collections import Counter
from randomizer.enemies import resolve_layout, sources_for
from randomizer.seed import generate, validate, fingerprint, solo_rewards, spheres
from randomizer.catalog import *

class EnemyLayoutTests(unittest.TestCase):
    def manifest(self, mask):
        m=generate('layout',collection_checks=True,starting_flarlic=1)
        m['enemy_mask']=mask; m['enemy_shuffle']='families-v1' if mask else 'none'
        m['enemy_layout']=resolve_layout(mask); validate(m); return m
    def test_all_masks_and_fills(self):
        fingerprints=set()
        for mask in range(8):
            m=self.manifest(mask); fingerprints.add(fingerprint(m))
            for name in BESTIARY_TARGETS: self.assertTrue(bestiary_sources(name,m))
            self.assertEqual(sum(map(len,spheres(solo_rewards(m),m))),59)
        self.assertEqual(len(fingerprints),8)
    def test_swapped_adults_and_protected_survivors(self):
        colors={RED:1,BLUE:1,YELLOW:1}
        base=self.manifest(0); swapped=self.manifest(3)
        adult='Bestiary: Deliver Spotty Bulborb'; bear='Bestiary: Deliver Spotty Bulbear'
        self.assertTrue(can_reach_manifest(adult,colors,base))
        self.assertFalse(can_reach_manifest(adult,colors,swapped))
        self.assertTrue(can_reach_manifest(adult,{**colors,SPRING_ACCESS:1},swapped))
        self.assertFalse(can_reach_manifest(bear,colors,base))
        self.assertTrue(can_reach_manifest(bear,colors,swapped))
        self.assertTrue(can_reach_manifest('Bestiary: Deliver Dwarf Bulborb',colors,swapped))
        self.assertEqual({r['stage'] for r in sources_for(swapped['enemy_layout'],3)}, {1,3})
        self.assertEqual(min(r['first_day'] for r in sources_for(base['enemy_layout'],31)),16)
        self.assertEqual(min(r['first_day'] for r in sources_for(swapped['enemy_layout'],31)),1)
    def test_protected_male_and_scheduled_alternatives(self):
        m=self.manifest(4)
        self.assertIn(2,{r['stage'] for r in sources_for(m['enemy_layout'],19)})
        self.assertNotIn(2,{r['stage'] for r in sources_for(m['enemy_layout'],18)})
        self.assertEqual({r['stage'] for r in sources_for(m['enemy_layout'],11)},{1,3})
        self.assertEqual({r['stage'] for r in sources_for(m['enemy_layout'],25)},{1,3})
        self.assertEqual({r['stage'] for r in sources_for(m['enemy_layout'],13)},{0})
        self.assertTrue(all(not r['protected'] for r in sources_for(m['enemy_layout'],13)))
    def test_tampering_and_old_manifest(self):
        m=self.manifest(1)
        for mutate in (lambda x:x['enemy_layout']['sources'].pop(),
                       lambda x:x['enemy_layout']['sources'][0].update(actual=0),
                       lambda x:x['enemy_layout'].update(version='unknown'),
                       lambda x:x.update(enemy_mask=2)):
            bad=copy.deepcopy(m); mutate(bad)
            with self.assertRaises(ValueError): validate(bad)
        old=copy.deepcopy(m); old.pop('enemy_layout'); validate(old)
    def test_color_and_carrier_rules(self):
        m=self.manifest(0); colors={RED:1,BLUE:1,YELLOW:1}
        name='Bestiary: Deliver Armored Cannon Beetle'
        self.assertFalse(can_reach_manifest(name,colors,m))
        self.assertTrue(can_reach_manifest(name,{**colors,FLARLIC:2},m))
        self.assertFalse(can_reach_manifest(name,{RED:1,FLARLIC:9},m))
