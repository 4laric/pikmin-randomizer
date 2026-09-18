"""Focused tests for the source-93 BombOtakara bridge pin audit (#791)."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "audit93", ROOT / "experimental" / "pikmin2_bombotakara93_bridge_pin_audit.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


class ParseAdmittedSourcesTests(unittest.TestCase):
    def test_baseline_admits_59_62(self):
        self.assertEqual(audit.parse_admitted_sources(audit.BASELINE_SOURCE_MAP),
                         {59, 60, 61, 62})

    def test_source_93_admitted_is_visible(self):
        text = audit.BASELINE_SOURCE_MAP.replace(
            "case 62: return p2dweevil::ElecId;",
            "case 62: return p2dweevil::ElecId;\n    case 93: return p2dweevil::BombId;")
        self.assertIn(93, audit.parse_admitted_sources(text))

    def test_missing_function_raises(self):
        with self.assertRaises(ValueError):
            audit.parse_admitted_sources("int unrelated(void) { return 0; }")

    def test_empty_text_raises(self):
        with self.assertRaises(ValueError):
            audit.parse_admitted_sources("")

    def test_no_cases_raises(self):
        with self.assertRaises(ValueError):
            audit.parse_admitted_sources("static int speciesFromSource(unsigned s) { return -1; }")

    def test_unterminated_body_raises(self):
        with self.assertRaises(ValueError):
            audit.parse_admitted_sources(
                "static int speciesFromSource(unsigned s) { case 59: return 1;")


class CheckSourceMapTests(unittest.TestCase):
    def test_baseline_passes(self):
        audit.check_source_map({59, 60, 61, 62})

    def test_drift_source_raises(self):
        with self.assertRaises(ValueError):
            audit.check_source_map({59, 60, 61, 62, 91})

    def test_source_93_raises(self):
        with self.assertRaises(ValueError):
            audit.check_source_map({59, 60, 61, 62, 93})


class ScanRootsTests(unittest.TestCase):
    def test_presence_records_integrated_bomb_mgr(self):
        presence = audit.scan_roots({"maint": Path(tempfile.gettempdir())})
        self.assertIn("bridge", presence["maint"])
        self.assertFalse(presence["maint"]["bridge"])

    def test_empty_roots_raises(self):
        with self.assertRaises(ValueError):
            audit.scan_roots({})

    def test_non_path_raises(self):
        with self.assertRaises(ValueError):
            audit.scan_roots({"x": 5})


class PacketTests(unittest.TestCase):
    def _packet(self):
        return audit.build_packet(audit.scan_roots({"m": tempfile.gettempdir()}),
                                  audit.BASELINE_SOURCE_MAP)

    def test_decision_and_gates(self):
        packet = self._packet()
        self.assertEqual(packet["decision"], "bind_93_via_616_bomb_mgr_birth")
        self.assertEqual(packet["refused_source"], 93)
        self.assertTrue(all(v == "UNTESTED" for v in packet["gates"].values()))

    def test_bad_schema_rejected(self):
        packet = self._packet()
        packet["schema"] = "wrong"
        with self.assertRaises(ValueError):
            audit.check_packet(packet)

    def test_non_untested_gate_rejected(self):
        packet = self._packet()
        packet["gates"]["death_corpse"] = "PASS"
        with self.assertRaises(ValueError):
            audit.check_packet(packet)

    def test_wrong_decision_rejected(self):
        packet = self._packet()
        packet["decision"] = "extend_otakara_bridge_for_93"
        with self.assertRaises(ValueError):
            audit.check_packet(packet)

    def test_missing_build_membership_rejected(self):
        packet = self._packet()
        packet["first_executable_slice"]["build_membership"] = []
        with self.assertRaises(ValueError):
            audit.check_packet(packet)


class RunTests(unittest.TestCase):
    def test_end_to_end_writes_packet_and_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            result = audit.run({"m": tempfile.gettempdir()}, out)
            self.assertTrue((out / "packet.json").is_file())
            self.assertTrue((out / "run.log").is_file())
            saved = json.loads((out / "packet.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["schema"], audit.SCHEMA)
            self.assertEqual(result["decision"], audit.DECISION)

    def test_missing_source_map_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                audit.run({"m": tempfile.gettempdir()}, Path(tmp) / "out",
                          Path(tmp) / "nope.cpp")


if __name__ == "__main__":
    unittest.main()