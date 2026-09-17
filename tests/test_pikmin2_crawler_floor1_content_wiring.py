"""Focused tests for the crawler floor-1 content-wiring bridge (#706)."""
import importlib.util
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

MODULE = (Path(__file__).resolve().parents[1] / "experimental"
          / "pikmin2_crawler_floor1_content_wiring.py")
_spec = importlib.util.spec_from_file_location("crawler_wiring", MODULE)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

staged_identity = _mod.staged_identity
verify_source_bytes = _mod.verify_source_bytes
decode_layout = _mod.decode_layout
decode_source_bytes = _mod.decode_source_bytes
load_staged_layout = _mod.load_staged_layout
cross_check = _mod.cross_check
pinned_staged_facts = _mod.pinned_staged_facts
arena_binding = _mod.arena_binding
actor_rows = _mod.actor_rows
starting_squad = _mod.starting_squad
boot_params = _mod.boot_params
wiring_packet = _mod.wiring_packet
MissingInput = _mod.MissingInput
HashMismatch = _mod.HashMismatch
LayoutDecodeError = _mod.LayoutDecodeError
BOOT_MARKERS = _mod.BOOT_MARKERS
SOURCE_SHA256 = _mod.SOURCE_SHA256
NATIVE_FIXTURE_CANDIDATE = _mod.NATIVE_FIXTURE_CANDIDATE


def mini_caveinfo():
    return ("{ {c000} 4 2 {_eof} } 2\n"
            "{ {f000} 4 0 {f001} 4 0 {f008} -1 pool_a.txt {f009} -1 light_a.ini "
            "{f015} 4 1 {_eof} }\n"
            "{ 2 Alpha 21 1 Beta 4 6 }\n{ 1 gem_one 10 }\n{ 1 gate 4000.000000 1 }\n"
            "{ 0 }\n"
            "{ {f000} 4 1 {f001} 4 1 {f008} -1 pool_b.txt {f009} -1 light_b.ini "
            "{f015} 4 1 {_eof} }\n"
            "{ 1 Gamma 10 1 }\n{ 0 }\n{ 0 }\n{ 0 }")


ENEMIES = {"Alpha", "Beta", "Gamma"}
TREASURES = {"gem_one"}


def write_layout(root, manifest=None, markers=None, omit=None):
    manifest = manifest if manifest is not None else {
        "schema": 1, "source_id": "ch_MAT_crawler", "source_sha256": SOURCE_SHA256,
        "floor_count": 2, "ui_index": 29, "floor_seconds": [170.0, 120.0],
        "floors": [
            {"floor": 1, "unit_pool": "pool_a.txt", "enemies": [None, None],
             "treasures": [None], "gates": [None], "caps": []},
            {"floor": 2, "unit_pool": "pool_b.txt", "enemies": [None],
             "treasures": [], "gates": [], "caps": []}]}
    markers = markers if markers is not None else (
        "P2_CRAWLER_WINDOW size=960x540\nP2_CRAWLER_SQUAD count=60\n"
        "P2_CRAWLER_FLOOR_READY floor=\nP2_CRAWLER_ACTOR id= x= z=\n"
        "P2_CRAWLER_PASS floors=2 actors=\n")
    files = {"stage-manifest.json": json.dumps(manifest),
             "squad.json": json.dumps({"squad": [{"color": 0, "maturity": 2,
                                                  "count": 30},
                                                 {"color": 1, "maturity": 2,
                                                  "count": 30}], "total": 60}),
             "run-config.json": json.dumps({"window": "960x540"}),
             "markers.txt": markers}
    for name, text in files.items():
        if name == omit:
            continue
        (root / name).write_text(text, encoding="utf-8")
    return root


class IdentityTests(unittest.TestCase):
    def test_staged_identity_pinned(self):
        ident = staged_identity()
        self.assertEqual(ident["cave_id"], "ch_MAT_crawler")
        self.assertEqual(ident["source_sha256"], SOURCE_SHA256)
        self.assertEqual(ident["source_offset"], 770486496)
        self.assertEqual(ident["source_size"], 2411)
        self.assertEqual(ident["floors"], 2)
        self.assertEqual(ident["ui_index"], 29)
        self.assertEqual(ident["squad_total"], 60)
        self.assertEqual(ident["floor_seconds"], [170.0, 120.0])
        self.assertEqual(ident["floors_pinned"][0]["unit_pool"],
                         "4_units_c_e_j_l_conc.txt")
        self.assertEqual(ident["floors_pinned"][1]["unit_pool"],
                         "1_units_manh_conc.txt")

    def test_source_hash_gate(self):
        with self.assertRaises(HashMismatch):
            verify_source_bytes(b"not the source")
        good = b"x" * _mod.SOURCE_SIZE
        with self.assertRaises(HashMismatch):
            verify_source_bytes(good)


