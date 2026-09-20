"""Tests for the reusable non-preview P2 campaign fixture (issue #837).

Pure unit/integration coverage only: command construction, session-path and
bootstrap validation, immutable manifests, log parsing and species-marker
contracts. Nothing here boots the game, touches native sources, or needs retail
assets: seeds are real ``randomizer.seed.generate`` P2 seeds against a minimal
accepted placement document with a patched (injected, labelled) admission
cohort, exactly like ``scripts/test_p2_generated_session.py``.
"""
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.p2_campaign_fixture import (
    FixtureRejected,
    GUARD_EXIT_CODE,
    MAX_SECONDS,
    PREVIEW_FLAGS,
    WINDOW_ENV,
    WINDOW_GEOMETRY,
    build_command,
    check_content_root,
    check_executable,
    evaluate,
    parse_native_log,
    require_guard,
    require_no_preview,
    require_safe_session_dir,
    stage_campaign,
    supervise,
    validate_bootstrap,
)

COHORT = (79,)  # Sokkuri: roster entry exists, committed admission denies by default.


def placement_document():
    """Minimal lane-04-style document accepting one ground slot for Sokkuri."""
    return {
        "schema": "p2-placement-v1",
        "slots": [{"uid": 401, "label": "sokkuri-slot", "stage": 1,
                   "terrain": "ground", "radius": 300.0,
                   "evidence": {"xyz": True, "terrain": True, "route": True}}],
        "profiles": [{"identity": "Sokkuri", "terrains": ["ground"],
                      "accepted_gates": ["xyz"]}],
    }


def real_manifest(seed_name="p2-fixture-test"):
    """A real P2 seed manifest with an injected (labelled) admission cohort."""
    import experimental.pikmin2_seed_bridge as bridge
    from randomizer.seed import generate
    with mock.patch.object(bridge, "admitted_ids", lambda roster: list(COHORT)):
        return generate(seed_name, collection_checks=True, p2_enemies=True,
                        p2_placement=placement_document())


def staged_session(manifest, parent):
    """A real NativeRun bootstrap for the manifest under a short tmp path."""
    from randomizer.session import Session
    from randomizer.runner import NativeRun
    session = Session(manifest, Path(parent) / "sess")
    run = NativeRun(session)
    return session, run


CLEAN_LOG = """\
[PC Port] loading stage
[BBFT] PIKMIN_WORLD_RENDERED
SESSION enabled=1 ready=1 bridge=1
P2_SEED_RESOLVE source_id=79 target=401 original_type=4 x=1.0 z=2.0
P2_SOKKURI_BIND generator=401 source_id=79
P2_SOKKURI_DELIVERY_BIND generator=401 source_id=79
P2_ENEMY_READY species=Sokkuri native_family=Chappy generator=401 x=1.0 y=2.0 z=3.0 health=150.0 max_health=150.0
"""


class CommandTests(unittest.TestCase):
    def test_production_shape(self):
        command = build_command(__file__, __file__)
        self.assertEqual(command[1], "--randomizer-seed")
        self.assertNotIn("--experimental-pikmin2-room", command)

    def test_every_preview_flag_rejected(self):
        for flag in PREVIEW_FLAGS:
            with self.assertRaises(FixtureRejected, msg=flag):
                require_no_preview(["nectar.exe", flag])
            with self.assertRaises(FixtureRejected, msg=flag):
                build_command(__file__, __file__, [flag])

    def test_experimental_prefix_rejected(self):
        with self.assertRaises(FixtureRejected):
            build_command(__file__, __file__, ["--experimental-pikmin2-room"])
        with self.assertRaises(FixtureRejected):
            require_no_preview(["--experimental-future-flag"])

    def test_missing_files_rejected(self):
        with self.assertRaises(FixtureRejected):
            build_command("C:/no/such/nectar.exe", __file__)
        with self.assertRaises(FixtureRejected):
            build_command(__file__, "C:/no/such/bootstrap.txt")


