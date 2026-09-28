"""Unit tests for the Armor damage-receiver + stone-flick validator (#407/#165)."""
import unittest

from experimental.pikmin2_armor_receiver_behavior import (
    RECEIVER_MODES, validate)

GOOD_LOG = '\n'.join([
    'P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0',
    'P2_ENEMY_READY species=Armor native_family=Chappy generator=346001 x=180.0 y=30.0 '
    'z=1850.0 health=300.0 max_health=300.0 behavior=native source_FSM=implemented '
    'attack=animation_event',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_ARMOR_RECEIVER_PART generator=346001 dmg1=absent weakpoint=cent '
    'mode=port_bounding_sphere',
    'P2_ARMOR_STONE_NOTE generator=346001 host_lifecycle=absent port_analogue=pressed',
    'P2_ARMOR_RECEIVER generator=346001 decision=reject reason=reject part=body '
    'bittered=0 weakpoint=cent',
    'P2_ARMOR_RECEIVER generator=346001 decision=accept reason=weakpoint part=cent '
    'bittered=0 weakpoint=cent',
    'P2_ARMOR_RECEIVER generator=346001 decision=accept reason=bittered part=none '
    'bittered=1 weakpoint=cent',
    'P2_ARMOR_STONE generator=346001 event=enter stuck=1 flicked=1',
    'P2_ARMOR_STONE generator=346001 event=exit',
])


class ArmorReceiverTests(unittest.TestCase):
    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['receiver_part'])
        self.assertTrue(result['checks']['stone_contract'])
        self.assertIn(result['watched']['mode'], RECEIVER_MODES)
        self.assertEqual(result['watched']['mode'], 'port_bounding_sphere')
        self.assertEqual(result['watched']['accepts'], ['weakpoint', 'bittered'])
        self.assertEqual(result['watched']['rejects'], ['reject'])
        self.assertEqual(result['watched']['stone_enter'], True)
        self.assertEqual(result['watched']['stone_exit'], True)

    def test_dmg1_present_reports_source_mode(self):
        log = GOOD_LOG.replace('dmg1=absent weakpoint=cent mode=port_bounding_sphere',
                               'dmg1=present weakpoint=dmg1 mode=source_dmg1')
        result = validate(log, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['watched']['dmg1_available'])
        self.assertEqual(result['watched']['mode'], 'source_dmg1')

    def test_stone_note_alone_satisfies_contract(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines()
                        if 'P2_ARMOR_STONE generator' not in line)
        result = validate(log, code=0)
        self.assertTrue(result['checks']['stone_contract'])
        self.assertTrue(result['passed'], result['checks'])

    def test_missing_receiver_part_fails(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines()
                        if 'P2_ARMOR_RECEIVER_PART' not in line)
        result = validate(log, code=0)
        self.assertFalse(result['checks']['receiver_part'])
        self.assertFalse(result['passed'])

    def test_missing_stone_contract_fails(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines()
                        if 'P2_ARMOR_STONE' not in line)
        result = validate(log, code=0)
        self.assertFalse(result['checks']['stone_contract'])
        self.assertFalse(result['passed'])

    def test_missing_identity_fails(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines()
                        if 'P2_ARMOR_BIND' not in line)
        result = validate(log, code=0)
        self.assertFalse(result['checks']['identity'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
