"""Focused regression for the muse breadbug lifecycle observer (#504).

Every test uses a synthetic host log; no native build or asset is required.
Negative tests prove the validator refuses vacuous, injected and
manager-recreation evidence instead of passing it.
"""
import unittest

from experimental.pikmin2_muse_breadbug import parse_muse_breadbug, validate_muse_breadbug, validate

GOOD_LOG = """Experimental preview window set to 960x540 windowed and centered
P2_BREADBUG_ACTOR_READY generator=186081 native_type=8 xyz=-150.000000,30.000000,1850.000000 behavior=P1_Collec_proxy
P2_BREADBUG_ACTOR_DRAW generator=186081 visual_proxy no_P2_FSM
P2_MUSE_BREADBUG_MOVE frame=60 displacement=120.500000 moving=45
P2_MUSE_BREADBUG_RING tick=400 reds=20 health=100.000000
P2_MUSE_BREADBUG_RING tick=460 reds=19 health=82.500000
P2_MUSE_BREADBUG_RING tick=520 reds=19 health=41.000000
P2_MUSE_BREADBUG_KILL_NATURAL tick=540
P2_BREADBUG_ACTOR_FORGET generator=186081 had_handle=0 dead_state=2
P2_MUSE_BREADBUG_CORPSE bodies=1 via_mpellet=1
P2_MUSE_BREADBUG_REBIRTH_BEGIN generator=186081
P2_MUSE_BREADBUG_REBIRTH_NEW recycled=0
P2_BREADBUG_ACTOR_REBIRTH generator=186081 native_type=8 replaced_stale=0
PASS P2_MUSE_BREADBUG move kill_natural funnel corpse rebirth
"""


def events(text=GOOD_LOG):
    return parse_muse_breadbug(text)


class ParseTest(unittest.TestCase):
    def test_good_log_passes_all_gates(self):
        result = validate_muse_breadbug(events())
        self.assertTrue(result['passed'], result['reasons'])
        self.assertTrue(all(result['checks'].values()))

    def test_generator_scoping(self):
        other = GOOD_LOG.replace('generator=186081', 'generator=186082')
        parsed = parse_muse_breadbug(other)
        self.assertEqual(parsed['ready'], [])
        self.assertEqual(parsed['forget'], [])
        self.assertEqual(parsed['rebirth'], [])
        # Fixture-side markers are generator-agnostic by design.
        self.assertTrue(parsed['moves'])
        self.assertIsNotNone(parsed['kill'])

    def test_window_and_visual_observed(self):
        parsed = events()
        self.assertTrue(parsed['window'])
        self.assertTrue(parsed['draw'])
        self.assertTrue(parsed['pass_marker'])


class NaturalKillTest(unittest.TestCase):
    def test_injected_marker_fails_natural_kill_only(self):
        log = GOOD_LOG + 'P2_MUSE_BREADBUG_INJECTED health_write tick=500\n'
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['natural_kill'])
        self.assertTrue(result['checks']['death_funnel'])
        self.assertTrue(result['checks']['corpse'])
        self.assertTrue(result['checks']['rebirth'])

    def test_flat_health_fails_natural_kill(self):
        log = GOOD_LOG.replace('health=82.500000', 'health=100.000000').replace('health=41.000000', 'health=100.000000')
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['checks']['natural_kill'])

    def test_single_ring_sample_fails_natural_kill(self):
        lines = [l for l in GOOD_LOG.splitlines() if 'RING tick=460' not in l and 'RING tick=520' not in l]
        result = validate_muse_breadbug(events('\n'.join(lines) + '\n'))
        self.assertFalse(result['checks']['natural_kill'])

    def test_missing_kill_fails(self):
        lines = [l for l in GOOD_LOG.splitlines() if 'KILL_NATURAL' not in l]
        result = validate_muse_breadbug(events('\n'.join(lines) + '\n'))
        self.assertFalse(result['checks']['natural_kill'])


class FunnelCorpseTest(unittest.TestCase):
    def test_slot_reuse_forget_is_not_a_death_funnel(self):
        log = GOOD_LOG.replace('dead_state=2', 'dead_state=0')
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['checks']['death_funnel'])
        self.assertTrue(result['checks']['natural_kill'])

    def test_missing_forget_fails_funnel(self):
        lines = [l for l in GOOD_LOG.splitlines() if 'ACTOR_FORGET' not in l]
        result = validate_muse_breadbug(events('\n'.join(lines) + '\n'))
        self.assertFalse(result['checks']['death_funnel'])

    def test_no_corpse_fails_corpse_gate(self):
        log = GOOD_LOG.replace('bodies=1 via_mpellet=1', 'bodies=0 via_mpellet=0')
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['checks']['corpse'])
        self.assertTrue(result['checks']['death_funnel'])

    def test_corpse_without_mpellet_fails(self):
        log = GOOD_LOG.replace('bodies=1 via_mpellet=1', 'bodies=1 via_mpellet=0')
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['checks']['corpse'])


class RebirthTest(unittest.TestCase):
    def test_second_ready_is_manager_recreation_not_reentry(self):
        log = GOOD_LOG + ('P2_BREADBUG_ACTOR_READY generator=186081 native_type=8 '
                          'xyz=-150.000000,30.000000,1850.000000 behavior=P1_Collec_proxy\n')
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['checks']['rebirth'])

    def test_missing_rebirth_fails(self):
        lines = [l for l in GOOD_LOG.splitlines() if 'ACTOR_REBIRTH generator' not in l]
        result = validate_muse_breadbug(events('\n'.join(lines) + '\n'))
        self.assertFalse(result['checks']['rebirth'])

    def test_stale_replacement_is_not_clean_reentry(self):
        log = GOOD_LOG.replace('replaced_stale=0', 'replaced_stale=1')
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['checks']['rebirth'])

    def test_missing_rebirth_begin_fails(self):
        lines = [l for l in GOOD_LOG.splitlines() if 'REBIRTH_BEGIN' not in l]
        result = validate_muse_breadbug(events('\n'.join(lines) + '\n'))
        self.assertFalse(result['checks']['rebirth'])


class MovementAndSingularityTest(unittest.TestCase):
    def test_weak_movement_fails_sample(self):
        log = GOOD_LOG.replace('displacement=120.500000 moving=45', 'displacement=4.000000 moving=3')
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['checks']['movement_sample'])
        self.assertTrue(result['checks']['natural_kill'])

    def test_duplicate_death_markers_fail(self):
        log = GOOD_LOG + 'P2_BREADBUG_ACTOR_DEATH generator=186081 corpse=1 held=0\n' * 2
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['checks']['single_death'])

    def test_missing_pass_marker_raises(self):
        lines = [l for l in GOOD_LOG.splitlines() if not l.startswith('PASS P2_MUSE_BREADBUG')]
        with self.assertRaises(ValueError):
            validate('\n'.join(lines) + '\n')

    def test_passing_run_requires_window_and_visual(self):
        no_window = GOOD_LOG.replace('Experimental preview window set to 960x540 windowed and centered\n', '')
        with self.assertRaises(ValueError):
            validate(no_window)
        no_visual = '\n'.join(l for l in GOOD_LOG.splitlines() if 'ACTOR_DRAW' not in l) + '\n'
        with self.assertRaises(ValueError):
            validate(no_visual)


if __name__ == '__main__':
    unittest.main()
