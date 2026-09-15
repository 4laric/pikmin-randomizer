"""Unit tests for the lane-22 natural elemental dweevil runtime gate (#447).

Exercises ``experimental.pikmin2_otakara_runtime.validate`` against a synthetic
native-log capture: the actor-bound FireOtakara (EnemyID 59) FSM spawn, the
natural InteractFire emitter -> receiver chain (fire-immune Red, fire-vulnerable
Blue), and the queue-then-apply death path. None of these touch GL, disc assets,
a player save or a real run.
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
    'P2_OTAKARA_HIT generator=349001 source_id=59 health=150.0->135.0 delta=15.0',
    'P2_OTAKARA_DISCHARGE_IMMUNE generator=349001 source_id=59 pikmin=1 colour=red '
    'stimulus=InteractFire',
    'P2_OTAKARA_DISCHARGE_HIT generator=349001 source_id=59 pikmin=0 colour=blue '
    'stimulus=InteractFire accepted=1 target_state=22(other)',
    'P2_OTAKARA_DISCHARGE generator=349001 source_id=59 stimulus=InteractFire applied=1 immune=3',
    'P2_OTAKARA_DEATH_INJECT before=135.0',
    'P2_OTAKARA_DEAD generator=349001 source_id=59 health=0',
    'PASS P2_OTAKARA_RUNTIME',
]

GOOD = '\n'.join(GOOD_LINES)

DEAD_LINE = 'P2_OTAKARA_DEAD generator=349001 source_id=59 health=0'
HIT_LINE = 'P2_OTAKARA_DISCHARGE_HIT generator=349001 source_id=59 pikmin=0 colour=blue ' \
           'stimulus=InteractFire accepted=1 target_state=22(other)'


def _without(target):
    return '\n'.join(line for line in GOOD_LINES if line != target)


class OtakaraRuntimeTests(unittest.TestCase):
    def test_validate_passes_on_source_log(self):
        result = runtime.validate(GOOD, code=0)
        self.assertTrue(result['passed'], result['checks'])

    def test_missing_dead_marker_fails(self):
        result = runtime.validate(_without(DEAD_LINE), code=0)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['dead'])

    def test_missing_discharge_hit_fails(self):
        # The DISCHARGE_HIT line is the only evidence of a fire-vulnerable Blue
        # Pikmin being accepted; removing it drops hit_blue. The apply is
        # independently proven by the P2_OTAKARA_DISCHARGE line, which remains.
        result = runtime.validate(_without(HIT_LINE), code=0)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['hit_blue'])
        self.assertTrue(result['checks']['discharge'])

    def test_nonzero_exit_code_fails(self):
        self.assertFalse(runtime.validate(GOOD, code=1)['passed'])


if __name__ == '__main__':
    unittest.main()
