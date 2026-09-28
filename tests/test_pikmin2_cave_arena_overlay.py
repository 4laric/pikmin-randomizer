"""Focused tests for the legal single-pr05 arena overlay provider (#654).

Pinned synthetic blobs use the REAL generator framing (validated by the
shared scripts.preview_pikmin2_room.records parser); pr05 model/label
bytes are the exact values observed in real staged chal0 arenas
(24 rows, one preview treasure bolt, model b50rp).
"""
import struct
import unittest

from experimental.pikmin2_cave_arena_overlay import (
    ArenaOverlayError,
    GUARD_SHA256,
    PR05_MODEL,
    decode_arena_gen,
    decode_run_inputs,
    emit_cargo_package,
    emit_single_pr05_overlay,
    evaluate_boot_predicate,
    guard_record,
    input_package,
)


def make_row(generator_id, model=b"XXXX", label=b"fixture row"):
    row = bytearray(96)
    row[0:8] = b"    0.0v"
    struct.pack_into("<I", row, 8, generator_id)
    row[16:48] = label.ljust(32, b"\x00")
    row[80:84] = model
    return bytes(row)


def make_blob(rows):
    header = b"1.0v" + struct.pack(">4fI", -85.0, 0.0, 0.0, 45.0, len(rows))
    return header + b"".join(rows)


BOLT = b"preview treasure bolt"


def two_pr05_blob():
    return make_blob([
        make_row(5000, PR05_MODEL, BOLT),
        make_row(5001, PR05_MODEL, BOLT),
        make_row(5002),
    ])


def one_pr05_blob():
    return make_blob([
        make_row(5000, PR05_MODEL, BOLT),
        make_row(5001),
    ])


class AbortPredicateTest(unittest.TestCase):
    def test_duplicate_pr05_no_cargo_aborts(self):
        decoded = decode_arena_gen(two_pr05_blob())
        self.assertEqual([r["generator_id"] for r in decoded["pr05"]],
                         [5000, 5001])
        verdict = evaluate_boot_predicate(decoded, {
            "has_cargo": False, "has_cargo_free": False, "has_pod": False,
            "cargo_specs": None})
        self.assertEqual(verdict["verdict"], "abort-duplicate-treasure")

    def test_single_pr05_control_is_legal(self):
        decoded = decode_arena_gen(one_pr05_blob())
        verdict = evaluate_boot_predicate(decoded, {
            "has_cargo": False, "has_cargo_free": False, "has_pod": False,
            "cargo_specs": None})
        self.assertEqual(verdict["verdict"], "legal-single-treasure")

    def test_duplicate_generator_ids_abort(self):
        blob = make_blob([make_row(5000, PR05_MODEL, BOLT),
                          make_row(5000, PR05_MODEL, BOLT)])
        decoded = decode_arena_gen(blob)
        verdict = evaluate_boot_predicate(decoded, {
            "has_cargo": False, "has_cargo_free": False, "has_pod": False,
            "cargo_specs": None})
        self.assertEqual(verdict["verdict"], "abort-duplicate-generator")

    def test_zero_pr05_no_cargo_never_ready(self):
        decoded = decode_arena_gen(make_blob([make_row(5000)]))
        verdict = evaluate_boot_predicate(decoded, {
            "has_cargo": False, "has_cargo_free": False, "has_pod": False,
            "cargo_specs": None})
        self.assertEqual(verdict["verdict"], "no-treasure")

    def test_cargo_free_requires_zero_pr05(self):
        run = {"has_cargo": False, "has_cargo_free": True, "has_pod": False,
               "cargo_specs": None}
        self.assertEqual(evaluate_boot_predicate(
            decode_arena_gen(make_blob([make_row(5000)])), run)["verdict"],
            "legal-cargo-free")
        self.assertEqual(evaluate_boot_predicate(
            decode_arena_gen(one_pr05_blob()), run)["verdict"],
            "abort-duplicate-treasure")

    def test_malformed_blob_fails_closed(self):
        with self.assertRaises(ArenaOverlayError):
            decode_arena_gen(b"not a generator file")
        with self.assertRaises(ArenaOverlayError):
            decode_arena_gen(b"")
        with self.assertRaises(ArenaOverlayError):
            decode_arena_gen(None)


