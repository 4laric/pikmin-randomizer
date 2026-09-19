"""Focused tests for experimental/pikmin2_bomb_birth_notifier_port.py.

Verifies the #715 evidence bundle (real lane out/ dir) plus fail-closed
negatives on tampered copies. No engine, build, or display needed.
"""
import json
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from experimental.pikmin2_bomb_birth_notifier_port import verify_bundle

OUT_DIR = ("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
           "prerequisites/bomb-birth-hook-notifier-port-native/out")


class NotifierEvidenceTest(unittest.TestCase):
    def test_real_bundle_passes(self):
        ok, report, problems = verify_bundle(OUT_DIR)
        self.assertEqual(problems, [])
        self.assertTrue(ok)
        self.assertTrue(report["checks"]["build_steps"])
        self.assertTrue(report["checks"]["provider_test"])

    def _copied(self, tmp):
        dst = os.path.join(tmp, "out")
        shutil.copytree(OUT_DIR, dst)
        return dst

    def test_tampered_exe_hash_fails(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="notif-ev-")
        self.addCleanup(shutil.rmtree, tmp, True)
        dst = self._copied(tmp)
        recs = [f for f in os.listdir(dst) if f.startswith("build-record-")]
        path = os.path.join(dst, sorted(recs)[-1])
        record = json.load(open(path, encoding="utf-8"))
        exe = next(iter(record["executables"]))
        record["executables"][exe] = "0" * 64
        json.dump(record, open(path, "w", encoding="utf-8"))
        ok, _report, problems = verify_bundle(dst)
        self.assertFalse(ok)
        self.assertTrue(any("hash mismatch" in p for p in problems))

    def test_missing_pass_marker_fails(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="notif-ev-")
        self.addCleanup(shutil.rmtree, tmp, True)
        dst = self._copied(tmp)
        logs = sorted(f for f in os.listdir(dst)
                      if f.startswith("ctest-") and f.endswith(".log"))
        self.assertTrue(logs)
        path = os.path.join(dst, logs[-1])
        text = open(path, encoding="utf-8").read()
        text = text.replace("ALL_FIXTURE_PASS", "ALL_FIXTURE_MARKER_REDACTED")
        # The redacted token must not contain the original marker as a prefix.
        self.assertNotIn("ALL_FIXTURE_PASS", text.replace(
            "ALL_FIXTURE_MARKER_REDACTED", ""))
        open(path, "w", encoding="utf-8").write(text)
        ok, _report, problems = verify_bundle(dst)
        self.assertFalse(ok)

    def test_missing_bundle_refused(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="notif-ev-empty-")
        self.addCleanup(shutil.rmtree, tmp, True)
        ok, _report, problems = verify_bundle(tmp)
        self.assertFalse(ok)
        self.assertTrue(any("unreadable build record" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
