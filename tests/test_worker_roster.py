import unittest
from workflow.worker_roster import roster
from workflow.dashboard import render_dashboard


class WorkerRosterTests(unittest.TestCase):
    def test_coordinator_standby_is_not_failure_but_other_blockers_remain_visible(self):
        lane=dict(lane='acceptance-backlog-planner',worker_id='a',state='blocked',
                  dependencies=['#581'],next_action='Awaiting helper proposals / next backlog-refill demand')
        state=dict(throughput=dict(workers={'a':{}}),lanes={'acceptance-backlog-planner':lane})
        self.assertEqual(roster(state,set(),{})['workers'][0]['status'],'Waiting for proposals')
        lane['dependencies'].append('#999')
        self.assertEqual(roster(state,set(),{})['workers'][0]['status'],'Unavailable / recovery')

    def test_counts_persistent_workers_once_and_distinguishes_pending_and_terminal(self):
        state = dict(throughput=dict(workers={k:{} for k in ['a','b','c','d']}), lanes={
            'old':dict(lane='old',worker_id='a',state='done',created_at=1),
            'planning-new':dict(lane='planning-new',worker_id='a',state='running',created_at=2),
            'queued':dict(lane='queued',worker_id='b',state='ready',created_at=3),
            'report':dict(lane='report',worker_id='c',state='review_ready',created_at=4)},
            control=dict(launches={
                'x':dict(lane='planning-new',status='running',created_at=2),
                'y':dict(lane='report',status='running',created_at=4)}))
        result=roster(state,{'d'},{'planning-new':dict(status='recent session activity',activity_age_seconds=5)})
        self.assertEqual(result['total'],4)
        self.assertEqual(sum(result['counts'].values()),4)
        self.assertEqual(result['counts'],{'Running':1,'Queued':1,'Awaiting integration / review':1,'Idle':1})
        self.assertEqual(result['workers'][0]['lane'],'planning-new')
        self.assertEqual(result['workers'][0]['role'],'Planning')

    def test_unreleased_completed_worker_is_not_idle(self):
        result=roster(dict(throughput=dict(workers={'a':{}}),lanes={
            'old':dict(lane='old',worker_id='a',state='done')}),set(),{})
        self.assertEqual(result['workers'][0]['status'],'Releasing / inspect')

    def test_roster_rendering_is_compact_and_escapes_text(self):
        html=render_dashboard(dict(worker_roster=dict(total=1,counts={'Unavailable / recovery':1},workers=[
            dict(worker='<worker>',status='Unavailable / recovery',role='Implementation / QA',
                 lane='<lane>',detail='<script>bad</script>',issue=635,activity='unavailable') ])))
        self.assertIn('Total workers: 1',html)
        self.assertIn('What each worker is doing',html)
        self.assertIn('&lt;script&gt;bad&lt;/script&gt;',html)
        self.assertNotIn('<worker>',html)
        self.assertIn('id="worker-roster"',html)
