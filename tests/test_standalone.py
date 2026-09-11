import copy
import json
import tempfile
import unittest
from pathlib import Path
from randomizer.catalog import *
from randomizer.seed import generate, validate, fingerprint, solo_rewards, spheres
from randomizer.session import Session, SessionLock
from randomizer.runner import NativeRun


class SeedTests(unittest.TestCase):
    def test_100_constructive_seeds(self):
        arrangements = set()
        for i in range(100):
            m = generate(str(i))
            rewards = solo_rewards(m)
            self.assertEqual(rewards, solo_rewards(generate(str(i))))
            self.assertEqual(len(rewards), 30)
            self.assertEqual(sum(r == REPAIR for r in rewards.values()), 25)
            self.assertEqual(sum(map(len, spheres(rewards))), 30)
            arrangements.add(tuple(rewards[n] for n in NAMES))
        self.assertGreater(len(arrangements), 90)

    def test_reject_incompatible_manifests(self):
        changes = dict(schema=2, goal=28, placement="shuffle", profile="full-campaign",
                       day_policy="vanilla", capabilities=["winged"], assignments={}, mode="BBFT")
        for field, value in changes.items():
            m = generate("x"); m[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): validate(m)
        m = generate("x"); m["unknown"] = 1
        with self.assertRaises(ValueError): validate(m)
        m = generate("x"); m["schema"] = True
        with self.assertRaises(ValueError): validate(m)

    def test_identities_and_spoiler_separation(self):
        m = generate("abc")
        self.assertNotIn("rewards", m)
        self.assertNotEqual(fingerprint(m), fingerprint(generate("abc", slot="Player2")))
        self.assertEqual(len(set(LOCATION_IDS.values())), 30)
        self.assertEqual(len(set(ITEM_IDS.values())), 27)
        self.assertFalse(set(LOCATION_IDS.values()) & set(ITEM_IDS.values()))
        self.assertNotIn("Pikmin: Main Engine", LOCATION_IDS)
        self.assertNotIn("Pikmin: Positron Generator", LOCATION_IDS)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_solo_persistence_and_duplicate_delivery(self):
        m = generate("solo")
        s = Session(m, self.root)
        for name in NAMES:
            self.assertTrue(s.collect(name))
            self.assertFalse(s.collect(name))
        self.assertEqual(s.inventory[REPAIR], 25)
        self.assertTrue(s.goal)
        reloaded = Session(m, self.root)
        self.assertEqual(reloaded.inventory, s.inventory)
        self.assertTrue(reloaded.goal)
        with self.assertRaises(ValueError): Session(generate("other"), self.root)

    def test_ap_collection_does_not_grant_local_reward(self):
        s = Session(generate("ap", "ap"), self.root)
        s.collect(NAMES[0])
        self.assertFalse(s.inventory)
        self.assertFalse(s.goal)
        with self.assertRaises(ValueError): s.receive(0, [ITEM_IDS[REPAIR]])
        s.bind_ap("room1", 0, 1)
        s.receive(0, [ITEM_IDS[REPAIR]])
        s.receive(0, [ITEM_IDS[REPAIR]])
        self.assertEqual(s.inventory[REPAIR], 1)
        s.receive(1, [ITEM_IDS[REPAIR]] * 24)
        self.assertTrue(s.goal)
        with self.assertRaises(ValueError): s.bind_ap("room2", 0, 1)
        with self.assertRaises(ValueError): s.receive(0, [ITEM_IDS[YELLOW]])
        with self.assertRaises(ValueError): s.receive(99, [])
        with self.assertRaises(ValueError): s.receive(25, [123])
        self.assertEqual(Session(s.manifest, self.root).inventory[REPAIR], 25)

    def test_native_handshake_and_partial_record(self):
        s = Session(generate("native"), self.root)
        run = NativeRun(s)
        journal = run.directory / "checks.txt"
        journal.write_text("0\n1", encoding="ascii")
        run.poll()
        self.assertEqual(s.data["checked"], [])
        hello = f"PIKMIN_HELLO 1 {run.token} {s.fingerprint} identity-placement-v1 foh-day2-v1 repair-goal-v1 repeat-day29-v1 END\n"
        (run.directory / "hello.txt").write_text(hello, encoding="ascii")
        run.poll()
        self.assertEqual(s.data["checked"], [NAMES[0]])
        journal.write_text("0\n1\n1\n", encoding="ascii")
        run.poll(); run.poll()
        self.assertEqual(s.data["checked"], [NAMES[0], NAMES[1]])
        journal.write_text("", encoding="ascii")
        with self.assertRaises(ValueError): run.poll()

    def test_native_mismatch_rejected_before_checks(self):
        s = Session(generate("native"), self.root)
        run = NativeRun(s)
        (run.directory / "hello.txt").write_text("PIKMIN_HELLO 99 wrong", encoding="ascii")
        with self.assertRaises(ValueError): run.poll()
        self.assertFalse(s.data["checked"])

    def test_crash_recovery_and_single_writer(self):
        m = generate("crash")
        session = Session(m, self.root)
        run = NativeRun(session)
        (run.directory / "checks.txt").write_text("0\n1", encoding="ascii")
        recovered = Session(m, self.root)
        self.assertEqual(recovered.data["checked"], [NAMES[0]])
        with SessionLock(self.root):
            with self.assertRaises(ValueError):
                with SessionLock(self.root):
                    pass
        with SessionLock(self.root):
            pass

    def test_reject_unknown_checks_and_corrupt_save(self):
        s = Session(generate("x"), self.root)
        with self.assertRaises(ValueError): s.collect("Pikmin: Main Engine")
        s.save()
        data = json.loads(s.path.read_text())
        data["received"] = [True]
        s.path.write_text(json.dumps(data))
        with self.assertRaises(ValueError): Session(s.manifest, self.root)


if __name__ == "__main__": unittest.main()
