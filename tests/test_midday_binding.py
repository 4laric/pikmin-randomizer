import concurrent.futures
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from randomizer.midday_binding import IDENTITY_FILE, bind_checkpoint_session
from randomizer.seed import generate
from randomizer.session import Session


class MiddayBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "campaign"
        self.session = SimpleNamespace(manifest={"mode": "solo"}, fingerprint="ab" * 32, directory=self.directory)

    def test_actual_generated_session_reopens_without_journal_changes(self):
        manifest = generate("midday-binding-integration", mode="solo")
        first_session = Session(manifest, self.directory)
        first_session.save()
        original = first_session.path.read_bytes()
        first = bind_checkpoint_session(first_session)
        reopened = Session(manifest, self.directory)
        second = bind_checkpoint_session(reopened)
        self.assertEqual(first, second)
        self.assertEqual(first.seed, reopened.fingerprint)
        self.assertEqual(first_session.path.read_bytes(), original)
        self.assertEqual(reopened.data, first_session.data)

    def test_two_launches_share_campaign_binding(self):
        self.session.token = "first"
        first = bind_checkpoint_session(self.session)
        raw = (self.directory / IDENTITY_FILE).read_bytes()
        self.session.token = "second"
        second = bind_checkpoint_session(self.session)
        self.assertEqual(first, second)
        self.assertEqual((self.directory / IDENTITY_FILE).read_bytes(), raw)
        self.assertEqual(first.directory, self.directory / "midday")
        self.assertEqual(len(first.session_digest), 64)

    def test_campaign_move_preserves_digest(self):
        first = bind_checkpoint_session(self.session)
        moved = Path(self.temp.name) / "moved"
        shutil.move(self.directory, moved)
        self.session.directory = moved
        second = bind_checkpoint_session(self.session)
        self.assertEqual(first.session_digest, second.session_digest)
        self.assertEqual(first.campaign_id, second.campaign_id)
        self.assertEqual(second.directory, moved / "midday")

    def test_distinct_campaigns_do_not_share_identity(self):
        first = bind_checkpoint_session(self.session)
        self.session.directory = Path(self.temp.name) / "another"
        second = bind_checkpoint_session(self.session)
        self.assertNotEqual(first.session_digest, second.session_digest)

    def test_different_seed_refuses_existing_identity(self):
        bind_checkpoint_session(self.session)
        raw = (self.directory / IDENTITY_FILE).read_bytes()
        self.session.fingerprint = "cd" * 32
        with self.assertRaises(ValueError):
            bind_checkpoint_session(self.session)
        self.assertEqual((self.directory / IDENTITY_FILE).read_bytes(), raw)

    def test_corrupt_unknown_version_and_boolean_schema_preserved(self):
        bind_checkpoint_session(self.session)
        path = self.directory / IDENTITY_FILE
        original = json.loads(path.read_text())
        cases = [b"{", b"x" * 4097, b"\xff", json.dumps(dict(original, schema=2)).encode(),
                 json.dumps(dict(original, schema=True)).encode(), json.dumps(dict(original, mode="ap")).encode(),
                 json.dumps(dict(original, campaign="bad")).encode(), json.dumps(dict(original, extra=1)).encode(),
                 json.dumps(original).replace('"schema": 1', '"schema": 2, "schema": 1').encode()]
        for raw in cases:
            with self.subTest(raw=raw[:40]):
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    bind_checkpoint_session(self.session)
                self.assertEqual(path.read_bytes(), raw)

    def test_competing_creators_converge(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            bindings = list(pool.map(lambda _: bind_checkpoint_session(self.session), range(16)))
        self.assertEqual(len({b.session_digest for b in bindings}), 1)
        self.assertEqual(len({b.campaign_id for b in bindings}), 1)
        self.assertEqual(list(self.directory.glob("*.pending")), [])

    def test_interrupted_pending_is_ignored_and_preserved(self):
        self.directory.mkdir()
        foreign = self.directory / ".midday-identity-foreign.pending"
        foreign.write_bytes(b"incomplete")
        bind_checkpoint_session(self.session)
        self.assertEqual(foreign.read_bytes(), b"incomplete")

    def test_publication_failure_is_explicit_and_preserves_foreign_files(self):
        self.directory.mkdir()
        foreign = self.directory / ".midday-identity-foreign.pending"
        foreign.write_bytes(b"existing")
        with patch("randomizer.midday_binding.os.link", side_effect=PermissionError("unsupported publication")):
            with self.assertRaises(PermissionError):
                bind_checkpoint_session(self.session)
        self.assertFalse((self.directory / IDENTITY_FILE).exists())
        self.assertEqual(list(self.directory.glob("*.pending")), [foreign])
        self.assertEqual(foreign.read_bytes(), b"existing")

    def test_ap_or_invalid_fingerprint_refuses_before_writing(self):
        self.session.manifest["mode"] = "ap"
        with self.assertRaises(ValueError):
            bind_checkpoint_session(self.session)
        self.assertFalse(self.directory.exists())
        self.session.manifest["mode"] = "solo"
        self.session.fingerprint = "not a digest"
        with self.assertRaises(ValueError):
            bind_checkpoint_session(self.session)
        self.assertFalse(self.directory.exists())


if __name__ == "__main__":
    unittest.main()
