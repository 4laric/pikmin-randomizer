"""Focused tests for the #644 ownership/pin helpers: positives plus
malformed/missing-input negatives. Stdlib only (unittest)."""

import unittest

from experimental.pikmin2_generated_claim_ownership import (
    OwnershipError,
    check_birth_field_owner,
    check_catalog_pin,
    check_claim_arm_owner,
    check_packet,
    lane_record,
    load_status,
)


def _status(extra=None):
    lanes = {
        "enemy-waterwraith99-generated": {
            "lane": "enemy-waterwraith99-generated",
            "issue": 572, "state": "blocked",
            "scope": "Close identity_spawn for source99 BlackMan",
        },
        "planning-shard-provider-actor-birth-projectiles-cycle-13": {
            "lane": "planning-shard-provider-actor-birth-projectiles-cycle-13",
            "issue": 608, "state": "done",
            "scope": "Generic real engine actor-manager/birth and "
                     "projectile/payload infrastructure; "
                     "excludes family-specific consumer FSMs.",
        },
    }
    if extra:
        lanes.update(extra)
    return {"lanes": lanes}


DOC = ("line one\n"
       "Family generated-claim arm (this lane owns pc_p2_waterwraith_actor /\n"
       "line three\n")


class StatusTests(unittest.TestCase):
    def test_missing_file_is_error(self):
        with self.assertRaises(OwnershipError):
            load_status("C:/nonexistent/status-snap.json")

    def test_malformed_snapshot_is_error(self):
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("[1, 2]")
            with self.assertRaises(OwnershipError):
                load_status(path)
        finally:
            os.unlink(path)

    def test_unknown_lane_is_error(self):
        with self.assertRaises(OwnershipError):
            lane_record(_status(), "no-such-lane")

    def test_known_lane_returns_record(self):
        record = lane_record(_status(), "enemy-waterwraith99-generated")
        self.assertEqual(record["issue"], 572)


class ClaimArmTests(unittest.TestCase):
    def test_self_assignment_found_with_line(self):
        facts = check_claim_arm_owner(_status(), DOC)
        self.assertEqual(facts["owner"], "enemy-waterwraith99-generated")
        self.assertEqual(facts["issue"], 572)
        self.assertTrue(facts["self_assignment"].endswith(":2"))
        self.assertEqual(len(facts["surface"]), 4)

    def test_missing_marker_is_explicit_unknown(self):
        facts = check_claim_arm_owner(_status(), "unrelated text")
        self.assertEqual(facts["self_assignment"], "UNKNOWN")

    def test_issue_mismatch_is_error(self):
        status = _status({"enemy-waterwraith99-generated": {"issue": 999}})
        with self.assertRaises(OwnershipError):
            check_claim_arm_owner(status, DOC)


class BirthFieldTests(unittest.TestCase):
    def test_actor_birth_shard_excluded(self):
        facts = check_birth_field_owner(_status())
        self.assertEqual(facts["owner"], "enemy-waterwraith99-generated")
        self.assertEqual(facts["actor_birth_shard"], "excluded")

    def test_missing_shard_is_explicit_unknown(self):
        status = {"lanes": {"enemy-waterwraith99-generated": {"issue": 572}}}
        facts = check_birth_field_owner(status)
        self.assertEqual(facts["actor_birth_shard"], "UNKNOWN")

    def test_scope_without_exclusion_is_unknown(self):
        status = _status({"planning-shard-provider-actor-birth-projectiles-cycle-13":
                          {"scope": "generic birth infra"}})
        facts = check_birth_field_owner(status)
        self.assertEqual(facts["actor_birth_shard"], "UNKNOWN")


class PinTests(unittest.TestCase):
    def test_live_repo_pins(self):
        import subprocess
        root = "C:/Users/alari/pikmin-randomizer"
        if subprocess.run(["git", "-C", root, "rev-parse", "--is-inside-work-tree"],
                           capture_output=True).returncode != 0:
            self.skipTest("no live repo available")
        pins = check_catalog_pin(root + "/.git", root + "/native/.git")
        self.assertTrue(pins["catalog"]["exists"])
        self.assertFalse(pins["catalog"]["in_canonical_head"])
        self.assertTrue(pins["packaging"]["exists"])
        self.assertFalse(pins["packaging"]["in_canonical_head"])
        self.assertTrue(pins["native_bind"]["exists"])
        self.assertFalse(pins["native_bind"]["in_canonical_head"])
        self.assertFalse(pins["wave_root_note"]["carries_bind_file"])
        self.assertFalse(pins["native_wave_note"]["carries_bind_file"])


class PacketTests(unittest.TestCase):
    def test_complete_packet(self):
        result = check_packet(["#572", "f42ecca0", "#608", "#575/#576"])
        self.assertTrue(result["complete"])

    def test_missing_consumer_is_error(self):
        with self.assertRaises(OwnershipError):
            check_packet(["#572", "#608"])

    def test_non_list_is_error(self):
        with self.assertRaises(OwnershipError):
            check_packet("#572")


if __name__ == "__main__":
    unittest.main()