class StagedLayoutTests(unittest.TestCase):
    def test_load_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_layout(Path(tmp))
            staged = load_staged_layout(root)
            self.assertEqual(staged["source_id"], "ch_MAT_crawler")
            self.assertEqual(staged["floor_count"], 2)
            self.assertEqual(staged["ui_index"], 29)
            self.assertEqual(len(staged["floors"]), 2)
            self.assertEqual(staged["squad_total"], 60)

    def test_missing_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_layout(Path(tmp), omit="markers.txt")
            with self.assertRaises(MissingInput):
                load_staged_layout(root)
        with self.assertRaises(MissingInput):
            load_staged_layout(Path(tempfile.gettempdir()) / "no-such-layout-dir")

    def test_bad_schema_or_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = write_layout(Path(tmp)).joinpath("stage-manifest.json")
            bad.write_text("{ not json", encoding="utf-8")
            with self.assertRaises(LayoutDecodeError):
                load_staged_layout(Path(tmp))
        with tempfile.TemporaryDirectory() as tmp:
            manifest = json.loads((write_layout(Path(tmp)) /
                                   "stage-manifest.json").read_text())
            manifest["source_id"] = "ch_OTHER"
            write_layout(Path(tmp), manifest=manifest)
            with self.assertRaises(LayoutDecodeError):
                load_staged_layout(Path(tmp))
        with tempfile.TemporaryDirectory() as tmp:
            manifest = json.loads((write_layout(Path(tmp)) /
                                   "stage-manifest.json").read_text())
            manifest["source_sha256"] = "0" * 64
            write_layout(Path(tmp), manifest=manifest)
            with self.assertRaises(HashMismatch):
                load_staged_layout(Path(tmp))

    def test_incomplete_markers_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_layout(Path(tmp), markers="P2_CRAWLER_WINDOW size=960x540\n")
            with self.assertRaises(LayoutDecodeError):
                load_staged_layout(Path(tmp))


class DecodeTests(unittest.TestCase):
    def test_synthetic_decode_and_cross_check(self):
        decoded = decode_layout(mini_caveinfo(), ENEMIES, TREASURES)
        staged = load_staged_layout(write_layout(Path(tempfile.mkdtemp())))
        staged["floors"] = [
            {"floor": 1, "unit_pool": "pool_a.txt", "enemies": [None, None],
             "treasures": [None], "gates": [None], "caps": []},
            {"floor": 2, "unit_pool": "pool_b.txt", "enemies": [None],
             "treasures": [], "gates": [], "caps": []}]
        self.assertTrue(cross_check(decoded, staged))
        arena = arena_binding(decoded)
        self.assertEqual(arena[0]["unit_pool"], "pool_a.txt")
        self.assertEqual(arena[1]["unit_pool"], "pool_b.txt")
        rows = actor_rows(decoded)
        c = Counter((r["floor"], r["kind"]) for r in rows)
        self.assertEqual(c[(1, "enemy")], 2)
        self.assertEqual(c[(1, "treasure")], 1)
        self.assertEqual(c[(1, "gate")], 1)
        self.assertEqual(c[(2, "enemy")], 1)

    def test_mismatch_fails_closed(self):
        decoded = decode_layout(mini_caveinfo(), ENEMIES, TREASURES)
        staged = load_staged_layout(write_layout(Path(tempfile.mkdtemp())))
        staged["floors"][0]["unit_pool"] = "wrong.txt"
        with self.assertRaises(LayoutDecodeError):
            cross_check(decoded, staged)

    def test_malformed_decode_fails_closed(self):
        for text in ("", "{ unbalanced",
                     mini_caveinfo().replace("{c000} 4 2", "{c000} 4 3"),
                     mini_caveinfo().replace("pool_a.txt", "../evil.txt")):
            with self.subTest(text=text[:30]):
                with self.assertRaises((ValueError, LayoutDecodeError)):
                    decode_layout(text, ENEMIES, TREASURES)

    def test_unknown_reference_rejected(self):
        with self.assertRaises(LayoutDecodeError):
            decode_layout(mini_caveinfo(), {"Other"}, TREASURES)


