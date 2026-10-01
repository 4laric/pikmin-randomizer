"""Unit tests for the lane-22 elemental dweevil runtime gate (#447), slice 3.

Exercises ``experimental.pikmin2_otakara_runtime.validate`` against a synthetic
native-log capture of the host seams: ordinary Pikmin ``InteractAttack`` combat,
the module's ``P2_OTAKARA_MODULE_DEAD`` observation, the ``BTeki::die()`` death
seam (``P2_OTAKARA_DEAD mDeadState=1``), the host corpse pellet, the lane-06
receipt from ``pc_p2_preview_deliver`` and the lane-07 ``pc_p2_otakara_forget``
clearance. None of these touch GL, disc assets, a player save or a real run.
"""
import unittest

from experimental import pikmin2_otakara_runtime as runtime

GOOD_LINES = [
    '[PC Port] Experimental preview window set to 960x540 windowed and centered',
    'P2_OTAKARA_BIND generator=349001 source_id=59 stimulus=InteractFire visual_only=0',
    'P2_ENEMY_READY species=FireOtakara native_family=Chappy generator=349001 x=0.0000000 '
    'y=30.0000000 z=1850.0000000 health=150.0 max_health=150.0 behavior=native '
    'source_FSM=implemented attack=elemental_discharge',
    'P2_OTAKARA_SQUAD red=19 blue=1 registered=1',
    'P2_OTAKARA_STATE generator=349001 state=flick',
    'P2_OTAKARA_DISCHARGE_IMMUNE generator=349001 source_id=59 pikmin=1 colour=red '
    'stimulus=InteractFire',
    'P2_OTAKARA_DISCHARGE_HIT generator=349001 source_id=59 pikmin=0 colour=blue '
    'stimulus=InteractFire accepted=1 target_state=22(other)',
    'P2_OTAKARA_DISCHARGE generator=349001 source_id=59 stimulus=InteractFire applied=1 immune=3',
    'P2_OTAKARA_DEPLOY free_squad=20',
    'P2_OTAKARA_HIT generator=349001 source_id=59 health=150.0->135.0 delta=15.0 '
    'interaction=InteractAttack attacker=red',
    'P2_OTAKARA_HIT generator=349001 source_id=59 health=135.0->0.0 delta=135.0 '
    'interaction=InteractAttack attacker=red',
    'P2_OTAKARA_MODULE_DEAD generator=349001 source_id=59 health=0',
    'P2_OTAKARA_DEAD generator=349001 source_id=59 mDeadState=1',
    'P2_OTAKARA_CORPSE generator=349001 pellet=1 state=3',
    'P2_POD_RECEIPT id=corpse:otakara:349001 value=15 new=1 pokos=25 seeds=0',
    'P2_OTAKARA_FORGET generator=349001 registered=1 count=0',
    'P2_OTAKARA_SEAM_OBSERVED generator=349001 registered=0 count=0',
    'PASS P2_OTAKARA_RUNTIME natural_death=1 corpse=1 receipt=1 forget=1',
]

GOOD = '\n'.join(GOOD_LINES)

DEAD_LINE = 'P2_OTAKARA_DEAD generator=349001 source_id=59 mDeadState=1'
CORPSE_LINE = 'P2_OTAKARA_CORPSE generator=349001 pellet=1 state=3'
RECEIPT_LINE = 'P2_POD_RECEIPT id=corpse:otakara:349001 value=15 new=1 pokos=25 seeds=0'
FORGET_LINE = 'P2_OTAKARA_FORGET generator=349001 registered=1 count=0'
HIT_LINE = 'P2_OTAKARA_DISCHARGE_HIT generator=349001 source_id=59 pikmin=0 colour=blue ' \
           'stimulus=InteractFire accepted=1 target_state=22(other)'

CARRY_FREE_LINE = 'P2_OTAKARA_CARRY_FREE carry=3 min=3'
ASSIST_LINE = 'P2_OTAKARA_ASSIST assigned=19'

GOOD_FIRE_CARRY = '\n'.join(GOOD_LINES + [CARRY_FREE_LINE])
GOOD_FIRE_ASSIST_AND_CARRY = '\n'.join(GOOD_LINES + [CARRY_FREE_LINE, ASSIST_LINE])

GOOD_BOMB_LINES = [
    '[PC Port] Experimental preview window set to 960x540 windowed and centered',
    'P2_OTAKARA_BIND generator=349001 source_id=93 stimulus=None visual_only=0',
    'P2_ENEMY_READY species=BombOtakara native_family=Chappy generator=349001 x=0.0000000 '
    'y=30.0000000 z=1850.0000000 health=150.0 max_health=150.0 behavior=native '
    'source_FSM=implemented attack=elemental_discharge',
    'P2_OTAKARA_SQUAD red=19 blue=1 registered=1',
    'P2_OTAKARA_STATE generator=349001 state=flick',
    'P2_OTAKARA_DISCHARGE_NONE generator=349001 source_id=93 payload_delegated=1',
    'P2_OTAKARA_DEPLOY free_squad=20',
    'P2_OTAKARA_HIT generator=349001 source_id=93 health=150.0->135.0 delta=15.0 '
    'interaction=InteractAttack attacker=red',
    'P2_OTAKARA_HIT generator=349001 source_id=93 health=135.0->0.0 delta=135.0 '
    'interaction=InteractAttack attacker=red',
    'P2_OTAKARA_MODULE_DEAD generator=349001 source_id=93 health=0',
    'P2_OTAKARA_DEAD generator=349001 source_id=93 mDeadState=1',
    'P2_OTAKARA_CORPSE generator=349001 pellet=1 state=3',
    'P2_POD_RECEIPT id=corpse:otakara:349001 value=15 new=1 pokos=25 seeds=0',
    'P2_OTAKARA_FORGET generator=349001 registered=1 count=0',
    'P2_OTAKARA_SEAM_OBSERVED generator=349001 registered=0 count=0',
    'PASS P2_OTAKARA_RUNTIME natural_death=1 corpse=1 receipt=1 forget=1',
]

