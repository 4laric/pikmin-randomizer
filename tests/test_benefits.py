import copy
import tempfile
import unittest
from collections import Counter
from randomizer.benefits import BENEFIT_ITEMS, WHISTLE, PLUCK, DELIVERY, FLOWERS, HEAL
from randomizer.catalog import MODERN_LOCATION_IDS, modern_names, item_pool, REPAIR, ITEM_IDS, can_reach_manifest
from randomizer.seed import generate, validate, solo_rewards, spheres
from randomizer.session import Session
from randomizer.runner import NativeRun


class BenefitTests(unittest.TestCase):
    def test_pool_and_conservative_fill(self):
        for permanent in (False, True):
            for seed in range(20):
                m = generate(str(seed), collection_checks=True, permanent_checks=permanent,
                             progressive_color_stats=True, starting_area='random', starting_color='random', starting_flarlic=1)
                pool = Counter(item_pool(m))
                self.assertEqual(pool[REPAIR], 25)
                self.assertEqual((pool[WHISTLE], pool[PLUCK]), (2, 2))
                self.assertEqual(pool[HEAL], 0)
                self.assertTrue(all(pool[n] for n in (WHISTLE, PLUCK)))
                self.assertEqual(sum(pool.values()), len(m['locations']))
                rewards = solo_rewards(m)
                self.assertEqual(pool, Counter(rewards.values()))
                self.assertEqual(sum(map(len, spheres(rewards, m))), len(m['locations']))
                # Receiving benefits never invents farming or color access in logic.
                for name in m['locations']:
                    self.assertEqual(can_reach_manifest(name, {}, m), can_reach_manifest(name, {n: 10 for n in BENEFIT_ITEMS}, m))

    def test_legacy_pool_and_capability(self):
        m = generate('old', permanent_checks=True)
        old = copy.deepcopy(m); old.pop('benefit_items'); old['capabilities'].remove('benefit-items-v1')
        validate(old)
        self.assertGreater(item_pool(old).count(REPAIR), 25)
        self.assertFalse(set(item_pool(old)) & set(BENEFIT_ITEMS))
        bad = copy.deepcopy(m); bad['capabilities'].remove('benefit-items-v1')
        with self.assertRaises(ValueError): validate(bad)

    def test_receipt_replay_and_journal_recovery(self):
        m = generate('receipts', 'ap', permanent_checks=True)
        m.pop('compact_population'); m['capabilities'].remove('compact-population-v1')
        m['locations'] = {n: MODERN_LOCATION_IDS[n] for n in modern_names(True, True, True)}
        validate(m)
        with tempfile.TemporaryDirectory() as d:
            s = Session(m, d); s.bind_ap('room', 0, 1)
            ids = [ITEM_IDS[n] for n in (DELIVERY, FLOWERS, HEAL, WHISTLE, PLUCK)]
            s.receive(0, ids); s.receive(0, ids)
            r = NativeRun(s)
            self.assertIn('BENEFITS 1\nEND', r.bootstrap.read_text())
            self.assertIn('BENEFITS 1 1 1 1 1 END', s.native_state(r.token, True))
            (r.directory / 'checks.txt').write_text('0\n')
            restored = Session(m, d)
            self.assertEqual(restored.inventory, s.inventory)
            self.assertEqual(restored.data['checked'], [s.names[0]])
            restored.receive(len(ids), [ITEM_IDS[WHISTLE]] * 3)
            self.assertIn('BENEFITS 1 1 1 2 1 END', restored.native_state(r.token, True))