class SessionPathTests(unittest.TestCase):
    def test_relative_rejected(self):
        with self.assertRaises(FixtureRejected):
            require_safe_session_dir("output/sess")

    def test_traversal_rejected(self):
        with self.assertRaises(FixtureRejected):
            require_safe_session_dir("C:/p2sess/../evil")

    def test_nul_rejected(self):
        with self.assertRaises(FixtureRejected):
            require_safe_session_dir("C:/p2sess\0evil")

    def test_too_long_rejected(self):
        with self.assertRaises(FixtureRejected):
            require_safe_session_dir("C:/" + "x" * 200)

    def test_inside_assets_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            assets = Path(raw) / "assets"
            (assets / "dataDir" / "stages").mkdir(parents=True)
            with self.assertRaises(FixtureRejected):
                require_safe_session_dir(assets / "sess", assets)

    def test_short_absolute_accepted(self):
        with tempfile.TemporaryDirectory() as raw:
            resolved = require_safe_session_dir(Path(raw) / "s")
            self.assertTrue(resolved.is_absolute())


class BootstrapTests(unittest.TestCase):
    def test_real_bootstrap_validates(self):
        manifest = real_manifest()
        with tempfile.TemporaryDirectory() as raw:
            _, run = staged_session(manifest, raw)
            info = validate_bootstrap(
                manifest, run.bootstrap.read_text(encoding="ascii"))
            self.assertEqual(len(info["token"]), 64)
            self.assertIn("ENEMY_P2", info["enemy_line"])

    def test_hand_written_row_rejected(self):
        manifest = real_manifest()
        with tempfile.TemporaryDirectory() as raw:
            _, run = staged_session(manifest, raw)
            text = run.bootstrap.read_text(encoding="ascii")
            tampered = re.sub(r"ENEMY_P2 1 (\S+) 1 401 79",
                              r"ENEMY_P2 1 \1 1 401 78", text, count=1)
            self.assertNotEqual(tampered, text)
            with self.assertRaises(FixtureRejected):
                validate_bootstrap(manifest, tampered)

    def test_missing_enemy_block_rejected(self):
        manifest = real_manifest()
        with tempfile.TemporaryDirectory() as raw:
            _, run = staged_session(manifest, raw)
            text = run.bootstrap.read_text(encoding="ascii")
            stripped = "\n".join(line for line in text.splitlines()
                                 if not line.startswith("ENEMY_P2")) + "\n"
            self.assertNotIn("ENEMY_P2", stripped)
            with self.assertRaises(FixtureRejected):
                validate_bootstrap(manifest, stripped)

    def test_fingerprint_mismatch_rejected(self):
        manifest = real_manifest()
        other = real_manifest("p2-fixture-other")
        with tempfile.TemporaryDirectory() as raw:
            _, run = staged_session(manifest, raw)
            text = run.bootstrap.read_text(encoding="ascii")
            with self.assertRaises(FixtureRejected):
                validate_bootstrap(other, text)

    def test_missing_header_rejected(self):
        manifest = real_manifest()
        with self.assertRaises(FixtureRejected):
            validate_bootstrap(manifest, "")
        with self.assertRaises(FixtureRejected):
            validate_bootstrap({"no": "layout"}, "PIKMIN_RANDOMIZER 9\n")


class FreshnessTests(unittest.TestCase):
    def test_guard_hash_recorded(self):
        digest = require_guard()
        self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_missing_guard_rejected(self):
        with self.assertRaises(FixtureRejected):
            require_guard("C:/no/such/guard.h")

    def test_exe_pin(self):
        with tempfile.TemporaryDirectory() as raw:
            exe = Path(raw) / "nectar.exe"
            exe.write_bytes(b"fake-exe")
            digest = check_executable(exe)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertEqual(check_executable(exe, digest), digest)
            with self.assertRaises(FixtureRejected):
                check_executable(exe, "0" * 64)

    def test_content_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "content"
            root.mkdir()
            with self.assertRaises(FixtureRejected):
                check_content_root(root)
            (root / "prepared.json").write_text(
                json.dumps({"extracted": [79]}), encoding="utf-8")
            self.assertRegex(check_content_root(root), r"^[0-9a-f]{64}$")