class RunInputsTest(unittest.TestCase):
    def test_missing_run_dir_fails(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ArenaOverlayError):
                decode_run_inputs(str(Path(tmp) / "absent"))

    def test_cargo_and_free_conflict(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "p2-cargo.txt").write_text(
                "P2_CARGO_1\n1\n5000 a:b m 10 5 5\n", encoding="ascii")
            (root / "p2-cargo-free.txt").write_text(
                "P2_CARGO_FREE_1\n", encoding="ascii")
            with self.assertRaises(ArenaOverlayError):
                decode_run_inputs(str(root))

    def test_bad_free_content_fails(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "p2-cargo-free.txt").write_text("bogus\n", encoding="ascii")
            with self.assertRaises(ArenaOverlayError):
                decode_run_inputs(str(root))

    def test_valid_cargo_decoded(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "p2-cargo.txt").write_text(
                "P2_CARGO_1\n1\n5000 a:b m 10 5 5\n", encoding="ascii")
            inputs = decode_run_inputs(str(root))
            self.assertTrue(inputs["has_cargo"])
            self.assertEqual(inputs["cargo_specs"][0]["generator"], 5000)


class OverlayEmissionTest(unittest.TestCase):
    def test_prune_to_lowest_pr05(self):
        blob = make_blob([make_row(5002, PR05_MODEL, BOLT),
                          make_row(5000),
                          make_row(5001, PR05_MODEL, BOLT)])
        overlay, digest = emit_single_pr05_overlay(blob)
        decoded = decode_arena_gen(overlay)
        self.assertEqual([r["generator_id"] for r in decoded["pr05"]], [5001])
        self.assertEqual(decoded["rows"], 2)
        self.assertEqual(decoded["header_count"], 2)
        self.assertEqual(
            evaluate_boot_predicate(decoded, {
                "has_cargo": False, "has_cargo_free": False,
                "has_pod": False, "cargo_specs": None})["verdict"],
            "legal-single-treasure")
        self.assertEqual(
            digest,
            "ba0c8d812142b524b456e2a64ab12d1e32821525329e35903b657b1c2eb4cb42")

    def test_prune_keep_id(self):
        overlay, _ = emit_single_pr05_overlay(two_pr05_blob(), 5001)
        decoded = decode_arena_gen(overlay)
        self.assertEqual([r["generator_id"] for r in decoded["pr05"]], [5001])

    def test_prune_unknown_keep_fails(self):
        with self.assertRaises(ArenaOverlayError):
            emit_single_pr05_overlay(two_pr05_blob(), 9999)

    def test_prune_without_pr05_fails(self):
        with self.assertRaises(ArenaOverlayError):
            emit_single_pr05_overlay(make_blob([make_row(5000)]))

    def test_overlay_deterministic_pin(self):
        first, _ = emit_single_pr05_overlay(two_pr05_blob())
        second, _ = emit_single_pr05_overlay(two_pr05_blob())
        self.assertEqual(first, second)


