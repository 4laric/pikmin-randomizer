"""Tests for experimental/pikmin2_lane24_gates (King free-mode / Queen natural).

Synthetic native-log fixtures exercise the pure-Python validators' gate logic
without requiring the native room process.
"""
import unittest

from experimental import pikmin2_lane24_gates as g


_KING_BASELINE = 'P2_KING_FREEMODE_BASELINE red=20'
_KING_ARMED = 'P2_KING_FREEMODE_ARMED deploy_once=1 no_injection=1'
_KING_READY = 'P2_KING_READY id=230020 enemy=53 variant=default'
_KING_COMBAT = 'P2_KING_COMBAT_DAMAGE id=230020 stuck=2 damage=5.0 health=620.0 interval=20'
_KING_DEAD = 'P2_KING_DEAD_KEY id=230020 frame=185 kill=1'
_KING_PASS_DEATH = 'PASS P2_KING_FREEMODE_DEATH'
_KING_FLOOR = 'P2_KING_FREEMODE_FLOOR tick=10800'


def king_log(*extra):
    return '\n'.join([
        _KING_BASELINE,
        _KING_ARMED,
        _KING_READY,
        _KING_COMBAT,
        *extra,
    ]) + '\n'


class KingFreeModeTests(unittest.TestCase):
    def test_kill_happy_path_passes(self):
        evidence = g.king_free_mode_validate(
            king_log(_KING_DEAD, _KING_PASS_DEATH), 0)
        self.assertTrue(evidence['passed'], evidence)
        self.assertTrue(evidence['killed'])
        self.assertTrue(evidence['checks']['consistent'])

    def test_floor_happy_path_passes(self):
        evidence = g.king_free_mode_validate(
            king_log(_KING_FLOOR), 0)
        self.assertTrue(evidence['passed'], evidence)
        self.assertFalse(evidence['killed'])
        self.assertEqual(evidence['health_floor'], 620.0)
        self.assertTrue(evidence['consistent'])

    def test_floor_without_floor_marker_fails(self):
        evidence = g.king_free_mode_validate(king_log(), 0)
        self.assertFalse(evidence['checks']['consistent'])
        self.assertFalse(evidence['passed'])

    def test_injection_marker_fails_no_injection(self):
        evidence = g.king_free_mode_validate(
            king_log(_KING_DEAD, _KING_PASS_DEATH,
                     'P2_KING_INJECT id=230020 tick=5 force=Kill fixture=1'), 0)
        self.assertFalse(evidence['checks']['no_injection'])
        self.assertFalse(evidence['passed'])

    def test_staging_marker_fails_no_staging(self):
        evidence = g.king_free_mode_validate(
            king_log(_KING_DEAD, _KING_PASS_DEATH,
                     'P2_KING_FREEMODE_NAVI_HEAL injection=1 staging=captain_refill'), 0)
        self.assertFalse(evidence['checks']['no_staging'])
        self.assertFalse(evidence['passed'])


_QUEEN_READY = 'P2_QUEEN_READY id=230010 enemy=30 variant=default'
_QUEEN_BIRTH_1 = 'P2_QUEEN_LARVA id=230010 xyz=-120.0,30.0,1800.0 born=1'
_QUEEN_BIRTH_2 = 'P2_QUEEN_LARVA id=230010 xyz=-120.0,30.0,1800.0 born=2'
_QUEEN_BITE = ('P2_QUEEN_LARVA_ATTACK id=230010 damage=2 '
               'captain_before=100.0 captain_health=98.0')
_QUEEN_DEATH = 'P2_QUEEN_STATE id=230010 from=2 to=0 health=0'
_QUEEN_RELEASE = 'P2_QUEEN_DEATH_LARVA_RELEASE id=230010 released=2'
_QUEEN_PASS = 'PASS P2_QUEEN_NATURAL_RUNTIME'


