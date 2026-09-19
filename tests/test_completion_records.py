import copy
import unittest
from tests import test_pikmin2_controller as fixtures
from workflow.runner import write


class CompletionRecordTests(unittest.TestCase):
    def check_corruption(self, name, payload, normalized=False):
        f=fixtures.ControllerTests();f.setUp();self.addCleanup(f.doCleanups)
        r,c=f.reg,f.controller
        if normalized:
            from workflow.storage import migrate
            migrate(r)
        item=f.plan();c.dispatch(item);r.bind_launch(item['id'],f.identity)
        original=r.control_status()['launches'][item['id']]
        good=copy.deepcopy(original);good['id']='valid-next';good['lane']='provider'
        with r.transaction() as s:
            s['control']['launches'][item['id']]['process']={'pid':-2}
            good['process']={'pid':-3}
            s['control']['launches'][good['id']]=good
            s['lanes']['provider']['state']='done'
        bad_dir=c.launch_directory(item['id'])
        write(bad_dir/'child.json',{'pid':-2})
        write(bad_dir/'result.json',{'kind':'exit','exit_code':0})
        (bad_dir/name).write_bytes(payload)
        good_dir=c.launch_directory(good['id']);good_dir.mkdir()
        write(good_dir/'child.json',{'pid':-3})
        write(good_dir/'result.json',{'kind':'exit','exit_code':0})
        c.complete_runs()
        launches=r.control_status()['launches']
        self.assertEqual(launches[item['id']]['status'],'running')
        self.assertEqual(launches[good['id']]['status'],'exited')
        self.assertEqual((bad_dir/name).read_bytes(),payload)
        self.assertEqual(len(launches),2)

    def test_nul_child_does_not_block_later_completion(self):
        self.check_corruption('child.json',b'\0'*84)

    def test_normalized_storage(self):
        self.check_corruption('child.json',b'\0'*84,True)

    def test_corrupt_result_and_non_object_records(self):
        for name,payload in [('result.json',b'{'),('child.json',b'null'),
                             ('result.json',b'[]'),('result.json',b'{"exit_code":0}')]:
            with self.subTest(name=name,payload=payload):self.check_corruption(name,payload)
