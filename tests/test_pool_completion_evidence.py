"""Completed pool assignments use immutable applied disposition evidence."""
import copy
import unittest

from tests import test_workflow_throughput_integration as fixtures
from workflow.handoff import digest
from workflow.throughput_controller import pool_tick


class PoolCompletionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ThroughputIntegrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.reg = self.fixture.reg
        self.controller = self.fixture.controller
        self.root = self.fixture.fixture.root
        self.applied_path = self.root / 'output/applied-disposition.txt'
        self.applied_path.write_text('Immutable independently applied review disposition')
        self.applied = {'path': str(self.applied_path), 'sha256': digest(self.applied_path)}
        pool_tick(self.controller)
        self.launch = next(iter(self.reg.control_status()['launches'].values()))
        self.controller.dispatch(self.launch)
        lane = self.reg.status()['lanes']['consumer']
        self.reg.finish('consumer', lane['generation'], 'review-ready', 'Review complete', self.fixture.fixture.ev)
        self.reg.accept_review('consumer', lane['generation'], 'Disposition applied', self.applied)
        with self.reg.transaction() as state:
            state['lanes']['consumer']['process'] = {'pid': -42, 'created': 'stopped-test-runner'}
            state['control']['launches'][self.launch['id']]['status'] = 'exited'

    def assignment(self):
        return next(iter(self.reg.scheduling_status()['assignments'].values()))

    def change(self, **changes):
        with self.reg.transaction() as state:
            state['lanes']['consumer'].update(changes)

    def assert_completes_with(self, expected):
        pool_tick(self.controller)
        item = self.assignment()
        self.assertEqual(item['status'], 'completed')
        self.assertEqual(item['evidence'], expected)
        self.assertEqual(self.reg.scheduling_status()['jobs']['review-one']['status'], 'completed')
        pool_tick(self.controller)  # accepted completion remains idempotent
        self.assertEqual(self.assignment(), item)

    def test_valid_disposition_beats_stale_progress_hash(self):
        stale = {'path': str(self.applied_path), 'sha256': '0' * 64}
        self.change(progress_evidence=stale)
        before = self.applied_path.read_bytes()
        self.assert_completes_with(self.applied)
        self.assertEqual(self.applied_path.read_bytes(), before)
        self.assertEqual(self.reg.status()['lanes']['consumer']['progress_evidence'], stale)

    def test_valid_disposition_beats_missing_progress_file(self):
        self.change(progress_evidence={'path': str(self.root / 'output/moved.txt'), 'sha256': 'a' * 64})
        self.assert_completes_with(self.applied)

    def test_valid_disposition_without_any_progress_or_outcome(self):
        self.change(progress_evidence=None, outcome=None)
        self.assert_completes_with(self.applied)

    def test_applied_integration_receipt_precedes_other_valid_evidence(self):
        path = self.root / 'output/integration.txt'
        path.write_text('Validated integration receipt')
        integration = {'path': str(path), 'sha256': digest(path)}
        self.change(integration={'validation_path': integration['path'], 'validation_sha256': integration['sha256']})
        self.assert_completes_with(integration)

    def test_valid_handoff_fallback_when_disposition_artifact_unavailable(self):
        self.change(review_disposition={'summary': 'Legacy receipt', 'evidence': self.applied})
        evidence = copy.deepcopy(self.fixture.fixture.ev)
        self.applied_path.unlink()
        self.change(handoff=dict(evidence, result={'outstanding_gates': []}), progress_evidence=None, outcome=None)
        self.assert_completes_with(evidence)

    def test_outcome_fallback_skips_invalid_disposition_handoff_and_progress(self):
        self.change(review_disposition={'summary': 'Legacy receipt', 'evidence': self.applied})
        evidence = copy.deepcopy(self.fixture.fixture.ev)
        self.applied_path.unlink()
        missing = {'path': str(self.root / 'output/missing.txt'), 'sha256': 'b' * 64}
        self.change(handoff=dict(missing, result=None), progress_evidence=missing, outcome={'evidence': evidence})
        self.assert_completes_with(evidence)

    def test_all_invalid_evidence_preserves_assignment_and_records_blocker(self):
        self.change(review_disposition={'summary': 'Legacy receipt', 'evidence': self.applied})
        self.applied_path.write_text('Changed after disposition')
        invalid = {'path': str(self.applied_path), 'sha256': 'b' * 64}
        self.change(progress_evidence=invalid, outcome={'evidence': invalid}, handoff=dict(invalid, result=None),
                    integration={'validation_path': invalid['path'], 'validation_sha256': invalid['sha256']})
        before = self.applied_path.read_bytes()
        pool_tick(self.controller)
        self.assertEqual(self.assignment()['status'], 'dispatched')
        self.assertEqual(self.reg.scheduling_status()['jobs']['review-one']['status'], 'assigned')
        self.assertEqual(self.applied_path.read_bytes(), before)
        notices = self.reg.control_status()['notices']
        self.assertTrue(any('No valid completion evidence' in str(value) for value in notices.values()))
        self.assertEqual(self.reg.status()['lanes']['consumer']['review_disposition']['evidence'], self.applied)

    def test_live_worker_still_prevents_completion_with_valid_disposition(self):
        self.change(process=self.fixture.fixture.identity)
        pool_tick(self.controller)
        self.assertEqual(self.assignment()['status'], 'dispatched')
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'], 'done')



    def test_deleted_inbox_uses_archive_and_acceptance_replay_is_safe(self):
        lane = self.reg.status()['lanes']['consumer']
        archive = lane['review_disposition']['archived_evidence']
        self.applied_path.unlink()
        self.reg.accept_review('consumer', lane['generation'], 'Disposition applied', self.applied)
        self.assert_completes_with(archive)

    def test_corrupt_archive_with_no_other_evidence_does_not_release(self):
        from pathlib import Path
        lane = self.reg.status()['lanes']['consumer']
        Path(lane['review_disposition']['archived_evidence']['path']).write_text('corrupt')
        self.applied_path.unlink()
        self.change(progress_evidence=None, outcome=None, handoff=None)
        pool_tick(self.controller)
        self.assertEqual(self.assignment()['status'], 'dispatched')
