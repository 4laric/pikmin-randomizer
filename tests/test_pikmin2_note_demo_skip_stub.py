"""Focused tests for experimental/pikmin2_note_demo_skip_stub.py.

Verifies the #704 evidence bundle (real lane out/ dir) plus fail-closed
negatives on tampered copies. No engine, build, or display needed.
"""
import json
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from experimental.pikmin2_note_demo_skip_stub import verify_bundle

OUT_DIR = ("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
           "prerequisites/audio-note-demo-skip-stub-native/out")


class StubEvidenceTest(unittest.TestCase):
    def test_real_bundle_passes(self):
        ok, report, problems = verify_bundle(OUT_DIR)
        self.assertEqual(problems, [])
        self.assertTrue(ok)
        self.assertTrue(report["checks"]["build_steps"])
        self.assertTrue(report["checks"]["stub_symbol"])
        self.assertTrue(report["checks"]["link_clean"])
        self.assertTrue(report["checks"]["focused_test"])

    def _copied(self, tmp):
        dst = os.path.join(tmp, "out")
        shutil.copytree(OUT_DIR, dst)
        return dst

    def test_tampered_exe_hash_fails(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="stub-ev-")
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

    def test_undefined_reference_fails(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="stub-ev-")
        self.addCleanup(shutil.rmtree, tmp, True)
        dst = self._copied(tmp)
        logs = sorted(f for f in os.listdir(dst)
                      if f.startswith("leased-build-") and f.endswith(".log"))
        with open(os.path.join(dst, logs[-1]), "a",
                  encoding="utf-8") as f:
            f.write("undefined reference to Jac_NoteDemoSkipped()\n")
        ok, _report, problems = verify_bundle(dst)
        self.assertFalse(ok)
        self.assertTrue(any("undefined reference" in p for p in problems))

    def test_missing_pass_marker_fails(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="stub-ev-")
        self.addCleanup(shutil.rmtree, tmp, True)
        dst = self._copied(tmp)
        path = os.path.join(dst, "stub-test-build.log")
        text = open(path, encoding="utf-8").read()
        text = text.replace("PASS P2_NOTE_DEMO_SKIP_STUB",
                            "PASS MARKER REDACTED")
        open(path, "w", encoding="utf-8").write(text)
        ok, _report, problems = verify_bundle(dst)
        self.assertFalse(ok)

    def test_missing_bundle_refused(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="stub-ev-empty-")
        self.addCleanup(shutil.rmtree, tmp, True)
        ok, _report, problems = verify_bundle(tmp)
        self.assertFalse(ok)
        self.assertTrue(any("unreadable build record" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
