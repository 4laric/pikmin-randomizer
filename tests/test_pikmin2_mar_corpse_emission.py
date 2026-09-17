"""Focused evidence tests for the Mar corpse-emission lane (#716)."""
import importlib.util as _importlib_util
import unittest
from pathlib import Path

_MOD_PATH = (Path(__file__).resolve().parents[1] / "experimental"
             / "pikmin2_mar_corpse_emission.py")
_SPEC = _importlib_util.spec_from_file_location("pikmin2_mar_corpse_emission", _MOD_PATH)
_mod = _importlib_util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_mod)

EvidenceError = _mod.EvidenceError
parse_markers = _mod.parse_markers
verify_receipt = _mod.verify_receipt
verify_source_tokens = _mod.verify_source_tokens
verify_pin = _mod.verify_pin

LOG_GOOD = "\n".join([
    "[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)",
    "P2_MAR_DEAD generator=375001 source_id=29 health=0",
    "P2_MAR_CORPSE_EMITTED generator=375001 source_id=29",
    "P2_MAR_CORPSE_EMITTED_OBSERVED generator=375001 source_id=29 pellet=0x1",
    "P2_MAR_CORPSE_READY generator=375001 source_id=29 receipt=corpse:mar:375001",
    "P2_MAR_CORPSE_RECEIPT_RESOLVED generator=375001 source_id=29",
    "PASS P2_MAR_CORPSE_EMISSION corpse=1 receipt=1 injected=0",
])
LOG_CAPTAIN = LOG_GOOD + "\nP2_FIXTURE_CAPTAIN_DOWN tick=4 hp=0.500 outcome=BLOCKED"
LOG_NO_EMIT = "\n".join([
    "P2_MAR_DEAD generator=375001 source_id=29 health=0",
    "FAIL P2_MAR_CORPSE no_corpse_pellet",
])
NATIVE_REL = Path(__file__).resolve().parents[1].parent / "mar-corpse-emission-native-native"


class MarkerTests(unittest.TestCase):
    def test_parse_markers_positive(self):
        markers = parse_markers(LOG_GOOD)
        self.assertTrue(markers["dead"])
        self.assertTrue(markers["receipt"])
        self.assertTrue(markers["pass_run"])
        self.assertTrue(markers["window_960x540"])
        self.assertFalse(markers["captain_down"])
        self.assertEqual(len(markers["emitted"]), 1)

    def test_parse_markers_negative(self):
        markers = parse_markers(LOG_NO_EMIT)
        self.assertTrue(markers["dead"])
        self.assertFalse(markers["emitted"])
        self.assertFalse(markers["receipt"])
        self.assertFalse(markers["pass_run"])
        markers = parse_markers(LOG_CAPTAIN)
        self.assertTrue(markers["captain_down"])
        self.assertFalse(parse_markers("")["dead"])

    def test_verify_receipt_positive(self):
        report = verify_receipt(parse_markers(LOG_GOOD))
        self.assertTrue(report["ok"])
        self.assertEqual(report["emitted_lines"], 1)

    def test_verify_receipt_fails_closed(self):
        with self.assertRaises(EvidenceError):
            verify_receipt(parse_markers(LOG_CAPTAIN))
        with self.assertRaises(EvidenceError):
            verify_receipt(parse_markers(LOG_NO_EMIT))
        with self.assertRaises(EvidenceError):
            verify_receipt(parse_markers("P2_MAR_DEAD only"))


class SourceContractTests(unittest.TestCase):
    def test_emission_source_keeps_contract(self):
        source = (NATIVE_REL / "pc_port" / "pc_p2_mar.cpp").read_text(encoding="utf-8")
        self.assertTrue(verify_source_tokens(source))

    def test_missing_contract_token_rejected(self):
        with self.assertRaises(EvidenceError):
            verify_source_tokens("bool pc_p2_mar_emit_corpse(BTeki* a) { return false; }")

    def test_injection_token_rejected(self):
        bad = ("bool pc_p2_mar_emit_corpse(BTeki* a) { "
               "a->changeMode(PikiMode::TransportMode, 0); "
               "P2_MAR_CORPSE_EMITTED; becomePellet(0, a->getPosition(), 0); return true; }")
        with self.assertRaises(EvidenceError):
            verify_source_tokens(bad)

    def test_pin_roundtrip(self):
        import tempfile
        with tempfile.NamedTemporaryFile("wb", delete=False) as handle:
            handle.write(b"pin-me")
            path = handle.name
        import hashlib
        digest = hashlib.sha256(b"pin-me").hexdigest()
        self.assertEqual(verify_pin(path, digest)["sha256"], digest)
        with self.assertRaises(EvidenceError):
            verify_pin(path, "0" * 64)
        Path(path).unlink()


if __name__ == "__main__":
    unittest.main()