import copy,json,unittest
from tests import test_workflow_autofill as fixtures
from workflow.prepared_repair import repair
from workflow.control import fingerprint
from workflow.handoff import Rejected

class PreparedRepairTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.AutofillTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.spec=copy.deepcopy(self.f.spec);self.spec['instruction']+=' Prepare a private candidate only.'
    def run_repair(self):
        return repair(self.f.reg,self.f.manifest,self.spec,fingerprint(self.f.spec),self.f.f.evidence,lambda n:self.f.remote[n])
    def test_unclaimed_repair_preserves_original_and_revalidates(self):
        self.run_repair()
        self.assertEqual(json.loads(self.f.manifest.read_text())['items'][0],self.spec)
        with self.f.reg.transaction() as s:self.assertIn(fingerprint(self.f.spec),s['prepared_spec_repairs'])
    def test_changed_manifest_and_owned_scope_rejected(self):
        self.spec['lane']['owned_files']=['unowned']
        with self.assertRaises(Rejected):self.run_repair()
    def test_registered_lane_cannot_be_rewritten(self):
        with self.f.reg.transaction() as s:s['lanes'][self.spec['lane']['lane']]=dict(s['lanes']['owner'])
        with self.assertRaisesRegex(Rejected,'Registered'):self.run_repair()
