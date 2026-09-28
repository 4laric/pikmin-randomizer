"""Focused tests for lane 51's item-5 independent QA checker."""
from __future__ import annotations

import json
import unittest

from experimental.pikmin2_cave_item5_qa import (
    NATURAL,
    STAGED,
    MOCKED,
    MISSING,
    REAL,
    PROXY,
    PASS,
    FAIL,
    STAGED_OPEN,
    evaluate,
    main,
    parse_markers,
)

NATURAL_LOG = """\
P2_CAVE_BUD_ACTOR slot=forest_1:f1:bud:0 colour=yellow segment=0 count=5 x=120.000 y=-0.000 z=48.000 spawned=1
P2_CAVE_BUD_ACCEPT slot=forest_1:f1:bud:0 colour=yellow thrown_colour=1 used=1 budget=5
P2_CAVE_BUD_SPROUT slot=forest_1:f1:bud:0 colour=yellow colour_index=2 plucked=1 natural=1
P2_CAVE_ROOMS_GRANT species=yellow natural_acquire=1 staged=0 conversions=1
P2_CAVE_GEOMETRY_NODE id=choke_water_0 kind=choke hazard=water class=real model=m1.mod proxy=0
P2_CAVE_GEOMETRY_NODE id=leaf_water_0 kind=leaf hazard=water class=real model=m1.mod proxy=0
P2_CAVE_GEOMETRY_NODE id=leaf_elec_0 kind=leaf hazard=elec class=real model=m2.mod proxy=0
P2_CAVE_GEOMETRY_NODE id=gate:leaf_elec_0 kind=gate hazard=elec class=real model=g.mod proxy=0
P2_CAVE_GEOMETRY_READY nodes=6 real=4 proxy=2 gate_actors=2 geometry=real cave=forest_1 floor=1 seed=468001 salt=0
P2_CAVE_GEOMETRY_DRAW nodes=6 models=4 gates=2 geometry=real
P2_CAVE_GEOMETRY_GATE_DENKI id=leaf_elec_0 actor=p2_elec_gate target=1 accepted=1 target_state=35
P2_CAVE_ROOMS_TIMELINE tag=fresh_floor_no_abilities hole=0 treasure_elec=0 treasure_water=0 untagged=1
P2_CAVE_CARRY_DOOR id=leaf_elec_0 kind=leaf hazard=elec carry_block=elec key=yellow
P2_CAVE_CARRY_DOOR id=leaf_water_0 kind=leaf hazard=water carry_block=water key=blue
P2_CAVE_CARRY_PLAN doors=6 blocking=4 elec=2 water=2 geometry=real cave=forest_1 floor=1 seed=468001
P2_CAVE_CARRY_BLOCKED id=leaf_elec_0 hazard=elec species=1 carrying=1 accepted=1
P2_CAVE_CARRY_BLOCKED id=choke_water_0 hazard=water species=1 carrying=1 accepted=1
P2_CAVE_CARRY_OPEN id=leaf_elec_0 hazard=elec reason=electric_immune
P2_CAVE_ROOMS_TIMELINE tag=come_back_with_yellow hole=0 treasure_elec=1 treasure_water=0 untagged=1
P2_CAVE_ITEM_RECEIPT id=x item=treasure_elec host=leaf_elec_0 tagged=1 new=1 tag=cave_treasure seed=468001 result=1
P2_CAVE_ITEM_RECEIPT id=x item=treasure_elec host=leaf_elec_0 tagged=1 new=0 tag=cave_treasure seed=468001 result=0
P2_CAVE_ROOMS_TIMELINE tag=return_with_yellow_and_blue hole=1 treasure_elec=1 treasure_water=1 untagged=1
"""


class ParseTest(unittest.TestCase):
    def test_ignores_non_markers_and_records_malformed(self):
        parsed = parse_markers("hello\nP2_CAVE_BUD_ACTOR oops\nP2_CAVE_GEN source=engine\n")
        self.assertEqual(len(parsed["malformed"]), 1)
        self.assertEqual(len(parsed["gen"]), 1)

    def test_bytes_and_none_inputs(self):
        self.assertEqual(parse_markers(None)["grant"], [])
        self.assertEqual(len(parse_markers(b"P2_CAVE_BUD_ACCEPT slot=s colour=yellow thrown_colour=1 used=1 budget=5")["accept"]), 1)


