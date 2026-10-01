"""Contract tests for the piki-birth challenge-setup fix (issue #741).

Pins the fix contract and exercises the run-log verifier: canonical
challenge boot agreement, missing create/order markers, null-path hits,
panic, captain-down, injected lines, and empty logs. The behavioral proof
(headed chal4 boot with live squad births) lives in the lane's native
build + run evidence; agreement here alone never passes acceptance.
"""
import unittest

from experimental.pikmin2_piki_birth_fix import (
    CONSUMER_ISSUE,
    ENGINE_EDITS,
    PROVIDER,
    provider_contract,
    parse_run_markers,
    verify_boot,
)

GOOD = "\n".join([
    "P2_PIKI_INITSTAGE challenge=1",
    "P2_PIKI_CREATE requested=102 challenge=1",
    "P2_PIKI_CREATE_DONE max=102 size=0",
    "P2_PIKI_FINASETUP pool_max=102 pool_size=0",
    "P2_CHALLENGE_SQUAD squad_alive=20",
])


class ContractTests(unittest.TestCase):
    def test_contract_shape(self):
        contract = provider_contract()
        self.assertEqual(contract["schema"], PROVIDER)
        self.assertEqual(contract["consumer_issue"], CONSUMER_ISSUE)
        self.assertEqual(contract["consumer_issue"], 567)
        self.assertIn(721, contract["depends"])
        self.assertIn(186, contract["depends"])
        self.assertFalse(contract["runtime_claim"])
        self.assertEqual(len(contract["engine_edits"]), 5)
        self.assertIn("native/src/plugPikiKando/pikiMgr.cpp",
                      contract["engine_edits"])
        self.assertIn("native/src/plugPikiColin/newPikiGame.cpp",
                      contract["engine_edits"])

    def test_engine_edits_exact(self):
        self.assertEqual(list(ENGINE_EDITS), [
            "native/src/plugPikiKando/gameCoreSection.cpp",
            "native/src/plugPikiColin/newPikiGame.cpp",
            "native/src/plugPikiKando/objectMgr.cpp",
            "native/src/plugPikiKando/pikiMgr.cpp",
            "native/src/plugPikiKando/goalItem.cpp",
        ])


class VerifyBootTests(unittest.TestCase):
    def test_canonical_boot_agrees(self):
        result = verify_boot(parse_run_markers(GOOD))
        self.assertTrue(result["verdict"], result["problems"])
        self.assertEqual(result["create_requested"], 102)
        self.assertEqual(result["pool_max"], 102)
        self.assertEqual(result["squad_alive_max"], 20)

    def test_missing_create_refused(self):
        result = verify_boot(parse_run_markers("P2_PIKI_INITSTAGE challenge=1"))
        self.assertFalse(result["verdict"])
        self.assertIn("no-create-at-all", result["problems"])

    def test_challenge_flag_anomaly_recorded(self):
        log = GOOD.replace("challenge=1", "challenge=0")
        result = verify_boot(parse_run_markers(log))
        self.assertFalse(result["verdict"])
        self.assertIn("create-challenge-flag-[0]", result["problems"])

    def test_capstop_drain_reported(self):
        log = GOOD + "\nP2_PIKI_BIRTH_CAPSTOP queued=20\nP2_PIKI_DISPENSE_CAPSTOP queued=20"
        markers = parse_run_markers(log)
        self.assertEqual(markers["capstop"], [20])
        self.assertEqual(markers["dispense_capstop"], [20])
        result = verify_boot(markers)
        self.assertTrue(result["drained_quietly"])
        self.assertEqual(result["capstop_ticks"], 1)

    def test_baseinf_and_counters_parsed(self):
        log = GOOD + "\nP2_PIKI_BASEINF free=100 active=0 challenge=0\nP2_PIKI_COUNTERS formation=0 free=0 me=100 work=0 born=0 all=160"
        markers = parse_run_markers(log)
        self.assertEqual(markers["baseinf"], [(100, 0, 0)])
        self.assertEqual(markers["counters"], [(0, 0, 100, 0, 0, 160)])
        result = verify_boot(markers)
        self.assertEqual(result["baseinf"], (100, 0, 0))
        self.assertEqual(result["counters"], (0, 0, 100, 0, 0, 160))

    def test_zero_pool_refused(self):
        log = GOOD.replace("requested=102", "requested=0")
        result = verify_boot(parse_run_markers(log))
        self.assertFalse(result["verdict"])
        self.assertIn("create-requested-0", result["problems"])

    def test_null_path_refused(self):
        log = GOOD + "\nP2_PIKI_BIRTH_POOL_NULL total=19 pool_max=102 pool_size=0"
        result = verify_boot(parse_run_markers(log))
        self.assertFalse(result["verdict"])
        self.assertIn("birth-null-path-hit", result["problems"])

    def test_halt_refused(self):
        log = GOOD + "\nP2_PIKI_BIRTH_HALT pikiMgr=1 mapPikis=19 container=19 pool_max=102 pool_size=0"
        result = verify_boot(parse_run_markers(log))
        self.assertFalse(result["verdict"])
        self.assertIn("birth-null-path-hit", result["problems"])

    def test_pool_refusal_refused(self):
        log = GOOD + "\nP2_PIKI_POOL_FULL num=102 max=102"
        result = verify_boot(parse_run_markers(log))
        self.assertFalse(result["verdict"])
        self.assertIn("pool-or-cap-refusal-hit", result["problems"])

    def test_panic_refused(self):
        log = GOOD + "\n[PANIC] src/sysDolphin/system.cpp:1229 *** PIKI BIRTH FAILED !!!"
        result = verify_boot(parse_run_markers(log))
        self.assertFalse(result["verdict"])
        self.assertIn("piki-birth-panic-present", result["problems"])

    def test_captain_down_refused(self):
        log = GOOD + "\nP2_FIXTURE_CAPTAIN_DOWN tick=4 hp=0.500 outcome=BLOCKED"
        result = verify_boot(parse_run_markers(log))
        self.assertFalse(result["verdict"])
        self.assertIn("captain-down-cannot-substantiate", result["problems"])

    def test_no_live_squad_refused(self):
        log = "\n".join(l for l in GOOD.splitlines() if "squad_alive" not in l)
        result = verify_boot(parse_run_markers(log))
        self.assertFalse(result["verdict"])
        self.assertIn("no-live-squad", result["problems"])

    def test_injected_refused(self):
        result = verify_boot(parse_run_markers(GOOD + "\nP2_PIKI_INJECT x=1"))
        self.assertFalse(result["verdict"])
        self.assertIn("injected-markers-present", result["problems"])

    def test_empty_log_refused(self):
        result = verify_boot(parse_run_markers(""))
        self.assertFalse(result["verdict"])
        self.assertIn("no-create-at-all", result["problems"])


if __name__ == "__main__":
    unittest.main()
