"""Focused tests for the overworld save-serializer reference model (#736).

Deterministic unit matrix over serialize/parse/round-trip plus malformed and
size-guard negatives. No runtime, no native build, no ADMIT.
"""
import sys
import unittest
from pathlib import Path

WT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WT))

from experimental import pikmin2_overworld_save_serializer_engine as engine


def good_session():
    return {"area": "yakushima", "day": 1, "squad": [20, 0, 0, 0, 0, 0, 0, 0],
            "other": 0, "total": 20, "highscore": 100, "unlocked": 1}


class SerializerTests(unittest.TestCase):
    def test_round_trip_valid(self):
        session = good_session()
        self.assertTrue(engine.round_trip(session))
        data = engine.serialize(session)
        self.assertTrue(data.startswith(b"P2_OVERWORLD_SAVE_1\n"))
        self.assertEqual(engine.parse(data), session)

    def test_deterministic(self):
        self.assertEqual(engine.serialize(good_session()), engine.serialize(good_session()))

    def test_empty_and_nonbytes_rejected(self):
        for bad in (b"", bytearray(), "text", None, 123):
            with self.assertRaises(engine.SaveError):
                engine.parse(bad)

    def test_oversize_rejected(self):
        data = engine.serialize(good_session())
        with self.assertRaises(engine.SaveError):
            engine.parse(data, max_bytes=len(data) - 1)

    def test_truncated_rejected(self):
        data = engine.serialize(good_session())
        with self.assertRaises(engine.SaveError):
            engine.parse(data[:40])

    def test_bad_magic_rejected(self):
        data = b"BAD_HEADER\n" + engine.serialize(good_session()).split(b"\n", 1)[1]
        with self.assertRaises(engine.SaveError):
            engine.parse(data)

    def test_census_mismatch_rejected(self):
        bad = good_session(); bad["total"] = 21
        with self.assertRaises(engine.SaveError):
            engine.serialize(bad)

    def test_range_violations_rejected(self):
        for key, value in (("day", -1), ("highscore", -5), ("unlocked", 2), ("other", -1)):
            bad = good_session(); bad[key] = value
            with self.assertRaises(engine.SaveError):
                engine.serialize(bad)

    def test_bad_area_rejected(self):
        for area in ("", "a" * 64, "has space", "semi;colon", None, 7):
            bad = good_session(); bad["area"] = area
            with self.assertRaises(engine.SaveError):
                engine.serialize(bad)

    def test_mutated_field_breaks_round_trip(self):
        session = good_session()
        self.assertTrue(engine.round_trip(session))
        data = bytearray(engine.serialize(session))
        data = data.replace(b"yakushima", b"yakushimb")
        self.assertNotEqual(engine.parse(bytes(data)), session)
        broken = bytearray(engine.serialize(session))
        broken = broken.replace(b"total 20", b"total 21")
        with self.assertRaises(engine.SaveError):
            engine.parse(bytes(broken))

    def test_native_file_list(self):
        self.assertEqual(len(engine.NATIVE_FILES), 3)
        self.assertIn("native/pc_port/pc_p2_overworld_save.cpp", engine.NATIVE_FILES)


if __name__ == "__main__":
    unittest.main()