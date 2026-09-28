"""Adoption of the reusable P2 campaign fixture (issue #842).

Offline consumer-validation coverage only: reusable Sarai/Kogane/Kurage/
Sokkuri marker contracts that distinguish setup (bind/stage) from behavior
(natural gameplay), pinned fresh-path/hash/startup/guard/supervision
requirements, and fail-closed proof that stale/missing/preview/setup-only
evidence never passes. Nothing here boots the game, touches native sources,
relinks AP, admits a pool, or needs retail assets: all logs are synthetic
text and all freshness pins are local file validations.
"""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.p2_campaign_fixture import (
    FixtureRejected,
    GUARD_EXIT_CODE,
    MAX_SECONDS,
    SESSION_DIR_MAX_LEN,
    SPECIES_MARKER_CONTRACTS,
    WINDOW_ENV,
    WINDOW_GEOMETRY,
    build_command,
    check_content_root,
    check_executable,
    consumer_markers,
    evaluate,
    parse_native_log,
    require_guard,
    require_no_preview,
    require_safe_session_dir,
    species_contract,
)


def setup_log(setup_line, target="401"):
    """Synthetic booted + handshake log with one setup bind marker."""
    return (
        "[PC Port] loading stage\n"
        "[BBFT] PIKMIN_WORLD_RENDERED\n"
        "SESSION enabled=1 ready=1 bridge=1\n"
        "P2_SEED_RESOLVE source_id=0 target=%s original_type=4 x=1.0 z=2.0\n"
        "%s\n" % (target, setup_line)
    )


SETUP_LINES = {
    # Each line must bind the target under the shared smoke parser.
    "sarai": "P2_ENEMY_READY species=Sarai native_family=Demon generator=401 "
             "x=1.0 y=2.0 z=3.0 health=150.0 max_health=150.0",
    "kogane": "P2_KOGANE_BIND generator=219001 source_id=9",
    "kurage": "P2_ENEMY_READY species=Kurage native_family=Jellyfloat generator=402 "
              "x=1.0 y=2.0 z=3.0 health=100.0 max_health=100.0",
    "sokkuri": "P2_SOKKURI_BIND generator=401 source_id=79",
}

BEHAVIOR_LINES = {
    "sarai": "P2_SARAI_CORPSE_READY generator=401",
    "kogane": "P2_KOGANE_COLLECT_PASS generator=219001\n"
              "P2_KOGANE_NATURAL_ATTACK generator=219001",
    "kurage": "P2_KURAGE_CORPSE_RECEIPT_PASS generator=402\n"
              "P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS generator=402\n"
              "P2_KURAGE_CORPSE_CLEANUP_PASS forgotten=1 bound=0",
    "sokkuri": "P2_SOKKURI_DELIVERY_BIND generator=401 source_id=79\n"
               "P2_SOKKURI_DEAD generator=401 prior_health=12.0",
}

TARGETS = {"sarai": ["401"], "kogane": ["219001"],
           "kurage": ["402"], "sokkuri": ["401"]}


class ContractShapeTests(unittest.TestCase):
    def test_all_four_species_defined(self):
        self.assertEqual(sorted(SPECIES_MARKER_CONTRACTS),
                         ["kogane", "kurage", "sarai", "sokkuri"])

    def test_source_ids(self):
        self.assertEqual(species_contract("sarai")["source_ids"], (23,))
        self.assertEqual(species_contract("KOGANE")["source_ids"], (9, 10, 11))
        self.assertEqual(species_contract("kurage")["source_ids"], (57,))
        self.assertEqual(species_contract("sokkuri")["source_ids"], (79,))

    def test_unknown_species_rejected(self):
        with self.assertRaises(FixtureRejected):
            species_contract("wollywog")

    def test_consumer_referral_is_behavior_plus_block(self):
        for name in ("sarai", "kogane", "kurage", "sokkuri"):
            contract = species_contract(name)
            referral = consumer_markers(name)
            self.assertEqual(referral["pass_markers"], contract["behavior_markers"])
            self.assertEqual(referral["block_markers"], contract["block_markers"])
            self.assertTrue(referral["pass_markers"])
            self.assertTrue(referral["block_markers"])

    def test_setup_lines_bind_under_shared_parser(self):
        for name, line in SETUP_LINES.items():
            parsed = parse_native_log(setup_log(line, TARGETS[name][0]))
            self.assertTrue(parsed["booted"], msg=name)
            self.assertTrue(parsed["handshake"], msg=name)
            self.assertIn(int(TARGETS[name][0]), parsed["bound"], msg=name)


