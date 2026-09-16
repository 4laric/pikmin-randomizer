"""Focused regression for the muse breadbug lifecycle observer (#504).

Every test uses a synthetic host log; no native build or asset is required.
The GOOD_LOG mirrors the proven real-run shape: MOVED (not MOVE) movement
evidence, thrown-red health fall, no per-actor FORGET (LeaveCorpse deaths
bypass BTeki::doKill), corpse via mPellet, and a rebirth that replaces the
persisting dead entry (replaced_stale=1) with exactly one READY in the log.
Negative tests prove the validator refuses vacuous, injected,
manager-recreation and slot-reuse-as-funnel evidence instead of passing it.
"""
import unittest

from experimental.pikmin2_muse_breadbug import parse_muse_breadbug, validate_muse_breadbug, validate

GOOD_LOG = """Experimental preview window set to 960x540 windowed and centered
P2_BREADBUG_ACTOR_READY generator=186081 native_type=8 xyz=-150.000000,30.000000,1850.000000 behavior=P1_Collec_proxy
P2_BREADBUG_ACTOR_DRAW generator=186081 visual_proxy no_P2_FSM
P2_MUSE_BREADBUG_MOVED displacement=15.552806 moving=28
P2_MUSE_BREADBUG_THROW tick=1 reds=20 health=5000.0
P2_MUSE_BREADBUG_RING tick=60 reds=20 health=5000.0
P2_MUSE_BREADBUG_RING tick=1140 reds=20 health=4200.0
P2_MUSE_BREADBUG_RING tick=1980 reds=20 health=2600.0
P2_MUSE_BREADBUG_RING tick=2100 reds=20 health=200.0
P2_MUSE_BREADBUG_KILL_NATURAL tick=2136
P2_BREADBUG_ACTOR_DEATH generator=186081 corpse=0 held=0
P2_MUSE_BREADBUG_CORPSE bodies=1 via_mpellet=1
P2_MUSE_BREADBUG_REBIRTH_BEGIN generator=186081
P2_BREADBUG_ACTOR_REBIRTH generator=186081 native_type=8 xyz=-150.000000,30.000000,1850.000000 replaced_stale=1
P2_MUSE_BREADBUG_REBIRTH_NEW recycled=0
PASS P2_MUSE_BREADBUG move kill_natural funnel corpse rebirth
"""


def events(text=GOOD_LOG):
    return parse_muse_breadbug(text)


class ParseTest(unittest.TestCase):
    def test_good_log_passes_all_gates(self):
        result = validate_muse_breadbug(events())
        self.assertTrue(result['passed'], result['reasons'])
        self.assertTrue(all(result['checks'].values()))

    def test_reality_shape_recorded(self):
        result = validate_muse_breadbug(events())
        self.assertFalse(result['funnel_observed'])
        self.assertEqual(result['forget_count'], 0)
        self.assertEqual(result['replaced_stale'], 1)
        self.assertGreater(result['throw_count'], 0)

    def test_generator_scoping(self):
        other = GOOD_LOG.replace('generator=186081', 'generator=186082')
        parsed = parse_muse_breadbug(other)
        self.assertEqual(parsed['ready'], [])
        self.assertEqual(parsed['forget'], [])
        self.assertEqual(parsed['rebirth'], [])
        # Fixture-side markers are generator-agnostic by design.
        self.assertIsNotNone(parsed['moved'])
        self.assertIsNotNone(parsed['kill'])

    def test_window_and_visual_observed(self):
        parsed = events()
        self.assertTrue(parsed['window'])
        self.assertTrue(parsed['draw'])
        self.assertTrue(parsed['pass_marker'])

    def test_move_series_also_accepted(self):
        log = GOOD_LOG.replace(
            'P2_MUSE_BREADBUG_MOVED displacement=15.552806 moving=28\n',
            'P2_MUSE_BREADBUG_MOVE frame=60 displacement=120.500000 moving=45\n')
        result = validate_muse_breadbug(events(log))
        self.assertTrue(result['checks']['movement_sample'])


