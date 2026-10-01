"""Generated acceptance case preserves sampled identity and source authority."""
import copy
import unittest
from scripts.run_p2_generated_delivery import case, SOURCE, ABSENT, TARGET
from randomizer.seed import validate


class GeneratedDeliveryCaseTests(unittest.TestCase):
    def test_subset_keeps_exact_original_slot_and_source(self):
        manifest, audit = case()
        self.assertEqual(audit['slot']['uid'], TARGET)
        self.assertEqual(audit['campaign_slot']['source'], '3/0-14.gen@231')
        self.assertEqual(audit['slot']['stage'], audit['campaign_slot']['stage'])
        checks = manifest['enemy_catalog']['checks']
        self.assertEqual([r['species'] for r in checks if r['game'] == 'p2'], [SOURCE])
        self.assertEqual(manifest['p2_layout']['unplaced'], [ABSENT])
        self.assertTrue(any(r['game'] == 'p1' and r['species'] == 3 for r in checks))

    def test_forged_source_check_is_rejected(self):
        manifest, _ = case()
        bad = copy.deepcopy(manifest)
        row = next(r for r in bad['enemy_catalog']['checks'] if r['game'] == 'p2')
        row['species'] = ABSENT
        with self.assertRaises(ValueError):
            validate(bad)


if __name__ == '__main__':
    unittest.main()
