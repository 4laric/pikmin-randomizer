import unittest
from experimental.pikmin2_qurione_runtime import evidence
class QurioneRuntimeTests(unittest.TestCase):
 def test_empty_does_not_pass(self):
  r=evidence('',0);self.assertFalse(r['completed']);self.assertFalse(r['nectar_pointer'])
 def test_rejected_attack_not_reward(self):
  r=evidence('P2_QURIONE_STIMULUS injected_attack_receiver=1 accepted=0\nP2_QURIONE_REWARD nectar=0',0)
  self.assertFalse(r['attack_accepted']);self.assertFalse(r['nectar_pointer'])
 def test_positive_receipt_evidence_separate(self):
  r=evidence('P2_QURIONE_STIMULUS injected_attack_receiver=1 accepted=1\nP2_QURIONE_REWARD nectar=1',0)
  self.assertTrue(r['attack_accepted']);self.assertTrue(r['nectar_pointer']);self.assertFalse(r['completed'])
if __name__=='__main__':unittest.main()
