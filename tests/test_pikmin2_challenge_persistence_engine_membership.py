"""Focused fail-closed tests for the challenge persistence engine membership contract (#725).

Hermetic: checks the CMake membership text, the fixture's non-local-copy
property, and the exact 7/7 marker log contract. No engine, no build, no runtime.

The native CMakeLists and fixture are resolved without a lane-local path: from
P2_NATIVE_REPO (git show), the legacy sibling layout, or skipped cleanly.
"""

import importlib.util
import os
import subprocess
import unittest
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "experimental" / "pikmin2_challenge_persistence_engine_membership.py"
spec = importlib.util.spec_from_file_location("p2_persist_membership", MOD)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def native_file(relpath):
    repo = os.environ.get("P2_NATIVE_REPO")
    if repo:
        proc = subprocess.run(["git", "-C", repo, "show", "HEAD:" + relpath],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
    legacy = Path(__file__).resolve().parents[2] / "challenge-persistence-engine-membership-native-native" / relpath
    if legacy.is_file():
        return legacy.read_text(encoding="utf-8", errors="replace")
    raise unittest.SkipTest("native file not resolvable here: " + relpath)


def sample_log(stage=adapter.STAGE):
    lines = [adapter.probe_marker(s, stage) for s in adapter.PROBE_STEMS]
    lines.append(adapter.PASS_MARKER + " markers=7")
    return "\n".join(lines) + "\n"


class MembershipContractTests(unittest.TestCase):
    def test_cmake_membership_ok(self):
        text = native_file("CMakeLists.txt")
        self.assertTrue(adapter.cmake_membership_ok(text))
        self.assertIn(adapter.MODULE_SOURCE, text)

    def test_cmake_commented_out_rejected(self):
        fake = "set(PC_PORT_SOURCES\n    pc_port/pc_a.cpp\n    # pc_port/pc_p2_challenge_persistence.cpp\n)\n"
        self.assertFalse(adapter.cmake_membership_ok(fake))
        self.assertFalse(adapter.cmake_membership_ok("set(PC_PORT_SOURCES\n    pc_port/pc_b.cpp\n)\n"))

    def test_fixture_not_local_copy(self):
        text = native_file("tools/p2_challenge_persistence_membership_fixture.cpp")
        self.assertTrue(adapter.fixture_is_not_local_copy(text))
        self.assertFalse(adapter.fixture_is_not_local_copy(
            '// x\n#include "../pc_port/pc_p2_challenge_persistence.cpp"\n'))

    def test_marker_log_ok(self):
        ok, detail = adapter.check_marker_log(sample_log())
        self.assertTrue(ok, detail)

    def test_marker_log_missing(self):
        text = sample_log().replace(adapter.probe_marker("UNLOCK") + "\n", "")
        ok, detail = adapter.check_marker_log(text)
        self.assertFalse(ok)
        self.assertIn("UNLOCK", detail)

    def test_marker_log_duplicate_rejected(self):
        text = sample_log() + adapter.probe_marker("REENTRY") + "\n"
        ok, detail = adapter.check_marker_log(text)
        self.assertFalse(ok)

    def test_marker_log_captain_down_rejected(self):
        text = sample_log() + "P2_FIXTURE_CAPTAIN_DOWN tick=0 hp=0.000 outcome=BLOCKED\n"
        ok, _ = adapter.check_marker_log(text)
        self.assertFalse(ok)

    def test_marker_log_no_pass_rejected(self):
        ok, _ = adapter.check_marker_log("\n".join(
            adapter.probe_marker(s) for s in adapter.PROBE_STEMS))
        self.assertFalse(ok)

    def test_marker_log_refusal_rejected(self):
        text = sample_log() + "P2_CHALLENGE_PERSISTENCE_REFUSED reason=unknown-stage\n"
        ok, _ = adapter.check_marker_log(text)
        self.assertFalse(ok)

    def test_checklist_pins(self):
        c = adapter.source_requirement_checklist()
        self.assertEqual(c["module_source"], adapter.MODULE_SOURCE)
        self.assertEqual(c["stage"]["ui_index"], 27)
        self.assertEqual(len(c["probe_stems"]), 7)
        self.assertEqual(c["consumer"]["issue"], 561)


if __name__ == "__main__":
    unittest.main()