class NaturalKillTest(unittest.TestCase):
    def test_injected_marker_fails_natural_kill_only(self):
        log = GOOD_LOG + 'P2_MUSE_BREADBUG_INJECTED health_write tick=500\n'
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['natural_kill'])
        self.assertTrue(result['checks']['corpse'])
        self.assertTrue(result['checks']['rebirth'])

    def test_flat_health_fails_natural_kill(self):
        log = GOOD_LOG.replace('health=4200.0', 'health=5000.0').replace(
            'health=2600.0', 'health=5000.0').replace('health=200.0', 'health=5000.0')
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['checks']['natural_kill'])

    def test_single_ring_sample_fails_natural_kill(self):
        lines = [l for l in GOOD_LOG.splitlines() if 'RING tick=1140' not in l and 'RING tick=1980' not in l
                 and 'RING tick=2100' not in l]
        result = validate_muse_breadbug(events('\n'.join(lines) + '\n'))
        self.assertFalse(result['checks']['natural_kill'])

    def test_missing_kill_fails(self):
        lines = [l for l in GOOD_LOG.splitlines() if 'KILL_NATURAL' not in l]
        result = validate_muse_breadbug(events('\n'.join(lines) + '\n'))
        self.assertFalse(result['checks']['natural_kill'])


class FunnelReportTest(unittest.TestCase):
    def test_absent_funnel_is_reported_not_gated(self):
        result = validate_muse_breadbug(events())
        self.assertTrue(result['passed'])
        self.assertFalse(result['funnel_observed'])

    def test_pre_rebirth_forget_counts_as_funnel(self):
        log = GOOD_LOG.replace(
            'P2_MUSE_BREADBUG_CORPSE',
            'P2_BREADBUG_ACTOR_FORGET generator=186081 had_handle=0 dead_state=2\nP2_MUSE_BREADBUG_CORPSE')
        result = validate_muse_breadbug(events(log))
        self.assertTrue(result['funnel_observed'])
        self.assertTrue(result['passed'])

    def test_slot_reuse_forget_after_begin_is_not_funnel(self):
        log = GOOD_LOG + 'P2_BREADBUG_ACTOR_FORGET generator=186081 had_handle=0 dead_state=0\n'
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['funnel_observed'])
        self.assertTrue(result['passed'])

    def test_recycled_address_forget_after_begin_is_not_funnel(self):
        # A pooled slot reuse can surface a stale dead_state; position (after
        # REBIRTH_BEGIN) proves slot reuse, so it must not count as the death
        # funnel even with dead_state>=1.
        log = GOOD_LOG + 'P2_BREADBUG_ACTOR_FORGET generator=186081 had_handle=0 dead_state=2\n'
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['funnel_observed'])
        self.assertTrue(result['passed'])


class CorpseTest(unittest.TestCase):
    def test_no_corpse_fails_corpse_gate(self):
        log = GOOD_LOG.replace('bodies=1 via_mpellet=1', 'bodies=0 via_mpellet=0')
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['checks']['corpse'])

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

    def test_stale_replacement_passes_and_is_recorded(self):
        # The dead LeaveCorpse entry persists (no doKill), so the rebirth scan
        # replaces it: replaced_stale=1 is the honest cleanup signal here.
        result = validate_muse_breadbug(events())
        self.assertTrue(result['checks']['rebirth'])
        self.assertEqual(result['replaced_stale'], 1)

    def test_missing_rebirth_begin_fails(self):
        lines = [l for l in GOOD_LOG.splitlines() if 'REBIRTH_BEGIN' not in l]
        result = validate_muse_breadbug(events('\n'.join(lines) + '\n'))
        self.assertFalse(result['checks']['rebirth'])

    def test_missing_rebirth_new_fails(self):
        lines = [l for l in GOOD_LOG.splitlines() if 'REBIRTH_NEW' not in l]
        result = validate_muse_breadbug(events('\n'.join(lines) + '\n'))
        self.assertFalse(result['checks']['rebirth'])


class MovementAndSingularityTest(unittest.TestCase):
    def test_weak_movement_fails_sample(self):
        log = GOOD_LOG.replace('displacement=15.552806 moving=28', 'displacement=4.000000 moving=3')
        result = validate_muse_breadbug(events(log))
        self.assertFalse(result['checks']['movement_sample'])
        self.assertTrue(result['checks']['natural_kill'])

    def test_missing_movement_fails_sample(self):
        lines = [l for l in GOOD_LOG.splitlines() if 'MOVED' not in l and 'MOVE frame' not in l]
        result = validate_muse_breadbug(events('\n'.join(lines) + '\n'))
        self.assertFalse(result['checks']['movement_sample'])

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
