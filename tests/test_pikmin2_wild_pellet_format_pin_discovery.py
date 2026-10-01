"""Tests for the wild-pellet (pb01) tlep pin-discovery tooling (#825).

Unit checks run on synthetic generator blobs built with the pinned layout
(framing + record-relative offsets); they prove parser behavior only, never
the retail format itself. Format proof comes from the read-only audit of the
real #561 staged arena, gated behind WILD_PELLET_ARENA_GEN (+ optional
WILD_PELLET_POD_TXT) so this test stays green without sibling-lane paths:
the env-gated case skips when the operator does not point it at real bytes.
"""
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experimental"))
from pikmin2_wild_pellet_format_pin_discovery import (  # noqa: E402
    CITATIONS,
    FINDING,
    NEXT_SLICE,
    audit_arena,
    check_pod_config,
    classify_delivery,
    decode_model,
    diagnose,
    frame_records,
    parse_tlep,
)

MODULE = Path(__file__).resolve().parents[1] / "experimental" / \
    "pikmin2_wild_pellet_format_pin_discovery.py"


def make_record(kind=b"tlep", version=b"0.0v", model=b"10bp",
                gen_id=3342389, name=b"synthetic pellet",
                pos=(-601.4042358398438, 0.0, 1680.8521728515625),
                total=164):
    row = bytearray(total)
    row[0:8] = b"    0.0v"
    struct.pack_into("<I", row, 8, gen_id)
    row[16:16 + len(name)] = name
    struct.pack_into(">6f", row, 48, *pos, 0.0, 0.0, 0.0)
    row[72:76] = kind
    row[76:80] = version
    row[80:84] = model
    return bytes(row)


def make_blob(rows):
    return b"1.0v" + struct.pack(">4fI", -85, 0, 0, 45, len(rows)) + \
        b"".join(rows)


class DecodeTests(unittest.TestCase):
    def test_stored_order_decodes_to_retail_fourcc(self):
        self.assertEqual(decode_model(b"10bp"), "pb01")
        self.assertEqual(decode_model(b"50rp"), "pr05")
        self.assertEqual(decode_model(b"10yp"), "py01")

    def test_decode_rejects_bad_field(self):
        with self.assertRaises(ValueError):
            decode_model(b"abc")
        with self.assertRaises(ValueError):
            decode_model("pb01")

    def test_parse_tlep_pinned_offsets(self):
        entry = parse_tlep(make_record())
        self.assertEqual(entry["model"], "pb01")
        self.assertEqual(entry["stored_model"], b"10bp".hex())
        self.assertEqual(entry["generator_id"], 3342389)
        self.assertEqual(entry["position"][0],
                         struct.unpack(">f", struct.pack(
                             ">f", -601.4042358398438))[0])

    def test_parse_rejects_wrong_kind_version_and_short_rows(self):
        with self.assertRaises(ValueError):
            parse_tlep(make_record(kind=b"iket"))
        with self.assertRaises(ValueError):
            parse_tlep(make_record(version=b"1.0v"))
        with self.assertRaises(ValueError):
            parse_tlep(b"short")

    def test_framing_matches_room_parser_contract(self):
        rows = [make_record(model=b"10bp"), make_record(model=b"50rp")]
        self.assertEqual(len(frame_records(make_blob(rows))), 2)
        with self.assertRaises(ValueError):
            frame_records(b"0.0v" + b"\x00" * 64)
        with self.assertRaises(ValueError):
            frame_records(make_blob(rows)[:40])

    def test_classify_binds_only_pr05(self):
        binding, abort = classify_delivery("pr05")
        self.assertFalse(abort)
        self.assertIn("previewTreasure", binding)
        for model in ("pb01", "pr01", "py01", "pb20"):
            binding, abort = classify_delivery(model)
            self.assertTrue(abort)
            self.assertIn("409", binding)


