import copy
import unittest
from workflow.operator import report
from workflow.integration_wakeup import receipt_gaps


class OperatorTests(unittest.TestCase):
    def state(self):
        return dict(lanes={'a':dict(lane='a',state='handoff_ready',generation=2,revision=4,native=None,handoff_at=10)},
                    throughput=dict(workstreams={'species':{}},batches={'b':dict(state='closed',workstream='species',
                        candidates={'a':{'generation':2}},isolated={})}))

    def test_closed_batch_gap_is_visible_without_mutation(self):
        state=self.state();before=copy.deepcopy(state)
        data=report(state,50)
        self.assertEqual(data['actions'][0]['batch'],'b')
        self.assertEqual(data['handoffs'][0]['age_seconds'],40)
        self.assertEqual(state,before)

    def test_completed_isolated_or_new_generation_not_reconciled(self):
        for update in ({'integration':{'root_commit':'x'}},{'generation':3},{'state':'blocked'}):
            state=self.state();state['lanes']['a'].update(update)
            self.assertEqual(receipt_gaps(state,'species'),[])
        state=self.state();state['throughput']['batches']['b']['isolated']['a']={}
        self.assertEqual(receipt_gaps(state,'species'),[])

    def test_native_export_requirement_and_capacity_next_action(self):
        state=self.state();state['lanes']['a']['native']={'head':'x'}
        state['throughput_runtime']={'autofill':{'items':{'job':dict(lane='next',phase='pending',
            dependency_kind='worker_capacity',status='blocked',reason='No compatible worker')}}}
        data=report(state,50)
        self.assertIn('export',data['actions'][0]['next_action'])
        self.assertIn('adaptation',data['actions'][1]['next_action'])
