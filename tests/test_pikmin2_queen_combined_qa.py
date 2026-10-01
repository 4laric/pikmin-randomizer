"""Unit tests for the #529 combined-candidate Queen QA checker.

Synthetic log chains only. Lane24's historical gate5 log and the #496
review are consumed as-is and never re-derived here.
"""

import unittest

from experimental.pikmin2_queen_combined_qa import qa_validate


def chain(**overrides):
    """Build a synthetic full-chain log; overrides delete/replace rows."""
    rows = dict(
        ready="P2_QUEEN_TEKI_READY generator=230010 type=3 "
              "binding=creature_host health=5000.0",
        suppressed="P2_QUEEN_TEKI_HOST_AI_SUPPRESSED generator=230010 "
                   "method=param_seam",
        attached="P2_QUEEN_TEKI_ATTACHED generator=230010 attached=7",
        flick="P2_QUEEN_TEKI_FLICK generator=230010 shaken=1 "
              "blown_threshold=30 stuck_threshold=5",
        corpse="P2_QUEEN_TEKI_CORPSE generator=230010 health=0.0 "
               "carcass_pellet=0",
        pellet="P2_QUEEN_CREATURE_CORPSE_PELLET found=1",
        carry="P2_QUEEN_CREATURE_CARRY carcass_state=0 carry=3 transport=7 "
              "nearest=6.2 pokos=0",
        receipt="[Pikipelago] P2_POD_RECEIPT id=corpse:queen:230010 value=2 "
                "new=1 pokos=2 seeds=0",
        window="[PC Port] Experimental preview window set to 960x540 "
               "windowed and centered (override note).",
        baseline="P2_QUEEN_CREATURE_BASELINE red=64",
        verdict="PASS P2_QUEEN_CREATURE_RUNTIME",
    )
    rows.update(overrides)
    return "\n".join(v for v in rows.values() if v is not None)


class QueenCombinedQaTests(unittest.TestCase):
    def test_full_chain_passes(self):
        result = qa_validate(chain(), 0)
        self.assertTrue(result["passed"], result["failed"])
        self.assertEqual(result["flick_count"], 1)
        self.assertEqual(result["transport_peak"], 7)
        self.assertEqual(result["receipts"],
                         ["queen:230010 value=2 new=1"])
        self.assertEqual(len(result["caveats"]), 3)

    def test_nonzero_exit_fails_completion(self):
        result = qa_validate(chain(), 3)
        self.assertFalse(result["passed"])
        self.assertIn("completion", result["failed"])

    def test_missing_receipt_fails(self):
        result = qa_validate(chain(receipt=None), 0)
        self.assertFalse(result["passed"])
        self.assertIn("pod_receipt", result["failed"])

    def test_duplicate_grant_fails_exactly_once(self):
        extra = ("\n[Pikipelago] P2_POD_RECEIPT id=corpse:queen:230010 "
                 "value=2 new=1 pokos=2 seeds=0")
        result = qa_validate(chain() + extra, 0)
        self.assertFalse(result["passed"])
        self.assertIn("pod_receipt", result["failed"])

    def test_wrong_generator_fails(self):
        bad = chain().replace("230010", "221010")
        result = qa_validate(bad, 0)
        self.assertFalse(result["passed"])
        for gate in ("ready_hp", "natural_death", "pod_receipt"):
            self.assertIn(gate, result["failed"])

    def test_wrong_hp_fails_ready(self):
        result = qa_validate(chain(ready="P2_QUEEN_TEKI_READY "
                                         "generator=230010 type=3 "
                                         "binding=creature_host "
                                         "health=1300.0"), 0)
        self.assertFalse(result["passed"])
        self.assertIn("ready_hp", result["failed"])

    def test_nonzero_death_health_fails(self):
        result = qa_validate(chain(corpse="P2_QUEEN_TEKI_CORPSE "
                                           "generator=230010 health=12.5 "
                                           "carcass_pellet=0"), 0)
        self.assertFalse(result["passed"])
        self.assertIn("natural_death", result["failed"])

    def test_staging_marker_fails(self):
        result = qa_validate(chain() + "\nNAVI_HEAL captain=1", 0)
        self.assertFalse(result["passed"])
        self.assertIn("no_staging", result["failed"])
        self.assertIn("NAVI_HEAL", result["staging_hits"])

    def test_captain_return_fails(self):
        result = qa_validate(chain() + "\nP2_POD_CAPTAIN_RETURN pellet=1", 0)
        self.assertFalse(result["passed"])
        self.assertIn("no_staging", result["failed"])

    def test_no_latch_fails(self):
        still = ("P2_QUEEN_CREATURE_CARRY carcass_state=0 carry=0 "
                 "transport=0 nearest=44.0 pokos=0")
        result = qa_validate(chain(carry=still), 0)
        self.assertFalse(result["passed"])
        self.assertIn("carrier_latch", result["failed"])

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            qa_validate(None, 0)


if __name__ == "__main__":
    unittest.main()
