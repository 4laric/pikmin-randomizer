"""Unit tests for the lane-13 Dwarf Orange Pod receipt witness (#120)."""
import unittest

import experimental.pikmin2_dwarf_orange_pod as pod


POD_RECEIPT_LOG = '\n'.join([
    'P2_DWARF_ORANGE_POD_READY treasure=dia_a_red value=180 pokos=0',
    'P2_KOCHAPPY_DEAD generator=211001 source_id=44',
    'P2_DWARF_ORANGE_POD_CORPSE tick=118',
    'P2_DWARF_ORANGE_POD_CARRY tick=120 state=0 alive=1 distance=341.2 transport=8 pokos=0 goal=1',
    '[Pikipelago] P2_POD_RECEIPT id=corpse:211001 value=2 new=1 pokos=2 seeds=0',
    'PASS P2_DWARF_ORANGE_P1_POD distance=341.2 reached=1',
])


class DwarfOrangePodTests(unittest.TestCase):
    def test_pod_evidence_pass(self):
        result = pod.evidence(POD_RECEIPT_LOG, 0)
        self.assertTrue(result['passed'])
        self.assertTrue(all(result['checks'].values()))

    def test_pod_evidence_requires_receipt(self):
        no_receipt = '\n'.join(
            line for line in POD_RECEIPT_LOG.splitlines()
            if 'P2_POD_RECEIPT' not in line)
        result = pod.evidence(no_receipt, 0)
        self.assertFalse(result['checks']['receipt'])
        self.assertFalse(result['passed'])

    def test_pod_evidence_requires_new_receipt(self):
        dup = POD_RECEIPT_LOG.replace('new=1', 'new=0')
        self.assertFalse(pod.evidence(dup, 0)['checks']['receipt'])

    def test_pod_evidence_requires_carry(self):
        no_carry = '\n'.join(
            line for line in POD_RECEIPT_LOG.splitlines()
            if 'P2_DWARF_ORANGE_POD_CARRY' not in line)
        self.assertFalse(pod.evidence(no_carry, 0)['checks']['transport'])


if __name__ == '__main__':
    unittest.main()
