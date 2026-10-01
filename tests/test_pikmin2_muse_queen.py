"""Focused regression for the muse-queen independent gate-5 review (#496).

Covers the independent reviewer (experimental.pikmin2_muse_queen) against the
real cited lane24 candidate log plus synthetic negative/edge cases, and
compile-checks the additive C++ marker observer
(native/tools/p2_muse_queen_fixture.cpp) with strict MinGW when available.

No Queen/King/shared native module is touched; the legacy lane24 worktrees are
only read.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_muse_queen import (  # noqa: E402
    STAGING_MARKERS,
    review_queen_gate5_log,
)

CANDIDATE_LOG = Path(
    r"C:\Users\alari\pikmin-randomizer\output\dsw\l24-out\queen-creature-runtime"
    r"\queen\62b8ff57457c4edb90dd16958f665118\native.log"
)
CPP_TOOL = ROOT / "native" / "tools" / "p2_muse_queen_fixture.cpp"
MINGW_GXX = Path(r"C:\msys64\mingw64\bin\g++.exe")

BASE_CHAIN = """\
[PC Port] Experimental preview window set to 960x540 windowed and centered
P2_QUEEN_TEKI_READY generator=230010 type=3 binding=creature_host health=5000.0 scale=1.00 xyz=78.075,30.0,11.0
P2_QUEEN_TEKI_HOST_AI_SUPPRESSED generator=230010 method=param_seam sight_attack_indices=9 eat_state=CHAPPYSTATE_Unk8 latch_preserved=1
P2_QUEEN_CREATURE_BASELINE red=64
P2_QUEEN_CREATURE_ARMED no_injection=1 deploy_once=1
P2_QUEEN_TEKI_FLICK generator=230010 shaken=0 blown_threshold=30 stuck_threshold=5
P2_QUEEN_TEKI_FLICK generator=230010 shaken=1 blown_threshold=35 stuck_threshold=10
P2_QUEEN_TEKI_FLICK generator=230010 shaken=2 blown_threshold=50 stuck_threshold=15
P2_QUEEN_TEKI_CORPSE generator=230010 health=0.0 carcass_pellet=0
P2_QUEEN_CREATURE_DEATH_SEEN receiver=engine host_health=0
P2_QUEEN_CREATURE_CORPSE_PELLET found=1
P2_QUEEN_CREATURE_CARRY carcass_state=0 carry=3 transport=6 nearest=8.5 pokos=0
P2_QUEEN_CREATURE_CARRY carcass_state=1 carry=3 transport=0 nearest=22.0 pokos=0
[Pikipelago] P2_POD_RECEIPT id=corpse:queen:230010 value=2 new=1 pokos=2 seeds=0
PASS P2_QUEEN_CREATURE_RUNTIME
"""


def _write_tmp(text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".log")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class TestQueenGate5Reviewer(unittest.TestCase):
    def test_candidate_log_passes_with_caveats(self):
        if not CANDIDATE_LOG.exists():
            self.skipTest(f"candidate log absent: {CANDIDATE_LOG}")
        v = review_queen_gate5_log(CANDIDATE_LOG, expect_generator="230010")
        self.assertTrue(v.ok, f"candidate chain rejected: {v.failures}")
        self.assertEqual(v.generator, "230010")
        self.assertEqual(v.host_type, "3")
        self.assertEqual(v.ready_line, 727)
        self.assertEqual(v.receipt_line, 1386)
        self.assertEqual(v.receipt_value, 2)
        self.assertEqual(v.staging_hits, [])
        self.assertGreaterEqual(v.flick_count, 3)
        self.assertGreater(v.max_transport, 0)
        # Caveats are always reported, never silent.
        self.assertEqual(len(v.caveats), 3)

    def test_synthetic_clean_chain_passes(self):
        path = _write_tmp(BASE_CHAIN)
        try:
            v = review_queen_gate5_log(path, expect_generator="230010")
            self.assertTrue(v.ok, v.failures)
            self.assertEqual(v.max_transport, 6)
            self.assertEqual(v.carry_at_latch, 3)
        finally:
            os.unlink(path)

    def test_benign_no_injection_substring_does_not_trip(self):
        # "no_injection=1" contains "INJECT" as a substring; exact-token
        # matching must not flag it.
        path = _write_tmp(BASE_CHAIN)
        try:
            v = review_queen_gate5_log(path)
            self.assertTrue(v.ok, v.failures)
            self.assertEqual(v.staging_hits, [])
        finally:
            os.unlink(path)

    def test_forced_transport_marker_fails(self):
        bad = BASE_CHAIN + "P2_QUEEN_TEKI_FORCED_TRANSPORT generator=230010\n"
        path = _write_tmp(bad)
        try:
            v = review_queen_gate5_log(path)
            self.assertFalse(v.ok)
            self.assertTrue(any("staging" in f for f in v.failures))
        finally:
            os.unlink(path)

    def test_each_staging_marker_fails(self):
        for marker in STAGING_MARKERS:
            if marker == "TransportMode":
                line = "p->changeMode(TransportMode,n) forced\n"
            else:
                line = f"{marker} generator=230010\n"
            path = _write_tmp(BASE_CHAIN + line)
            try:
                v = review_queen_gate5_log(path)
                self.assertFalse(v.ok, f"marker {marker} not rejected")
            finally:
                os.unlink(path)

    def test_missing_receipt_fails(self):
        cut = "\n".join(l for l in BASE_CHAIN.splitlines() if "P2_POD_RECEIPT" not in l)
        path = _write_tmp(cut + "\n")
        try:
            v = review_queen_gate5_log(path)
            self.assertFalse(v.ok)
            self.assertTrue(any("missing chain" in f for f in v.failures))
        finally:
            os.unlink(path)

    def test_wrong_health_fails(self):
        bad = BASE_CHAIN.replace("health=5000.0", "health=1300.0")
        path = _write_tmp(bad)
        try:
            v = review_queen_gate5_log(path)
            self.assertFalse(v.ok)
            self.assertTrue(any("health" in f for f in v.failures))
        finally:
            os.unlink(path)

    def test_generator_mismatch_fails(self):
        path = _write_tmp(BASE_CHAIN)
        try:
            v = review_queen_gate5_log(path, expect_generator="999999")
            self.assertFalse(v.ok)
        finally:
            os.unlink(path)

    def test_receipt_generator_crosscheck_fails(self):
        bad = BASE_CHAIN.replace("id=corpse:queen:230010", "id=corpse:queen:221010")
        path = _write_tmp(bad)
        try:
            v = review_queen_gate5_log(path)
            self.assertFalse(v.ok)
        finally:
            os.unlink(path)

    def test_empty_log_fails(self):
        path = _write_tmp("")
        try:
            v = review_queen_gate5_log(path)
            self.assertFalse(v.ok)
        finally:
            os.unlink(path)

    def test_cpp_observer_builds_and_agrees(self):
        if not MINGW_GXX.exists():
            self.skipTest("MinGW g++ unavailable")
        if not CPP_TOOL.exists():
            self.skipTest(f"C++ tool absent: {CPP_TOOL}")
        tmp = Path(tempfile.mkdtemp())
        try:
            exe = tmp / "p2_muse_queen_check.exe"
            src = os.path.realpath(CPP_TOOL)
            # MinGW requires its bin dir on PATH (cc1plus DLLs), per the
            # fan-out private-build recipe; without it g++ dies silently.
            env = dict(os.environ)
            env["PATH"] = r"C:\msys64\mingw64\bin;" + env.get("PATH", "")
            build = subprocess.run(
                [str(MINGW_GXX), "-std=c++17", "-O1", "-Wall", "-Wextra",
                 "-Werror", src, "-o", str(exe)],
                capture_output=True, text=True, timeout=120, env=env,
            )
            self.assertEqual(build.returncode, 0, build.stderr[-2000:])
            log = tmp / "chain.log"
            log.write_text(BASE_CHAIN, encoding="utf-8")
            with open(log, "rb") as fh:
                run = subprocess.run([str(exe)], stdin=fh,
                                     capture_output=True, text=True, timeout=60,
                                     env=env)
            self.assertEqual(run.returncode, 0, run.stdout[-2000:])
            self.assertIn("VERDICT PASS", run.stdout)
            bad = tmp / "bad.log"
            bad.write_text(BASE_CHAIN + "P2_POD_CAPTAIN_RETURN pokos_unchanged=1 seeds=0\n",
                           encoding="utf-8")
            with open(bad, "rb") as fh:
                run_bad = subprocess.run([str(exe)], stdin=fh,
                                         capture_output=True, text=True, timeout=60,
                                         env=env)
            self.assertNotEqual(run_bad.returncode, 0)
            self.assertIn("VERDICT FAIL", run_bad.stdout)
            # A staging marker mid-chain (before the receipt) must also fail.
            mid = BASE_CHAIN.replace(
                "P2_QUEEN_TEKI_CORPSE",
                "P2_QUEEN_NATURAL_REPIN staging=1\nP2_QUEEN_TEKI_CORPSE", 1)
            mid_path = tmp / "mid.log"
            mid_path.write_text(mid, encoding="utf-8")
            with open(mid_path, "rb") as fh:
                run_mid = subprocess.run([str(exe)], stdin=fh,
                                         capture_output=True, text=True, timeout=60,
                                         env=env)
            self.assertNotEqual(run_mid.returncode, 0)
            self.assertIn("VERDICT FAIL", run_mid.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
