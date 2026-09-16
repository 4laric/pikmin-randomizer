"""Focused tests for the l67 fixture-build preflight adapter (#507).

Each test reproduces one observed l52-l61 failure mode against synthetic
inputs, plus the real maintained-builder rejection on the l60 link line.
No build, configure, or lane worktree is touched; the only subprocesses
spawned are hermetic fakes on PATH in tmp directories.
"""

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_muse_fixturetools import (  # noqa: E402
    diagnose_commands,
    find_ninja,
    preflight,
    split_windows_args,
    unwrap_command,
)

HEAD = "7b9ecaa668fd55332073446cdbdaf6424b209ea7"

# The exact builder-selected link line shape that rejected l60-fixture-01
# and the l61 fixture-build under the maintained script (shortened paths;
# the contract is the `@...rsp ... -o ...` combination, not the prefix).
RSP_LINK_LINE = (
    "C:\\Windows\\system32\\cmd.exe /C \"cd . && C:\\msys64\\mingw64\\bin\\"
    "g++.exe -O3 -DNDEBUG -flto=auto -mconsole @CMakeFiles\\pikmin_pc.rsp "
    "-o bin\\nectar.exe -Wl,--out-implib,libnectar.dll.a && cd .\""
)

PLAIN_COMPILE_LINE = (
    "C:\\msys64\\mingw64\\bin\\g++.exe -O3 -DNDEBUG -DTEST_DEFINE=1 "
    "-I..\\include -c ..\\pc_port\\pc_main.cpp -o pc_main.cpp.obj"
)


def make_tree():
    tmp = Path(tempfile.mkdtemp(prefix="l67-preflight-"))
    source = tmp / "native"
    (source / "pc_port").mkdir(parents=True)
    (source / "CMakeLists.txt").write_text("cmake_minimum_required()\n")
    (source / "pc_port" / "pc_main.cpp").write_text("int main(){}\n")
    build = tmp / "build"
    build.mkdir()
    (build / "CMakeCache.txt").write_text(
        "CMAKE_GENERATOR:INTERNAL=Ninja\n"
        "CMAKE_HOME_DIRECTORY:STATIC=" + str(source) + "\n"
        "CMAKE_C_COMPILER:FILEPATH=C:/msys64/mingw64/bin/gcc.exe\n"
        "CMAKE_CXX_COMPILER:FILEPATH=C:/msys64/mingw64/bin/g++.exe\n"
        "CMAKE_MAKE_PROGRAM:FILEPATH=C:/ninja/ninja.exe\n"
        "CMAKE_BUILD_TYPE:STRING=Release\n")
    fixture = source / "tools" / "probe.cpp"
    fixture.parent.mkdir()
    fixture.write_text("int probe(){return 0;}\n")
    output = tmp / "out"
    return tmp, source, build, fixture, output


def write_fake_exe(directory, name, script):
    path = Path(directory) / name
    path.write_text(script)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


class NinjaDiscoveryTests(unittest.TestCase):
    def test_missing_ninja_reports_remediation(self):
        # Hermetic PATH plus a blocked `ninja` package import: no candidate
        # exists, so discovery must fail instead of crashing.
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(sys.modules, {"ninja": None}):
                ninja, notes = find_ninja(search_path=tmp, hint=None)
        self.assertIsNone(ninja)
        self.assertIsInstance(notes, list)
        self.assertTrue(notes)

    def test_hint_hit_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = write_fake_exe(tmp, "ninja.exe", "x")
            ninja, _ = find_ninja(search_path=tmp, hint=str(fake))
            self.assertEqual(ninja, fake)


class GrammarTests(unittest.TestCase):
    def test_response_reference_is_unparsable(self):
        self.assertIsNone(split_windows_args(
            "g++.exe -O3 @CMakeFiles\\pikmin_pc.rsp -o bin\\nectar.exe"))

    def test_empty_command_is_unparsable(self):
        self.assertIsNone(split_windows_args("   "))

    def test_plain_compile_parses(self):
        args = split_windows_args(PLAIN_COMPILE_LINE)
        self.assertIsNotNone(args)
        self.assertIn("-c", args)
        self.assertIn("-o", args)

    def test_wrapper_unwrap(self):
        inner = unwrap_command(RSP_LINK_LINE)
        self.assertIn("@CMakeFiles\\pikmin_pc.rsp", inner)
        self.assertNotIn("cmd.exe", inner)


