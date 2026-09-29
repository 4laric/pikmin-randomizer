import copy
import tempfile
import unittest
from collections import Counter
from randomizer.benefits import DAY_LENGTH, WHISTLE_PLUCK, benefit_lines
from randomizer.catalog import item_pool, REPAIR, ITEM_IDS, ITEM_BASE, can_reach_manifest
from randomizer.seed import generate, validate
from randomizer.session import Session
from randomizer.runner import NativeRun


class WhistlePluckItemTests(unittest.TestCase):
    def test_one_item_takes_a_filler_slot(self):
        for permanent in (False, True):
            m = generate('wp', 'ap', collection_checks=True, permanent_checks=permanent, combined_captain=True, progressive_maturity=True, whistle_pluck_item=True)
            validate(m)
            without = generate('wp', 'ap', collection_checks=True, permanent_checks=permanent, combined_captain=True, progressive_maturity=True)
            pool, base = Counter(item_pool(m)), Counter(item_pool(without))
            self.assertEqual(pool[WHISTLE_PLUCK], 1)
            self.assertEqual(pool[REPAIR], base[REPAIR])
            self.assertEqual(sum(pool.values()), len(m['locations']))
            self.assertEqual(sum(pool.values()), sum(base.values()))
            self.assertIn('whistle-pluck-item-v1', m['capabilities'])
            # Outside logic: nothing becomes reachable because of it.
            for name in m['locations']:
                self.assertEqual(can_reach_manifest(name, {}, m), can_reach_manifest(name, {WHISTLE_PLUCK: 1}, m))

    def test_older_manifests_unchanged(self):
        old = generate('wp', 'ap', collection_checks=True, combined_captain=True, progressive_maturity=True)
        self.assertNotIn('whistle_pluck_item', old)
        self.assertNotIn(WHISTLE_PLUCK, item_pool(old))
        # Appended after Progressive Day Length; existing IDs do not move.
        self.assertEqual(ITEM_IDS[DAY_LENGTH], ITEM_BASE + 43)
        self.assertEqual(ITEM_IDS[WHISTLE_PLUCK], ITEM_BASE + 44)

    def test_validation(self):
        m = generate('wp', 'ap', collection_checks=True, combined_captain=True, whistle_pluck_item=True)
        bad = copy.deepcopy(m); bad['whistle_pluck_item'] = False
        with self.assertRaises(ValueError): validate(bad)
        bad = copy.deepcopy(m); bad['capabilities'].remove('whistle-pluck-item-v1')
        with self.assertRaises(ValueError): validate(bad)
        with self.assertRaises(ValueError): generate('x', whistle_pluck_item=1)

    def test_protocol_and_replay(self):
        m = generate('wp', 'ap', collection_checks=True, combined_captain=True, progressive_maturity=True, progressive_day_length=2, whistle_pluck_item=True)
        with tempfile.TemporaryDirectory() as d:
            s = Session(m, d); s.bind_ap('room', 0, 1)
            r = NativeRun(s)
            self.assertIn('DAY_LENGTH 2 25\nWHISTLE_PLUCK 1\n', r.bootstrap.read_text())
            self.assertIn(' DAYLENGTH 0 WHISTLEPLUCK 0 END', s.native_state(r.token, True))
            self.assertIn('WHISTLE PLUCK LOCKED', benefit_lines(m, s.inventory))
            s.receive(0, [ITEM_IDS[WHISTLE_PLUCK]]); s.receive(0, [ITEM_IDS[WHISTLE_PLUCK]])
            s.receive(1, [ITEM_IDS[WHISTLE_PLUCK]])  # a duplicate copy still reads as one
            self.assertIn(' WHISTLEPLUCK 1 END', s.native_state(r.token, True))
            self.assertIn('WHISTLE PLUCK ON', benefit_lines(m, s.inventory))
            (r.directory / 'checks.txt').write_text('0\n')
            restored = Session(m, d)  # bootstrap field count must still match
            self.assertEqual(restored.inventory, s.inventory)


if __name__ == '__main__':
    unittest.main()
