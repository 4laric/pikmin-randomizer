"""Contract tests for the tutorial stage-table row provider (issue #754).

Pins the ch_ABEM_tutorial row values and exercises the record stager plus
the fixture-log validator: canonical agreement, double resolution, wrong
cave/ui/floors, injected markers, and empty logs. The native behavioral
proof (row resolution by the real lookup plus a guarded boot) lives in
native/tools/p2_tutorial_stage_guarded_fixture.cpp; agreement here
alone never passes acceptance.
"""
import unittest

from experimental.pikmin2_tutorial_stage_table_row import (
    PINNED,
    PROVIDER,
    RECORD_FILE,
    RECORD_MAGIC,
    provider_contract,
    render_record,
    validate_log,
)

GOOD = "\n".join([
    "P2_TUTORIAL_STAGE_RESOLVED cave=ch_ABEM_tutorial ui_index=0 floors=2",
    "P2_TUTORIAL_STAGE_REFUSED reason=unknown-key",
])


class ContractTests(unittest.TestCase):
    def test_contract_shape(self):
        contract = provider_contract()
        self.assertEqual(contract["schema"], PROVIDER)
        self.assertEqual(contract["consumer_issue"], 534)
        self.assertTrue(contract["exactly_once"])
        self.assertFalse(contract["runtime_claim"])
        self.assertIn("pc_bbft.cpp", contract["integration"])

    def test_pins(self):
        self.assertEqual(PINNED["cave_id"], "ch_ABEM_tutorial")
        self.assertEqual(PINNED["cave_path"],
                         "user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt")
        self.assertEqual(PINNED["ui_index"], 0)
        self.assertEqual(PINNED["table_order"], 0)
        self.assertEqual(PINNED["floors"], 2)
        self.assertEqual(PINNED["floor_seconds"], [100.0, 100.0])
        self.assertEqual(PINNED["roster"][1], [50, 0, 0])
        self.assertEqual(PINNED["roster"][0], [0, 0, 0])
        self.assertEqual(PINNED["roster"][6], [0, 0, 0])
        self.assertEqual((PINNED["bitter_sprays"], PINNED["spicy_sprays"]), (2, 2))
        self.assertEqual(PINNED["legacy_time"], 0.0)
        self.assertEqual(PINNED["treasure_count_field"], 0)
        self.assertEqual(PINNED["source_sha256"],
                         "e21f31f7fa5621a5922d9ee54ffb211a8e4f0e797866d70cc1edb98389ab097d")


class RecordTests(unittest.TestCase):
    def test_record_shape(self):
        text = render_record()
        lines = text.splitlines()
        self.assertEqual(lines[0], RECORD_MAGIC)
        self.assertEqual(lines[1], "cave ch_ABEM_tutorial ui_index 0 table_order 0 floors 2")
        self.assertEqual(lines[2], "source user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt "
                                   "e21f31f7fa5621a5922d9ee54ffb211a8e4f0e797866d70cc1edb98389ab097d")
        self.assertEqual(lines[3], "timers 100.0 100.0 legacy 0.0")
        self.assertEqual(lines[4], "sprays bitter 2 spicy 2 treasure_field 0")
        self.assertEqual(lines[5], "roster 0 0 0")
        self.assertEqual(lines[6], "roster 50 0 0")
        self.assertEqual(len(lines), 12)
        self.assertTrue(text.endswith("\n") and not text.endswith("\n\n"))

    def test_record_file_name(self):
        self.assertEqual(RECORD_FILE, "p2-tutorial-stage-select.txt")


class ValidateLogTests(unittest.TestCase):
    def test_canonical_log_agrees(self):
        result = validate_log(GOOD)
        self.assertTrue(result["verdict"], result["problems"])
        self.assertEqual(result["resolved"][0]["cave"], "ch_ABEM_tutorial")

    def test_double_resolution_refused(self):
        lines = GOOD + "\nP2_TUTORIAL_STAGE_RESOLVED cave=ch_ABEM_tutorial ui_index=0 floors=2"
        result = validate_log(lines)
        self.assertFalse(result["verdict"])
        self.assertIn("resolved-count-2", result["problems"])

    def test_wrong_cave_refused(self):
        result = validate_log("P2_TUTORIAL_STAGE_RESOLVED cave=ch_NARI_01kusachi ui_index=3 floors=1")
        self.assertFalse(result["verdict"])
        self.assertIn("wrong-cave:ch_NARI_01kusachi", result["problems"])

    def test_wrong_ui_refused(self):
        result = validate_log("P2_TUTORIAL_STAGE_RESOLVED cave=ch_ABEM_tutorial ui_index=1 floors=2")
        self.assertFalse(result["verdict"])
        self.assertIn("wrong-ui:1", result["problems"])

    def test_wrong_floors_refused(self):
        result = validate_log("P2_TUTORIAL_STAGE_RESOLVED cave=ch_ABEM_tutorial ui_index=0 floors=1")
        self.assertFalse(result["verdict"])
        self.assertIn("wrong-floors:1", result["problems"])

    def test_injected_markers_refused(self):
        result = validate_log(GOOD + "\nP2_TUTORIAL_INJECT cave=ch_ABEM_tutorial")
        self.assertFalse(result["verdict"])
        self.assertIn("injected-markers-present", result["problems"])

    def test_empty_log_refused(self):
        result = validate_log("")
        self.assertFalse(result["verdict"])
        self.assertIn("resolved-count-0", result["problems"])


if __name__ == "__main__":
    unittest.main()
