"""Focused tests for the Mar29 Pod dispatch candidate (#665)."""
import json
import subprocess
import unittest
from pathlib import Path

from experimental.pikmin2_mar29_pod_dispatch_candidate import (
    ADD_INCLUDE,
    ANCHOR_ARM_AFTER,
    ANCHOR_ARM_BEFORE,
    ANCHOR_INCLUDE,
    ARM_LINES,
    CandidateRejected,
    apply_patch,
    candidate_packet,
    verify_hook,
)

BASE = (
    '#include "pc_p2_kurage_teki.h"\n'
    '#include "pc_p2_bombsarai_teki.h"\n'
    '        else if(unsigned generator=0;pc_p2_long_legs_receipt(pellet,generator)) {\n'
    '            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"longlegs:"+std::to_string(generator);value=corpseValue;\n'
    '        }\n'
    '        else {\n'
    '            auto found=corpses.find(pellet->mPelletView);\n'
    '        }\n'
)

ADAPTER_HASHES = {"pc_p2_mar_receipt.h": "51502c3e75415b81",
                  "pc_p2_mar_receipt.cpp": "0cd70df739825066",
                  "p2_muse_mar_receipt_fixture.cpp": "0b3437662a9ee53b"}


class DispatchCandidateTests(unittest.TestCase):
    def test_apply_clean_and_verify(self):
        patched = apply_patch(BASE)
        self.assertIn(ADD_INCLUDE, patched)
        self.assertIn(ARM_LINES.strip(), patched)
        findings = verify_hook(patched)
        self.assertTrue(findings["ok"], findings)

    def test_arm_order_longlegs_then_mar_then_fallback(self):
        patched = apply_patch(BASE)
        longlegs = patched.find(ANCHOR_ARM_BEFORE)
        arm = patched.find(ARM_LINES.strip())
        fallback = patched.find(ANCHOR_ARM_AFTER)
        self.assertTrue(0 <= longlegs < arm < fallback)

    def test_existing_arms_intact(self):
        patched = apply_patch(BASE)
        self.assertIn("pc_p2_long_legs_receipt(pellet,generator)", patched)
        self.assertIn("auto found=corpses.find(pellet->mPelletView)", patched)
        self.assertEqual(patched.count("pc_p2_long_legs_receipt"), 1)

    def test_double_apply_refused(self):
        patched = apply_patch(BASE)
        with self.assertRaises(CandidateRejected):
            apply_patch(patched)

    def test_missing_anchors_refused(self):
        for broken in ("", "no anchors here",
                       BASE.replace(ANCHOR_INCLUDE, ""),
                       BASE.replace(ANCHOR_ARM_BEFORE, ""),
                       BASE.replace(ANCHOR_ARM_AFTER, "")):
            with self.subTest(broken=broken[:30]), self.assertRaises(CandidateRejected):
                apply_patch(broken)

    def test_empty_input_refused(self):
        with self.assertRaises(CandidateRejected):
            apply_patch("")
        with self.assertRaises(CandidateRejected):
            apply_patch(None)

    def test_packet_writes_nothing_on_failure(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "out"
            with self.assertRaises(CandidateRejected):
                candidate_packet("broken", ADAPTER_HASHES, out)
            self.assertFalse((out / "pc_p2_preview.cpp.candidate").exists())
            self.assertFalse((out / "mar29-pod-dispatch-packet.json").exists())

    def test_packet_refuses_overwrite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            candidate_packet(BASE, ADAPTER_HASHES, out)
            with self.assertRaises(CandidateRejected):
                candidate_packet(BASE, ADAPTER_HASHES, out)

    def test_real_pinned_base_applies(self):
        base = Path("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
                    "planning-shards/enemies-2/prepared/mar29-receipt-provider-native")
        if not (base / "pc_port/pc_p2_preview.cpp").is_file():
            self.skipTest("pinned native checkout absent")
            return
        text = (base / "pc_port/pc_p2_preview.cpp").read_text(encoding="utf-8")
        patched = apply_patch(text)
        self.assertTrue(verify_hook(patched)["ok"])


if __name__ == "__main__":
    unittest.main()
