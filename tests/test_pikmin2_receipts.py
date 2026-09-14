"""Reward descriptor validation and exactly-once receipt ledger contract."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_receipts import (SCHEMA_VERSION, LEDGER_VERSION, RECEIPTS_STATE_VERSION,
                                           ReceiptLedger, InMemoryPersistence, JsonReceiptPersistence,
                                           RewardRegistry, validate_descriptor, validate_descriptors,
                                           receipt_key, grant_events, reconcile)


def descriptor(identity='corpse:floor1:5000', **overrides):
    row = {'version': SCHEMA_VERSION, 'identity': identity, 'family': 'lane-13-bulborbs',
           'drop': 'corpse', 'ledger': 'onion', 'value': None, 'count': None}
    row.update(overrides)
    return row


class DescriptorValidationTests(unittest.TestCase):
    def test_valid_descriptor_normalized(self):
        result = validate_descriptor({'version': SCHEMA_VERSION, 'identity': 'corpse:5000',
                                      'family': 'lane-13-bulborbs', 'drop': 'corpse', 'ledger': 'onion'})
        self.assertEqual(result['value'], None)
        self.assertEqual(result['count'], None)
        self.assertEqual(result['drop'], 'corpse')

    def test_unknown_version_rejected(self):
        with self.assertRaises(ValueError):
            validate_descriptor(descriptor(version='p2-reward-descriptor-v2'))

    def test_duplicate_identity_rejected(self):
        with self.assertRaises(ValueError):
            validate_descriptors([descriptor(), descriptor()])

    def test_invalid_drop_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_descriptor(descriptor(drop='seed'))

    def test_negative_and_noninteger_value_rejected(self):
        for bad in (-1, True, 1.5, '2'):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                validate_descriptor(descriptor(value=bad))

    def test_unknown_ledger_tag_rejected(self):
        with self.assertRaises(ValueError):
            validate_descriptor(descriptor(ledger='bank'))

    def test_missing_and_unknown_fields_rejected(self):
        with self.assertRaises(ValueError):
            validate_descriptor({'version': SCHEMA_VERSION, 'identity': 'corpse:1'})
        with self.assertRaises(ValueError):
            validate_descriptor(descriptor(weight=1))

    def test_invalid_identity_and_family_rejected(self):
        for bad in ('', '../corpse', 'corpse 1', 5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_descriptor(descriptor(identity=bad))
        with self.assertRaises(ValueError):
            validate_descriptor(descriptor(family='Lane 13'))


class ReceiptLedgerTests(unittest.TestCase):
    def test_same_event_granted_once(self):
        ledger = ReceiptLedger(InMemoryPersistence())
        event = ('seed-a', 'corpse:5000', 7, 'tutorial_1:floor1')
        self.assertTrue(ledger.grant(*event))
        self.assertFalse(ledger.grant(*event))
        self.assertEqual(len(ledger), 1)
        self.assertTrue(ledger.has(*event))

    def test_distinct_events_granted_separately(self):
        ledger = ReceiptLedger(InMemoryPersistence())
        first = ('seed-a', 'corpse:5000', 7, 'tutorial_1:floor1')
        second = ('seed-a', 'corpse:5000', 8, 'tutorial_1:floor1')
        third = ('seed-a', 'corpse:5001', 7, 'tutorial_1:floor1')
        self.assertEqual(grant_events(ledger, [first, first, second, third]), (True, False, True, True))
        self.assertEqual(len(ledger), 3)

    def test_reload_does_not_regrant(self):
        persistence = InMemoryPersistence()
        ledger = ReceiptLedger(persistence)
        event = ('seed-a', 'treasure:dia_a_red', 'pod-1', 'tutorial_1:floor1')
        self.assertTrue(ledger.grant(*event))
        reloaded = ledger.reload()
        self.assertTrue(reloaded.has(*event))
        self.assertFalse(reloaded.grant(*event))
        self.assertEqual(len(reloaded), 1)

    def test_receipt_key_is_deterministic_and_typed(self):
        self.assertEqual(receipt_key('a', 'corpse:1', 2, 'x'), receipt_key('a', 'corpse:1', '2', 'x'))
        with self.assertRaises(ValueError):
            receipt_key('a', 'bad identity', 2, 'x')

    def test_malformed_persistence_state_rejected(self):
        for state in ({'version': 'v0', 'receipts': []},
                      {'version': LEDGER_VERSION, 'receipts': 'x'},
                      {'version': LEDGER_VERSION, 'receipts': [['a', 'b', 'c']]},
                      {'version': LEDGER_VERSION, 'receipts': [['a', 'b', 'c', 'd'], ['a', 'b', 'c', 'd']]}):
            with self.subTest(state=state), self.assertRaises(ValueError):
                ReceiptLedger(InMemoryPersistence(state))

    def test_non_persistence_backend_rejected(self):
        with self.assertRaises(ValueError):
            ReceiptLedger(object())


class ReconcileTests(unittest.TestCase):
    def test_full_coverage_ok(self):
        rows = [descriptor(identity='corpse:5000', family='lane-13-bulborbs'),
                descriptor(identity='treasure:dia_a_red', family='lane-23-flora', drop='treasure', ledger='ap',
                           value=180)]
        report = reconcile(rows, ['corpse:5000', 'treasure:dia_a_red'])
        self.assertTrue(report['ok'])
        self.assertEqual(report['missing_sources'], [])
        self.assertEqual(report['pod_leaks'], [])

    def test_missing_source_reported(self):
        rows = [descriptor(identity='corpse:5000')]
        report = reconcile(rows, ['corpse:5000', 'corpse:5001'])
        self.assertFalse(report['ok'])
        self.assertEqual(report['missing_sources'], ['corpse:5001'])

    def test_pod_only_leak_refused_by_default(self):
        rows = [descriptor(identity='treasure:dia_a_red', family='lane-23-flora', drop='treasure',
                           ledger='pod', value=180)]
        with self.assertRaises(ValueError):
            reconcile(rows, ['treasure:dia_a_red'])

    def test_pod_only_leak_reported_when_not_refused(self):
        rows = [descriptor(identity='treasure:dia_a_red', family='lane-23-flora', drop='treasure',
                           ledger='pod', value=180)]
        report = reconcile(rows, ['treasure:dia_a_red'], refuse_pod_leaks=False)
        self.assertFalse(report['ok'])
        self.assertEqual(report['pod_leaks'], ['treasure:dia_a_red'])
        self.assertEqual(report['experimental_sources'], ['treasure:dia_a_red'])

    def test_experimental_source_outside_expected_is_allowed(self):
        rows = [descriptor(identity='corpse:5000'),
                descriptor(identity='treasure:dia_a_red', family='lane-23-flora', drop='treasure',
                           ledger='pod', value=180)]
        report = reconcile(rows, ['corpse:5000'])
        self.assertTrue(report['ok'])
        self.assertEqual(report['experimental_sources'], ['treasure:dia_a_red'])

    def test_invented_ordinary_check_reported(self):
        rows = [descriptor(identity='corpse:5000'), descriptor(identity='corpse:9999', ledger='ap', value=1)]
        report = reconcile(rows, ['corpse:5000'])
        self.assertFalse(report['ok'])
        self.assertEqual(report['unexpected_sources'], ['corpse:9999'])

    def test_duplicate_expected_check_rejected(self):
        with self.assertRaises(ValueError):
            reconcile([descriptor()], ['corpse:5000', 'corpse:5000'])


class JsonPersistenceTests(unittest.TestCase):
    def test_json_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'nested' / 'receipts.json'
            first = ('seed-a', 'corpse:5000', 7, 'tutorial_1:floor1')
            second = ('seed-a', 'treasure:dia_a_red', 'pod-1', 'tutorial_1:floor1')
            ledger = ReceiptLedger(JsonReceiptPersistence(path))
            self.assertEqual(grant_events(ledger, [first, second]), (True, True))
            reopened = ReceiptLedger(JsonReceiptPersistence(path))
            self.assertEqual(reopened.receipts, ledger.receipts)
            self.assertEqual(json.loads(path.read_text())['version'], LEDGER_VERSION)

    def test_restart_does_not_regrant_and_grants_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'receipts.json'
            ledger = ReceiptLedger(JsonReceiptPersistence(path))
            prior = ('seed-a', 'corpse:5000', 7, 'tutorial_1:floor1')
            self.assertTrue(ledger.grant(*prior))
            restarted = ledger.restart()
            self.assertTrue(restarted.has(*prior))
            self.assertFalse(restarted.grant(*prior))
            self.assertTrue(restarted.grant('seed-a', 'corpse:5000', 8, 'tutorial_1:floor1'))
            self.assertEqual(len(restarted), 2)

    def test_interrupted_write_keeps_last_good_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'receipts.json'
            ledger = ReceiptLedger(JsonReceiptPersistence(path))
            prior = ('seed-a', 'corpse:5000', 7, 'tutorial_1:floor1')
            self.assertTrue(ledger.grant(*prior))
            with patch('experimental.pikmin2_receipts.os.replace', side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):
                    ledger.grant('seed-a', 'corpse:5000', 8, 'tutorial_1:floor1')
            self.assertTrue(path.with_name(path.name + '.tmp').exists())
            reopened = ReceiptLedger(JsonReceiptPersistence(path))
            self.assertEqual(len(reopened), 1)
            self.assertTrue(reopened.has(*prior))

    def test_stale_tmp_file_does_not_corrupt_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'receipts.json'
            ledger = ReceiptLedger(JsonReceiptPersistence(path))
            event = ('seed-a', 'corpse:5000', 7, 'tutorial_1:floor1')
            self.assertTrue(ledger.grant(*event))
            path.with_name(path.name + '.tmp').write_text('{ not json')
            reopened = ReceiptLedger(JsonReceiptPersistence(path))
            self.assertTrue(reopened.has(*event))
            self.assertEqual(len(reopened), 1)

    def test_corrupt_and_unknown_version_rejected(self):
        valid = {'schema': RECEIPTS_STATE_VERSION, 'version': LEDGER_VERSION, 'receipts': []}
        documents = ['not json', '[]', '{}',
                     json.dumps({'schema': RECEIPTS_STATE_VERSION, 'version': LEDGER_VERSION}),
                     json.dumps({**valid, 'schema': 'p2-receipts-v2'}),
                     json.dumps({**valid, 'version': 'p2-receipt-ledger-v2'}),
                     json.dumps({**valid, 'receipts': [['a', 'b', 'c']]})]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'receipts.json'
            for document in documents:
                with self.subTest(document=document):
                    path.write_text(document)
                    with self.assertRaises(ValueError):
                        JsonReceiptPersistence(path)


class RewardRegistryTests(unittest.TestCase):
    def test_add_get_and_descriptors(self):
        registry = RewardRegistry()
        added = registry.add(descriptor(identity='corpse:5000'))
        self.assertEqual(added['identity'], 'corpse:5000')
        self.assertEqual(registry.get('corpse:5000')['drop'], 'corpse')
        self.assertIsNone(registry.get('missing'))
        self.assertEqual([row['identity'] for row in registry.descriptors], ['corpse:5000'])

    def test_duplicate_identity_rejected(self):
        registry = RewardRegistry([descriptor(identity='corpse:5000')])
        with self.assertRaises(ValueError):
            registry.add(descriptor(identity='corpse:5000'))

    def test_reconcile_all_ok(self):
        registry = RewardRegistry([
            descriptor(identity='corpse:5000'),
            descriptor(identity='treasure:dia_a_red', family='lane-23-flora', drop='treasure', ledger='ap',
                       value=180)])
        report = registry.reconcile_all(['corpse:5000', 'treasure:dia_a_red'])
        self.assertTrue(report['ok'])
        self.assertEqual(report['missing_sources'], [])

    def test_reconcile_all_refuses_pod_leak(self):
        registry = RewardRegistry([
            descriptor(identity='treasure:dia_a_red', family='lane-23-flora', drop='treasure', ledger='pod',
                       value=180)])
        with self.assertRaises(ValueError):
            registry.reconcile_all(['treasure:dia_a_red'])

    def test_reconcile_all_reports_missing_ap_source(self):
        registry = RewardRegistry([descriptor(identity='corpse:5000')])
        report = registry.reconcile_all(['corpse:5000', 'treasure:dia_a_red'])
        self.assertFalse(report['ok'])
        self.assertEqual(report['missing_sources'], ['treasure:dia_a_red'])


if __name__ == '__main__':
    unittest.main()
