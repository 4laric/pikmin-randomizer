"""Fail-closed tests for the tutorial row landing-request packet (#754).

Diagnosis/packet only: these tests pin the source contract, the destination
table parse, the emitted unified spec, and the refusal paths for malformed
or missing input. They never edit engine files or claim acceptance.
"""
import unittest

from experimental.pikmin2_tutorial_row_landing_request import (
    DESTINATION,
    PACKET,
    SOURCE,
    cmake_membership_assessment,
    decision_request,
    downstream_record,
    landing_spec,
    parse_table,
    render_row_literal,
    validate,
)

# Mirror of the live destination table region (pc_bbft.cpp).
FIXTURE = "\n".join([
    "struct P2ChallengeStageRow {",
    "    const char* caveId;",
    "    const char* cavePath;",
    "    const char* sourceSha256;",
    "    int uiIndex;",
    "    int tableOrder;",
    "    int floors;",
    "    float floorSeconds[8];",
    "    int roster[7][3];",
    "    int bitterSprays;",
    "    int spicySprays;",
    "    float legacyTime;",
    "    int treasureCountField;",
    "};",
    "static const P2ChallengeStageRow kP2ChallengeStages[] = {",
    '    { "ch_NARI_01kusachi",',
    '      "user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt",',
    '      "b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85",',
    "      3, 3, 1,",
    "      { 180.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f },",
    "      { {0,0,50}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },",
    "      1, 2, 350.0f, 0 },",
    "};",
    "const P2ChallengeStageRow* pc_p2_challenge_stage_lookup(const char* caveId) {",
    "    return nullptr;",
    "}",
    "",
])


class ParseTests(unittest.TestCase):
    def test_rows_only_kusachi(self):
        parsed = parse_table(FIXTURE)
        self.assertEqual(parsed["rows"], ["ch_NARI_01kusachi"])
        self.assertEqual(parsed["anchor_index"], 22)


class LandingSpecTests(unittest.TestCase):
    def test_spec_contains_row_and_source(self):
        spec = landing_spec(FIXTURE)
        self.assertEqual(spec["packet"], PACKET)
        self.assertIn("ch_ABEM_tutorial", spec["unified_spec"])
        self.assertIn(SOURCE["row"]["source_sha256"], spec["unified_spec"])
        self.assertTrue(spec["unified_spec"].startswith("--- a/"))
        self.assertIn("@@", spec["unified_spec"])

    def test_literal_field_order(self):
        literal = render_row_literal()
        self.assertIn('"ch_ABEM_tutorial"', literal)
        self.assertIn("0, 0, 2,", literal)
        self.assertIn("{ 100.0f, 100.0f,", literal)
        self.assertIn("{ {0,0,0}, {50,0,0},", literal)

    def test_refuses_when_row_present(self):
        present = FIXTURE.replace(
            "static const P2ChallengeStageRow kP2ChallengeStages[] = {",
            "static const P2ChallengeStageRow kP2ChallengeStages[] = {\n"
            '    { "ch_ABEM_tutorial",')
        with self.assertRaises(ValueError):
            landing_spec(present)


class ValidateTests(unittest.TestCase):
    def test_positive(self):
        result = validate(FIXTURE)
        self.assertTrue(result["verdict"], result["problems"])

    def test_row_already_present_refused(self):
        present = FIXTURE.replace(
            "static const P2ChallengeStageRow kP2ChallengeStages[] = {",
            "static const P2ChallengeStageRow kP2ChallengeStages[] = {\n"
            '    { "ch_ABEM_tutorial",')
        result = validate(present)
        self.assertFalse(result["verdict"])
        self.assertTrue(any("row-already-present" in p
                            for p in result["problems"]), result["problems"])

    def test_missing_struct_refused(self):
        result = validate("int main() { return 0; }\n")
        self.assertFalse(result["verdict"])
        self.assertIn("missing P2ChallengeStageRow struct", result["problems"])

    def test_missing_table_refused(self):
        result = validate("struct P2ChallengeStageRow { int x; };\n")
        self.assertFalse(result["verdict"])
        self.assertIn("missing kP2ChallengeStages table", result["problems"])

    def test_unexpected_existing_row_refused(self):
        other = FIXTURE.replace("ch_NARI_01kusachi", "ch_OTHER_row")
        result = validate(other)
        self.assertFalse(result["verdict"])
        self.assertTrue(any(p.startswith("existing-rows:") for p in
                            result["problems"]), result["problems"])


class RecordTests(unittest.TestCase):
    def test_decision_request(self):
        req = decision_request()
        self.assertEqual(req["issue"], 186)
        self.assertEqual(req["options"],
                         ["approve", "approve-with-changes", "reject"])
        self.assertEqual(req["file"], "native/pc_port/pc_bbft.cpp")

    def test_downstream_record(self):
        rec = downstream_record()
        self.assertEqual(rec["recovery_id"], "e8e113b9")
        self.assertEqual(rec["consumer_issue"], 534)
        self.assertFalse(rec["runtime_claim"])

    def test_cmake_assessment(self):
        a = cmake_membership_assessment()
        self.assertFalse(a["needs_new_source_membership"])
        self.assertIn("native/CMakeLists.txt", a["do_not_edit"])

    def test_destination_pins_recorded(self):
        self.assertEqual(DESTINATION["table_symbol"], "kP2ChallengeStages")
        self.assertEqual(SOURCE["issue"], 754)


if __name__ == "__main__":
    unittest.main()