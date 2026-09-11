import copy
import unittest
from collections import Counter
from randomizer.seed import generate, validate, solo_rewards, spheres
from randomizer.campaign_data import CAMPAIGN_SLOTS
from randomizer.catalog import BESTIARY_TARGETS, bestiary_sources

class CampaignEnemyTests(unittest.TestCase):
    def test_layout_and_all_check_sweep(self):
        for seed in range(150):
            m=generate(str(seed),campaign_enemies=True,starting_area=('forest','navel','impact','spring','trial')[seed%5],starting_color=('red','yellow','blue')[(seed//5)%3],starting_flarlic=1,permanent_checks=bool(seed%2),randomize_color_stats=True,progressive_color_stats=True)
            actual={a['uid']:a['actual'] for a in m['campaign_layout']['assignments']}
            self.assertEqual(len(actual),72)
            for r in CAMPAIGN_SLOTS:self.assertIn(actual[r['uid']],r['miniboss_allowed'])
            for stage in range(4):self.assertTrue(any(actual[r['uid']]!=r['original'] for r in CAMPAIGN_SLOTS if r['stage']==stage))
            for stage in (1,2,3):self.assertEqual(sum(actual[r['uid']] in (9,17,24) for r in CAMPAIGN_SLOTS if r['stage']==stage),1)
            for r in CAMPAIGN_SLOTS:
                if actual[r['uid']] in (9,17,24):self.assertTrue(r['expires_after_day'] is None or r['expires_after_day']>=29)
            self.assertEqual(len({actual[r['uid']] for r in CAMPAIGN_SLOTS if r['stage']==0}),1)
            self.assertFalse(any(r['stage']==4 for r in CAMPAIGN_SLOTS))
            self.assertTrue(all(bestiary_sources(n,m) for n in BESTIARY_TARGETS))
            self.assertEqual(sum(map(len,spheres(solo_rewards(m),m))),len(m['locations']))

    def test_strict_layout_and_legacy(self):
        m=generate('strict',campaign_enemies=True)
        for key,value in (('actual',22),('uid',0)):
            bad=copy.deepcopy(m);bad['campaign_layout']['assignments'][0][key]=value
            with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(m);bad['enemy_layout']['sources'][0]['actual']=22
        with self.assertRaises(ValueError):validate(bad)
        legacy=generate('strict',miniboss_enemies=True)
        self.assertNotIn('campaign_layout',legacy)
        self.assertEqual(len(legacy['spawn_layout']['assignments']),15)
        self.assertEqual(m,generate('strict',campaign_enemies=True,per_spawn_enemies=True,group_spawn_enemies=True,enemy_shuffle=True))