class BootParamTests(unittest.TestCase):
    def setUp(self):
        self.decoded = decode_layout(mini_caveinfo(), ENEMIES, TREASURES)
        self.staged = load_staged_layout(write_layout(Path(tempfile.mkdtemp())))
        self.staged["floors"] = [
            {"floor": 1, "unit_pool": "pool_a.txt", "enemies": [None, None],
             "treasures": [None], "gates": [None], "caps": []},
            {"floor": 2, "unit_pool": "pool_b.txt", "enemies": [None],
             "treasures": [], "gates": [], "caps": []}]

    def test_squad_wiring(self):
        squad = starting_squad(self.staged)
        self.assertEqual(squad["squad_total"], 60)
        self.assertEqual(squad["ui_index"], 29)
        self.assertEqual(squad["floor_seconds"], [170.0, 120.0])

    def test_boot_params_shape(self):
        params = boot_params(self.staged, self.decoded)
        self.assertEqual(params["cave_id"], "ch_MAT_crawler")
        self.assertEqual(params["ui_index"], 29)
        self.assertEqual(params["selection"]["mechanism"],
                         "host-mode StageEntry table keyed by ui_index")
        self.assertIn("harness", params)
        self.assertEqual(list(params["markers"]), list(BOOT_MARKERS))
        self.assertEqual(len(BOOT_MARKERS), 5)

    def test_boot_params_carry_no_placements(self):
        blob = repr(boot_params(self.staged, self.decoded))
        for banned in ("spawn_position", "coordinates", "x=", "z="):
            self.assertNotIn(banned, blob)

    def test_packet_shape_and_native_candidate(self):
        packet = wiring_packet(boot_params(self.staged, self.decoded))
        self.assertEqual(packet["schema"], 1)
        self.assertEqual(packet["source_sha256"], SOURCE_SHA256)
        self.assertEqual(packet["downstream_consumer"],
                         "p2-challenge-ch-mat-crawler-p1 (#562)")
        self.assertFalse(packet["generated"])
        self.assertEqual(packet["semantic_resolution"], "open")
        self.assertTrue(packet["blockers"] and packet["limitations"])
        self.assertFalse(packet["native_fixture_candidate"]["required"])
        self.assertTrue(packet["native_fixture_candidate"]["if_needed"])
        self.assertEqual(list(packet["native_fixture_candidate"]["candidate_anchors"]),
                         list(NATIVE_FIXTURE_CANDIDATE["candidate_anchors"]))


class RealDiscTests(unittest.TestCase):
    ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")

    def test_real_disc_decode_matches_pins(self):
        if not self.ISO.is_file():
            self.skipTest("local legal disc absent")
        from experimental.pikmin2_assets import disc_files
        catalog = disc_files(self.ISO)
        self.assertIn(_mod.SOURCE_PATH, catalog)
        offset, length = catalog[_mod.SOURCE_PATH]
        self.assertEqual((offset, length), (_mod.SOURCE_OFFSET, _mod.SOURCE_SIZE))
        with self.ISO.open("rb") as handle:
            handle.seek(offset)
            data = handle.read(length)
        decoded = decode_source_bytes(data)
        self.assertTrue(cross_check(decoded, pinned_staged_facts()))
        bindings = arena_binding(decoded)
        self.assertEqual(bindings[0]["unit_pool"], "4_units_c_e_j_l_conc.txt")
        self.assertEqual(bindings[1]["unit_pool"], "1_units_manh_conc.txt")
        counts = Counter((r["floor"], r["kind"]) for r in actor_rows(decoded))
        self.assertEqual(counts[(1, "enemy")], 14)
        self.assertEqual(counts[(2, "enemy")], 7)
        self.assertEqual(counts[(1, "treasure")], 3)
        self.assertEqual(counts[(1, "gate")], 1)


if __name__ == "__main__":
    unittest.main()