class DiagnoseTests(unittest.TestCase):
    def test_rsp_link_line_diagnosed(self):
        result = diagnose_commands(RSP_LINK_LINE + "\n" + PLAIN_COMPILE_LINE)
        self.assertFalse(result["ok"])
        self.assertEqual(result["selected"], 2)
        self.assertEqual(len(result["response_lines"]), 1)
        self.assertIn("pikmin_pc.rsp",
                      result["response_lines"][0]["reference"])

    def test_clean_commands_pass(self):
        result = diagnose_commands(PLAIN_COMPILE_LINE + "\n"
                                   + "ar.exe qc libx.a obj1.obj obj2.obj\n")
        # The archive line has no ' -o ' selector... it has neither -c nor
        # -o, so only the compile line is selected and clean.
        self.assertTrue(result["ok"])
        self.assertEqual(result["selected"], 1)

    def test_unselected_lines_ignored(self):
        self.assertTrue(diagnose_commands("ninja: no work to do.\n")["ok"])


class PreflightPathTests(unittest.TestCase):
    def test_missing_source_files_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = preflight(Path(tmp) / "nosuch", Path(tmp), Path(tmp),
                               Path(tmp) / "f.cpp", HEAD)
            self.assertEqual(report["status"], "rejected")
            self.assertEqual(report["checks"][-1]["check"], "source-paths")

    def test_missing_cache_rejected(self):
        tmp, source, build, fixture, output = make_tree()
        (build / "CMakeCache.txt").unlink()
        report = preflight(source, build, output, fixture, HEAD)
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["checks"][-1]["check"], "build-paths")

    def test_wrong_generator_rejected(self):
        tmp, source, build, fixture, output = make_tree()
        cache = build / "CMakeCache.txt"
        cache.write_text(cache.read_text().replace(
            "CMAKE_GENERATOR:INTERNAL=Ninja",
            "CMAKE_GENERATOR:INTERNAL=Unix Makefiles"))
        report = preflight(source, build, output, fixture, HEAD)
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["checks"][-1]["check"], "generator")
        self.assertIn("-G Ninja",
                      report["checks"][-1]["remediation"])

    def test_configured_source_mismatch_rejected(self):
        tmp, source, build, fixture, output = make_tree()
        cache = build / "CMakeCache.txt"
        cache.write_text(cache.read_text().replace(
            str(source), str(tmp / "other-native")))
        report = preflight(source, build, output, fixture, HEAD)
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["checks"][-1]["check"],
                         "configured-source")

    def test_missing_toolchain_rejected(self):
        tmp, source, build, fixture, output = make_tree()
        cache = build / "CMakeCache.txt"
        cache.write_text(cache.read_text().replace(
            "C:/msys64/mingw64/bin/g++.exe", "C:/nonexistent/g++.exe"))
        report = preflight(source, build, output, fixture, HEAD)
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["checks"][-1]["check"], "toolchain")

    def test_output_inside_source_rejected(self):
        tmp, source, build, fixture, output = make_tree()
        report = preflight(source, build, source / "inner-out", fixture,
                           HEAD)
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["checks"][-1]["check"], "output-paths")

    def test_bad_fixture_suffix_rejected(self):
        tmp, source, build, fixture, output = make_tree()
        bad = source / "tools" / "probe.txt"
        bad.write_text("x")
        report = preflight(source, build, output, bad, HEAD)
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["checks"][-1]["check"], "fixture-paths")

    def test_malformed_expected_head_rejected(self):
        tmp, source, build, fixture, output = make_tree()
        report = preflight(source, build, output, fixture, "short")
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["checks"][-1]["check"], "expected-head")


class PreflightLiveProbeTests(unittest.TestCase):
    """The toolchain gate fires before any live probe when Ninja is gone."""

    def test_missing_ninja_gate_before_live_probes(self):
        tmp, source, build, fixture, output = make_tree()
        with mock.patch(
                "experimental.pikmin2_muse_fixturetools.find_ninja",
                return_value=(None, ["no candidate"])):
            report = preflight(source, build, output, fixture, HEAD,
                               search_path=str(tmp))
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["checks"][-1]["check"], "ninja")
        self.assertIn("CMAKE_MAKE_PROGRAM",
                      report["checks"][-1]["remediation"])


class JsonContractTests(unittest.TestCase):
    def test_report_is_json_serialisable(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = preflight(Path(tmp) / "nope", Path(tmp), Path(tmp),
                               Path(tmp) / "f.cpp", HEAD)
            json.dumps(report)
            self.assertEqual(report["checks"][-1]["check"], "source-paths")


if __name__ == "__main__":
    unittest.main()
