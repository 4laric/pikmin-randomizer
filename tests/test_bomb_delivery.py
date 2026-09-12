import copy
import tempfile
import unittest
from collections import Counter
from randomizer.benefits import BOMBS, benefit_state
from randomizer.catalog import item_pool, ITEM_IDS, REPAIR
from randomizer.seed import generate, validate, solo_rewards, spheres
from randomizer.session import Session
from randomizer.runner import NativeRun

class BombDeliveryTests(unittest.TestCase):
    def test_weights_and_legacy(self):
        for weight in (0, 1, 5, 10):
            m = generate('bombs', permanent_checks=True, bomb_rock_weight=weight)
            pool = Counter(item_pool(m))
            self.assertEqual(pool[REPAIR], 30)
            self.assertEqual(sum(pool.values()), len(m['locations']))
            self.assertEqual(pool[BOMBS] > 0, weight > 0)
            self.assertEqual('bomb-delivery-v1' in m['capabilities'], weight > 0)
            self.assertEqual(sum(map(len, spheres(solo_rewards(m), m))), len(m['locations']))
        for invalid in (-1, 11, True):
            with self.assertRaises(ValueError): generate('bad', bomb_rock_weight=invalid)

    def test_protocol_and_replay(self):
        m = generate('bombs', 'ap', bomb_rock_weight=1)
        with tempfile.TemporaryDirectory() as d:
            s = Session(m, d); s.bind_ap('room', 0, 1)
            s.receive(0, [ITEM_IDS[BOMBS]]); s.receive(0, [ITEM_IDS[BOMBS]])
            self.assertEqual(s.inventory[BOMBS], 1)
            run = NativeRun(s)
            self.assertIn('BENEFITS 2', run.bootstrap.read_text())
            self.assertIn('BENEFITS 0 0 0 0 0 1', s.native_state(run.token, True))
            self.assertEqual(Session(m, d).inventory[BOMBS], 1)
        bad = copy.deepcopy(m); bad['capabilities'].remove('bomb-delivery-v1')
        with self.assertRaises(ValueError): validate(bad)