class AuditTests(unittest.TestCase):
    def _stage(self, tmp, rows, pod=True):
        gen = Path(tmp) / "default.gen"
        gen.write_bytes(make_blob(rows))
        pod_path = None
        if pod:
            pod_path = Path(tmp) / "p2-pod.txt"
            pod_path.write_text("P2_POD_1\nroute_rover_pod 180 15 25\n"
                                "Kochappy 2\n", encoding="utf-8")
        return gen, pod_path

    def test_audit_histogram_and_unregistered(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen, _ = self._stage(tmp, [
                make_record(model=b"10bp", gen_id=1),
                make_record(model=b"10bp", gen_id=2),
                make_record(model=b"50rp", gen_id=3),
            ])
            audit = audit_arena(gen)
            self.assertEqual(audit["rows"], 3)
            self.assertEqual(audit["tlep_records"], 3)
            self.assertEqual(audit["model_histogram"],
                             {"pb01": 2, "pr05": 1})
            self.assertEqual(audit["unregistered_models"], ["pb01"])
            self.assertEqual(audit["gen_sha256"],
                             hashlib.sha256(gen.read_bytes()).hexdigest())

    def test_audit_fails_closed_on_missing_or_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                audit_arena(Path(tmp) / "nope.gen")
            bad = Path(tmp) / "bad.gen"
            bad.write_bytes(b"junk")
            with self.assertRaises(ValueError):
                audit_arena(bad)

    def test_pod_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, pod = self._stage(tmp, [make_record()])
            self.assertEqual(check_pod_config(pod)["treasure"],
                             "route_rover_pod")
            missing = Path(tmp) / "absent.txt"
            with self.assertRaises(FileNotFoundError):
                check_pod_config(missing)
            broken = Path(tmp) / "broken.txt"
            broken.write_text("garbage\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                check_pod_config(broken)

    def test_diagnose_names_consumer_and_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen, pod = self._stage(tmp, [make_record()])
            result = diagnose(gen, pod)
            self.assertIn("pb01", result["finding"])
            self.assertIn("409", result["finding"])
            self.assertIn("#561", result["downstream_consumer"])
            self.assertEqual(result["recovery_request"],
                             "1282ac9d1a5bce83b7a826f8a9fce7870411e14b3df7507f331770529daf13cb")
            self.assertEqual(result["next_slice"]["producer_contract"]
                             ["kind"], "diagnosis")
            self.assertIn("p2-challenge-ch_mat_route_rover-p1",
                          result["next_slice"]["producer_contract"]
                          ["consumers"][0]["lane"])

    def test_citations_cover_pin_and_binding(self):
        for key in ("records", "tlep_row_use", "enemy_audit_gap",
                    "chappy_fill", "pr05_scan", "pod_ready",
                    "unregistered_abort", "cargo_format", "pellet_table"):
            self.assertIn(key, CITATIONS)
        self.assertIn("409", FINDING)
        self.assertEqual(NEXT_SLICE["consumer"],
                         "p2-challenge-ch_mat_route_rover-p1 (#561)")

    def test_cli_json_and_fail_closed_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen, pod = self._stage(tmp, [make_record(model=b"50rp")])
            proc = subprocess.run(
                [sys.executable, str(MODULE), "--gen", str(gen),
                 "--pod", str(pod)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["audit"]
                             ["model_histogram"], {"pr05": 1})
            proc = subprocess.run(
                [sys.executable, str(MODULE), "--gen",
                 str(Path(tmp) / "absent.gen")],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("refused", proc.stderr)


@unittest.skipUnless(os.environ.get("WILD_PELLET_ARENA_GEN"),
                     "set WILD_PELLET_ARENA_GEN to a real staged default.gen")
class RealArenaTests(unittest.TestCase):
    """Read-only proof against real #561 staged bytes (operator-supplied)."""

    def test_real_arena_matches_pin(self):
        gen = Path(os.environ["WILD_PELLET_ARENA_GEN"])
        pod_env = os.environ.get("WILD_PELLET_POD_TXT")
        result = diagnose(gen, pod_env) if pod_env else diagnose(gen)
        audit = result["audit"]
        self.assertEqual(audit["rows"], 137)
        self.assertEqual(audit["tlep_records"], 53)
        self.assertEqual(audit["model_histogram"].get("pb01"), 10)
        self.assertEqual(audit["model_histogram"].get("pr05"), 2)
        self.assertIn("pb01", audit["unregistered_models"])
        self.assertEqual(
            audit["gen_sha256"],
            "8a5f18539202ca8939a36b095a93061cca756ecdf2c355fb8147522ffdd38a3d")


if __name__ == "__main__":
    unittest.main()
