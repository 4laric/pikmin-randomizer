import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

from workflow.recovery_evidence_refresh import (
    REPAIR_EVIDENCE_REASON,
    audit,
    diagnose,
    find_truthful,
    recovery_requests,
    verify_recorded,
)


HAS_LIVE_PLANNER = importlib.util.find_spec('workflow.prerequisite_queue') is not None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lane(name, **over):
    base = dict(lane=name, state='blocked', issue=42, root={}, native=None,
                dependencies=['#42 missing input'], handoff=None, integration=None,
                progress_at=1, started_at=1, worker_id='worker-' + name)
    base.update(over)
    return base


class RecoveryEvidenceRefreshTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'output/workflow/evidence').mkdir(parents=True)

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def request(self, report, **over):
        value = dict(id='req-1', scope='enemies-2', lanes=['owner'], report=report)
        value.update(over)
        return value

    # --- byte verification -------------------------------------------------

    def test_verified_recorded_bytes_reported_without_action(self):
        data = b'verified recovery report'
        path = self.write('output/run/report.md', data)
        result = diagnose(self.root, self.request(dict(path=str(path), sha256=sha(data))))
        self.assertEqual(result['status'], 'verified')
        self.assertIsNone(result['owner_action'])
        self.assertIsNone(result['refreshed'])
        self.assertFalse(result['applied'])
        self.assertFalse(result['dispatched'])

    def test_stale_bytes_are_refused_and_never_refreshed(self):
        data = b'recorded bytes'
        path = self.write('output/run/report.md', data)
        recorded = dict(path=str(path), sha256=sha(data))
        # A truthful archived copy exists, but changed live bytes must still be refused.
        (self.root / 'output/workflow/evidence' / recorded['sha256']).write_bytes(data)
        self.write('output/run/report.md', b'tampered bytes')
        result = diagnose(self.root, self.request(recorded))
        self.assertEqual(result['status'], 'stale_bytes')
        self.assertIsNone(result['refreshed'])
        self.assertFalse(result['applied'])
        self.assertEqual(result['actual_sha256'], sha(b'tampered bytes'))
        self.assertIn(recorded['sha256'], result['owner_action'])
        self.assertIn('owner', result['owner_action'])

    def test_missing_record_without_survivor_fails_closed(self):
        recorded = dict(path=str(self.root / 'output/run/gone.md'), sha256='a' * 64)
        result = diagnose(self.root, self.request(recorded))
        self.assertEqual(result['status'], 'unavailable')
        self.assertIsNone(result['refreshed'])
        self.assertIn('a' * 64, result['owner_action'])
        self.assertIn('owner', result['owner_action'])

    def test_malformed_record_is_refused(self):
        result = diagnose(self.root, self.request({}))
        self.assertEqual(result['status'], 'malformed')
        self.assertIsNotNone(result['owner_action'])
        self.assertIsNone(result['refreshed'])

    # --- non-applying refresh ---------------------------------------------

    def test_byte_identical_archive_is_reported_not_applied(self):
        data = b'archived recovery report'
        recorded = dict(path=str(self.root / 'output/run/removed.md'), sha256=sha(data))
        archived = self.write('output/workflow/evidence/' + recorded['sha256'], data)
        self.assertEqual(find_truthful(self.root, recorded), archived)
        result = diagnose(self.root, self.request(recorded))
        self.assertEqual(result['status'], 'refreshable')
        self.assertIsNone(result['owner_action'])
        self.assertFalse(result['applied'])
        self.assertFalse(result['dispatched'])
        refreshed = result['refreshed']
        self.assertIsNotNone(refreshed)
        self.assertEqual(refreshed['report']['sha256'], recorded['sha256'])
        self.assertEqual(refreshed['report']['path'], 'output/workflow/evidence/' + recorded['sha256'])
        self.assertEqual(refreshed['id'], 'req-1')
        self.assertEqual(refreshed['lanes'], ['owner'])
        # The refreshed report must itself re-verify against the original hash.
        self.assertEqual(verify_recorded(self.root, refreshed['report'])['status'], 'verified')

    def test_diagnose_never_mutates_the_submitted_request(self):
        data = b'archived recovery report'
        request = self.request(dict(path=str(self.root / 'output/run/removed.md'), sha256=sha(data)))
        self.write('output/workflow/evidence/' + request['report']['sha256'], data)
        before = copy.deepcopy(request)
        diagnose(self.root, request)
        self.assertEqual(request, before)

    # --- planner reproduction ---------------------------------------------

    def recovery_state(self, evidence):
        return dict(
            lanes={'owner': lane('owner', outcome=dict(outcome='blocked', evidence=evidence))},
            throughput_runtime={'autofill': {'prerequisite_requests': {}, 'prerequisite_recovery': {}}},
            throughput={})

    @unittest.skipUnless(HAS_LIVE_PLANNER, 'live planner recovery modules unavailable at this base')
    def test_recovery_requests_reports_sleeping_scope_without_mutation(self):
        evidence = dict(path=str(self.root / 'output/run/gone.md'), sha256='b' * 64)
        state = self.recovery_state(evidence)
        before = copy.deepcopy(state)
        helpers = [dict(scope='enemies-2', prerequisite_lanes=['owner'])]
        records = {'enemies-2': {'completed_at': 1}}
        result = recovery_requests(self.root, state, helpers, records, 2000,
                                   age_seconds=900, cross_partition=False)
        self.assertEqual(state, before)
        entry = result['sleeping']['enemies-2']
        self.assertEqual(entry['reason'], REPAIR_EVIDENCE_REASON)
        self.assertEqual(entry['report'], evidence)
        self.assertNotIn('enemies-2', result['recovery'])
        self.assertIn('enemies-2', result['demands'])

    @unittest.skipUnless(HAS_LIVE_PLANNER, 'live planner recovery modules unavailable at this base')
    def test_audit_reports_refreshable_match_and_leaves_state_untouched(self):
        data = b'archived recovery report'
        evidence = dict(path=str(self.root / 'output/run/gone.md'), sha256=sha(data))
        self.write('output/workflow/evidence/' + evidence['sha256'], data)
        state = self.recovery_state(evidence)
        before = copy.deepcopy(state)
        helpers = [dict(scope='enemies-2', prerequisite_lanes=['owner'])]
        records = {'enemies-2': {'completed_at': 1}}
        result = audit(self.root, state, helpers, records, 2000, age_seconds=900)
        self.assertEqual(state, before)
        self.assertEqual(len(result['diagnoses']), 1)
        diagnosis = result['diagnoses'][0]
        self.assertEqual(diagnosis['scope'], 'enemies-2')
        self.assertEqual(diagnosis['status'], 'refreshable')
        self.assertFalse(diagnosis['applied'])

    @unittest.skipUnless(HAS_LIVE_PLANNER, 'live planner recovery modules unavailable at this base')
    def test_audit_reports_stale_scope_as_refused(self):
        data = b'recorded bytes'
        path = self.write('output/run/report.md', data)
        evidence = dict(path=str(path), sha256=sha(data))
        self.write('output/run/report.md', b'tampered')
        state = self.recovery_state(evidence)
        helpers = [dict(scope='enemies-2', prerequisite_lanes=['owner'])]
        records = {'enemies-2': {'completed_at': 1}}
        result = audit(self.root, state, helpers, records, 2000, age_seconds=900)
        self.assertEqual(result['diagnoses'][0]['status'], 'stale_bytes')
        self.assertIsNone(result['diagnoses'][0]['refreshed'])


if __name__ == '__main__':
    unittest.main()
