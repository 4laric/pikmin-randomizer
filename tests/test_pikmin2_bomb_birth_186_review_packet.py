"""Focused tests for the #186 Bomb birth review packet (#186)."""
import hashlib
import importlib.util
import unittest
from pathlib import Path

MODULE = (Path(__file__).resolve().parents[1] / "experimental"
          / "pikmin2_bomb_birth_186_review_packet.py")
_spec = importlib.util.spec_from_file_location("bomb_birth_186", MODULE)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

DriftError = _mod.DriftError
INPUTS = _mod.INPUTS
REVIEW_ITEMS = _mod.REVIEW_ITEMS
item_verdict = _mod.item_verdict
review = _mod.review
validate_packet = _mod.validate_packet
verify_candidate_artifacts = _mod.verify_candidate_artifacts

RESEARCH_MAINTAINED = b"case EnemyTypeID::EnemyID_Bomb:\ncase EnemyTypeID::EnemyID_BombOtakara:\n"
RESEARCH_INTEGRATED = RESEARCH_MAINTAINED + b"pc_p2_bomb_birth_hook_notify(enemyID);\n"
CMAKE_MAINTAINED = b"enable_testing()\nadd_executable(pc_generator_cache_validation_test)\n"
CMAKE_INTEGRATED = CMAKE_MAINTAINED + b"pc_port/pc_p2_bomb_mgr_birth.cpp\n"
PROVIDER_H = b"constexpr int P2_BOMB_MGR_SOURCE_ID = 36;\n"
PAYLOAD_H = b"struct P2BombPayloadConfig {};\n"
JOINT_H = b"void pc_p2_otakara_joint_capture_poll();\n"


def reader(maintained_integrated=False, drop=(), tamper=(), absent_ok=True):
    """Synthetic input reader; pins are set to match these bytes."""
    blob = {
        "maintained_cmake": CMAKE_INTEGRATED if maintained_integrated else CMAKE_MAINTAINED,
        "maintained_research": RESEARCH_INTEGRATED if maintained_integrated else RESEARCH_MAINTAINED,
        "candidate_engine_hook": RESEARCH_INTEGRATED,
        "candidate_provider_h": PROVIDER_H,
        "candidate_provider_cpp": b"pc_p2_bomb_mgr_birth\n",
        "candidate_payload_h": PAYLOAD_H,
        "candidate_payload_cpp": b"payload\n",
        "candidate_joint_h": JOINT_H,
        "candidate_joint_cpp": b"joint\n",
    }
    if maintained_integrated:
        blob["maintained_payload_h"] = PAYLOAD_H
        blob["maintained_payload_cpp"] = b"payload\n"
        blob["maintained_joint_h"] = JOINT_H
        blob["maintained_joint_cpp"] = b"joint\n"
    for key in drop:
        blob.pop(key, None)
    for key in tamper:
        blob[key] = b"tampered"
    return blob


def pin_reader(blob):
    """Pin every present key to the synthetic bytes (except tamper drift)."""
    for key, data in blob.items():
        if key in INPUTS:
            INPUTS[key]["sha256"] = hashlib.sha256(data).hexdigest()
    return lambda key: blob.get(key)


class PositiveTests(unittest.TestCase):
    def test_integrated_line_approves_all(self):
        blob = reader(maintained_integrated=True)
        packet = review(pin_reader(blob))
        self.assertEqual(packet["decision"], "APPROVED")
        self.assertTrue(all(i["status"] == "APPROVED" for i in packet["gated_items"]))
        self.assertTrue(validate_packet(packet, pin_reader(blob)))

    def test_missing_integration_is_changes_required(self):
        blob = reader(maintained_integrated=False)
        packet = review(pin_reader(blob))
        self.assertEqual(packet["decision"], "CHANGES_REQUIRED")
        for item in packet["gated_items"]:
            self.assertEqual(item["status"], "CHANGES_REQUIRED")
            self.assertTrue(item["missing_change"])


class FailClosedTests(unittest.TestCase):
    def test_missing_candidate_artifact_refused(self):
        blob = reader(maintained_integrated=True, drop=("candidate_payload_h",))
        with self.assertRaises(DriftError):
            review(pin_reader(blob))

    def test_missing_maintained_base_refused(self):
        blob = reader(drop=("maintained_research",))
        with self.assertRaises(DriftError):
            review(pin_reader(blob))

    def test_hash_mismatch_refused(self):
        blob = reader(maintained_integrated=True)
        read = pin_reader(blob)
        INPUTS["candidate_provider_h"]["sha256"] = "0" * 64
        with self.assertRaises(DriftError):
            review(read)

    def test_candidate_token_missing_refused_in_verdict(self):
        blob = reader(maintained_integrated=True)
        blob["candidate_engine_hook"] = b"nothing useful here"
        read = pin_reader(blob)
        item = next(i for i in REVIEW_ITEMS if i["id"] == "engine-bomb-birth-path")
        verdict = item_verdict(item, read)
        self.assertEqual(verdict["status"], "CHANGES_REQUIRED")
        self.assertTrue(any("missing token" in p for p in verdict["problems"]))


class TamperTests(unittest.TestCase):
    def test_tampered_approval_rejected(self):
        blob = reader(maintained_integrated=False)
        read = pin_reader(blob)
        packet = review(read)
        for item in packet["gated_items"]:
            item["status"] = "APPROVED"
            item["integration_evidence"] = [
                {"token": "x", "present_on_maintained": True}]
        with self.assertRaises(DriftError):
            validate_packet(packet, read)

    def test_tampered_schema_rejected(self):
        blob = reader()
        read = pin_reader(blob)
        packet = review(read)
        packet["schema"] = "tampered"
        with self.assertRaises(DriftError):
            validate_packet(packet, read)

    def test_unsubstantiated_approval_rejected(self):
        blob = reader(maintained_integrated=True)
        read = pin_reader(blob)
        packet = review(read)
        for item in packet["gated_items"]:
            for ev in item["integration_evidence"]:
                ev["present_on_maintained"] = False
        with self.assertRaises(DriftError):
            validate_packet(packet, read)


class PacketShapeTests(unittest.TestCase):
    def test_packet_names_downstream_and_steps(self):
        blob = reader()
        packet = review(pin_reader(blob))
        self.assertEqual(packet["schema"], _mod.SCHEMA)
        self.assertEqual(packet["issue"], 186)
        self.assertEqual(packet["consumer"], "enemy-bombotakara93-payload (#573)")
        for key in ("573", "616", "703"):
            self.assertIn(key, packet["downstream"])
        self.assertEqual(len(packet["gated_items"]), 3)
        self.assertEqual(sorted(i["id"] for i in packet["gated_items"]),
                         ["dynamic-bridge-source-93", "engine-bomb-birth-path",
                          "provider-cmake-membership"])
        self.assertTrue(packet["integrator_steps"])
        self.assertEqual(len(packet["gates"]), 6)
        self.assertTrue(all(g["status"] == "UNTESTED" for g in packet["gates"].values()))
        self.assertFalse(packet["generated"])
        for item in packet["gated_items"]:
            self.assertEqual(len(item["candidate_artifacts"]),
                             len(next(i for i in REVIEW_ITEMS if i["id"] == item["id"])["candidate_inputs"]))

    def test_candidate_evidence_has_hashes(self):
        blob = reader()
        evidence = verify_candidate_artifacts(pin_reader(blob))
        self.assertTrue(evidence)
        for entry in evidence.values():
            self.assertEqual(len(entry["sha256"]), 64)
            self.assertTrue(entry["match"])


if __name__ == "__main__":
    unittest.main()