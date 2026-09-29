import copy
import tempfile
import unittest
from collections import Counter
from randomizer.benefits import BENEFIT_ITEMS, FLOWERS, MATURITY, DAY_LENGTH, benefit_state, benefit_lines
from randomizer.catalog import item_pool, REPAIR, ITEM_IDS, ITEM_BASE, can_reach_manifest
from randomizer.seed import generate, validate, solo_rewards
from randomizer.session import Session
from randomizer.runner import NativeRun


class MaturityTests(unittest.TestCase):
    def test_maturity_replaces_flower_shower(self):
        for permanent in (False, True):
            m = generate('mat', 'ap', collection_checks=True, permanent_checks=permanent, combined_captain=True, bomb_rock_weight=1, progressive_maturity=True)
            validate(m)
            pool = Counter(item_pool(m))
            self.assertEqual(pool[FLOWERS], 0)
            self.assertEqual([pool[n] for n in MATURITY.values()], [2, 2, 2])
            self.assertEqual(pool[REPAIR], 30)
            self.assertEqual(sum(pool.values()), len(m['locations']))
            self.assertIn('progressive-maturity-v1', m['capabilities'])
            for name in m['locations']:
                self.assertEqual(can_reach_manifest(name, {}, m), can_reach_manifest(name, {n: 2 for n in MATURITY.values()}, m))

    def test_legacy_manifests_unchanged(self):
        old = generate('mat', 'ap', collection_checks=True, combined_captain=True)
        self.assertNotIn('progressive_maturity', old)
        self.assertGreater(Counter(item_pool(old))[FLOWERS], 0)
        self.assertFalse(set(item_pool(old)) & set(MATURITY.values()))
        # Existing item IDs are stable; new items are appended.
        self.assertEqual(ITEM_IDS[FLOWERS], ITEM_BASE + 31)
        self.assertEqual([ITEM_IDS[n] for n in (*MATURITY.values(), DAY_LENGTH)], [ITEM_BASE + i for i in range(40, 44)])

    def test_validation(self):
        m = generate('mat', 'ap', collection_checks=True, combined_captain=True, progressive_maturity=True, progressive_day_length=3)
        for key, value in (('progressive_maturity', False), ('progressive_day_length', 0), ('progressive_day_length', 11),
                           ('day_length_step', 7), ('day_length_step', 5), ('day_length_step', 105)):
            bad = copy.deepcopy(m); bad[key] = value
            with self.assertRaises(ValueError): validate(bad)
        for cap in ('progressive-maturity-v1', 'progressive-day-length-v1'):
            bad = copy.deepcopy(m); bad['capabilities'].remove(cap)
            with self.assertRaises(ValueError): validate(bad)
        bad = copy.deepcopy(m); bad.pop('day_length_step')
        with self.assertRaises(ValueError): validate(bad)
        with self.assertRaises(ValueError): generate('x', progressive_day_length=11)
        with self.assertRaises(ValueError): generate('x', progressive_day_length=1, day_length_step=12)

    def test_protocol_and_replay(self):
        m = generate('mat', 'ap', collection_checks=True, combined_captain=True, progressive_maturity=True, progressive_day_length=2, day_length_step=50)
        with tempfile.TemporaryDirectory() as d:
            s = Session(m, d); s.bind_ap('room', 0, 1)
            ids = [ITEM_IDS[MATURITY['red']], ITEM_IDS[MATURITY['blue']], ITEM_IDS[MATURITY['blue']], ITEM_IDS[MATURITY['blue']], ITEM_IDS[DAY_LENGTH]]
            s.receive(0, ids); s.receive(0, ids)
            r = NativeRun(s)
            bootstrap = r.bootstrap.read_text()
            self.assertIn('MATURITY 1\nDAY_LENGTH 2 50\n', bootstrap)
            state = s.native_state(r.token, True)
            # Blue, red, yellow; tiers cap at 2. Day length caps at the seed's count.
            self.assertIn(' MATURITY 2 1 0 DAYLENGTH 1 END', state)
            s.receive(len(ids), [ITEM_IDS[DAY_LENGTH]] * 3)
            self.assertIn(' DAYLENGTH 2 END', s.native_state(r.token, True))
            self.assertIn('DAY LENGTH 200%  (2/2)', benefit_lines(m, s.inventory))
            (r.directory / 'checks.txt').write_text('0\n')
            restored = Session(m, d)  # bootstrap field count must still match
            self.assertEqual(restored.inventory, s.inventory)

    def test_day_length_fits_smallest_check_set(self):
        m = generate('day', 'solo', collection_checks=True, combined_captain=True, progressive_maturity=True, progressive_day_length=8)
        self.assertEqual(Counter(solo_rewards(m).values())[DAY_LENGTH], 8)
        big = generate('day', 'solo', permanent_checks=True, combined_captain=True, progressive_maturity=True, progressive_day_length=10)
        self.assertEqual(Counter(solo_rewards(big).values())[DAY_LENGTH], 10)
        self.assertIn(DAY_LENGTH, BENEFIT_ITEMS + tuple(ITEM_IDS))


if __name__ == '__main__':
    unittest.main()