class SupervisionBoundsTests(unittest.TestCase):
    def test_unbounded_budgets_rejected_without_spawning(self):
        manifest = real_manifest()
        with tempfile.TemporaryDirectory() as raw:
            session, run = staged_session(manifest, raw)
            for bad in (0, -5, "soon", None, MAX_SECONDS + 1):
                with self.assertRaises(FixtureRejected, msg=str(bad)):
                    supervise(["nectar.exe"], session, run.directory.name,
                              run.directory, bad)

    def test_preview_command_rejected_without_spawning(self):
        manifest = real_manifest()
        with tempfile.TemporaryDirectory() as raw:
            session, run = staged_session(manifest, raw)
            with self.assertRaises(FixtureRejected):
                supervise(["nectar.exe", "--experimental-pikmin2-room"],
                          session, run.directory.name, run.directory, 5)

    def test_missing_run_dir_rejected(self):
        manifest = real_manifest()
        with tempfile.TemporaryDirectory() as raw:
            session, run = staged_session(manifest, raw)
            with self.assertRaises(FixtureRejected):
                supervise(["nectar.exe"], session, "deadbeef",
                          Path(raw) / "gone", 5)


class LogContractTests(unittest.TestCase):
    def test_clean_campaign_passes(self):
        parsed = parse_native_log(CLEAN_LOG)
        self.assertTrue(parsed["booted"])
        self.assertTrue(parsed["handshake"])
        self.assertFalse(parsed["captain_down"])
        self.assertIn(401, parsed["bound"])
        verdict = evaluate(parsed, ["401"])
        self.assertEqual(verdict["outcome"], "PASS")

    def test_missing_handshake_fails(self):
        text = CLEAN_LOG.replace("SESSION enabled=1 ready=1 bridge=1\n", "")
        verdict = evaluate(parse_native_log(text), ["401"])
        self.assertEqual(verdict["outcome"], "FAIL")
        self.assertTrue(any("handshake" in reason for reason in verdict["reasons"]))

    def test_preview_hint_fails(self):
        text = CLEAN_LOG + "boot --experimental-pikmin2-room bridge-only\n"
        verdict = evaluate(parse_native_log(text), ["401"])
        self.assertEqual(verdict["outcome"], "FAIL")

    def test_captain_down_blocks(self):
        text = (CLEAN_LOG
                + "P2_FIXTURE_CAPTAIN_DOWN tick=5139 hp=0.000 orima_dead=1 outcome=BLOCKED\n")
        parsed = parse_native_log(text)
        self.assertTrue(parsed["captain_down"])
        self.assertEqual(evaluate(parsed, ["401"])["outcome"], "BLOCKED")
        self.assertEqual(GUARD_EXIT_CODE, 86)

    def test_species_contract(self):
        parsed = parse_native_log(
            CLEAN_LOG,
            pass_markers=[r"P2_SOKKURI_DELIVERY_BIND generator=401"],
            block_markers=[r"P2_SETUP_ABORT\s+Sokkuri"])
        self.assertEqual(parsed["pass_hits"],
                         [r"P2_SOKKURI_DELIVERY_BIND generator=401"])
        self.assertEqual(parsed["block_hits"], [])
        self.assertEqual(evaluate(parsed, ["401"])["outcome"], "PASS")

    def test_block_marker_fails(self):
        text = CLEAN_LOG + "P2_SETUP_ABORT Sokkuri actor_type_mismatch\n"
        parsed = parse_native_log(text, block_markers=[r"P2_SETUP_ABORT\s+Sokkuri"])
        verdict = evaluate(parsed, ["401"])
        self.assertEqual(verdict["outcome"], "FAIL")

    def test_missing_pass_marker_fails(self):
        parsed = parse_native_log(CLEAN_LOG, pass_markers=[r"P2_SOKKURI_RECEIPT x=1"])
        self.assertEqual(evaluate(parsed, ["401"])["outcome"], "FAIL")

    def test_resolution_alone_is_not_a_bind(self):
        text = ("[BBFT] PIKMIN_WORLD_RENDERED\n"
                "SESSION enabled=1 ready=1 bridge=1\n"
                "P2_SEED_RESOLVE source_id=79 target=401 original_type=4\n")
        parsed = parse_native_log(text)
        self.assertIn(401, parsed["resolved"])
        self.assertNotIn(401, parsed["bound"])
        self.assertEqual(evaluate(parsed, ["401"])["outcome"], "FAIL")


