"""Unit tests for the ElecBug natural electrical emitter validator (#408/#131)."""
import unittest

from experimental.pikmin2_elecbug_denki_runtime import validate

GOOD_LOG = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_DENKI_SQUAD alive=20 reds=18 yellow=2 bulbmin=5 blue=0',
    'P2_ELECBUG_BIND generator=346002 source_id=28 visual_only=0',
    'P2_ELECBUG_DENKI generator=346002 source_id=28 emitter=sweep target=0 accepted=1 '
    'target_state=35(DenkiDying)',
    'P2_ELECBUG_SHOCK generator=346002 pikmin=1 color=blue',
    'P2_ELECBUG_IMMUNE generator=346002 source_id=28 pikmin=yellow species=2',
    'P2_ELECBUG_IMMUNE generator=346002 source_id=28 pikmin=bulbmin species=5',
    'P2_DENKI_ACCEPT target=blue yellow_state=0 bulbmin_state=0 observed=500',
    'P2_DENKI_LETHAL target=blue alive=0 yellow_alive=1 yellow_state=0 '
    'bulbmin_alive=1 bulbmin_state=0 violation=0 observed=700',
    'PASS P2_ELECBUG_DENKI_RUNTIME',
])


class ElecBugDenkiRuntimeTests(unittest.TestCase):
    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])

    def test_requires_the_native_receiver_acceptance(self):
        bad = GOOD_LOG.replace('accepted=1 target_state=35(DenkiDying)',
                               'accepted=0 target_state=0(other)')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['receiver_denki'])
        self.assertFalse(result['checks']['emitter_shock'])
        self.assertFalse(result['passed'])

    def test_rejects_shocking_an_immune_target(self):
        bad = GOOD_LOG.replace('emitter=sweep target=0 accepted=1',
                               'emitter=sweep target=2 accepted=1')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['immunity_yellow'])

    def test_requires_bulbmin_immunity_marker(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_IMMUNE generator=346002 source_id=28 pikmin=bulbmin '
                               'species=5\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['immunity_bulbmin'])

    def test_requires_lethal_path(self):
        bad = GOOD_LOG.replace('P2_DENKI_LETHAL target=blue alive=0 yellow_alive=1 '
                               'yellow_state=0 bulbmin_alive=1 bulbmin_state=0 violation=0 '
                               'observed=700\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['lethal_path'])
        self.assertFalse(result['passed'])

    def test_immune_violation_fails(self):
        bad = GOOD_LOG.replace('yellow_state=35', 'yellow_state=35')
        bad = GOOD_LOG.replace('yellow_state=0 bulbmin_state=0 observed=500',
                               'yellow_state=35 bulbmin_state=35 observed=500')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['no_immune_reaction'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
