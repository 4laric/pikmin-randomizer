"""Acceptance tests for the BombOtakara93 provider seam (#573).

Covers the independent log observer plus a strict MinGW compile-and-run of
the engine-free provider ownership machine in
native/pc_port/pc_p2_bombotakara_policy.h. No runtime is launched here.
"""

import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

observer = importlib.import_module("experimental.pikmin2_bombotakara_payload_acceptance")

NATIVE = Path(r"C:\Users\alari\pikmin-randomizer\output\autofill-native-573")
POLICY = NATIVE / "pc_port" / "pc_p2_bombotakara_policy.h"
MINGW_GXX = Path(r"C:\msys64\mingw64\bin\g++.exe")

REQUEST_ONLY = """\
[PC Port] Experimental preview window set to 960x540 windowed and centered
P2_MUSE_BOMBOTAKARA573_BASELINE red=20 blue=0
P2_MUSE_BOMBOTAKARA573_STAGE generator=349001 source_id=93 chain=family
P2_MUSE_BOMBOTAKARA573_SCENARIO provider_seam generator=349001
P2_BOMBOTAKARA_PROVIDER_REQUEST contract=p2-bomb-payload-provider-1 generator=349001 missing=no_bomb_mgr_birth owner=#169/#186
P2_BOMBOTAKARA_PROVIDER_ABSENT generator=349001 state=awaiting_birth
P2_MUSE_BOMBOTAKARA573_BLOCKED reason=no_bomb_mgr_birth generator=349001 bound=1 requests=1 live_payloads=0
"""

FUTURE_NATURAL = """\
P2_BOMBOTAKARA_PROVIDER_REQUEST contract=p2-bomb-payload-provider-1 generator=349001 missing=no_bomb_mgr_birth owner=#169/#186
P2_BOMBOTAKARA_PAYLOAD_BORN generator=349001 payload=7001 accepted=1 stale=0 state=attached provider=1
P2_BOMBOTAKARA_PAYLOAD_CAPTURED generator=349001 payload=7001 joint=otakara attached=1 state=attached provider=1
P2_BOMBOTAKARA_BLAST generator=349001 payload=7001 center=0.0,0.0,0.0 radius=90.0 receivers=5 hits=4 pikmin_hits=3 teki_damage=500.0 navi_piki_damage=10.0 shared_primitive=1
P2_BOMBOTAKARA_BOMB_HIT generator=349001 payload=7001 pikmin=2 accepted=1 target_state=5 interaction=InteractBomb natural=1
P2_BOMBOTAKARA_PAYLOAD_DETONATED generator=349001 payload=7001 accepted=1 stale=0 already_done=0 detonations=1 provider=1
"""

STUB_ONLY = """\
P2_BOMBOTAKARA_CARRY generator=30 payload=40 state=bomb_wait joint=otakara
P2_BOMBOTAKARA_ARM generator=30 payload=40 arm_seconds=1.50 source=stimulateBomb
P2_BOMBOTAKARA_DETONATE generator=30 payload=40 trigger=contact detonated=1 exactly_once=1 total_detonations=1
P2_BOMBOTAKARA_BLAST generator=30 payload=40 center=0.0,0.0,0.0 radius=90.0 receivers=11 hits=10 pikmin_hits=10 teki_damage=500.0 navi_piki_damage=10.0 shared_primitive=1
"""


