"""Focused P0 tests for the ch_MUKI_king import contract (#542).

All cave-shaped inputs below are SYNTHETIC fixtures exercising the parser
boundary only; they assert no retail fact. The only retail claims used are
structural: 5 floors (lane plan), the recorded source sha256, and enemy
names from the generated roster snapshot (read-only).
"""

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

adapter = importlib.import_module(
    "experimental.content_lanes.p2-challenge-ch_muki_king")

# SYNTHETIC enemy registry for fixtures (parser boundary only).
SYNTHETIC_NAMES = frozenset(
    {"YellowKochappy", "Kabuto", "Bomb", "Demon", "Fart", "UjiA"})


def _parms(first, last, version, unit):
    rows = [
        ("f000", 4, first), ("f001", 4, last), ("f002", 4, 10),
        ("f003", 4, 4), ("f004", 4, 2), ("f014", 4, 2), ("f005", 4, 4),
        ("f006", 4, 0.5), ("f007", 4, 0), ("f008", 64, unit),
        ("f009", 64, "light.ini"), ("f00A", 64, "vrbox"),
        ("f010", 4, 0), ("f011", 4, 0), ("f012", 4, 0), ("f013", 4, 0),
        ("f015", 4, version), ("f016", 4, 0.0), ("f017", 4, 0),
    ]
    return "\n".join("%s %s %s" % r for r in rows)


def _floor(first, last, version, unit, caps=True):
    text = _parms(first, last, version, unit) + "\n"
    text += "2\nYellowKochappy 10 0\n$2Kabuto 5 1\n"
    text += "1\nmap01 2\n"
    text += "1\ngateA 100.0 1\n"
    if version >= 1 and caps:
        text += "2\n0\n$1Bomb 4 0\n1\n"
    return text


def synthetic_cave(versions=(1, 1, 0, 1, 1)):
    out = "# SYNTHETIC ch_MUKI_king-shaped fixture\nc000 4 5\n5\n"
    for i, version in enumerate(versions, start=1):
        out += _floor(i, i, version, "units%s.txt" % i)
    return out