class StageTests(unittest.TestCase):
    def _stage(self, raw):
        root = Path(raw)
        content = root / "content"
        content.mkdir()
        (content / "prepared.json").write_text(
            json.dumps({"extracted": [79], "extracted_enums": ["Sokkuri"]}),
            encoding="utf-8")
        assets = root / "assets"
        (assets / "dataDir" / "stages").mkdir(parents=True)
        exe = root / "nectar.exe"
        exe.write_bytes(b"fake-exe")
        receipt = {"schema": 1, "mode": "identity-binding", "bindings": ["401"],
                   "cached": False, "plan_digest": "stub"}
        with mock.patch("experimental.pikmin2_family_install.install_layout",
                        return_value=receipt) as staged:
            record = stage_campaign(
                "p2-fixture-stage", root / "sess", content, assets, exe=exe,
                species=[79], out=root / "fixture-manifest.json",
                placement=placement_document())
        self.assertEqual(staged.call_count, 1)
        return root, record

    def test_stage_records_immutable_manifest(self):
        import experimental.pikmin2_seed_bridge as bridge
        with mock.patch.object(bridge, "admitted_ids", lambda roster: list(COHORT)):
            with tempfile.TemporaryDirectory() as raw:
                root, record = self._stage(raw)
                manifest_path = Path(record["manifest_path"])
                self.assertTrue(manifest_path.is_file())
                stored = json.loads(manifest_path.read_text(encoding="utf-8"))
                self.assertEqual(stored["window"], {WINDOW_ENV: WINDOW_GEOMETRY,
                                                    "centred": True})
                self.assertRegex(stored["guard_source_sha256"], r"^[0-9a-f]{64}$")
                self.assertNotIn("--experimental-pikmin2-room",
                                 " ".join(stored["command"]))
                # Hashes reproduce from the staged files.
                from scripts.p2_campaign_fixture import sha256
                self.assertEqual(
                    stored["bootstrap_sha256"],
                    sha256(Path(stored["bootstrap"])))
                self.assertEqual(
                    stored["content_prepared_sha256"],
                    sha256(Path(stored["content_root"]) / "prepared.json"))
                self.assertEqual(
                    stored["exe_sha256"], sha256(Path(stored["exe"])))
                self.assertTrue((root / "sess" / "seed-manifest.json").is_file())
                # The staged bootstrap is the production derivation.
                manifest = json.loads(
                    (root / "sess" / "seed-manifest.json").read_text(encoding="utf-8"))
                validate_bootstrap(
                    manifest,
                    Path(stored["bootstrap"]).read_text(encoding="ascii"))

    def test_stage_rejects_preview_species_confusion(self):
        # --species parsing is fail-closed; the stage path never invents a pool.
        from scripts.p2_campaign_fixture import _species_list
        self.assertIsNone(_species_list("admitted"))
        self.assertEqual(_species_list("playable"), "playable")
        self.assertEqual(_species_list("79,54"), [79, 54])
        with self.assertRaises(FixtureRejected):
            _species_list("red")


if __name__ == "__main__":
    unittest.main()
