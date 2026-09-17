"""Focused pin-audit tests: inventory completeness, verdict honesty, boundaries (#648)."""
import json
import unittest
from pathlib import Path

import experimental.pikmin2_umimushi_aquatic_pin_audit as audit


class InventoryTests(unittest.TestCase):
    def test_identities(self):
        ids = {row["id"]: row for row in audit.IDENTITIES}
        self.assertEqual(set(ids), {71, 100, 101})
        self.assertTrue(ids[71]["spawnable"])
        self.assertFalse(ids[100]["spawnable"])
        self.assertTrue(ids[101]["spawnable"])

    def test_every_anchor_cited_or_explicitly_absent(self):
        for row in audit.inventory():
            self.assertIn(row["area"],
                          {"identity", "birth", "attack", "receiver", "death", "cleanup"})
            if row["file"] is None:
                self.assertIsNone(row["lines"])
                self.assertIn("ABSENT", row["note"])
            else:
                self.assertTrue(row["file"] and row["lines"] and row["note"])

    def test_cleanup_absence_recorded_not_invented(self):
        missing = [r for r in audit.inventory() if r["area"] == "cleanup"]
        self.assertEqual(len(missing), 1)
        self.assertIsNone(missing[0]["file"])

    def test_death_anchor_present(self):
        death = [r for r in audit.inventory() if r["area"] == "death"]
        self.assertTrue(any("634" in r["lines"] for r in death))


class VerdictTests(unittest.TestCase):
    def test_verdict_structure(self):
        verdict = audit.verdict()
        self.assertEqual(verdict["downstream"],
                         {"lane": "shard-enemies-6-umimushi71-observer", "issue": 374})
        self.assertEqual(len(verdict["missing_inputs"]), 3)
        for item in verdict["missing_inputs"]:
            self.assertTrue(item["input"] and item["why"] and item["producer"]
                            and item["prescription"])

    def test_wake_not_satisfied(self):
        wake = audit.verdict()["wake_167"]
        self.assertFalse(wake["satisfied"])
        self.assertIn("#167", wake["reason"])
        self.assertIn("#641", wake["reason"])

    def test_no_live_scope_duplicated(self):
        producers = [i["producer"] for i in audit.verdict()["missing_inputs"]]
        self.assertTrue(any("shard-enemies-6-umimushi71-observer" in p for p in producers))
        self.assertTrue(any("NONE live" in p for p in producers))

    def test_missing_prerequisite_text(self):
        text = audit.missing_prerequisite()
        self.assertIn("#374", text)
        self.assertIn("#167", text)
        self.assertIn("NOT satisfied", text)


class BoundaryTests(unittest.TestCase):
    def test_cli_report_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "verdict.json"
            self.assertEqual(audit.main(["--out", str(target)]), 0)
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(payload["issue"], 648)
            self.assertEqual(len(payload["anchors"]), len(audit.ANCHORS))


if __name__ == "__main__":
    unittest.main()