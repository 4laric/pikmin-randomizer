import unittest
from scripts.test_pikmin2_atlas_slope import validate


class AtlasEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.roster = dict(actors=[dict(category='treasure', instance_id='atlas', value=200, position=[0, 10, 640])])
        self.log = ('P2_CARGO_START_XYZ 0.000 10.000 640.000\n'
                    'P2_POD_RECEIPT id=treasure:atlas value=200 new=1 pokos=200 seeds=0\n'
                    'PASS P2 second cargo actual native transport and Pod delivery\n')
        self.receipt = 'P2_ECONOMY_1\ntreasure:atlas 200\n'

    def test_complete_evidence(self):
        self.assertEqual(validate(self.log, self.roster, self.receipt)['value'], 200)

    def test_rejects_moved_start_missing_receipt_and_false_success(self):
        for text in (self.log.replace('0.000 10.000', '-470.000 25.000'),
                     self.log.replace('new=1', 'new=0'),
                     self.log.replace('value=200', 'value=100'),
                     self.log+'FAIL cargo dropped\n',
                     self.log.replace('PASS P2', 'INCOMPLETE P2')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate(text, self.roster, self.receipt)

    def test_rejects_duplicate_award_and_wrong_persisted_identity(self):
        event = 'P2_POD_RECEIPT id=treasure:atlas value=200 new=1 pokos=200 seeds=0\n'
        with self.assertRaises(ValueError):
            validate(self.log+event, self.roster, self.receipt)
        with self.assertRaises(ValueError):
            validate(self.log, self.roster, self.receipt.replace('atlas', 'other'))


if __name__ == '__main__':
    unittest.main()