class CargoEmissionTest(unittest.TestCase):
    SPECS = [
        {"generator": 5000, "instance": "t:t1", "model": "m1",
         "value": 100, "weight": 10, "slots": 8},
        {"generator": 5001, "instance": "t:t2", "model": "m2",
         "value": 200, "weight": 20, "slots": 16},
    ]

    def test_cargo_text_exact(self):
        decoded = decode_arena_gen(two_pr05_blob())
        text, package = emit_cargo_package(decoded, self.SPECS)
        self.assertEqual(
            text,
            "P2_CARGO_1\n2\n5000 t:t1 m1 100 10 8\n5001 t:t2 m2 200 20 16\n")
        self.assertEqual(package["pr05_generators"], [5000, 5001])
        self.assertEqual(package["downstream"], ["#161", "#154", "#642"])
        self.assertEqual(
            package["cargo_sha256"],
            "70653f6a045cbf1c4a936091fe1455cd224cb158b8bda7ec9482a759ecd8f874")

    def test_cargo_generator_mismatch_fails(self):
        decoded = decode_arena_gen(two_pr05_blob())
        specs = [dict(self.SPECS[0], generator=5009), self.SPECS[1]]
        with self.assertRaises(ArenaOverlayError):
            emit_cargo_package(decoded, specs)

    def test_cargo_duplicate_generator_fails(self):
        decoded = decode_arena_gen(two_pr05_blob())
        specs = [self.SPECS[0], dict(self.SPECS[0], instance="t:t9")]
        with self.assertRaises(ArenaOverlayError):
            emit_cargo_package(decoded, specs)

    def test_cargo_bad_value_fails(self):
        decoded = decode_arena_gen(two_pr05_blob())
        specs = [dict(self.SPECS[0], value=1000001), self.SPECS[1]]
        with self.assertRaises(ArenaOverlayError):
            emit_cargo_package(decoded, specs)

    def test_cargo_bad_model_fails(self):
        decoded = decode_arena_gen(two_pr05_blob())
        specs = [dict(self.SPECS[0], model="../m"), self.SPECS[1]]
        with self.assertRaises(ArenaOverlayError):
            emit_cargo_package(decoded, specs)

    def test_empty_specs_fails(self):
        decoded = decode_arena_gen(two_pr05_blob())
        with self.assertRaises(ArenaOverlayError):
            emit_cargo_package(decoded, [])

    def test_no_pr05_to_bind_fails(self):
        decoded = decode_arena_gen(make_blob([make_row(5000)]))
        with self.assertRaises(ArenaOverlayError):
            emit_cargo_package(decoded, self.SPECS[:1])


class GuardAndPackageTest(unittest.TestCase):
    def test_guard_hash_pinned(self):
        record = guard_record("C:/Users/alari/pikmin-randomizer")
        self.assertEqual(record["sha256"], GUARD_SHA256)

    def test_guard_missing_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ArenaOverlayError):
                guard_record(tmp)

    def test_input_package_shape(self):
        decoded = decode_arena_gen(one_pr05_blob())
        package = input_package(decoded, {
            "has_cargo": False, "has_cargo_free": False, "has_pod": False,
            "cargo_specs": None},
            {"path": "scripts/p2_fixture_captain_guard.h",
             "sha256": GUARD_SHA256})
        self.assertEqual(package["verdict"], "legal-single-treasure")
        self.assertEqual(package["pr05_generators"], [5000])
        self.assertIn("runtime-checked", package["limitations"][0])


class RealArenaGroundingTest(unittest.TestCase):
    REAL_ARENAS_GLOB = ("C:/Users/alari/pikmin-randomizer/output/workflow/"
                        "paid-scale/l51/stage/arena/*/assets/dataDir/stages/"
                        "chal0/default.gen")
    REAL_ARENA_SHA256 = ("2f6fd4950392fa2d7707f664c390366afdad1e8cf8a4300d18"
                         "be707b07228792")

    def test_real_staged_arena_decodes(self):
        import glob
        from pathlib import Path
        arenas = sorted(glob.glob(self.REAL_ARENAS_GLOB))
        if not arenas:
            self.skipTest("no staged real arena present")
        raw = Path(arenas[0]).read_bytes()
        self.assertEqual(
            __import__("hashlib").sha256(raw).hexdigest(),
            self.REAL_ARENA_SHA256)
        decoded = decode_arena_gen(raw)
        self.assertEqual(decoded["rows"], 24)
        self.assertEqual(len(decoded["pr05"]), 1)
        self.assertEqual(decoded["pr05"][0]["label"], "preview treasure bolt")
        verdict = evaluate_boot_predicate(decoded, {
            "has_cargo": False, "has_cargo_free": False, "has_pod": False,
            "cargo_specs": None})
        self.assertEqual(verdict["verdict"], "legal-single-treasure")


if __name__ == "__main__":
    unittest.main()
