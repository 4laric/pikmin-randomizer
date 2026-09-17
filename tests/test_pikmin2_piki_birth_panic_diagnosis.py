"""Focused fail-closed tests for the PIKI BIRTH panic diagnosis (#721)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "piki_birth_panic_diagnosis",
    ROOT / "experimental" / "pikmin2_piki_birth_panic_diagnosis.py")
diagnosis = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(diagnosis)


class AdjudicationTests(unittest.TestCase):
    def test_trial_facts_pinpoint_pool_empty(self):
        self.assertEqual(diagnosis.adjudicate(dict(diagnosis.TRIAL_FACTS)),
                         diagnosis.CAUSE_POOL_EMPTY)

    def test_cap_facts_yield_field_cap(self):
        facts = dict(diagnosis.TRIAL_FACTS)
        facts["total_pikis_estimate"] = 100
        self.assertEqual(diagnosis.adjudicate(facts), diagnosis.CAUSE_FIELD_CAP)

    def test_unwired_counts_yield_onion_counts(self):
        facts = dict(diagnosis.TRIAL_FACTS)
        facts["onion_counts_wired"] = False
        self.assertEqual(diagnosis.adjudicate(facts), diagnosis.CAUSE_ONION_COUNTS)

    def test_not_first_birth_is_undetermined(self):
        facts = dict(diagnosis.TRIAL_FACTS)
        facts["first_birth_null"] = False
        self.assertEqual(diagnosis.adjudicate(facts), diagnosis.CAUSE_UNDETERMINED)

    def test_missing_cap_pin_is_undetermined(self):
        facts = dict(diagnosis.TRIAL_FACTS)
        del facts["max_pikis"]
        self.assertEqual(diagnosis.adjudicate(facts), diagnosis.CAUSE_UNDETERMINED)

    def test_missing_total_is_undetermined(self):
        facts = dict(diagnosis.TRIAL_FACTS)
        facts["total_pikis_estimate"] = None
        self.assertEqual(diagnosis.adjudicate(facts), diagnosis.CAUSE_UNDETERMINED)

    def test_non_dict_is_undetermined(self):
        self.assertEqual(diagnosis.adjudicate([]), diagnosis.CAUSE_UNDETERMINED)
        self.assertEqual(diagnosis.adjudicate(None), diagnosis.CAUSE_UNDETERMINED)

    def test_boundary_total_equals_max_is_cap(self):
        facts = dict(diagnosis.TRIAL_FACTS)
        facts["total_pikis_estimate"] = facts["max_pikis"]
        self.assertEqual(diagnosis.adjudicate(facts), diagnosis.CAUSE_FIELD_CAP)


class RegistryTests(unittest.TestCase):
    def test_build_validates_clean(self):
        registry = diagnosis.build_registry()
        self.assertEqual(diagnosis.validate_registry(registry), [])
        self.assertEqual(registry["schema"], "p2-piki-birth-panic-diagnosis-1")
        self.assertEqual((registry["lane"], registry["issue"], registry["generation"]),
                         ("piki-birth-panic-diagnosis", 721, 2))
        self.assertFalse(registry["runtime_claim"])

    def test_native_and_exe_pins(self):
        registry = diagnosis.build_registry()
        self.assertEqual(registry["native_commit"],
                         "c549997e7bdf66fb09c0f0756c56e65fdad55861")
        self.assertEqual(registry["trial_exe_sha256"],
                         "ea20973846b43afaa199b28c48f95558fcf29d1c98a436a2bebbcab2f19bf4fc")

    def test_twelve_code_pins(self):
        pins = diagnosis.build_registry()["code_pins"]
        self.assertEqual(len(pins), 12)
        self.assertEqual(len({p["path"] for p in pins}), 12)
        for pin in pins:
            self.assertEqual(len(pin["blob"]), 40)
            int(pin["blob"], 16)

    def test_log_facts_pinned(self):
        facts = diagnosis.build_registry()["log_facts"]
        self.assertEqual(facts["runlog"]["sha256"],
                         "26f5cec70c9975abd4cbf9e6f518061806df8c47f4177c81549754fa7a0e0d80")
        self.assertEqual(facts["report"]["sha256"],
                         "8a53721829131431b599bd26ca2ea7e8d33dd3f6e7364a1cce64461ec9b1fdf4")
        self.assertEqual(facts["lines"]["panic"], 769)
        self.assertIn("2d err", facts["absent_markers"])

    def test_diagnosis_names_fix_owner(self):
        diag = diagnosis.build_registry()["diagnosis"]
        self.assertEqual(diag["cause"], diagnosis.CAUSE_POOL_EMPTY)
        self.assertIn("#186", diag["fix_owner"])
        self.assertIn("#52", diag["fix_owner"])
        self.assertEqual(len(diag["fix_files"]), 4)
        self.assertTrue(any("gameCoreSection.cpp:1009-1027" in f for f in diag["fix_files"]))
        self.assertTrue(any("newPikiGame.cpp:2021" in f for f in diag["fix_files"]))

    def test_downstream_567(self):
        downstream = diagnosis.build_registry()["downstream"]
        self.assertEqual(downstream["issue"], 567)
        self.assertEqual(downstream["lane"], "p1-challenge-trial-runtime-acceptance")

    def test_gates_untested(self):
        gates = diagnosis.build_registry()["gates"]
        self.assertEqual(set(gates),
                         {"identity_spawn", "movement_animation", "attacks_receivers",
                          "death_corpse", "transport_reward", "cleanup_reentry"})
        self.assertTrue(all(v == "UNTESTED" for v in gates.values()))

    def test_packet_names_pins_and_downstream(self):
        packet = diagnosis.build_packet(diagnosis.build_registry())
        self.assertEqual(packet["kind"], "diagnosis")
        self.assertEqual(packet["native_commit"],
                         "c549997e7bdf66fb09c0f0756c56e65fdad55861")
        self.assertEqual(packet["cause"], diagnosis.CAUSE_POOL_EMPTY)
        self.assertEqual(packet["downstream"]["issue"], 567)

    def test_sha_stable(self):
        registry = diagnosis.build_registry()
        self.assertEqual(diagnosis.registry_sha256(registry),
                         diagnosis.registry_sha256(registry))
        self.assertEqual(len(diagnosis.registry_sha256(registry)), 64)

    def test_no_aliasing(self):
        first = diagnosis.build_registry()
        first["code_pins"][0]["blob"] = "0" * 40
        second = diagnosis.build_registry()
        self.assertNotEqual(second["code_pins"][0]["blob"], "0" * 40)


class RefusalTests(unittest.TestCase):
    def test_non_dict_refused(self):
        self.assertEqual(diagnosis.validate_registry([]), ["registry-must-be-dict"])

    def test_bad_schema_refused(self):
        row = diagnosis.build_registry()
        row["schema"] = "x"
        self.assertIn("bad-schema", diagnosis.validate_registry(row))

    def test_bad_identity_refused(self):
        row = diagnosis.build_registry()
        row["issue"] = 1
        self.assertIn("bad-identity", diagnosis.validate_registry(row))

    def test_bad_native_commit_refused(self):
        row = diagnosis.build_registry()
        row["native_commit"] = "0" * 40
        self.assertIn("bad-native-commit", diagnosis.validate_registry(row))

    def test_bad_trial_exe_refused(self):
        row = diagnosis.build_registry()
        row["trial_exe_sha256"] = "0" * 64
        self.assertIn("bad-trial-exe", diagnosis.validate_registry(row))

    def test_code_pin_changed_refused(self):
        row = diagnosis.build_registry()
        row["code_pins"][0]["blob"] = "0" * 40
        problems = diagnosis.validate_registry(row)
        self.assertTrue(any(p.startswith("code-pin-changed-") for p in problems))

    def test_short_pin_list_refused(self):
        row = diagnosis.build_registry()
        row["code_pins"] = row["code_pins"][:11]
        self.assertIn("bad-code-pins", diagnosis.validate_registry(row))

    def test_log_fact_changed_refused(self):
        row = diagnosis.build_registry()
        row["log_facts"]["runlog"]["sha256"] = "0" * 64
        self.assertIn("log-fact-changed-runlog", diagnosis.validate_registry(row))

    def test_wrong_trial_facts_refused(self):
        row = diagnosis.build_registry()
        row["trial_facts"]["max_pikis"] = 0
        self.assertIn("bad-trial-facts", diagnosis.validate_registry(row))

    def test_diagnosis_mismatch_refused(self):
        row = diagnosis.build_registry()
        row["diagnosis"]["cause"] = diagnosis.CAUSE_FIELD_CAP
        self.assertIn("diagnosis-mismatch-cause", diagnosis.validate_registry(row))

    def test_fix_files_changed_refused(self):
        row = diagnosis.build_registry()
        row["diagnosis"]["fix_files"] = row["diagnosis"]["fix_files"][:3]
        self.assertIn("diagnosis-changed-fix-files", diagnosis.validate_registry(row))

    def test_wrong_downstream_refused(self):
        row = diagnosis.build_registry()
        row["downstream"]["issue"] = 1
        self.assertIn("bad-downstream", diagnosis.validate_registry(row))

    def test_runtime_claim_refused(self):
        row = diagnosis.build_registry()
        row["runtime_claim"] = True
        self.assertIn("no-runtime-claims", diagnosis.validate_registry(row))

    def test_bad_gates_refused(self):
        row = diagnosis.build_registry()
        row["gates"] = {"identity_spawn": "PASS"}
        self.assertIn("bad-gates", diagnosis.validate_registry(row))

    def test_main_check_passes(self):
        self.assertEqual(diagnosis.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
