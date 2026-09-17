"""Focused boundary tests for the Pom actor-birth marker contract."""
import unittest

from experimental.pikmin2_pom_actor_provider import (
    BASE_ID,
    COLORED_FIRST,
    COLORED_LAST,
    PARENT_ID,
    provider_contract,
    validate_log,
)


class ContractTest(unittest.TestCase):
    def test_contract_shape(self):
        contract = provider_contract()
        self.assertEqual(contract["schema"], "p2-pom-actor/1")
        self.assertEqual(contract["consumer_issue"], 448)
        self.assertEqual(contract["colored_source_ids"], [3, 4, 5, 6, 7, 8])
        self.assertEqual(contract["parent_id"], 82)
        self.assertEqual(contract["base_refused"], 82)
        self.assertFalse(contract["runtime_claim"])

    def test_identity_constants(self):
        self.assertEqual((COLORED_FIRST, COLORED_LAST, BASE_ID, PARENT_ID),
                         (3, 8, 82, 82))


class ValidateLogTest(unittest.TestCase):
    def test_valid_birth_log(self):
        verdict, detail = validate_log(
            "P2_POM_ACTOR_BIRTH generator=11 source_id=4 parent_id=82\n")
        self.assertTrue(verdict)
        self.assertIn("providers=1", detail)

    def test_valid_refusal_only_log(self):
        verdict, _ = validate_log(
            "P2_POM_BASE_REJECTED generator=11 source_id=82\n")
        self.assertTrue(verdict)

    def test_empty_log_fails_closed(self):
        self.assertFalse(validate_log("   \n")[0])
        self.assertFalse(validate_log("")[0])
        self.assertFalse(validate_log(None)[0])

    def test_birth_with_base_source_rejected(self):
        verdict, detail = validate_log(
            "P2_POM_ACTOR_BIRTH generator=11 source_id=82 parent_id=82\n")
        self.assertFalse(verdict)
        self.assertIn("non-colored", detail)

    def test_birth_with_wrong_source_rejected(self):
        verdict, _ = validate_log(
            "P2_POM_ACTOR_BIRTH generator=11 source_id=9 parent_id=82\n")
        self.assertFalse(verdict)

    def test_birth_with_wrong_parent_rejected(self):
        verdict, _ = validate_log(
            "P2_POM_ACTOR_BIRTH generator=11 source_id=4 parent_id=7\n")
        self.assertFalse(verdict)

    def test_double_birth_rejected(self):
        verdict, _ = validate_log(
            "P2_POM_ACTOR_BIRTH generator=11 source_id=4 parent_id=82\n"
            "P2_POM_ACTOR_BIRTH generator=11 source_id=4 parent_id=82\n")
        self.assertFalse(verdict)

    def test_generator_disagreement_rejected(self):
        verdict, detail = validate_log(
            "P2_POM_ACTOR_BIRTH generator=11 source_id=4 parent_id=82\n"
            "P2_POM_ACTOR_BIRTH generator=12 source_id=4 parent_id=82\n"
            "P2_POM_ACTOR_BIRTH generator=11 source_id=5 parent_id=82\n")
        self.assertFalse(verdict)
        self.assertIn("disagreement", detail)

    def test_refusal_naming_non_base_rejected(self):
        verdict, _ = validate_log(
            "P2_POM_BASE_REJECTED generator=11 source_id=4\n")
        self.assertFalse(verdict)

    def test_injected_markers_rejected(self):
        verdict, _ = validate_log(
            "P2_POM_ACTOR_BIRTH generator=11 source_id=4 parent_id=82\n"
            "P2_POM_INJECT generator=11\n")
        self.assertFalse(verdict)

    def test_markerless_log_rejected(self):
        verdict, _ = validate_log("some unrelated engine line\n")
        self.assertFalse(verdict)

    def test_malformed_lines_ignored(self):
        verdict, _ = validate_log(
            "P2_POM_ACTOR_BIRTH generator=xx source_id=4\n"
            "P2_POM_ACTOR_BIRTH generator=11 source_id=5 parent_id=82\n")
        self.assertTrue(verdict)


if __name__ == "__main__":
    unittest.main()
