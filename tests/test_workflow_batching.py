import copy
import concurrent.futures
import json
import unittest

from tests import test_pikmin2_workflow as fixtures
from workflow.batching import BatchingMixin
from workflow.handoff import Rejected
from workflow.registry import Registry


BatchRegistry = Registry


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.reg = BatchRegistry(f.db, f.root, clock=lambda: f.now, process_probe=lambda _: f.health)
        f.reg = self.reg
        for key in ('one', 'two'):
            lane = f.running(key)
            path = f.root / ('output/' + key + '.json')
            path.write_text(json.dumps(f.handoff(lane)))
            self.reg.submit_handoff(key, 1, lane['revision'], str(path))
        f.running('three')
        with self.reg.transaction() as state:
            state['throughput'] = {'workstreams': {'cave': {'owner_lane': 'three', 'lanes': ['one', 'two']}}}
        self.pins = [dict(key=k, generation=1, revision=3) for k in ('one', 'two')]

    def claim(self, identity='batch'):
        return self.reg.batch_claim(identity, 'cave', 'three', 1, 2, self.pins)

    def test_concurrent_claims_serialize(self):
        def attempt(name):
            try:
                return self.claim(name)['id']
            except Rejected:
                return None
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(attempt, ('a', 'b')))
        self.assertEqual(sum(x is not None for x in results), 1)

    def test_auto_claim_batches_oldest_first_for_live_owner(self):
        batches = self.reg.auto_claim_batches()
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]['workstream'], 'cave')
        self.assertEqual(list(batches[0]['candidates']), ['one', 'two'])

    def test_auto_claim_rejections_are_contained_and_reported(self):
        from unittest.mock import patch
        with patch.object(self.reg, 'batch_claim', side_effect=Rejected('Batch ID already exists')):
            self.assertEqual(self.reg.auto_claim_batches(), [])
        self.assertIn('auto_batch_claim_rejected', [n['kind'] for n in self.reg.control_status()['notices'].values()])
        with patch.object(self.reg, 'check_handoff', side_effect=Rejected('Stale evidence')):
            self.assertEqual(self.reg.auto_claim_batches(), [])

    def test_isolated_unchanged_handoffs_wait_for_revision(self):
        batch = self.reg.auto_claim_batches()[0]
        self.reg.batch_isolate(batch['id'], 'three', 1, 1, 'one', 'Missing prerequisite')
        self.reg.batch_isolate(batch['id'], 'three', 1, 2, 'two', 'Failed validation')
        self.reg.batch_close(batch['id'], 'three', 1, 3)
        self.fixture.health = 'dead'
        self.assertEqual(self.reg.auto_claim_batches(), [])
        self.assertEqual(self.reg.auto_claim_batches(), [])
        notices = [n for n in self.reg.control_status()['notices'].values() if n['kind'] == 'integration_repair_needed']
        self.assertEqual(len(notices), 2)
        self.fixture.health = 'alive'
        with self.reg.transaction() as state:
            state['lanes']['one']['revision'] += 1
        new = self.reg.auto_claim_batches()
        self.assertEqual(len(new), 1)
        self.assertEqual(list(new[0]['candidates']), ['one'])

    def test_stale_owner_and_candidate_fences(self):
        self.pins[0]['generation'] = 2
        with self.assertRaises(Rejected): self.claim()
        self.pins[0]['generation'] = 1
        self.fixture.health = 'dead'
        with self.assertRaises(Rejected): self.claim()
        self.fixture.health = 'alive'
        batch = self.claim()
        with self.assertRaises(Rejected): self.reg.batch_close('batch', 'three', 1, 2)
        self.assertEqual(batch['revision'], 1)

    def test_drift_isolation_and_no_automatic_acceptance(self):
        self.claim()
        with self.reg.transaction() as state:
            state['lanes']['one']['root']['dirty'] = 'changed'
        source = copy.deepcopy(self.reg.status()['lanes']['two']['root'])
        with self.assertRaises(Rejected):
            self.reg.batch_record_build('batch', 'three', 1, 1, {'root': source, 'native': None}, {'log': self.fixture.evidence})
        self.reg.batch_isolate('batch', 'three', 1, 1, 'one', 'Source changed; re-review independently')
        result = self.reg.batch_record_build('batch', 'three', 1, 2, {'root': source, 'native': None}, {'log': self.fixture.evidence})
        self.assertEqual(result['builds'][0]['candidates'], ['two'])
        self.assertFalse(result['builds'][0]['gameplay_accepted'])
        self.assertEqual(self.reg.status()['lanes']['two']['state'], 'handoff_ready')
        with self.assertRaisesRegex(Rejected, 'per-lane integration receipts'):
            self.reg.batch_close('batch', 'three', 1, 3)
        lane=self.reg.status()['lanes']['two']
        lane=self.reg.checkpoint('two',1,lane['revision'],{'state':'integrating'})
        self.reg.integrate('two',1,lane['revision'],dict(root_commit=source['head'],
            validation_path=self.fixture.evidence['path'],validation_sha256=self.fixture.evidence['sha256']))
        self.reg.batch_close('batch', 'three', 1, 3)

    def test_source_file_overlap_rejected(self):
        # Simulate two otherwise-valid handoffs containing a shared approved path.
        from unittest.mock import patch
        with self.reg.transaction() as state:
            second = state['lanes']['two']
            path = self.fixture.root / 'output/two.json'
            data = json.loads(path.read_text())
            data['changed_files'] = ['WORKFLOW/ONE.PY']
            path.write_text(json.dumps(data))
            from workflow.handoff import digest
            second['handoff']['sha256'] = digest(path)
        with patch.object(self.reg, 'check_handoff', return_value={'pending_reviews': []}):
            with self.assertRaisesRegex(Rejected, 'overlap'): self.claim()

    def test_workstream_and_unresolved_reviews(self):
        with self.reg.transaction() as state:
            state['throughput']['workstreams']['cave']['lanes'] = ['one']
        with self.assertRaisesRegex(Rejected, 'workstream'): self.claim()

    def test_isolation_invalidates_previous_common_build(self):
        self.claim()
        source = self.reg.status()['lanes']['two']['root']
        self.reg.batch_record_build('batch', 'three', 1, 1, {'root': source, 'native': None}, {'log': self.fixture.evidence})
        result = self.reg.batch_isolate('batch', 'three', 1, 2, 'one', 'Failed validation')
        self.assertTrue(result['builds'][0]['superseded'])

    def test_atomic_cost_batch_rolls_back_conflicts(self):
        values = [dict(event_id='a', lane='one', amount=1), dict(event_id='b', lane='two', amount=2)]
        self.assertEqual(self.reg.report_cost_batch(values), 2)
        self.assertEqual(self.reg.report_cost_batch(values), 0)
        with self.assertRaises(Rejected):
            self.reg.report_cost_batch([dict(event_id='c', lane='one', amount=3), dict(event_id='a', lane='one', amount=5)])
        with self.reg.transaction() as state:
            self.assertNotIn('c', state['throughput']['costs'])

    def test_cost_idempotency_and_invalid_numbers(self):
        first = self.reg.report_cost('usage-1', 'one', 0)
        self.fixture.now += 10
        self.assertEqual(first, self.reg.report_cost('usage-1', 'one', 0))
        with self.assertRaises(Rejected): self.reg.report_cost('usage-1', 'one', 1)
        for amount in (float('nan'), float('inf'), -1, True):
            with self.assertRaises(Rejected): self.reg.report_cost('bad', 'one', amount)


if __name__ == '__main__':
    unittest.main()


