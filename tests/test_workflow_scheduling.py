"""Scheduling admission races and ownership fencing with isolated SQLite registries."""
import concurrent.futures
import os
from pathlib import Path
import tempfile
import unittest

from workflow.handoff import Rejected, digest
from workflow.registry import Registry
from workflow.scheduling import SchedulingMixin


PoolRegistry = Registry


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.reg = PoolRegistry(self.root / 'output/registry.sqlite3', self.root,
                                process_probe=lambda p: p.get('health', 'alive'))
        self.reg.init({'max_heavy_builds': 1})
        self.add_lane('owner', health='alive')
        self.add_lane('one')
        self.reg.set_workstream('p2', 'owner')
        self.reg.register_pool_worker('one', ['review', 'repair', 'implementation'], ['python'], 'orchestrator')
        path = self.root / 'output/evidence.txt'
        path.write_text('verified disposition')
        self.evidence = {'path': str(path), 'sha256': digest(path)}

    def add_lane(self, key, worker=None, health='dead'):
        value = dict(lane=key, owner='Codex through 4laric', worker_id=worker or key,
                     task_id='opencode:session-' + key, issue=525 + len(self.reg.status()['lanes']),
                     scope='bounded scheduling checks', target_level='tooling', next_action='Verify tests',
                     milestone='throughput', owned_files=['workflow/' + key + '.py'],
                     acceptance=['Reject duplicate execution'], pid=os.getpid(),
                     root=dict(base='a'*40, head='a'*40, commits=[], dirty='', worktree='.'), native=None)
        self.reg.register(value)
        with self.reg.transaction() as state:
            state['lanes'][key]['process']['health'] = health

    def job(self, key='one', role='review', heavy=False, identity=None):
        return dict(id=identity or key, lane=key, issue=self.reg.status()['lanes'][key]['issue'],
                    workstream='p2', role=role, capabilities=['python'], instruction='Apply bounded issue disposition', heavy=heavy)

    def claim(self):
        self.reg.enqueue_job(self.job())
        return self.reg.assign_job('one', 60)

    def finish(self, assignment, review=False):
        launch = self.reg.plan_assignment(assignment['id'], ['paid/muse'], 60)
        with self.reg.transaction() as state:
            lane = state['lanes'][assignment['lane']]
            lane['generation'] += 1
            state['control']['launches'][launch['id']].update(bound_generation=lane['generation'], status='completed')
            lane.update(state='done', **({'review_disposition': {'summary': 'accepted'}} if review else
                                         {'integration': {'root_commit': 'a'*40}}))
        return self.reg.complete_assignment(assignment['id'], self.evidence)

    def test_verified_parked_owner_allows_dispatch_without_liveness_race(self):
        self.reg.finish('owner', 1, 'review-ready', 'Prior batch complete; standby', self.evidence)
        with self.reg.transaction() as state:
            state['lanes']['owner']['process']['health'] = 'dead'
        assignment = self.claim()
        self.assertIsNotNone(assignment)
        launch = self.reg.plan_assignment(assignment['id'], ['paid/muse'], 60)
        self.assertEqual(launch['lane'], 'one')

    def test_uninspectable_parked_owner_or_open_batch_blocks_admission(self):
        self.reg.finish('owner', 1, 'review-ready', 'Prior batch complete; standby', self.evidence)
        self.reg.enqueue_job(self.job())
        with self.reg.transaction() as state:
            state['lanes']['owner']['process']['health'] = 'unknown'
        self.assertIsNone(self.reg.assign_job('one', 60))
        with self.reg.transaction() as state:
            state['lanes']['owner']['process']['health'] = 'dead'
            state['throughput']['batches'] = {'open': dict(integrator='owner', state='claimed')}
        self.assertIsNone(self.reg.assign_job('one', 60))

    def test_duplicate_and_mismatched_scope_rejected(self):
        job = self.job()
        self.reg.enqueue_job(job)
        self.assertEqual(self.reg.enqueue_job(job)['id'], 'one')
        with self.assertRaises(Rejected):
            self.reg.enqueue_job(self.job(identity='duplicate'))
        with self.assertRaises(Rejected):
            self.reg.enqueue_job(dict(job, issue=1))
        with self.assertRaises(Rejected):
            self.reg.enqueue_job(dict(job, instruction='different scope'))

    def test_unknown_capability_and_session_rejected(self):
        with self.assertRaises(Rejected):
            self.reg.enqueue_job(dict(self.job(), capabilities=['native-build']))
        with self.reg.transaction() as state:
            state['lanes']['one']['task_id'] = 'codex:unknown'
        with self.assertRaises(Rejected):
            self.reg.enqueue_job(self.job())

    def test_idle_worker_can_be_reassigned_with_explicit_fence(self):
        # Idle pool workers are stopped between lanes; the oldest lane being done must not matter.
        self.finish(self.claim(), review=True)
        self.reg.provision_pool_lane(self.slice_record(), 'one')
        record = self.reg.reassign_pool_worker('one', ['review', 'implementation'],
                                               ['python', 'fixture-build'], 'operator',
                                               'Promote idle worker for prepared fixture job')
        self.assertIn('implementation', record['roles'])
        self.assertIn('fixture-build', record['capabilities'])
        event = [e for e in self.reg.snapshot()['events'] if e['kind'] == 'pool_worker_reassigned'][-1]
        self.assertEqual((event['lane'], event['previous']['roles']), ('next', ['implementation', 'repair', 'review']))
        with self.assertRaises(Rejected):
            self.reg.reassign_pool_worker('one', ['review'], ['python'], 'operator', '')

    def test_reassignment_refuses_live_unknown_or_in_flight_worker_lanes(self):
        for health in ('alive', 'unknown'):
            with self.reg.transaction() as state:
                state['lanes']['one']['process']['health'] = health
            with self.assertRaises(Rejected):
                self.reg.reassign_pool_worker('one', ['review'], ['python'], 'operator', 'promote')
        with self.reg.transaction() as state:
            state['lanes']['one']['process']['health'] = 'dead'
        assignment = self.claim()
        with self.assertRaises(Rejected):  # Open assignment.
            self.reg.reassign_pool_worker('one', ['review'], ['python'], 'operator', 'promote')
        launch = self.reg.plan_assignment(assignment['id'], ['paid/muse'], 60)
        with self.reg.transaction() as state:
            state['throughput']['assignments'][assignment['id']]['status'] = 'completed'
        with self.assertRaises(Rejected):  # Launch intent still in flight.
            self.reg.reassign_pool_worker('one', ['review'], ['python'], 'operator', 'promote')

    def test_provisioned_lane_starts_a_fresh_session_only_on_its_first_launch(self):
        self.finish(self.claim(), review=True)
        self.reg.provision_pool_lane(self.slice_record(), 'one')
        self.reg.enqueue_job(self.job('next'))
        launch = self.reg.plan_assignment(self.reg.assign_job('one', 60)['id'], ['paid/muse'], 60)
        self.assertTrue(launch['fresh_session'])
        self.assertEqual(launch['session'], 'session-one')  # Inherited until the runner names the new one.
        first = self.reg.plan_assignment(self.claim_again('first'), ['paid/muse'], 60, fresh_session=False)
        self.assertNotIn('fresh_session', first)

    def claim_again(self, name):
        with self.reg.transaction() as state:
            for a in state['throughput']['assignments'].values(): a['status'] = 'completed'
            for j in state['throughput']['jobs'].values(): j['status'] = 'completed'
            for l in state['control']['launches'].values(): l['status'] = 'exited'
        self.reg.enqueue_job(self.job('next', identity=name))
        return self.reg.assign_job('one', 60)['id']

    def test_racing_claims_and_plans_are_idempotent(self):
        self.reg.enqueue_job(self.job())
        with concurrent.futures.ThreadPoolExecutor(4) as executor:
            results = list(executor.map(lambda _: self.reg.assign_job('one', 60), range(8)))
        self.assertEqual(len({r['id'] for r in results}), 1)
        with concurrent.futures.ThreadPoolExecutor(4) as executor:
            launches = list(executor.map(lambda _: self.reg.plan_assignment(results[0]['id'], ['paid/muse'], 60), range(8)))
        self.assertEqual(len({r['id'] for r in launches}), 1)
        self.assertEqual(len(self.reg.control_status()['launches']), 1)

    def test_live_unknown_or_dead_integrator_blocks_selection(self):
        self.reg.enqueue_job(self.job())
        for lane, health in [('one', 'alive'), ('one', 'unknown'), ('owner', 'dead'), ('owner', 'unknown')]:
            with self.reg.transaction() as state:
                state['lanes']['one']['process']['health'] = 'dead'
                state['lanes']['owner']['process']['health'] = 'alive'
                state['lanes'][lane]['process']['health'] = health
            self.assertIsNone(self.reg.assign_job('one', 60))

    def test_cannot_replace_live_or_unknown_owner(self):
        self.add_lane('replacement', health='alive')
        for health in ('alive', 'unknown'):
            with self.reg.transaction() as state:
                state['lanes']['owner']['process']['health'] = health
            with self.assertRaises(Rejected):
                self.reg.set_workstream('p2', 'replacement')

    def test_ram_ceiling_and_invalid_measurements(self):
        self.reg.enqueue_job(self.job())
        self.assertIsNone(self.reg.assign_job('one', 90))
        for value in (float('nan'), float('inf'), -1, True):
            with self.assertRaises(Rejected):
                self.reg.assign_job('one', value)
        assignment = self.reg.assign_job('one', 89.9)
        with self.assertRaises(Rejected):
            self.reg.plan_assignment(assignment['id'], ['paid/muse'], 90)
        self.assertFalse(self.reg.control_status()['launches'])

    def test_dispatch_rechecks_revision_and_owner(self):
        assignment = self.claim()
        with self.reg.transaction() as state:
            state['lanes']['one']['revision'] += 1
        with self.assertRaises(Rejected):
            self.reg.plan_assignment(assignment['id'], ['paid/muse'], 60)
        self.assertFalse(self.reg.control_status()['launches'])

    def test_heavy_capacity_is_reserved_between_concurrent_workers(self):
        self.add_lane('two')
        self.reg.register_pool_worker('two', ['review'], ['python'], 'orchestrator')
        self.reg.enqueue_job(self.job(heavy=True))
        self.reg.enqueue_job(self.job('two', heavy=True))
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            results = list(executor.map(lambda w: self.reg.assign_job(w, 60), ['one', 'two']))
        self.assertEqual(sum(r is not None for r in results), 1)

    def test_worker_reused_after_applied_review_disposition(self):
        assignment = self.claim()
        complete = self.finish(assignment, review=True)
        self.assertEqual(complete['status'], 'completed')
        self.assertEqual(self.reg.complete_assignment(assignment['id'], self.evidence), complete)
        self.add_lane('next', worker='one')
        self.reg.enqueue_job(self.job('next'))
        self.assertEqual(self.reg.assign_job('one', 60)['lane'], 'next')

    def test_unapplied_outcome_or_wrong_execution_cannot_complete(self):
        assignment = self.claim()
        launch = self.reg.plan_assignment(assignment['id'], ['paid/muse'], 60)
        with self.assertRaises(Rejected):
            self.reg.complete_assignment(assignment['id'], self.evidence)
        with self.reg.transaction() as state:
            state['control']['launches'][launch['id']]['bound_generation'] = state['lanes']['one']['generation']
            state['lanes']['one']['state'] = 'review_ready'
        with self.assertRaises(Rejected):
            self.reg.complete_assignment(assignment['id'], self.evidence)

    def test_release_requeues_only_unlaunched_work(self):
        assignment = self.claim()
        self.reg.release_assignment(assignment['id'], 'replan')
        replacement = self.reg.assign_job('one', 60)
        self.assertNotEqual(assignment['id'], replacement['id'])
        self.reg.plan_assignment(replacement['id'], ['paid/muse'], 60)
        with self.assertRaises(Rejected):
            self.reg.release_assignment(replacement['id'], 'unsafe')

    def slice_record(self, key='next'):
        return dict(lane=key, issue=900, owner='Codex through 4laric', scope='Next assigned slice',
                    target_level='tooling', next_action='Apply review', milestone='throughput',
                    owned_files=['workflow/next.py'], acceptance=['Review disposition applied'],
                    root=dict(base='a'*40, head='a'*40, commits=[], dirty='', worktree='.'), native=None)

    def test_provision_reuses_stopped_session_then_dispatches_next_slice(self):
        assignment = self.claim()
        self.finish(assignment, review=True)
        previous = self.reg.status()['lanes']['one']
        lane = self.reg.provision_pool_lane(self.slice_record(), 'one')
        self.assertEqual(lane['task_id'], previous['task_id'])
        self.assertEqual(lane['process'], previous['process'])
        self.assertIsNone(lane['started_at'])
        self.reg.enqueue_job(self.job('next'))
        second = self.reg.assign_job('one', 60)
        self.finish(second)
        self.assertEqual(self.reg.scheduling_status()['jobs']['next']['status'], 'completed')

    def test_provision_rejects_live_unknown_and_overlap(self):
        self.finish(self.claim(), review=True)
        for health in ('alive', 'unknown'):
            with self.reg.transaction() as state:
                state['lanes']['one']['process']['health'] = health
            with self.assertRaises(Rejected):
                self.reg.provision_pool_lane(self.slice_record(), 'one')
        with self.reg.transaction() as state:
            state['lanes']['one']['process']['health'] = 'dead'
        with self.assertRaises(Rejected):
            self.reg.provision_pool_lane(dict(self.slice_record(), owned_files=['workflow/owner.py']), 'one')
        with self.assertRaises(Rejected):
            self.reg.provision_pool_lane(dict(self.slice_record(), pid=os.getpid()), 'one')

    def test_membership_accepts_only_registered_lanes(self):
        self.assertEqual(self.reg.set_workstream('p2', 'owner', ['one'])['lanes'], ['one'])
        with self.assertRaises(Rejected):
            self.reg.set_workstream('p2', 'owner', ['invented'])

    def prepare_second_heavy_worker(self):
        self.reg.enqueue_job(self.job(heavy=True))
        first=self.reg.assign_job('one',60)
        self.add_lane('two')
        self.reg.register_pool_worker('two',['review'],['python'],'orchestrator')
        self.reg.enqueue_job(self.job('two',heavy=True))
        return first

    def test_stopped_blocked_heavy_assignment_does_not_deadlock_producer(self):
        first=self.prepare_second_heavy_worker()
        with self.reg.transaction() as state:
            state['lanes']['one'].update(state='blocked',dependencies=['two'])
        self.assertIsNotNone(self.reg.assign_job('two',60))
        assignment=self.reg.scheduling_status()['assignments'][first['id']]
        self.assertEqual(assignment['status'],'assigned')
        self.assertEqual(self.reg.status()['lanes']['one']['worker_id'],'one')
        self.assertFalse(self.reg.status()['leases'])
        with self.reg.transaction() as state:
            state['lanes']['one']['dependencies']=[]
        with self.assertRaises(Rejected):
            self.reg.plan_assignment(first['id'],['paid/muse'],60)

    def test_live_blocked_and_unknown_protected_child_keep_heavy_reservation(self):
        self.prepare_second_heavy_worker()
        for health in ('alive','unknown'):
            with self.reg.transaction() as state:
                state['lanes']['one'].update(state='blocked',dependencies=['two'])
                state['lanes']['one']['process']['health']=health
            self.assertIsNone(self.reg.assign_job('two',60))
        with self.reg.transaction() as state:
            state['lanes']['one']['process']['health']='dead'
            state['leases']['shared-runtime']={'lane':'one','process':{'health':'unknown'}}
        self.assertIsNone(self.reg.assign_job('two',60))

    def test_two_real_build_leases_still_exhaust_two_slot_budget(self):
        self.prepare_second_heavy_worker()
        with self.reg.transaction() as state:
            state['settings']['max_heavy_builds']=2
            state['lanes']['one'].update(state='blocked',dependencies=['two'])
            state['leases']['build:a']={'lane':'one','process':{'health':'dead'}}
            state['leases']['build:b']={'lane':'one','process':{'health':'dead'}}
        self.assertIsNone(self.reg.assign_job('two',60))
        self.assertEqual(len(self.reg.status()['leases']),2)

    def test_protected_child_and_dependencies_block_dispatch(self):
        assignment = self.claim()
        with self.reg.transaction() as state:
            state['leases']['shared-runtime'] = {'lane': 'one', 'process': {'health': 'unknown'}}
        with self.assertRaises(Rejected):
            self.reg.plan_assignment(assignment['id'], ['paid/muse'], 60)
        with self.reg.transaction() as state:
            state['leases'].clear()
            state['lanes']['one']['dependencies'] = ['unpublished:version']
        with self.assertRaises(Rejected):
            self.reg.plan_assignment(assignment['id'], ['paid/muse'], 60)


if __name__ == '__main__':
    unittest.main()
