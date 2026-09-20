"""Sole-integrator shared-review disposition; no delegated workers or ADMIT."""
import copy
import unittest

from workflow.handoff import Rejected, digest
from workflow.registry import Registry
from workflow.review_decisions import (
    apply_sole_disposition,
    delegated_review_enabled,
    require_sole_authority,
)
from tests import test_pikmin2_workflow as baseline


class SoleDispositionTests(unittest.TestCase):
    setUp = baseline.WorkflowTests.setUp
    data = baseline.WorkflowTests.data
    register = baseline.WorkflowTests.register
    running = baseline.WorkflowTests.running
    handoff = baseline.WorkflowTests.handoff
    save_handoff = baseline.WorkflowTests.save_handoff

    OWNER = 'sole-owner'

    def config(self, **overrides):
        config = dict(sole_integrator=self.OWNER)
        config.update(overrides)
        return config

    def ready(self, files=('shared-a.cpp', 'shared-b.cpp')):
        self.reg = Registry(self.db, self.root, clock=lambda: self.now,
                            process_probe=lambda _: self.health)
        lane = self.running()
        data = self.handoff(lane)
        data['shared_reviews'] = [dict(file=name, reason='shared behavior',
                                       issue_url='https://github.com/4laric/pikmin-randomizer/issues/526',
                                       status='requested', evidence=['log'])
                                  for name in files]
        data['changed_files'].extend(files)
        self.reg.submit_handoff('one', 1, lane['revision'], self.save_handoff(data))
        self.health = 'dead'
        return self.reg.status()['lanes']['one']

    def dispose(self, lane, config='default', version='sole-1', sha=None,
                file='shared-a.cpp', status='approved', reviewer=OWNER, evidence=None):
        if config == 'default':
            config = self.config()
        return self.reg.dispose_sole_review(
            config, 'one', 1, lane['revision'], version,
            lane['handoff']['sha256'] if sha is None else sha,
            file, status, reviewer, self.evidence if evidence is None else evidence)

    def test_approved_and_rejected_record_new_immutable_handoffs(self):
        lane = self.ready()
        original = lane['handoff']['sha256']
        approved = self.reg.dispose_sole_review(
            self.config(), 'one', 1, lane['revision'], 'sole-a', original,
            'shared-a.cpp', 'approved', self.OWNER, self.evidence)
        mid = self.reg.status()['lanes']['one']
        self.assertNotEqual(original, mid['handoff']['sha256'])
        rejected = self.reg.dispose_sole_review(
            self.config(), 'one', 1, mid['revision'], 'sole-b', mid['handoff']['sha256'],
            'shared-b.cpp', 'rejected', self.OWNER, self.evidence)
        updated = self.reg.status()['lanes']['one']
        self.assertNotEqual(mid['handoff']['sha256'], updated['handoff']['sha256'])
        reviews = {item['file']: item for item in
                   self.reg._delivery_read_handoff(updated)['shared_reviews']}
        self.assertEqual(reviews['shared-a.cpp']['status'], 'approved')
        self.assertEqual(reviews['shared-b.cpp']['status'], 'rejected')
        self.assertEqual(approved['request']['reviewer'], self.OWNER)
        self.assertEqual(rejected['request']['reviewer'], self.OWNER)
        self.assertFalse(updated['handoff']['result']['gameplay_accepted'])
        self.assertTrue(self.reg.check_handoff(updated)['slice_passed'])

    def test_unconfigured_owner_and_wrong_reviewer_rejected(self):
        lane = self.ready()
        with self.assertRaisesRegex(Rejected, 'Sole integrator not configured'):
            self.dispose(lane, config={})
        with self.assertRaisesRegex(Rejected, 'not the configured sole integrator'):
            self.dispose(lane, reviewer='someone-else')
        with self.assertRaises(Rejected):
            apply_sole_disposition(self.reg, self.config(), 'one', 1, lane['revision'],
                                   'sole-1', lane['handoff']['sha256'], 'shared-a.cpp',
                                   'needs-changes', self.OWNER, self.evidence)
        self.assertEqual(lane, self.reg.status()['lanes']['one'])

    def test_stale_generation_revision_handoff_and_source_pins_rejected(self):
        lane = self.ready()
        with self.assertRaises(Rejected):
            self.reg.dispose_sole_review(self.config(), 'one', 2, lane['revision'], 'v1',
                                         lane['handoff']['sha256'], 'shared-a.cpp',
                                         'approved', self.OWNER, self.evidence)
        with self.assertRaises(Rejected):
            self.reg.dispose_sole_review(self.config(), 'one', 1, lane['revision'] + 1, 'v1',
                                         lane['handoff']['sha256'], 'shared-a.cpp',
                                         'approved', self.OWNER, self.evidence)
        with self.assertRaises(Rejected):
            self.reg.dispose_sole_review(self.config(), 'one', 1, lane['revision'], 'v1',
                                         '0' * 64, 'shared-a.cpp',
                                         'approved', self.OWNER, self.evidence)
        with self.assertRaisesRegex(Rejected, 'root source changed'):
            self.reg.dispose_sole_review(self.config(), 'one', 1, lane['revision'], 'v1',
                                         lane['handoff']['sha256'], 'shared-a.cpp',
                                         'approved', self.OWNER, self.evidence,
                                         source={'root': dict(lane['root'], dirty='drifted')})
        self.assertEqual(lane, self.reg.status()['lanes']['one'])

    def test_live_producer_fenced(self):
        lane = self.ready()
        for health in ('alive', 'unknown'):
            self.health = health
            with self.assertRaises(Rejected):
                self.dispose(lane)
        self.health = 'dead'
        record = self.dispose(lane)
        self.assertEqual(record['request']['status'], 'approved')

    def test_evidence_drift_rejected(self):
        lane = self.ready()
        self.log.write_text('original log rotated')
        with self.assertRaises(Rejected):
            self.dispose(lane)
        self.assertEqual(lane, self.reg.status()['lanes']['one'])
        with self.assertRaises(Rejected):
            self.reg.dispose_sole_review(self.config(), 'one', 1, lane['revision'], 'v1',
                                         lane['handoff']['sha256'], 'shared-a.cpp',
                                         'approved', self.OWNER,
                                         {'path': str(self.log), 'sha256': '0' * 64})

    def test_idempotent_replay_and_conflicting_replay_rejected(self):
        lane = self.ready()
        first = self.dispose(lane)
        self.assertEqual(first, self.dispose(lane))
        updated = self.reg.status()['lanes']['one']
        with self.assertRaises(Rejected):
            self.reg.dispose_sole_review(self.config(), 'one', 1, lane['revision'], 'sole-1',
                                         lane['handoff']['sha256'], 'shared-a.cpp',
                                         'rejected', self.OWNER, self.evidence)
        self.assertEqual(updated, self.reg.status()['lanes']['one'])

    def test_source_pins_accept_exact_producer_identity(self):
        lane = self.ready()
        record = self.reg.dispose_sole_review(
            self.config(), 'one', 1, lane['revision'], 'sole-pinned',
            lane['handoff']['sha256'], 'shared-a.cpp', 'approved', self.OWNER,
            self.evidence, source={'root': copy.deepcopy(lane['root']),
                                   'native': lane['native']})
        self.assertEqual(record['request']['status'], 'approved')

    def test_delegated_mode_preserves_owner_review_behavior(self):
        lane = self.ready()
        config = dict(shared_review_routing={'enabled': True, 'files': {}})
        self.assertTrue(delegated_review_enabled(config))
        self.assertFalse(delegated_review_enabled(self.config()))
        self.assertEqual(require_sole_authority(config, 'any-owner'), 'delegated')
        record = self.reg.dispose_sole_review(
            config, 'one', 1, lane['revision'], 'delegated-1', lane['handoff']['sha256'],
            'shared-a.cpp', 'approved', 'any-owner', self.evidence)
        self.assertEqual(record['request']['reviewer'], 'any-owner')
        self.assertFalse(self.reg.status()['lanes']['one']['handoff']['result']['gameplay_accepted'])


if __name__ == '__main__':
    unittest.main()
