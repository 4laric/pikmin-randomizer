"""Log-parsing tests for the hidden-window P2 campaign smoke (#186).

Pure fixture text only: no native launch, no game assets. The abort, missing
bind and clean-run cases are the three the lane's acceptance names.
"""
import unittest

from scripts.p2_campaign_smoke import (
    evaluate,
    expected_bindings,
    parse_native_log,
)


CLEAN_LOG = """\
[PC Port] loading stage
P2_SEED_RESOLVE source_id=54 target=3731060235 original_type=4 x=325.2 z=955.0
P2_SEED_RESOLVE source_id=62 target=1877315663 original_type=4 x=-1356.4 z=2109.3
[BBFT] PIKMIN_WORLD_RENDERED
P2_MAMUTA_READY generator=3731060235 native_type=24 xyz=325.192841,-32.734291,954.977173 P1_proxy_source_pose_banks_no_P2_planting
P2_OTAKARA_BIND generator=1877315663 source_id=62 stimulus=InteractDenki visual_only=0
P2_ENEMY_READY species=ElecOtakara native_family=Chappy generator=1877315663 x=1.0 y=2.0 z=3.0 health=150.0 max_health=150.0 behavior=native source_FSM=implemented attack=elemental_discharge
"""

EXPECTED = [
    {"target": "3731060235", "label": "hope_0-29_2038", "source_id": 54,
     "enum_name": "Miulin", "first_day": 2},
    {"target": "1877315663", "label": "hope_0-29_2452", "source_id": 62,
     "enum_name": "ElecOtakara", "first_day": 2},
]


class ParseTests(unittest.TestCase):
    def test_clean_run(self):
        parsed = parse_native_log(CLEAN_LOG)
        self.assertTrue(parsed["booted"])
        self.assertFalse(parsed["aborted"])
        self.assertFalse(parsed["captain_down"])
        self.assertEqual(parsed["bound"][3731060235], "Miulin")
        self.assertEqual(parsed["bound"][1877315663], "ElecOtakara")
        self.assertEqual(parsed["species_counts"], {"Miulin": 1, "ElecOtakara": 1})
        result = evaluate(parsed, EXPECTED)
        self.assertTrue(result["ok"])
        self.assertEqual(result["missing_binds"], [])
        self.assertEqual(result["species_binds"], {"Miulin": 1, "ElecOtakara": 1})

    def test_abort_marker_fails(self):
        parsed = parse_native_log(
            CLEAN_LOG + "P2_SETUP_ABORT Otakara actor_type_mismatch\n")
        self.assertTrue(parsed["aborted"])
        self.assertIn("P2_SETUP_ABORT Otakara actor_type_mismatch", parsed["abort_markers"])
        self.assertFalse(evaluate(parsed, EXPECTED)["ok"])

    def test_missing_bind_fails(self):
        text = CLEAN_LOG.replace(
            "P2_MAMUTA_READY generator=3731060235 native_type=24 "
            "xyz=325.192841,-32.734291,954.977173 "
            "P1_proxy_source_pose_banks_no_P2_planting\n", "")
        result = evaluate(parse_native_log(text), EXPECTED)
        self.assertFalse(result["ok"])
        self.assertEqual([row["target"] for row in result["missing_binds"]],
                         ["3731060235"])
        self.assertEqual(result["species_binds"], {"ElecOtakara": 1})

    def test_resolution_alone_is_not_a_bind(self):
        text = ("P2_SEED_RESOLVE source_id=54 target=3731060235 original_type=4\n"
                "[BBFT] PIKMIN_WORLD_RENDERED\n")
        parsed = parse_native_log(text)
        self.assertIn(3731060235, parsed["resolved"])
        self.assertNotIn(3731060235, parsed["bound"])

    def test_not_booted_fails(self):
        result = evaluate(parse_native_log("P2_MAMUTA_READY generator=3731060235\n"),
                          EXPECTED)
        self.assertFalse(result["ok"])

    def test_captain_down_blocks(self):
        parsed = parse_native_log(
            CLEAN_LOG + "P2_FIXTURE_CAPTAIN_DOWN tick=4 hp=0.000 outcome=BLOCKED\n")
        self.assertTrue(parsed["captain_down"])
        self.assertFalse(evaluate(parsed, EXPECTED)["ok"])

    def test_setup_skip_and_missing_file_reported(self):
        text = CLEAN_LOG + (
            "P2_SETUP_SKIP BlueKochappy actor_roster_incomplete\n"
            "[PC Port] DVDOpen(\"dataDir/courses/pikmin2room/miulin_waitact_00.mod\") "
            "-> FAIL\n")
        parsed = parse_native_log(text)
        self.assertEqual(parsed["setup_skips"],
                         [{"species": "BlueKochappy", "reason": "actor_roster_incomplete"}])
        self.assertEqual(len(parsed["missing_files"]), 1)

    def test_generated_placement_and_batch2_bind(self):
        text = (
            "P2_GENERATED_PLACEMENT source_id=59 target=2074106479 generator=0 bound=1\n"
            "P2_BATCH2_BIND generator=3138990329 key=dweevil|ElecOtakara "
            "visual_only=1 native_fsm=unimplemented\n")
        parsed = parse_native_log(text)
        self.assertIn(2074106479, parsed["bound"])
        self.assertEqual(parsed["bound"][3138990329], "ElecOtakara")


class ExpectedTests(unittest.TestCase):
    SLOTS = {
        "1": {"uid": 1, "label": "hope_0-29_1624", "first_day": 2},
        "2": {"uid": 2, "label": "hope_4-29_1624", "first_day": 5},
        "3": {"uid": 3, "label": "impact_9_1764", "first_day": 10},
        "4": {"uid": 4, "label": "hope_0-29_2452", "first_day": 2},
    }

    def manifest(self, bindings):
        return {"p2_layout": {"bindings": bindings}}

    def test_filters_to_active_hope_slots(self):
        manifest = self.manifest([
            {"target": "1", "source_id": 54, "enum_name": "Miulin"},
            {"target": "2", "source_id": 54, "enum_name": "Miulin"},
            {"target": "3", "source_id": 54, "enum_name": "Miulin"},
            {"target": "4", "source_id": 62, "enum_name": "ElecOtakara"},
        ])
        rows = expected_bindings(manifest, self.SLOTS)
        self.assertEqual([row["target"] for row in rows], ["1", "4"])
        self.assertEqual([row["label"] for row in rows],
                         ["hope_0-29_1624", "hope_0-29_2452"])

    def test_unknown_target_ignored(self):
        manifest = self.manifest([{"target": "99", "source_id": 54,
                                   "enum_name": "Miulin"}])
        self.assertEqual(expected_bindings(manifest, self.SLOTS), [])


if __name__ == "__main__":
    unittest.main()
