"""Focused tests for the Bomb birth shared-hook candidate (#666)."""
import importlib.util
import unittest
from pathlib import Path

MODULE = (Path(__file__).resolve().parents[1] / "experimental"
          / "pikmin2_bomb_birth_shared_hook_candidate.py")
_spec = importlib.util.spec_from_file_location("bomb_birth_shared_hook_candidate", MODULE)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

candidate = _mod.candidate
verify_pin = _mod.verify_pin
verify_file_hash = _mod.verify_file_hash
verify_candidate = _mod.verify_candidate
HookError = _mod.HookError
REVIEW_ITEMS = _mod.REVIEW_ITEMS

EXPECTED_IDS = {"engine-bomb-birth-path", "provider-cmake-membership",
                "dynamic-bridge-source-93"}


class CandidateSchemaTests(unittest.TestCase):
    def test_three_items_with_unique_ids(self):
        data = candidate()
        self.assertEqual(data["schema"], 1)
        self.assertEqual(data["issue"], 666)
        self.assertEqual({i["id"] for i in data["items"]}, EXPECTED_IDS)
        for item in data["items"]:
            self.assertTrue(item["owner"] or item["shared_review"])

    def test_full_candidate_verifies(self):
        self.assertTrue(verify_candidate(candidate()))

    def test_schema_rejects_bad_input(self):
        with self.assertRaises(HookError):
            verify_candidate({})
        with self.assertRaises(HookError):
            verify_candidate({"schema": 1, "items": []})
        dup = candidate()
        dup["items"].append(dict(dup["items"][0]))
        with self.assertRaises(HookError):
            verify_candidate(dup)
        norole = candidate()
        norole["items"][0]["owner"] = None
        norole["items"][0]["shared_review"] = None
        with self.assertRaises(HookError):
            verify_candidate(norole)


class PinPresenceTests(unittest.TestCase):
    def test_every_recorded_pin_exists(self):
        data = candidate()
        total = 0
        for item in data["items"]:
            for pin in item["pins"]:
                with self.subTest(pin="%s:%d" % (pin["file"], pin["line"])):
                    self.assertTrue(verify_pin(pin))
                    total += 1
        self.assertEqual(
            {i["id"]: len(i["pins"]) for i in data["items"]},
            {"engine-bomb-birth-path": 4, "provider-cmake-membership": 3,
             "dynamic-bridge-source-93": 2})
        self.assertEqual(total, 9)

    def test_pin_failures_are_closed(self):
        good = dict(candidate()["items"][0]["pins"][0])
        for bad in (dict(good, line=1),
                    dict(good, line=10 ** 9),
                    dict(good, file="nope/missing.cpp"),
                    dict(good, symbol="NoSuchFunction"),
                    {"file": good["file"], "line": good["line"]}):
            with self.subTest(bad=bad), self.assertRaises(HookError):
                verify_pin(bad)


class OwnershipCoverageTests(unittest.TestCase):
    def test_shared_review_points_at_186(self):
        for item in candidate()["items"]:
            review = item["shared_review"] or {}
            self.assertIn("#186", review.get("owner", ""))

    def test_provider_files_hash_pinned(self):
        item = next(i for i in candidate()["items"]
                    if i["id"] == "provider-cmake-membership")
        base = Path(r"C:\Users\alari\pikmin-randomizer\output\workflow\autofill\planning-shards\provider-actor-birth-projectiles\prepared\bomb-mgr-birth-native")
        for rel, digest in item["provider_files"].items():
            self.assertTrue(verify_file_hash(base / rel, digest))

    def test_bridge_files_hash_pinned(self):
        item = next(i for i in candidate()["items"]
                    if i["id"] == "dynamic-bridge-source-93")
        base = Path(r"C:\Users\alari\pikmin-randomizer\output\workflow\autofill\planning-shards\provider-actor-birth-projectiles\prepared\bomb-mgr-birth-native")
        for rel, digest in item["bridge_files"].items():
            self.assertTrue(verify_file_hash(base / rel, digest))

    def test_hash_drift_fails_closed(self):
        drift = Path(__file__).parent / "_hash_drift.tmp"
        try:
            drift.write_bytes(b"changed")
            with self.assertRaises(HookError):
                verify_file_hash(drift, "0" * 64)
        finally:
            drift.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