class TestMukiKingAdapter(unittest.TestCase):
    def test_synthetic_happy_path(self):
        floor_max, floors = adapter.parse_caveinfo(
            synthetic_cave(), SYNTHETIC_NAMES)
        self.assertEqual(floor_max, 5)
        self.assertEqual(len(floors), 5)
        self.assertEqual(adapter.validate_coverage(floor_max, floors), [])
        self.assertEqual(floors[0].teki[1].enemy, "Kabuto")
        self.assertEqual(floors[0].teki[1].drop_mode, 2)
        self.assertEqual(floors[0].teki[1].weight, 5)
        manifest = adapter.build_manifest(floors and floor_max, floors,
                                          "<synthetic>", "0" * 64)
        self.assertFalse(manifest["placements_emitted"])
        self.assertEqual(manifest["expected_sha256"],
                         adapter.EXPECTED_SHA256)
        self.assertEqual(manifest["catalog_baseline"]["floors"], 5)
        self.assertEqual(manifest["catalog_baseline"]["bitter_sprays"], 2)
        self.assertEqual(len(manifest["catalog_baseline"]["floor_seconds"]), 5)
        self.assertEqual(len(manifest["resource_closure"]["unit_files"]), 5)
        self.assertEqual(floors[0].__class__.__name__, "Floor")

    def test_weight_sums_mirror_engine(self):
        _, floors = adapter.parse_caveinfo(synthetic_cave(), SYNTHETIC_NAMES)
        self.assertEqual(adapter.weight_sum(floors[0].teki), 15)
        self.assertEqual(adapter.weight_sum(floors[0].items), 2)
        self.assertEqual(adapter.weight_sum(floors[0].gates), 1)

    def test_version_zero_floor_has_no_caps(self):
        _, floors = adapter.parse_caveinfo(synthetic_cave(), SYNTHETIC_NAMES)
        self.assertEqual(floors[2].parms["f015"], 0)
        self.assertEqual(floors[2].caps, [])
        self.assertEqual(len(floors[0].caps), 2)

    def test_missing_source_reports_prerequisite(self):
        with self.assertRaises(adapter.SourceMissingError) as ctx:
            adapter.load_source_bytes("definitely/not/ch_MUKI_king.txt")
        self.assertIn("missing prerequisite", str(ctx.exception))
        self.assertIn("no values are invented", str(ctx.exception))

    def test_hash_mismatch_refused(self):
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(synthetic_cave())
            with self.assertRaises(adapter.CaveDecodeError) as ctx:
                adapter.decode_caveinfo_file(path, SYNTHETIC_NAMES)
            self.assertIn("!= recorded", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_empty_file_rejected(self):
        with self.assertRaises(adapter.CaveDecodeError):
            adapter.parse_caveinfo("", SYNTHETIC_NAMES)

    def test_bad_cave_parm_rejected(self):
        with self.assertRaises(adapter.CaveDecodeError):
            adapter.parse_caveinfo("c001 4 5\n0\n", SYNTHETIC_NAMES)
    def test_unknown_enemy_token_rejected(self):
        bad = synthetic_cave().replace("YellowKochappy 10 0",
                                       "NotAnEnemy 10 0", 1)
        with self.assertRaises(adapter.CaveDecodeError) as ctx:
            adapter.parse_caveinfo(bad, SYNTHETIC_NAMES)
        self.assertIn("unknown enemy token", str(ctx.exception))

    def test_drop_grammar(self):
        self.assertEqual(
            adapter.parse_teki_token("$Demon", SYNTHETIC_NAMES),
            ("Demon", "", 1))
        self.assertEqual(
            adapter.parse_teki_token("$9Kabuto", SYNTHETIC_NAMES),
            ("Kabuto", "", 9))
        self.assertEqual(
            adapter.parse_teki_token("Demon_tape_red", SYNTHETIC_NAMES),
            ("Demon", "tape_red", 0))
        self.assertEqual(
            adapter.parse_teki_token("$2Fart_whistle", SYNTHETIC_NAMES),
            ("Fart", "whistle", 2))
        with self.assertRaises(adapter.CaveDecodeError):
            adapter.parse_teki_token("$0Kabuto", SYNTHETIC_NAMES)
        with self.assertRaises(adapter.CaveDecodeError):
            adapter.parse_teki_token("Kabuto_", SYNTHETIC_NAMES)
        with self.assertRaises(adapter.CaveDecodeError):
            adapter.parse_teki_token("$", SYNTHETIC_NAMES)

    def test_bad_gen_type_rejected(self):
        bad = synthetic_cave().replace("YellowKochappy 10 0",
                                       "YellowKochappy 10 9", 1)
        with self.assertRaises(adapter.CaveDecodeError):
            adapter.parse_caveinfo(bad, SYNTHETIC_NAMES)

    def test_duplicate_parm_rejected(self):
        bad = synthetic_cave().replace("f001 4 1\n", "f001 4 1\nf001 4 1\n", 1)
        with self.assertRaises(adapter.CaveDecodeError):
            adapter.parse_caveinfo(bad, SYNTHETIC_NAMES)

    def test_unsupported_parm_is_explicit(self):
        bad = synthetic_cave().replace("f017 4 0", "f099 4 0", 1)
        with self.assertRaises(adapter.CaveDecodeError) as ctx:
            adapter.parse_caveinfo(bad, SYNTHETIC_NAMES)
        self.assertIn("unsupported parm id", str(ctx.exception))

    def test_trailing_tokens_rejected(self):
        with self.assertRaises(adapter.CaveDecodeError):
            adapter.parse_caveinfo(synthetic_cave() + " junk", SYNTHETIC_NAMES)

    def test_coverage_gap_flagged(self):
        floor_max, floors = adapter.parse_caveinfo(
            synthetic_cave(), SYNTHETIC_NAMES)
        floors[-1].last = 4
        defects = adapter.validate_coverage(floor_max, floors)
        self.assertTrue(any("coverage gap" in d for d in defects))

    def test_overlap_flagged(self):
        floor_max, floors = adapter.parse_caveinfo(
            synthetic_cave(), SYNTHETIC_NAMES)
        floors[1].first = 1
        defects = adapter.validate_coverage(floor_max, floors)
        self.assertTrue(any("overlapping" in d for d in defects))

    def test_comments_and_braces_tolerated(self):
        text = "{\n" + synthetic_cave() + "}\n"
        floor_max, floors = adapter.parse_caveinfo(text, SYNTHETIC_NAMES)
        self.assertEqual(adapter.validate_coverage(floor_max, floors), [])

    def test_truncated_file_rejected(self):
        with self.assertRaises(adapter.CaveDecodeError):
            adapter.parse_caveinfo(synthetic_cave()[:120], SYNTHETIC_NAMES)

    def test_decomp_registry_is_name_authority(self):
        names = adapter.load_known_enemies()
        if not names:
            self.skipTest("decomp enemyInfo.cpp unavailable")
        for expected in ("Sokkuri", "Queen", "KingChappy", "Demon",
                         "Kabuto", "YellowKochappy"):
            self.assertIn(expected, names)
        enemy, treasure, drop = adapter.parse_teki_token(
            "Queen_dashboots", names)
        self.assertEqual((enemy, treasure, drop), ("Queen", "dashboots", 0))

    def test_missing_registry_refuses_explicit_path(self):
        with self.assertRaises(adapter.CaveDecodeError):
            adapter.load_known_enemies("definitely/not/enemyInfo.cpp")

    def test_manifest_never_emits_placements(self):
        floor_max, floors = adapter.parse_caveinfo(
            synthetic_cave(), SYNTHETIC_NAMES)
        manifest = adapter.build_manifest(floor_max, floors, "s", "h")
        self.assertFalse(manifest["placements_emitted"])
        self.assertNotIn("placements", manifest)


if __name__ == "__main__":
    unittest.main()