class SetupVsBehaviorTests(unittest.TestCase):
    def test_setup_only_fails_closed_for_every_species(self):
        for name in ("sarai", "kogane", "kurage", "sokkuri"):
            referral = consumer_markers(name)
            parsed = parse_native_log(
                setup_log(SETUP_LINES[name], TARGETS[name][0]),
                pass_markers=referral["pass_markers"],
                block_markers=referral["block_markers"])
            verdict = evaluate(parsed, TARGETS[name])
            self.assertEqual(verdict["outcome"], "FAIL", msg=name)
            self.assertTrue(
                any("no species pass marker" in reason
                    for reason in verdict["reasons"]), msg=name)

    def test_behavior_completes_the_pass_for_every_species(self):
        for name in ("sarai", "kogane", "kurage", "sokkuri"):
            referral = consumer_markers(name)
            text = (setup_log(SETUP_LINES[name], TARGETS[name][0])
                    + BEHAVIOR_LINES[name] + "\n")
            parsed = parse_native_log(
                text, pass_markers=referral["pass_markers"],
                block_markers=referral["block_markers"])
            self.assertEqual(evaluate(parsed, TARGETS[name])["outcome"],
                             "PASS", msg=name)

    def test_species_block_marker_fails(self):
        cases = {
            "sarai": "P2_SETUP_ABORT Sarai actor_type_mismatch",
            "kogane": "P2_SETUP_ABORT Kogane actor_type_mismatch",
            "kurage": "P2_SETUP_ABORT Kurage actor_type_mismatch",
            "sokkuri": "P2_SETUP_ABORT Sokkuri actor_type_mismatch",
        }
        for name, abort in cases.items():
            referral = consumer_markers(name)
            text = (setup_log(SETUP_LINES[name], TARGETS[name][0])
                    + BEHAVIOR_LINES[name] + "\n" + abort + "\n")
            parsed = parse_native_log(
                text, pass_markers=referral["pass_markers"],
                block_markers=referral["block_markers"])
            verdict = evaluate(parsed, TARGETS[name])
            self.assertEqual(verdict["outcome"], "FAIL", msg=name)
            self.assertTrue(parsed["block_hits"], msg=name)

    def test_resolution_alone_is_not_a_bind(self):
        text = ("[BBFT] PIKMIN_WORLD_RENDERED\n"
                "SESSION enabled=1 ready=1 bridge=1\n"
                "P2_SEED_RESOLVE source_id=79 target=401 original_type=4\n")
        referral = consumer_markers("sokkuri")
        parsed = parse_native_log(text, pass_markers=referral["pass_markers"],
                                  block_markers=referral["block_markers"])
        self.assertIn(401, parsed["resolved"])
        self.assertNotIn(401, parsed["bound"])
        self.assertEqual(evaluate(parsed, ["401"])["outcome"], "FAIL")