def _write_tmp(text):
    fd, path = tempfile.mkstemp(suffix=".log")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class TestPayloadObserver(unittest.TestCase):
    def _validate(self, text):
        path = _write_tmp(text)
        try:
            return observer.validate(path)
        finally:
            os.unlink(path)

    def test_request_only_is_honest_blocked(self):
        v = self._validate(REQUEST_ONLY)
        self.assertTrue(v["provider_request"])
        self.assertEqual(v["request_generator"], 349001)
        self.assertEqual(v["missing_reason"], "no_bomb_mgr_birth")
        self.assertTrue(v["provider_absent"])
        self.assertFalse(v["born"])
        self.assertFalse(v["stub_present"])
        self.assertEqual(v["injected"], [])
        self.assertFalse(v["gate1_attach_provider_linked"])
        self.assertFalse(v["gate3_blast_provider_linked"])

    def test_future_natural_chain_passes(self):
        v = self._validate(FUTURE_NATURAL)
        self.assertTrue(v["gate1_attach_provider_linked"])
        self.assertTrue(v["gate3_blast_provider_linked"])
        self.assertFalse(v["stub_present"])
        self.assertEqual(v["exactly_once_violations"], [])
        self.assertEqual(v["stale_violations"], [])

    def test_stub_blast_is_not_natural(self):
        v = self._validate(STUB_ONLY)
        self.assertTrue(v["stub_present"])
        self.assertFalse(v["gate1_attach_provider_linked"])
        self.assertFalse(v["gate3_blast_provider_linked"])

    def test_injection_rejected(self):
        v = self._validate(FUTURE_NATURAL + "P2_BOMBOTAKARA_INJECT_1 75 349001 contact\n")
        self.assertTrue(v["injected"])
        self.assertFalse(v["gate1_attach_provider_linked"])
        self.assertFalse(v["gate3_blast_provider_linked"])

    def test_second_detonation_flagged(self):
        double = FUTURE_NATURAL + (
            "P2_BOMBOTAKARA_PAYLOAD_DETONATED generator=349001 payload=7001 "
            "accepted=1 stale=0 already_done=0 detonations=2 provider=1\n")
        v = self._validate(double)
        self.assertTrue(v["exactly_once_violations"])
        self.assertFalse(v["gate3_blast_provider_linked"])

    def test_post_gone_event_flagged(self):
        text = (FUTURE_NATURAL
                + "P2_BOMBOTAKARA_PAYLOAD_CARRIER_GONE generator=349001 accepted=1 stale=0 state=gone no_stale_payload=1\n"
                + "P2_BOMBOTAKARA_PAYLOAD_BORN generator=349001 payload=7002 accepted=0 stale=1 state=gone provider=1\n")
        v = self._validate(text)
        self.assertTrue(v["stale_violations"])

    def test_unlinked_blast_not_natural(self):
        v = self._validate(
            "P2_BOMBOTAKARA_BLAST generator=30 payload=40 center=0.0,0.0,0.0 radius=90.0 "
            "receivers=5 hits=4 pikmin_hits=3 teki_damage=500.0 navi_piki_damage=10.0 shared_primitive=1\n")
        self.assertFalse(v["gate3_blast_provider_linked"])

    def test_empty_log(self):
        v = self._validate("")
        self.assertFalse(v["provider_request"])
        self.assertFalse(v["gate1_attach_provider_linked"])

    def test_cli_exit_codes(self):
        for text, code in ((REQUEST_ONLY, 2), (FUTURE_NATURAL, 0), (STUB_ONLY, 1)):
            path = _write_tmp(text)
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "experimental.pikmin2_bombotakara_payload_acceptance",
                     "--log", path],
                    capture_output=True, text=True, timeout=60, cwd=str(ROOT))
                self.assertEqual(proc.returncode, code, proc.stdout[-1000:])
            finally:
                os.unlink(path)


PROVIDER_TU = r"""
#include "pc_p2_bombotakara_policy.h"
#include <cassert>
#include <cstdio>
using namespace p2bombotakara_provider;
int main() {
    assert(std::string(kContract) == "p2-bomb-payload-provider-1");
    assert(std::string(kMissingReason) == "no_bomb_mgr_birth");
    PayloadOwnership own;
    assert(own.state() == PayloadState::AwaitingBirth);
    assert(!own.hasLivePayload());
    ProviderEventResult born = own.noteBorn(7001);
    assert(born.accepted && !born.stale);
    assert(own.hasLivePayload() && own.token() == 7001);
    ProviderEventResult dup = own.noteBorn(7002);
    assert(!dup.accepted && !dup.stale);  // single mTargetCreature refused, not stacked
    assert(own.token() == 7001);
    ProviderEventResult det = own.noteDetonated(7001);
    assert(det.accepted && own.detonations() == 1);
    ProviderEventResult det2 = own.noteDetonated(7001);
    assert(!det2.accepted && det2.alreadyDone);  // exactly-once
    assert(own.detonations() == 1);
    ProviderEventResult wrong = own.noteDetonated(9999);
    assert(!wrong.accepted && wrong.stale);  // foreign token stale
    ProviderEventResult rel = own.noteReleased(7001);
    assert(!rel.accepted && rel.alreadyDone);
    ProviderEventResult gone = own.noteCarrierGone();
    assert(gone.accepted && own.state() == PayloadState::Gone && own.token() == 0);
    ProviderEventResult late = own.noteBorn(7003);
    assert(!late.accepted && late.stale);  // Gone stays Gone: no stale payload
    assert(PayloadOwnership::attributeToCarrier(true) && !PayloadOwnership::attributeToCarrier(false));
    std::printf("PROVIDER_OWNERSHIP_OK\n");
    return 0;
}
"""


class TestProviderOwnershipNative(unittest.TestCase):
    def test_policy_compiles_strict_and_machine_holds(self):
        if not MINGW_GXX.exists():
            self.skipTest("MinGW g++ unavailable")
        if not POLICY.exists():
            self.skipTest("policy header absent")
        tmp = Path(tempfile.mkdtemp())
        try:
            src = tmp / "provider_check.cpp"
            src.write_text(PROVIDER_TU, encoding="utf-8")
            exe = tmp / "provider_check.exe"
            env = dict(os.environ)
            env["PATH"] = r"C:\msys64\mingw64\bin;" + env.get("PATH", "")
            build = subprocess.run(
                [str(MINGW_GXX), "-std=c++17", "-O1", "-Wall", "-Wextra",
                 "-Werror", "-I", str(NATIVE / "pc_port"), str(src),
                 "-o", str(exe)],
                capture_output=True, text=True, timeout=180, env=env)
            self.assertEqual(build.returncode, 0, build.stderr[-2000:])
            run = subprocess.run([str(exe)], capture_output=True, text=True,
                                 timeout=60, env=env)
            self.assertEqual(run.returncode, 0, run.stdout[-1000:])
            self.assertIn("PROVIDER_OWNERSHIP_OK", run.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
