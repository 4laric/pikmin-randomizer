"""Focused fail-closed tests for the pc-bbft follow-on anchor audit (#775).

Synthetic git fixtures plus one live read-only check against the real
native repo state recorded in the report. No builds, no runtime, no ADMIT.
"""
import importlib.util
import subprocess
import unittest
from pathlib import Path


def _load_adapter():
    path = (Path(__file__).resolve().parents[1] / "experimental" /
            "pc_bbft_followon_anchor_audit.py")
    spec = importlib.util.spec_from_file_location("followon_anchor", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ADAPTER = _load_adapter()

NATIVE_REPO = Path("C:/Users/alari/pikmin-randomizer/native")


def _fixture_repo():
    import tempfile
    directory = Path(tempfile.mkdtemp())
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    import os
    full = dict(os.environ)
    full.update(env)
    subprocess.run(["git", "init", "-q"], cwd=directory, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=directory,
                   check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=directory,
                   check=True, capture_output=True)
    (directory / "pc_port").mkdir()
    (directory / "pc_port" / "pc_bbft.cpp").write_text(
        "const char* pc_p2_challenge_stage_lookup() { return 0; }\n",
        encoding="utf-8")
    (directory / "pc_port" / "pc_p2_challenge_stages_ext.h").write_text(
        "// ext\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=directory, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "-qm", "anchor"], cwd=directory,
                   check=True, capture_output=True)
    (directory / "pc_port" / "pc_bbft.cpp").write_text(
        "// no anchor here\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-qam", "drop"], cwd=directory,
                   check=True, capture_output=True)
    return directory


class AnchorPresenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = _fixture_repo()
        out = subprocess.run(
            ["git", "-C", str(cls.repo), "rev-list", "--max-parents=0", "HEAD"],
            capture_output=True, text=True, check=True)
        cls.first = out.stdout.strip().splitlines()[-1]
        cls.head = subprocess.run(
            ["git", "-C", str(cls.repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True).stdout.strip()

    def test_lookup_present_at_first(self):
        self.assertTrue(ADAPTER.symbol_in_blob(
            self.repo, self.first, "pc_port/pc_bbft.cpp",
            "pc_p2_challenge_stage_lookup"))
        self.assertTrue(ADAPTER.blob_present(
            self.repo, self.first, "pc_port/pc_p2_challenge_stages_ext.h"))

    def test_lookup_absent_at_head(self):
        self.assertFalse(ADAPTER.symbol_in_blob(
            self.repo, self.head, "pc_port/pc_bbft.cpp",
            "pc_p2_challenge_stage_lookup"))

    def test_bad_rev_fails_closed(self):
        self.assertFalse(ADAPTER.symbol_in_blob(
            self.repo, "0" * 40, "pc_port/pc_bbft.cpp", "x"))
        with self.assertRaises(ADAPTER.AnchorError):
            ADAPTER.blob_present(self.repo, "", "pc_port/pc_bbft.cpp")
        with self.assertRaises(ADAPTER.AnchorError):
            ADAPTER.symbol_in_blob(self.repo, self.first,
                                   "pc_port/pc_bbft.cpp", "")

    def test_git_unavailable_fails_closed(self):
        with self.assertRaises(ADAPTER.AnchorError):
            ADAPTER.blob_present(self.repo, self.first,
                                 "pc_port/pc_bbft.cpp", git_available=False)


class DispositionTests(unittest.TestCase):
    def test_complete(self):
        record = ADAPTER.anchor_status(True, True)
        self.assertEqual(record["verdict"], "anchor-complete")
        self.assertIn("rebase", record["resume"])

    def test_split_either_way(self):
        for lookup, ext in ((True, False), (False, True)):
            record = ADAPTER.anchor_status(lookup, ext)
            self.assertEqual(record["verdict"], "anchor-split")
            self.assertIn("rebase", record["resume"])

    def test_absent(self):
        record = ADAPTER.anchor_status(False, False)
        self.assertEqual(record["verdict"], "anchor-absent")

    def test_non_bool_rejected(self):
        with self.assertRaises(ADAPTER.AnchorError):
            ADAPTER.anchor_status("yes", False)

    def test_ownership_record(self):
        live = ADAPTER.ownership_record("some-lane", "blocked", True)
        self.assertTrue(live["resumable_in_place"])
        dead = ADAPTER.ownership_record("some-lane", "blocked", False)
        self.assertFalse(dead["resumable_in_place"])
        with self.assertRaises(ADAPTER.AnchorError):
            ADAPTER.ownership_record("some-lane", "bogus", True)

    def test_packet_names_downstream_and_hashes(self):
        record = ADAPTER.anchor_status(False, False)
        packet = ADAPTER.packet(record, [ADAPTER.ownership_record(
            "x", "blocked", False)],
            {"lane": "p2-challenge-ch-nari-03toy-p1", "issue": 746})
        self.assertEqual(packet["downstream"]["issue"], 746)
        self.assertFalse(packet["admit"])
        self.assertRegex(packet["packet_sha256"], r"[0-9a-f]{64}")

    def test_packet_rejects_bad_inputs(self):
        with self.assertRaises(ADAPTER.DiagnosisError if hasattr(
                ADAPTER, "DiagnosisError") else ADAPTER.AnchorError):
            ADAPTER.packet({}, [], {})


class LivePinTests(unittest.TestCase):
    def test_lookup_absent_at_pinned_base(self):
        self.assertFalse(ADAPTER.symbol_in_blob(
            NATIVE_REPO, "a95040b66a0ffc9cdbfc649502569a29e66949a7",
            "pc_port/pc_bbft.cpp", "pc_p2_challenge_stage_lookup"))

    def test_cli_json_output(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "packet.json"
            self.assertEqual(ADAPTER.main(
                ["--repo", str(NATIVE_REPO), "--rev",
                 "a95040b66a0ffc9cdbfc649502569a29e66949a7",
                 "--output", str(out)]), 0)
            import json
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(packet["verdict"] if "verdict" in packet
                             else packet["anchor"]["verdict"], "anchor-absent")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