def queen_log(*extra):
    return '\n'.join([
        _QUEEN_READY,
        _QUEEN_BIRTH_1,
        _QUEEN_BIRTH_2,
        _QUEEN_BITE,
        _QUEEN_DEATH,
        _QUEEN_RELEASE,
        _QUEEN_PASS,
        *extra,
    ]) + '\n'


class QueenNaturalTests(unittest.TestCase):
    def test_happy_path_passes(self):
        evidence = g.queen_natural_validate(queen_log(), 0)
        self.assertTrue(evidence['passed'], evidence)
        self.assertTrue(evidence['checks']['birth'])

    def test_duplicate_birth_fails_birth(self):
        text = '\n'.join([
            _QUEEN_READY,
            _QUEEN_BIRTH_1,
            'P2_QUEEN_LARVA id=230010 xyz=-120.0,30.0,1800.0 born=1',
            _QUEEN_BITE,
            _QUEEN_DEATH,
            _QUEEN_RELEASE,
            _QUEEN_PASS,
        ]) + '\n'
        evidence = g.queen_natural_validate(text, 0)
        self.assertFalse(evidence['checks']['birth'])
        self.assertFalse(evidence['passed'])

    def test_bite_without_health_drop_fails_bite(self):
        text = '\n'.join([
            _QUEEN_READY,
            _QUEEN_BIRTH_1,
            _QUEEN_BIRTH_2,
            'P2_QUEEN_LARVA_ATTACK id=230010 damage=2 '
            'captain_before=100.0 captain_health=100.0',
            _QUEEN_DEATH,
            _QUEEN_RELEASE,
            _QUEEN_PASS,
        ]) + '\n'
        evidence = g.queen_natural_validate(text, 0)
        self.assertFalse(evidence['checks']['bite'])
        self.assertFalse(evidence['passed'])

    def test_missing_death_release_fails(self):
        text = '\n'.join([
            _QUEEN_READY,
            _QUEEN_BIRTH_1,
            _QUEEN_BIRTH_2,
            _QUEEN_BITE,
            _QUEEN_DEATH,
            _QUEEN_PASS,
        ]) + '\n'
        evidence = g.queen_natural_validate(text, 0)
        self.assertFalse(evidence['checks']['death_release'])
        self.assertFalse(evidence['passed'])


_QF_BASELINE = 'P2_QUEEN_FREEMODE_BASELINE red=64'
_QF_ARMED = 'P2_QUEEN_FREEMODE_ARMED deploy_once=1 no_injection=1'
_QF_READY = 'P2_QUEEN_READY id=230010 enemy=30 variant=default'
_QF_COMBAT = 'P2_QUEEN_COMBAT_DAMAGE id=230010 stuck=8 damage=8.0 health=1200.0 interval=20'
_QF_DEATH = 'P2_QUEEN_STATE id=230010 from=2 to=0 health=0'
_QF_PASS_DEATH = 'PASS P2_QUEEN_FREEMODE_DEATH'
_QF_FLOOR = 'P2_QUEEN_FREEMODE_FLOOR tick=10800'


def queen_free_log(*extra):
    return '\n'.join([
        _QF_BASELINE,
        _QF_ARMED,
        _QF_READY,
        _QF_COMBAT,
        *extra,
    ]) + '\n'