GOOD_BOMB = '\n'.join(GOOD_BOMB_LINES)
BOMB_DISCHARGE_NONE_LINE = 'P2_OTAKARA_DISCHARGE_NONE generator=349001 source_id=93 ' \
                           'payload_delegated=1'

SPECIES_DISCHARGE = {
    'WaterOtakara': (60, 'InteractBubble'),
    'GasOtakara': (61, 'InteractGas'),
    'ElecOtakara': (62, 'InteractDenki'),
}


def _without(target):
    return '\n'.join(line for line in GOOD_LINES if line != target)


class OtakaraRuntimeTests(unittest.TestCase):
    def test_validate_passes_on_host_seam_log(self):
        result = runtime.validate(GOOD, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['natural_death'])
        self.assertTrue(result['checks']['corpse'])
        self.assertTrue(result['checks']['receipt'])
        self.assertTrue(result['checks']['forget'])

    def test_missing_die_seam_flips_natural_death(self):
        result = runtime.validate(_without(DEAD_LINE), code=0)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['natural_death'])

    def test_missing_corpse_fails(self):
        result = runtime.validate(_without(CORPSE_LINE), code=0)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['corpse'])

    def test_missing_receipt_fails(self):
        result = runtime.validate(_without(RECEIPT_LINE), code=0)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['receipt'])

    def test_missing_forget_marker_fails(self):
        result = runtime.validate(_without(FORGET_LINE), code=0)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['forget'])

    def test_unnamed_attack_fails_natural_hit(self):
        text = GOOD.replace(' interaction=InteractAttack attacker=red', '')
        result = runtime.validate(text, code=0)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['natural_hit'])

    def test_injected_death_marks_not_natural(self):
        text = GOOD.replace('\n' + DEAD_LINE,
                            '\nP2_OTAKARA_DEATH_INJECT before=135.0\n' + DEAD_LINE)
        result = runtime.validate(text, code=0)
        self.assertFalse(result['checks']['natural_death'])
        self.assertTrue(result['injected'])

    def test_missing_discharge_hit_flips_hit_blue(self):
        result = runtime.validate(_without(HIT_LINE), code=0)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['hit_blue'])
        self.assertTrue(result['checks']['discharge'])

    def test_nonzero_exit_code_fails(self):
        self.assertFalse(runtime.validate(GOOD, code=1)['passed'])

    def test_carry_free_yields_pass_natural_transport(self):
        result = runtime.validate(GOOD_FIRE_CARRY, 0, 'FireOtakara')
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['gates']['transport_reward'], 'pass_natural')
        self.assertTrue(result['natural_carry'])
        self.assertFalse(result['assisted'])

    def test_assist_makes_transport_pass_assisted(self):
        result = runtime.validate(GOOD_FIRE_ASSIST_AND_CARRY, 0, 'FireOtakara')
        self.assertNotEqual(result['gates']['transport_reward'], 'pass_natural')
        self.assertEqual(result['gates']['transport_reward'], 'pass_assisted')
        self.assertTrue(result['assisted'])

    def test_no_carry_free_means_not_pass_natural(self):
        result = runtime.validate(GOOD, 0, 'FireOtakara')
        self.assertNotEqual(result['gates']['transport_reward'], 'pass_natural')
        self.assertFalse(result['natural_carry'])

    def test_bomb_otakara_discharge_none_seam(self):
        result = runtime.validate(GOOD_BOMB, 0, 'BombOtakara')
        self.assertFalse(result['checks']['discharge'])
        self.assertTrue(result['checks']['discharge_none'])
        self.assertEqual(result['gates']['attacks_receivers'], 'n/a')
        self.assertTrue(result['passed'], result['checks'])

    def test_bomb_without_discharge_none_line(self):
        stripped = GOOD_BOMB.replace(BOMB_DISCHARGE_NONE_LINE + '\n', '')
        no_line = runtime.validate(stripped, 0, 'BombOtakara')
        self.assertEqual(no_line['gates']['attacks_receivers'], 'n/a')
        self.assertFalse(no_line['checks']['discharge_none'])
        self.assertFalse(no_line['passed'])

    def test_per_species_discharge_does_not_raise(self):
        for species, (source_id, stim) in SPECIES_DISCHARGE.items():
            text = '\n'.join([
                'P2_OTAKARA_BIND generator=349001 source_id=%d stimulus=%s visual_only=0'
                % (source_id, stim),
                'P2_OTAKARA_DISCHARGE generator=349001 source_id=%d stimulus=%s '
                'applied=1 immune=0' % (source_id, stim),
            ])
            result = runtime.validate(text, 0, species)
            self.assertTrue(result['checks']['discharge'], species)
            self.assertEqual(result['species'], species)


if __name__ == '__main__':
    unittest.main()
