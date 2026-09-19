"""Focused tests for the DangoMushi driver contract (#664).

All fixtures are synthetic: a fabricated family file exercising anchor
verification, plus malformed packet inputs. No value here is claimed as retail
fact. Real-file verification against the pinned wave-native module is recorded
in the review doc, not asserted here (hermetic tests must run anywhere).
"""
import importlib.util
import unittest
from pathlib import Path
import tempfile

ADAPTER = (Path(__file__).resolve().parents[1] / "experimental"
           / "pikmin2_dangomushi_driver_contract.py")


def load_adapter():
    spec = importlib.util.spec_from_file_location("dangomushi_driver_contract", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synth_family(extra=""):
    """Minimal synthetic family file carrying the exact anchor lines."""
    mod = load_adapter()
    lines = ["// synthetic family module %d" % n for n in range(1, 1100)]
    for name, (line, text) in mod.ANCHORS.items():
        lines[line - 1] = text
    if extra:
        lines.append(extra)
    return "\n".join(lines) + "\n"


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_contract_schema(self):
        packet = self.mod.contract()
        self.assertEqual(packet["issue"], 664)
        self.assertEqual(packet["family_issue"], 376)
        self.assertEqual(packet["source_id"], 94)
        self.assertEqual(len(packet["anchors"]), 11)
        self.assertEqual(len(packet["observer_legs"]), 4)
        self.assertTrue(packet["downstream"])

    def test_no_family_diff_recorded(self):
        packet = self.mod.contract()
        self.assertEqual(packet["family_patch"], "")
        self.assertTrue(packet["no_patch_rationale"])

    def test_verify_anchors_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pc_p2_dangomushi.cpp"
            path.write_text(synth_family(), encoding="utf-8")
            report = self.mod.verify_anchors(str(path))
        self.assertEqual(len(report), 11)
        self.assertTrue(all(v["verified"] for v in report.values()))

    def test_verify_anchors_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pc_p2_dangomushi.cpp"
            path.write_text(synth_family().replace("DANGO_DEAD", "DANGO_GONE"),
                            encoding="utf-8")
            with self.assertRaises(self.mod.ContractError):
                self.mod.verify_anchors(str(path))

    def test_verify_anchors_missing_file_rejected(self):
        with self.assertRaises(self.mod.ContractError):
            self.mod.verify_anchors("/nonexistent/pc_p2_dangomushi.cpp")

    def test_verify_anchors_short_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pc_p2_dangomushi.cpp"
            path.write_text("// too short\n", encoding="utf-8")
            with self.assertRaises(self.mod.ContractError):
                self.mod.verify_anchors(str(path))

    def test_validate_packet_positive(self):
        self.assertEqual(self.mod.validate_packet(self.mod.contract())["issue"], 664)

    def test_validate_packet_missing_field_rejected(self):
        packet = self.mod.contract()
        del packet["driver_spec"]
        with self.assertRaises(self.mod.ContractError):
            self.mod.validate_packet(packet)

    def test_validate_packet_wrong_issue_rejected(self):
        packet = self.mod.contract()
        packet["issue"] = 999
        with self.assertRaises(self.mod.ContractError):
            self.mod.validate_packet(packet)

    def test_validate_packet_leg_tokens_required(self):
        packet = self.mod.contract()
        packet["observer_legs"] = ["bind", "death", "corpse", "rebind"]
        with self.assertRaises(self.mod.ContractError):
            self.mod.validate_packet(packet)

    def test_validate_packet_non_dict_rejected(self):
        with self.assertRaises(self.mod.ContractError):
            self.mod.validate_packet([])

    def test_driver_spec_covers_sequence(self):
        spec = self.mod.contract()["driver_spec"]
        joined = " ".join(spec).lower()
        for token in ("bind", "damage", "death", "corpse", "reset", "re-bind"):
            self.assertIn(token, joined, token)


if __name__ == "__main__":
    unittest.main()