class QueenFreeModeTests(unittest.TestCase):
    def test_kill_happy_path_passes(self):
        evidence = g.queen_free_mode_validate(
            queen_free_log(_QF_DEATH, _QF_PASS_DEATH), 0)
        self.assertTrue(evidence['passed'], evidence)
        self.assertTrue(evidence['killed'])
        self.assertTrue(evidence['checks']['consistent'])

    def test_floor_happy_path_passes(self):
        evidence = g.queen_free_mode_validate(
            queen_free_log(_QF_FLOOR), 0)
        self.assertTrue(evidence['passed'], evidence)
        self.assertFalse(evidence['killed'])
        self.assertEqual(evidence['health_floor'], 1200.0)
        self.assertTrue(evidence['consistent'])

    def test_floor_without_floor_marker_fails(self):
        evidence = g.queen_free_mode_validate(queen_free_log(), 0)
        self.assertFalse(evidence['checks']['consistent'])
        self.assertFalse(evidence['passed'])

    def test_staging_marker_fails_no_staging(self):
        evidence = g.queen_free_mode_validate(
            queen_free_log(_QF_DEATH, _QF_PASS_DEATH,
                           'P2_QUEEN_NATURAL_NAVI_HEAL injection=1 staging=captain_refill'), 0)
        self.assertFalse(evidence['checks']['no_staging'])
        self.assertFalse(evidence['passed'])

    def test_injection_marker_fails_no_injection(self):
        evidence = g.queen_free_mode_validate(
            queen_free_log(_QF_DEATH, _QF_PASS_DEATH,
                           'P2_QUEEN_INJECT id=230010 tick=5 force=Kill fixture=1'), 0)
        self.assertFalse(evidence['checks']['no_injection'])
        self.assertFalse(evidence['passed'])


_KC_TEKI_READY = 'P2_KING_TEKI_READY generator=221010 type=53'
_KC_ATTACHED = 'P2_KING_TEKI_ATTACHED generator=221010 attached=7 blows=34 stuck=7 tier=0 flick=1'
_KC_FLICK = 'P2_KING_TEKI_FLICK generator=221010 shaken=34 blown_threshold=30 stuck_threshold=5'
_KC_CORPSE = 'P2_KING_TEKI_CORPSE generator=221010 health=0.0 corpse_pellet=1 cleanup_engine=1'
_KC_POD_RECEIPT = 'P2_POD_RECEIPT id=corpse:king:221010 value=15 new=1 pokos=15 seeds=0'
_KC_PASS = 'PASS P2_KING_CREATURE_RUNTIME'


def king_creature_log(*extra):
    return '\n'.join([
        _KC_TEKI_READY,
        _KC_ATTACHED,
        _KC_FLICK,
        _KC_CORPSE,
        _KC_POD_RECEIPT,
        _KC_PASS,
        *extra,
    ]) + '\n'