class PinTests(unittest.TestCase):
    def test_startup_pin(self):
        self.assertEqual(WINDOW_ENV, "PIKMIN_P2_ROOM_WINDOW")
        self.assertEqual(WINDOW_GEOMETRY, "960x540")

    def test_captain_guard_pin(self):
        self.assertEqual(GUARD_EXIT_CODE, 86)
        digest = require_guard()
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        from scripts.p2_campaign_fixture import GUARD_SOURCE
        text = Path(GUARD_SOURCE).read_text(encoding="utf-8")
        self.assertIn("p2_fixture_require_captain", text)
        self.assertIn("P2_FIXTURE_CAPTAIN_DOWN", text)

    def test_captain_down_blocks_every_species(self):
        for name in ("sarai", "kogane", "kurage", "sokkuri"):
            referral = consumer_markers(name)
            text = (setup_log(SETUP_LINES[name], TARGETS[name][0])
                    + BEHAVIOR_LINES[name] + "\n"
                    + "P2_FIXTURE_CAPTAIN_DOWN tick=5139 hp=0.000 "
                      "orima_dead=1 outcome=BLOCKED\n")
            parsed = parse_native_log(
                text, pass_markers=referral["pass_markers"],
                block_markers=referral["block_markers"])
            self.assertTrue(parsed["captain_down"], msg=name)
            self.assertEqual(evaluate(parsed, TARGETS[name])["outcome"],
                             "BLOCKED", msg=name)

    def test_supervision_bound_pin(self):
        self.assertEqual(MAX_SECONDS, 600.0)
        self.assertEqual(SESSION_DIR_MAX_LEN, 100)

    def test_fresh_private_path_required(self):
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(FixtureRejected):
                require_safe_session_dir("output/sess")
            with self.assertRaises(FixtureRejected):
                require_safe_session_dir("C:/p2sess/../evil")
            existing = Path(raw) / "session"
            existing.mkdir()
            sentinel = existing / "keep.txt"
            sentinel.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FixtureRejected):
                require_safe_session_dir(existing)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")
            assets = Path(raw) / "assets"
            (assets / "dataDir" / "stages").mkdir(parents=True)
            with self.assertRaises(FixtureRejected):
                require_safe_session_dir(assets / "sess", assets)


class StaleMissingPreviewTests(unittest.TestCase):
    def test_missing_handshake_fails(self):
        referral = consumer_markers("sokkuri")
        text = setup_log(SETUP_LINES["sokkuri"], "401").replace(
            "SESSION enabled=1 ready=1 bridge=1\n", "")
        text += BEHAVIOR_LINES["sokkuri"] + "\n"
        verdict = evaluate(
            parse_native_log(text, pass_markers=referral["pass_markers"],
                             block_markers=referral["block_markers"]), ["401"])
        self.assertEqual(verdict["outcome"], "FAIL")
        self.assertTrue(any("handshake" in reason for reason in verdict["reasons"]))

    def test_preview_hint_fails(self):
        referral = consumer_markers("sokkuri")
        text = (setup_log(SETUP_LINES["sokkuri"], "401")
                + BEHAVIOR_LINES["sokkuri"] + "\n"
                + "boot --experimental-pikmin2-room bridge-only\n")
        verdict = evaluate(
            parse_native_log(text, pass_markers=referral["pass_markers"],
                             block_markers=referral["block_markers"]), ["401"])
        self.assertEqual(verdict["outcome"], "FAIL")

    def test_preview_flags_refused(self):
        with self.assertRaises(FixtureRejected):
            require_no_preview(["nectar.exe", "--experimental-pikmin2-room"])
        with self.assertRaises(FixtureRejected):
            build_command(__file__, __file__, ["--preview"])
        with self.assertRaises(FixtureRejected):
            build_command(__file__, __file__, ["--experimental-future-flag"])

    def test_stale_executable_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            exe = Path(raw) / "nectar.exe"
            exe.write_bytes(b"fake-exe")
            digest = check_executable(exe)
            self.assertEqual(check_executable(exe, digest), digest)
            with self.assertRaises(FixtureRejected):
                check_executable(exe, "0" * 64)

    def test_missing_content_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "content"
            root.mkdir()
            with self.assertRaises(FixtureRejected):
                check_content_root(root)
            (root / "prepared.json").write_text(
                json.dumps({"extracted": [79]}), encoding="utf-8")
            self.assertRegex(check_content_root(root), r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
