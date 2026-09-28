"""Focused fail-closed tests for the save serializer conformance (#712)."""
import unittest

from experimental.pikmin2_save_serializer_conformance import (
    BLOCK_FIELDS,
    DOWNSTREAM,
    PINS,
    all_present,
    parse,
    review_request,
    round_trip,
    serialize,
    verify_pins,
)

RESEARCH = "C:/Users/alari/pikmin-randomizer"


def sample(kind):
    if kind == "playdata":
        return {"version": 1, "treasure_count": 3, "debt_flags": [0, 1],
                "area_records": [{"course": 0}], "squad_records": [10],
                "captain_records": [{"hp": 100}]}
    if kind == "olimardata":
        return {"flags": [1, 0]}
    return {"formation": [1, 2], "time": 300.0, "course_idx": 2,
            "cave_id": "tutorial_1", "floor": 1,
            "waterwraith": {"alive": False, "timer": 0.0},
            "gated": {"active_navi": 0}}


class PinTests(unittest.TestCase):
    def test_all_six_pins_present(self):
        rows = verify_pins(RESEARCH)
        self.assertEqual(len(rows), 6)
        self.assertTrue(all_present(rows), rows)
        names = {(row["symbol"], row["line"]) for row in rows}
        self.assertEqual(names, {(s, n) for s, n, _ in PINS})

    def test_absent_tree_is_absent_not_invented(self):
        rows = verify_pins("C:/nonexistent-research-root-712")
        self.assertEqual(len(rows), 6)
        self.assertFalse(all_present(rows))
        self.assertTrue(all(row["status"] == "ABSENT" for row in rows))


class RoundTripTests(unittest.TestCase):
    def test_all_kinds_round_trip(self):
        for kind in ("playdata", "olimardata", "cavesavedata"):
            self.assertTrue(round_trip(kind, sample(kind)),
                            "round trip failed for " + kind)

    def test_mutation_breaks_equality(self):
        block = sample("olimardata")
        blob = serialize("olimardata", block)
        other = dict(block, flags=[0, 0])
        self.assertNotEqual(
            __import__("json").loads(blob.decode())["fields"], other)
        self.assertTrue(round_trip("olimardata", other))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            serialize("nope", {})
        with self.assertRaises(ValueError):
            parse("nope", b"{}")


class GuardTests(unittest.TestCase):
    def test_empty_and_malformed_refused(self):
        for bad in (b"", bytearray(), "text", None, 7):
            with self.assertRaises(ValueError):
                parse("playdata", bad)

    def test_kind_mismatch_refused(self):
        blob = serialize("playdata", sample("playdata"))
        with self.assertRaises(ValueError):
            parse("olimardata", blob)

    def test_truncated_and_oversize_refused(self):
        blob = serialize("cavesavedata", sample("cavesavedata"))
        with self.assertRaises(ValueError):
            parse("cavesavedata", blob[:-4])
        with self.assertRaises(ValueError):
            parse("cavesavedata", blob, size=len(blob) - 1)

    def test_missing_field_rejected(self):
        block = sample("playdata")
        del block["squad_records"]
        with self.assertRaises(ValueError):
            serialize("playdata", block)


class ContractTests(unittest.TestCase):
    def test_block_fields_cover_downstream(self):
        self.assertIn("area_records", BLOCK_FIELDS["playdata"])
        self.assertIn("squad_records", BLOCK_FIELDS["playdata"])
        self.assertIn("captain_records", BLOCK_FIELDS["playdata"])
        self.assertEqual(DOWNSTREAM, (132, 112, 68, 533, 550, 154, 161))

    def test_review_request_names_186_and_pins(self):
        text = review_request()
        self.assertIn("#186", text)
        for symbol in ("PlayData", "CaveSaveData", "OlimarData"):
            self.assertIn(symbol, text)
        self.assertNotIn("ADMIT", text)


if __name__ == "__main__":
    unittest.main()
