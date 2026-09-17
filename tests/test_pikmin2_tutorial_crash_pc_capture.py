"""Focused fail-closed tests for the tutorial post-audio crash-PC capture (#750)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "crash_pc_capture",
    ROOT / "experimental" / "pikmin2_tutorial_crash_pc_capture.py")
capture = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(capture)


def fault_record(module="C:\\game\\p2_tutorial_p1_runtime.exe", address=0x140001234,
                 offset=0x1234, symbol=None):
    return {"exit_code": 3221225477,
            "fault": {"code": 3221225477, "address": address, "access": 0,
                      "target": 0, "module": module, "offset": offset,
                      "nearest_export": symbol}}


class CollapseTests(unittest.TestCase):
    def test_outside_exe_narrows_audio_host(self):
        rec = fault_record(module="C:\\Windows\\System32\\audio.dll")
        verdict, detail = capture.collapse_suspects(rec)
        self.assertEqual(verdict, "NARROWED-AUDIO-HOST")
        self.assertIn("ranks 1/3", detail)

    def test_inside_exe_with_symbol(self):
        rec = fault_record(symbol="renderJAudioFrame")
        verdict, detail = capture.collapse_suspects(rec)
        self.assertEqual(verdict, "NARROWED-EXE-SYMBOL")
        self.assertIn("renderJAudioFrame", detail)

    def test_inside_exe_without_symbol(self):
        rec = fault_record(symbol=None)
        verdict, detail = capture.collapse_suspects(rec)
        self.assertEqual(verdict, "NARROWED-EXE-OFFSET")

    def test_wrong_exit_refused(self):
        rec = fault_record()
        rec["exit_code"] = 0
        self.assertEqual(capture.collapse_suspects(rec)[0], "REFUSED")

    def test_missing_fault_refused(self):
        self.assertEqual(capture.collapse_suspects({})[0], "REFUSED")
        self.assertEqual(capture.collapse_suspects(None)[0], "REFUSED")
        rec = fault_record(module=None, address=None)
        self.assertEqual(capture.collapse_suspects(rec)[0], "REFUSED")

    def test_module_basename_case_insensitive(self):
        rec = fault_record(module="C:/GAME/P2_TUTORIAL_P1_RUNTIME.EXE",
                           symbol="Init")
        self.assertEqual(capture.collapse_suspects(rec)[0],
                         "NARROWED-EXE-SYMBOL")


class ExportParseTests(unittest.TestCase):
    def test_non_pe_returns_empty(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                         delete=False) as tmp:
            tmp.write("not a pe file")
            path = tmp.name
        self.assertEqual(capture.parse_export_names(path), {})

    def test_missing_file_returns_empty(self):
        self.assertEqual(
            capture.parse_export_names("C:\\no\\such\\file.dll"), {})

    def test_nearest_export_picks_preceding(self):
        exports = {0x1000: "aaa", 0x2000: "bbb", 0x3000: "ccc"}
        self.assertEqual(capture.nearest_export(exports, 0x2500), "bbb")
        self.assertEqual(capture.nearest_export(exports, 0x1000), "aaa")
        self.assertIsNone(capture.nearest_export(exports, 0x0FFF))
        self.assertIsNone(capture.nearest_export({}, 0x2000))

    def test_real_exe_parses_without_crash(self):
        exe = str(ROOT.parents[6] / "output" / "tutorial-p1-native-runtime-build"
                  / "p2_tutorial_p1_runtime.exe")
        import os
        if not os.path.isfile(exe):
            self.skipTest("pinned exe absent")
        exports = capture.parse_export_names(exe)
        self.assertIsInstance(exports, dict)
        self.assertEqual(capture.nearest_export(exports, 0), None)


class RecordTests(unittest.TestCase):
    def test_packet_shape(self):
        import tempfile
        rec = fault_record(symbol="pumpAudio")
        with tempfile.TemporaryDirectory() as tmp:
            packet, verdict = capture.build_packet(rec, tmp)
        self.assertEqual(packet["kind"], "capture")
        self.assertEqual(packet["issue"], 750)
        self.assertEqual(packet["downstream"]["issue"], 148)
        self.assertEqual(packet["gates"], "all six UNTESTED")
        self.assertEqual(verdict, "NARROWED-EXE-SYMBOL")
        self.assertEqual(len(packet["suspects"]), 4)

    def test_constants_pinned(self):
        self.assertEqual(capture.EXE_SHA256,
                         "f235e032d9d12ef1c7290416e69684bbec484f924691743fbdeb8d93c6ff3a9d")
        self.assertEqual(capture.CRASH_CODE, 0xC0000005)
        self.assertEqual(capture.GUARD_SHA256,
                         "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474")
        self.assertEqual(len(capture.SUSPECTS), 4)

    def test_collapsed_with_resolved_symbol(self):
        rec = fault_record(symbol=None)
        rec["fault"]["resolved_symbol"] = "Font::setTexture+0x64"
        verdict, detail = capture.collapse_suspects(rec)
        self.assertEqual(verdict, "COLLAPSED-EXE-FUNCTION")
        self.assertIn("Font::setTexture", detail)

    def test_main_check_passes(self):
        self.assertEqual(capture.main(["--check"]), 0)



class MinidumpParseTests(unittest.TestCase):
    def build_dump(self):
        import struct
        mod_path = "C:\\game\\p2_tutorial_p1_runtime.exe".encode("utf-16-le") + b"\x00\x00"
        name_len = len(mod_path)
        exc = struct.pack("<II", 1, 0)
        exc += struct.pack("<IIQQII", 3221225477, 0, 0, 0x140001234, 2, 0)
        exc += struct.pack("<15Q", 0, 0xDEAD, *(0 for _ in range(13)))
        assert len(exc) == 160
        mod_off = 32 + 24 + 160
        name_off = mod_off + 4 + 92
        mod = struct.pack("<QIII", 0x140000000, 0x100000, 0, 0)
        mod += struct.pack("<I", name_off)
        mod += b"\x00" * 52
        mod += struct.pack("<II", 8, 0)
        mod += struct.pack("<II", 8, 0)
        assert len(mod) == 92
        hdr = b"MDMP" + struct.pack("<IIIIIQ", 0, 2, 32, 0, 0, 0)
        d1 = struct.pack("<III", 4, 4 + 92, mod_off)
        d2 = struct.pack("<III", 6, 172, 56)
        return (hdr + d1 + d2 + exc + struct.pack("<I", 1) + mod
                + struct.pack("<I", name_len) + mod_path)
    def test_synthetic_dump_parses(self):
        import tempfile, os
        data = self.build_dump()
        with tempfile.NamedTemporaryFile(suffix=".dmp", delete=False) as tmp:
            tmp.write(data)
            path = tmp.name
        try:
            parsed = capture.parse_minidump_crash(path)
        finally:
            os.unlink(path)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["code"], 3221225477)
        self.assertEqual(parsed["address"], 0x140001234)
        self.assertEqual(len(parsed["modules"]), 1)
        self.assertEqual(parsed["modules"][0]["base"], 0x140000000)
        self.assertTrue(parsed["modules"][0]["path"].endswith(
            "p2_tutorial_p1_runtime.exe"))

    def test_bad_dump_returns_none(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".dmp", delete=False) as tmp:
            tmp.write(b"not a dump")
            path = tmp.name
        try:
            self.assertIsNone(capture.parse_minidump_crash(path))
        finally:
            os.unlink(path)
        self.assertIsNone(capture.parse_minidump_crash("C:\\no\\such.dmp"))

if __name__ == "__main__":
    unittest.main()