class KingCreatureValidatorTests(unittest.TestCase):
    def test_creature_pass(self):
        evidence = g.king_creature_validate(king_creature_log(), 0)
        self.assertTrue(evidence['passed'], evidence)
        self.assertEqual(evidence['failed'], [])

    def test_missing_receipt_fails(self):
        text = '\n'.join([
            _KC_TEKI_READY,
            _KC_ATTACHED,
            _KC_FLICK,
            _KC_CORPSE,
            _KC_PASS,
        ]) + '\n'
        evidence = g.king_creature_validate(text, 0)
        self.assertIn('pod_receipt', evidence['failed'])

    def test_staging_marker_fails(self):
        evidence = g.king_creature_validate(
            king_creature_log('NAVI_SUSTAIN tick=999'), 0)
        self.assertIn('no_staging', evidence['failed'])

    def test_missing_corpse_fails(self):
        text = '\n'.join([
            _KC_TEKI_READY,
            _KC_ATTACHED,
            _KC_FLICK,
            _KC_POD_RECEIPT,
            _KC_PASS,
        ]) + '\n'
        evidence = g.king_creature_validate(text, 0)
        self.assertIn('lethal', evidence['failed'])

    def test_injected_kill_fails(self):
        evidence = g.king_creature_validate(
            king_creature_log('P2_KING_INJECT id=221010 tick=5 force=Kill fixture=1'), 0)
        self.assertIn('no_staging', evidence['failed'])

    def test_forced_transport_fails(self):
        evidence = g.king_creature_validate(
            king_creature_log('P2_KING_TEKI_FORCED_TRANSPORT generator=221010 mode=Transport'), 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('no_staging', evidence['failed'])


_QC_TEKI_READY = 'P2_QUEEN_TEKI_READY generator=221020 type=3'
_QC_ATTACHED = 'P2_QUEEN_TEKI_ATTACHED generator=221020 attached=9 blows=34 stuck=9 tier=0 flick=1'
_QC_FLICK = 'P2_QUEEN_TEKI_FLICK generator=221020 shaken=34 blown_threshold=30 stuck_threshold=5'
_QC_CORPSE = 'P2_QUEEN_TEKI_CORPSE generator=221020 health=0.0 carcass_pellet=1 cleanup_engine=1'
_QC_POD_RECEIPT = 'P2_POD_RECEIPT id=corpse:queen:221020 value=15 new=1 pokos=15 seeds=0'
_QC_PASS = 'PASS P2_QUEEN_CREATURE_RUNTIME'


def queen_creature_log(*extra):
    return '\n'.join([
        _QC_TEKI_READY,
        _QC_ATTACHED,
        _QC_FLICK,
        _QC_CORPSE,
        _QC_POD_RECEIPT,
        _QC_PASS,
        *extra,
    ]) + '\n'


class QueenCreatureValidatorTests(unittest.TestCase):
    def test_pass(self):
        evidence = g.queen_creature_validate(queen_creature_log(), 0)
        self.assertTrue(evidence['passed'], evidence)
        self.assertEqual(evidence['failed'], [])

    def test_missing_receipt_fails(self):
        text = '\n'.join([
            _QC_TEKI_READY,
            _QC_ATTACHED,
            _QC_FLICK,
            _QC_CORPSE,
            _QC_PASS,
        ]) + '\n'
        evidence = g.queen_creature_validate(text, 0)
        self.assertIn('pod_receipt', evidence['failed'])

    def test_forced_transport_fails(self):
        evidence = g.queen_creature_validate(
            queen_creature_log('P2_QUEEN_TEKI_FORCED_TRANSPORT generator=221020 mode=Transport'), 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('no_staging', evidence['failed'])


_QT_READY = 'P2_QUEEN_READY id=230010 enemy=30 variant=default'
_QT_DEATH = 'P2_QUEEN_STATE id=230010 from=2 to=0 health=0'
_QT_CORPSE = 'P2_QUEEN_TEKI_CORPSE generator=221020 health=0.0 carcass_pellet=1 cleanup_engine=1'
_QT_POD_RECEIPT = 'P2_POD_RECEIPT id=corpse:queen:221020 value=15 new=1 pokos=15 seeds=0'
_QT_PASS = 'PASS P2_QUEEN_TRANSPORT_RUNTIME'


def queen_transport_log(*extra):
    return '\n'.join([
        _QT_READY,
        _QT_DEATH,
        _QT_CORPSE,
        _QT_POD_RECEIPT,
        _QT_PASS,
        *extra,
    ]) + '\n'


class QueenTransportValidatorTests(unittest.TestCase):
    def test_pass(self):
        evidence = g.queen_transport_validate(queen_transport_log(), 0)
        self.assertTrue(evidence['passed'], evidence)
        self.assertEqual(evidence['failed'], [])

    def test_captain_carry_fails_pod_receipt(self):
        text = '\n'.join([
            _QT_READY,
            _QT_DEATH,
            _QT_CORPSE,
            'P2_POD_CAPTAIN_RETURN id=captain:0 value=0',
            _QT_PASS,
        ]) + '\n'
        evidence = g.queen_transport_validate(text, 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('pod_receipt', evidence['failed'])

    def test_repin_staging_fails_no_staging(self):
        evidence = g.queen_transport_validate(
            queen_transport_log('REPIN tick=999 squad=red'), 0)
        self.assertFalse(evidence['passed'])
        self.assertIn('no_staging', evidence['failed'])


if __name__ == '__main__':
    unittest.main()
