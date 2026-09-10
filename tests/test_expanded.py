import copy
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from randomizer.catalog import *
from randomizer.seed import generate, fingerprint, solo_rewards, spheres, validate
from randomizer.session import Session
from randomizer.runner import NativeRun


class ExpandedTests(unittest.TestCase):
    def test_expanded_pool_and_100_solvable_seeds(self):
        for seed in range(100):
            manifest = generate(str(seed), expanded=True)
            rewards = solo_rewards(manifest)
            self.assertEqual(len(rewards), 55)
            self.assertEqual(Counter(rewards.values()), Counter(item_pool(manifest)))
            self.assertEqual(sum(map(len, spheres(rewards))), 55)
            self.assertEqual(Counter(rewards.values())[FLARLIC], 8)
            self.assertEqual(Counter(rewards.values())[REPAIR], 42)
            self.assertEqual(rewards, solo_rewards(manifest))
            inventory = Counter()
            for group in spheres(rewards):
                self.assertTrue(all(can_reach(n, inventory, True) for n in group))
                inventory.update(rewards[n] for n in group)

    def test_capacity_gates_real_weight_and_population(self):
        inventory = Counter({n:1 for n in UNLOCKS})
        dynamo = "Pikmin: Eternal Fuel Dynamo"
        shock = "Pikmin: Shock Absorber"
        gluon = "Pikmin: Gluon Drive"
        self.assertEqual(PART_WEIGHTS[dynamo], 40)
        self.assertFalse(can_reach(dynamo, inventory, True))
        self.assertFalse(can_reach(shock, inventory, True))
        inventory[FLARLIC] = 1
        self.assertTrue(can_reach(shock, inventory, True))
        self.assertFalse(can_reach(dynamo, inventory, True))
        inventory[FLARLIC] = 2
        self.assertTrue(can_reach(dynamo, inventory, True))
        self.assertFalse(can_reach(gluon, inventory, True))
        inventory[FLARLIC] = 3
        self.assertTrue(can_reach(gluon, inventory, True))
        self.assertFalse(can_reach("Population: 60 Pikmin in the field", inventory, True))
        inventory[FLARLIC] = 100
        self.assertEqual(field_capacity(inventory), 100)
        self.assertTrue(can_reach("Population: 100 Pikmin in the field", inventory, True))

    def test_legacy_identity_and_rules_preserved(self):
        m = generate("old")
        self.assertEqual(m["schema"], 1)
        self.assertEqual(m["locations"], LOCATION_IDS)
        for name, value in LOCATION_IDS.items(): self.assertEqual(ALL_LOCATION_IDS[name], value)
        self.assertTrue(can_reach("Pikmin: Eternal Fuel Dynamo", {}, False))
        self.assertFalse(can_reach("Pikmin: Eternal Fuel Dynamo", {}, True))
        self.assertNotEqual(fingerprint(m), fingerprint(generate("old", expanded=True)))

    def test_state_high_bits_receipts_and_journal_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            m=generate("new", "ap", expanded=True)
            session=Session(m,Path(temp));session.bind_ap("room",0,1)
            session.receive(0,[ITEM_IDS[FLARLIC]]*8)
            session.receive(0,[ITEM_IDS[FLARLIC]]*8)
            self.assertEqual(session.inventory[FLARLIC],8)
            self.assertFalse(session.data["checked"])
            run=NativeRun(session)
            (run.directory/"checks.txt").write_text("54\n54\n",encoding="ascii")
            session=Session(m,Path(temp))
            self.assertEqual(session.data["checked"],[EXPANDED_NAMES[54]])
            state=session.native_state(run.token,True).split()
            self.assertEqual(state[1],"2");self.assertEqual(state[6],"8")
            self.assertEqual(int(state[7]),1<<54)
            with self.assertRaises(ValueError):Session(generate("new","ap"),Path(temp))

    def test_legacy_refuses_expanded_items_and_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Session(generate("old","ap"),Path(temp));session.bind_ap("room",0,1)
            with self.assertRaises(ValueError):session.receive(0,[ITEM_IDS[FLARLIC]])
            with self.assertRaises(ValueError):session.collect(next(iter(POPULATION)))

    def test_new_feature_catalog_is_required(self):
        m=generate("new",expanded=True)
        m["capabilities"].remove("bestiary-v1")
        with self.assertRaises(ValueError):validate(m)