class AcquisitionTest(unittest.TestCase):
    def test_natural_loop_passes(self):
        result = evaluate(NATURAL_LOG)
        self.assertTrue(result["pass"], json.dumps(result["remaining"]))
        self.assertEqual(result["rows"]["natural_acquisition"], NATURAL)
        self.assertEqual(result["evidence_class"], NATURAL)

    def test_staged_grant_downgrades(self):
        log = NATURAL_LOG.replace("natural_acquire=1 staged=0", "natural_acquire=0 staged=1")
        result = evaluate(log)
        self.assertFalse(result["pass"])
        self.assertEqual(result["rows"]["natural_acquisition"], STAGED)
        self.assertIn("staged_grant", result["natural_acquisition"]["reasons"])
        # A staged opening can never pass the credit row naturally.
        self.assertEqual(result["rows"]["gate_open_credit"], STAGED_OPEN)
        self.assertTrue(any("natural_acquisition" in r for r in result["remaining"]))

    def test_staged_other_species_does_not_poison_natural(self):
        # Lane 48's live shape: natural yellow alongside a still-staged blue.
        log = NATURAL_LOG + "P2_CAVE_ROOMS_GRANT species=blue natural_acquire=0 staged=1\n"
        result = evaluate(log)
        self.assertEqual(result["rows"]["natural_acquisition"], NATURAL)

    def test_missing_bud_is_missing_not_natural(self):
        lines = [ln for ln in NATURAL_LOG.splitlines() if not ln.startswith("P2_CAVE_BUD")]
        result = evaluate("\n".join(lines))
        self.assertFalse(result["pass"])
        self.assertIn(result["rows"]["natural_acquisition"], (MOCKED, MISSING))

    def test_conversion_without_bud_is_mocked(self):
        log = "P2_CAVE_BUD_ACCEPT slot=s colour=yellow thrown_colour=1 used=1 budget=5\nP2_CAVE_ROOMS_GRANT species=yellow natural_acquire=1 staged=0\n"
        result = evaluate(log)
        self.assertFalse(result["natural_acquisition"]["pass"])
        self.assertEqual(result["natural_acquisition"]["classification"], MOCKED)


class GeometryTest(unittest.TestCase):
    def test_real_geometry_passes(self):
        result = evaluate(NATURAL_LOG)
        self.assertEqual(result["rows"]["real_geometry"], REAL)

    def test_proxy_geometry_fails(self):
        log = NATURAL_LOG.replace("class=real", "class=proxy").replace("proxy=0", "proxy=1")
        log = log.replace("geometry=real", "geometry=proxy").replace("real=4", "real=0")
        result = evaluate(log)
        self.assertFalse(result["pass"])
        self.assertEqual(result["rows"]["real_geometry"], PROXY)

    def test_no_geometry_is_missing(self):
        lines = [ln for ln in NATURAL_LOG.splitlines() if "GEOMETRY" not in ln]
        result = evaluate("\n".join(lines))
        self.assertEqual(result["rows"]["real_geometry"], MISSING)


class CarryTest(unittest.TestCase):
    def test_full_carry_loop_passes(self):
        result = evaluate(NATURAL_LOG)
        self.assertEqual(result["rows"]["carry_blocked_closed"], PASS)
        self.assertEqual(result["rows"]["gate_open_credit"], PASS)
        self.assertEqual(result["rows"]["water_gating"], PASS)

    def test_credit_while_closed_fails_both_rows(self):
        lines = NATURAL_LOG.splitlines()
        # Move the fresh receipt above the open marker.
        receipt = [ln for ln in lines if "new=1" in ln][0]
        lines.remove(receipt)
        idx = next(i for i, ln in enumerate(lines) if ln.startswith("P2_CAVE_CARRY_OPEN"))
        lines.insert(idx, receipt)
        result = evaluate("\n".join(lines))
        self.assertEqual(result["rows"]["carry_blocked_closed"], FAIL)
        self.assertEqual(result["rows"]["gate_open_credit"], FAIL)

    def test_no_open_is_missing_or_fail(self):
        lines = [ln for ln in NATURAL_LOG.splitlines()
                 if not ln.startswith("P2_CAVE_CARRY_OPEN") and "new=" not in ln]
        result = evaluate("\n".join(lines))
        self.assertIn(result["rows"]["gate_open_credit"], (FAIL, MISSING))

    def test_no_water_block_fails_water_row(self):
        lines = [ln for ln in NATURAL_LOG.splitlines() if "hazard=water species=" not in ln]
        result = evaluate("\n".join(lines))
        self.assertEqual(result["rows"]["water_gating"], FAIL)

    def test_no_carry_markers_is_missing(self):
        result = evaluate("P2_CAVE_ROOMS_TIMELINE tag=fresh_floor_no_abilities hole=0 treasure_elec=0 treasure_water=0 untagged=1\n")
        self.assertEqual(result["rows"]["carry_blocked_closed"], MISSING)
        self.assertEqual(result["rows"]["water_gating"], MISSING)


class TimelineTest(unittest.TestCase):
    def test_hole_open_early_fails(self):
        log = NATURAL_LOG.replace("tag=fresh_floor_no_abilities hole=0", "tag=fresh_floor_no_abilities hole=1")
        result = evaluate(log)
        self.assertEqual(result["rows"]["hole_gating"], FAIL)
        self.assertEqual(result["rows"]["timeline"], FAIL)

    def test_determinism(self):
        self.assertEqual(evaluate(NATURAL_LOG), evaluate(NATURAL_LOG))

    def test_multi_log_merge(self):
        half = NATURAL_LOG.split("P2_CAVE_CARRY_OPEN")[0]
        rest = "P2_CAVE_CARRY_OPEN" + NATURAL_LOG.split("P2_CAVE_CARRY_OPEN")[1]
        result = evaluate([half, rest])
        self.assertTrue(result["pass"])


class CliTest(unittest.TestCase):
    def test_main_rejects_missing_log(self):
        self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
