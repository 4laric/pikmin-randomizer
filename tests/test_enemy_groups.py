import copy, unittest
from randomizer.seed import generate, validate, solo_rewards, spheres
from randomizer.enemy_slots import resolve_group_layout
from randomizer.spawn_data import GROUP_SLOTS
from randomizer.catalog import BESTIARY_TARGETS, bestiary_sources

class EnemyGroupTests(unittest.TestCase):
    def test_coverage_and_all_checks(self):
        choices=set()
        for seed in range(100):
            layout=resolve_group_layout(seed,'Player1');choices.add(tuple(r['actual'] for r in layout['assignments']))
            self.assertEqual(layout,resolve_group_layout(seed,'Player1'))
            m=generate(seed,group_spawn_enemies=True,starting_area=('impact','forest','navel','spring','trial')[seed%5],starting_color=('red','yellow','blue')[seed%3],starting_flarlic=1,permanent_checks=bool(seed%2),randomize_color_stats=True,progressive_color_stats=True)
            self.assertEqual(sum(map(len,spheres(solo_rewards(m),m))),len(m['locations']))
            for name in BESTIARY_TARGETS:self.assertTrue(bestiary_sources(name,m))
            for pair in ((3,31),(18,19)):
                early={a['actual'] for r,a in zip(GROUP_SLOTS,layout['assignments']) if r['stage']==1 and r['first_day']==2 and r['original'] in pair}
                self.assertEqual(early,set(pair))
            self.assertTrue(all(r['first_day']==16 for r in m['enemy_layout']['sources'] if r['stage']==3 and r['original'] in (3,31) and not r['protected']))
        self.assertGreater(len(choices),20)
    def test_legacy_and_tampering(self):
        adult=generate('same',per_spawn_enemies=True)
        group=generate('same',group_spawn_enemies=True)
        self.assertEqual(adult['spawn_layout'],group['spawn_layout'])
        self.assertNotIn('group_layout',adult)
        for mutate in (lambda m:m['group_layout']['assignments'].reverse(),lambda m:m['group_layout']['assignments'][0].update(actual=4),lambda m:m.pop('spawn_layout')):
            bad=copy.deepcopy(group);mutate(bad)
            with self.assertRaises(ValueError):validate(bad)
