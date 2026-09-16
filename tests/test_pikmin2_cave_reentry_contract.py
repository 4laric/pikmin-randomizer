"""Focused tests for the cave re-entry contract checker (#488 review).

All fixtures are synthetic temp trees and synthetic logs exercising the
presence/sequence boundary. No value here is claimed as retail fact and no
real worktree path or run log is asserted; real-pin evidence lives in
docs/PIKMIN2_CAVE_REENTRY_PROVIDER_REVIEW.md.
"""
import importlib.util
import unittest
from pathlib import Path
import tempfile

ADAPTER = (Path(__file__).resolve().parents[1] / "experimental"
           / "pikmin2_cave_reentry_contract.py")


def load_adapter():
    spec = importlib.util.spec_from_file_location("reentry_contract", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GOOD_LOG = """P2_LANE11_SQUAD red=16 yellow=1 purple=1 bulbmin=1
P2_LANE11_WRITE ok=1
P2_CAVE_TRANSFER_3
P2_LANE11_READ bulbmin=1 observed=5000
P2_CAVE_RESTORE species=5 maturity=0
PASS P2_LANE11_RESTORE
"""


def make_tree(root, restore=True, runtime=True, tests=True, schema=True):
    port = Path(root) / "engine" / "pc_port"
    port.mkdir(parents=True, exist_ok=True)
    exp = Path(root) / "experimental"
    exp.mkdir(parents=True, exist_ok=True)
    tst = Path(root) / "tests"
    tst.mkdir(parents=True, exist_ok=True)
    tools = Path(root) / "engine" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    (port / "pc_p2_cave.cpp").write_text(
        'printf("P2_CAVE_RESTORE species=%d maturity=%d\\n");\n' if restore
        else "// no restore emitter\n", encoding="utf-8")
    (exp / "pikmin2_cave_restart_runtime.py").write_text(
        "P2_LANE11_WRITE\nP2_CAVE_TRANSFER_3\nPASS P2_LANE11_RESTORE\n" if runtime
        else "# stub\n", encoding="utf-8")
    (tst / "test_pikmin2_cave_restart_runtime.py").write_text(
        "class T: pass\n" if tests else "", encoding="utf-8")
    (tools / "test_p2_cave_transfer.cpp").write_text(
        "P2_CAVE_TRANSFER_3\n" if schema else "// nothing\n", encoding="utf-8")


class ReentryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_full_provider_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp)
            report = self.mod.check_provider(tmp)
            self.assertTrue(report["passed"])
            self.assertTrue(all(report["checks"].values()))

    def test_each_missing_piece_fails_named_check(self):
        cases = [
            ({"restore": False}, "restore_emitter"),
            ({"runtime": False}, "restart_validator"),
            ({"tests": False}, "restart_tests"),
            ({"schema": False}, "transfer_schema"),
        ]
        for kwargs, key in cases:
            with self.subTest(kwargs=kwargs):
                with tempfile.TemporaryDirectory() as tmp:
                    make_tree(tmp, **kwargs)
                    report = self.mod.check_provider(tmp)
                    self.assertFalse(report["checks"][key])
                    self.assertFalse(report["passed"])

    def test_good_log_passes_with_staged_recorded(self):
        report = self.mod.check_runlog(GOOD_LOG, staged=True)
        self.assertTrue(report["passed"])
        self.assertEqual(report["restore_count"], 1)
        self.assertTrue(report["staged"])

    def test_staged_flag_never_inferred(self):
        report = self.mod.check_runlog(GOOD_LOG, staged=None)
        self.assertTrue(report["passed"])
        self.assertIsNone(report["staged"])
        report = self.mod.check_runlog(GOOD_LOG, staged=False)
        self.assertTrue(report["passed"])
        self.assertFalse(report["staged"])

    def test_out_of_order_markers_fail(self):
        lines = GOOD_LOG.splitlines()
        bad = "\n".join([lines[5], lines[0], lines[1], lines[2], lines[3], lines[4]]) + "\n"
        report = self.mod.check_runlog(bad, staged=True)
        self.assertFalse(report["checks"]["sequence_ordered"])
        self.assertFalse(report["passed"])

    def test_missing_pass_fails(self):
        bad = GOOD_LOG.replace("PASS P2_LANE11_RESTORE\n", "")
        report = self.mod.check_runlog(bad, staged=True)
        self.assertFalse(report["checks"]["restore_pass"])
        self.assertFalse(report["passed"])

    def test_no_restore_lines_fails(self):
        bad = "\n".join(l for l in GOOD_LOG.splitlines()
                        if "P2_CAVE_RESTORE" not in l) + "\n"
        report = self.mod.check_runlog(bad, staged=True)
        self.assertFalse(report["checks"]["restore_observed"])
        self.assertEqual(report["restore_count"], 0)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp)
            log = Path(tmp) / "run.log"
            log.write_text(GOOD_LOG, encoding="utf-8")
            with self.assertRaises(SystemExit) as ok:
                self.mod.main(["--native", tmp, "--log", str(log), "--staged", "yes"])
            self.assertEqual(ok.exception.code, 0)
            (Path(tmp) / "engine" / "pc_port" / "pc_p2_cave.cpp").unlink()
            with self.assertRaises(SystemExit) as bad:
                self.mod.main(["--native", tmp, "--log", str(log)])
            self.assertEqual(bad.exception.code, 1)


if __name__ == "__main__":
    unittest.main()