"""Focused fail-closed tests for the yakushima4 save-persistence adapter (#784).

Synthetic inputs only: no engine files, no runtime, no shared state. Pins the
#132 cave-save wire format, the floor/roster state checks, the day anchors and
the #779 pin record validation.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "pikmin2_yakushima4_save_persistence",
    ROOT / "experimental/pikmin2_yakushima4_save_persistence.py")
_adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_adapter)

SavePersistenceError = _adapter.SavePersistenceError
audit_floor_boundary = _adapter.audit_floor_boundary
blockers = _adapter.blockers
default_pin_record = _adapter.default_pin_record
format_floor_boundary_transfer = _adapter.format_floor_boundary_transfer
load_pin_record = _adapter.load_pin_record
transfer_schema = _adapter.transfer_schema
validate_checkpoint_text = _adapter.validate_checkpoint_text
validate_day_anchors = _adapter.validate_day_anchors
validate_floor_boundary_state = _adapter.validate_floor_boundary_state
validate_pin_record = _adapter.validate_pin_record

TOKEN = "a" * 32


def entry_text(version="P2_CAVE_ENTRY_1", squad=((0, 0), (1, 1), (3, 2)), floor=1, health=0.625, token=TOKEN):
    body = "\n".join("%d %d" % s for s in squad)
    return "%s\n%s\n%d %.9g %d\n%s\n" % (version, token, floor, health, len(squad), body)


def good_state(floor=1, census=3):
    return {"floor_id": floor, "squad": [{"species": 0, "maturity": 0}] * census,
            "census": census, "nav_topology": {"rooms": 8, "links": 36}}


def good_anchors(floor=1):
    return {"day_count": 8, "mCurrentCaveID": "ch_NARI_03toy", "mCurrentFloor": floor,
            "cave_day_end_state": "init", "cave_save_data": "present"}


class PinRecordTests(unittest.TestCase):
    def test_default_record_validates(self):
        result = validate_pin_record(default_pin_record())
        self.assertTrue(result["validated"])
        self.assertEqual(result["downstream"], _adapter.DOWNSTREAM_CONSUMER)

    def test_missing_contract_refused(self):
        rec = default_pin_record()
        del rec["contracts"]["dayclock_anchors"]
        with self.assertRaises(SavePersistenceError) as ctx:
            validate_pin_record(rec)
        self.assertEqual(ctx.exception.blocker, "missing-section")

    def test_malformed_pin_refused(self):
        rec = default_pin_record()
        rec["root_base"] = "nothex"
        with self.assertRaises(SavePersistenceError) as ctx:
            validate_pin_record(rec)
        self.assertEqual(ctx.exception.blocker, "invalid-pin")

    def test_absent_provider_refused(self):
        rec = default_pin_record()
        rec["downstream"] = "some-other-lane"
        with self.assertRaises(SavePersistenceError) as ctx:
            validate_pin_record(rec)
        self.assertEqual(ctx.exception.blocker, "absent-provider")

    def test_empty_sections_refused(self):
        rec = default_pin_record()
        rec["contracts"]["cave_save"]["sections"] = {}
        with self.assertRaises(SavePersistenceError) as ctx:
            validate_pin_record(rec)
        self.assertEqual(ctx.exception.blocker, "missing-section")

    def test_load_pin_record_missing_file(self):
        with self.assertRaises(SavePersistenceError) as ctx:
            load_pin_record("C:/nonexistent/pin-record.json")
        self.assertEqual(ctx.exception.blocker, "absent-provider")

    def test_load_pin_record_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.json"
            path.write_text(json.dumps(default_pin_record()), encoding="utf-8")
            self.assertTrue(load_pin_record(path)["validated"])


class WireFormatTests(unittest.TestCase):
    def test_valid_entry_and_transfer_parse(self):
        entry = validate_checkpoint_text(entry_text())
        self.assertEqual((entry["direction"], entry["schema"], entry["count"]), ("entry", 1, 3))
        transfer = validate_checkpoint_text(entry_text(version="P2_CAVE_TRANSFER_3",
                                                       squad=((0, 0), (5, 0))))
        self.assertEqual(transfer["direction"], "transfer")
        self.assertEqual(transfer["squad"][1]["species"], 5)

    def test_bad_token_and_unknown_schema_refused(self):
        for text in (entry_text(token="g" * 32), entry_text(version="P2_CAVE_ENTRY_9"),
                     entry_text(version="P2_OTHER_1")):
            with self.subTest(text=text[:20]):
                with self.assertRaises(SavePersistenceError) as ctx:
                    validate_checkpoint_text(text)
                self.assertEqual(ctx.exception.blocker, "header")

    def test_out_of_scope_floor_refused_exactly(self):
        with self.assertRaises(SavePersistenceError) as ctx:
            validate_checkpoint_text(entry_text(floor=3))
        self.assertEqual(ctx.exception.blocker, "out-of-scope-floor")

    def test_bad_health_count_and_trailing_refused(self):
        for text in (entry_text(health=1.5), entry_text(health=0.0), entry_text(floor=7),
                     entry_text(squad=()) , entry_text() + "0 0\n"):
            with self.subTest(text=text[:20]):
                with self.assertRaises(SavePersistenceError):
                    validate_checkpoint_text(text)

    def test_species_schema_enforced(self):
        # Bulbmin (5) needs schema 3; White (4) needs schema 2.
        with self.assertRaises(SavePersistenceError) as ctx:
            validate_checkpoint_text(entry_text(version="P2_CAVE_ENTRY_2", squad=((5, 0),)))
        self.assertEqual(ctx.exception.blocker, "Pikmin")
        with self.assertRaises(SavePersistenceError):
            validate_checkpoint_text(entry_text(version="P2_CAVE_ENTRY_1", squad=((4, 0),)))
        # Bad maturity refused too.
        with self.assertRaises(SavePersistenceError):
            validate_checkpoint_text(entry_text(squad=((0, 3),)))

    def test_transfer_schema_bumps_and_never_downgrades(self):
        self.assertEqual(transfer_schema(1, [{"species": 0}]), 1)
        self.assertEqual(transfer_schema(1, [{"species": 0}, {"species": 4}]), 2)
        self.assertEqual(transfer_schema(2, [{"species": 5}]), 3)
        self.assertEqual(transfer_schema(3, [{"species": 0}]), 3)

    def test_format_round_trip_and_out_of_scope(self):
        text = format_floor_boundary_transfer({"token": TOKEN, "floor": 1, "health": 0.625,
                                               "squad": [{"species": 0, "maturity": 0},
                                                         {"species": 5, "maturity": 2}]})
        parsed = validate_checkpoint_text(text)
        self.assertEqual(parsed["schema"], 3)
        self.assertEqual(len(parsed["squad"]), 2)
        with self.assertRaises(SavePersistenceError) as ctx:
            format_floor_boundary_transfer({"token": TOKEN, "floor": 4, "health": 0.5,
                                            "squad": [{"species": 0, "maturity": 0}]})
        self.assertEqual(ctx.exception.blocker, "out-of-scope-floor")


class StateAndAnchorTests(unittest.TestCase):
    def test_floor_state_valid_and_refusals(self):
        self.assertEqual(validate_floor_boundary_state(good_state())["census"], 3)
        with self.assertRaises(SavePersistenceError) as ctx:
            validate_floor_boundary_state(good_state(floor=4))
        self.assertEqual(ctx.exception.blocker, "out-of-scope-floor")
        bad = good_state()
        bad["census"] = 2
        with self.assertRaises(SavePersistenceError):
            validate_floor_boundary_state(bad)
        bad = good_state()
        bad["nav_topology"] = {}
        with self.assertRaises(SavePersistenceError):
            validate_floor_boundary_state(bad)

    def test_day_anchors_valid_and_refusals(self):
        self.assertEqual(validate_day_anchors(good_anchors())["day_count"], 8)
        for mutate in ({"day_count": 0}, {"day_count": 30}, {"mCurrentCaveID": ""},
                       {"mCurrentFloor": 6}, {"cave_day_end_state": "idle"}, {"cave_save_data": "?"}):
            bad = good_anchors()
            bad.update(mutate)
            with self.subTest(mutate=mutate):
                with self.assertRaises(SavePersistenceError):
                    validate_day_anchors(bad)


class AuditTests(unittest.TestCase):
    def test_audit_valid_assembles_plan(self):
        plan = audit_floor_boundary(default_pin_record(), entry_text(), good_state(), good_anchors())
        self.assertTrue(plan["pinned"]["validated"])
        self.assertEqual(plan["floor_state"]["nav_topology"]["links"], 36)
        self.assertEqual(set(plan["citations"]), {"cave_save", "dayclock_anchors", "surface_session"})

    def test_audit_refuses_mismatched_floor_and_census(self):
        with self.assertRaises(SavePersistenceError) as ctx:
            audit_floor_boundary(default_pin_record(), entry_text(floor=2), good_state(floor=1), good_anchors())
        self.assertEqual(ctx.exception.blocker, "mismatched-floor")
        with self.assertRaises(SavePersistenceError) as ctx:
            audit_floor_boundary(default_pin_record(), entry_text(), good_state(census=1), good_anchors())
        self.assertEqual(ctx.exception.blocker, "mismatched-census")

    def test_blockers_collects_exact_reasons(self):
        bad = default_pin_record()
        bad["root_base"] = "x"
        found = blockers(record=bad, checkpoint_text=None, state=None, anchors=None)
        kinds = {b["blocker"] for b in found}
        self.assertIn("invalid-pin", kinds)
        self.assertIn("absent-provider", kinds)
        self.assertEqual(blockers(record=default_pin_record(), checkpoint_text=entry_text(),
                                 state=good_state(), anchors=good_anchors()), [])
        self.assertTrue(blockers())  # missing inputs are blockers, never a pass


if __name__ == "__main__":
    unittest.main()
