"""Focused tests for the cave-generator landing-presence checker (#129 review).

All fixtures are synthetic temp trees exercising the presence boundary
(module files, hook markers, partial landings, missing tree). No value here
is claimed as retail fact and no real worktree path is asserted; real-pin
evidence lives in docs/PIKMIN2_CAVE_GENERATOR_LANDING_REVIEW.md.
"""
import importlib.util
import unittest
from pathlib import Path
import tempfile

ADAPTER = (Path(__file__).resolve().parents[1] / "experimental"
           / "pikmin2_cave_generator_landing_check.py")


def load_adapter():
    spec = importlib.util.spec_from_file_location("landing_check", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_tree(root, header=True, header_marker=True, tu=True, tu_marker=True,
              hook_include=True, hook_call=True):
    port = Path(root) / "pc_port"
    port.mkdir(parents=True, exist_ok=True)
    if header:
        body = ("inline bool pc_p2_cave_generate_run();\n" if header_marker
                else "// unrelated header\n")
        (port / "pc_p2_cave_generate.h").write_text(body, encoding="utf-8")
    if tu:
        body = ("const char* kP2CaveGenerateModule = \"v1\";\n" if tu_marker
                else "// unrelated tu\n")
        (port / "pc_p2_cave_generate.cpp").write_text(body, encoding="utf-8")
    lines = []
    if hook_include:
        lines.append('#include "pc_p2_cave_generate.h"')
    if hook_call:
        lines.append("    pc_p2_cave_generate_run();")
    (port / "pc_p2_cave.cpp").write_text("\n".join(lines) + "\n", encoding="utf-8")


class LandingCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_full_landing_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp)
            report = self.mod.check_landing(tmp)
            self.assertTrue(report["passed"])
            self.assertTrue(all(report["checks"].values()))

    def test_missing_header_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp, header=False)
            report = self.mod.check_landing(tmp)
            self.assertFalse(report["passed"])
            self.assertFalse(report["checks"]["module_header"])
            self.assertTrue(report["checks"]["hook_call"])

    def test_header_without_marker_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp, header_marker=False)
            report = self.mod.check_landing(tmp)
            self.assertFalse(report["checks"]["module_header"])

    def test_missing_tu_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp, tu=False)
            report = self.mod.check_landing(tmp)
            self.assertFalse(report["checks"]["module_tu"])

    def test_include_without_call_is_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp, hook_call=False)
            report = self.mod.check_landing(tmp)
            self.assertTrue(report["checks"]["hook_include"])
            self.assertFalse(report["checks"]["hook_call"])
            self.assertFalse(report["passed"])

    def test_missing_tree_fails_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.mod.check_landing(str(Path(tmp) / "absent"))
            self.assertFalse(report["passed"])
            self.assertFalse(any(report["checks"].values()))

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_tree(tmp)
            with self.assertRaises(SystemExit) as ok:
                self.mod.main(["--native", tmp])
            self.assertEqual(ok.exception.code, 0)
            (Path(tmp) / "pc_port" / "pc_p2_cave_generate.h").unlink()
            with self.assertRaises(SystemExit) as bad:
                self.mod.main(["--native", tmp])
            self.assertEqual(bad.exception.code, 1)


if __name__ == "__main__":
    unittest.main()