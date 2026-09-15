import unittest

from experimental.pikmin2_projectile_engine_receiver import (
    BOMB_ENGINE_HIT_RE, BOMB_NOHIT_RE, ENGINE_STRIKE_RE, MAGIC, bomb_config,
    build_config, evaluate, groink_config, parse_engine_strikes, stone_config,
    kabuto_config, rig_bank_text, strike_ratio_of)


# This test file exercises ONLY the Python log-evaluator/config functions
# (build_config, parse_engine_strikes, evaluate, stone_config, kabuto_config),
# not the native engine behavior. The native receiver mutation is validated by
# the real-GL runtime evidence, not by pytest.


SAMPLE_LOG = """\
Experimental preview window set to 960x540 windowed and centered
[Pikipelago] P2_ROOM_READY treasure=bolt carry=5
P2_PROJECTILES_READY stone=1 egg=0 kabuto=1 rock=0 seed=1
P2_PROJECTILE_KABUTO_READY species=Kabuto mouth=(175.0,0.0,-180.0) face_deg=90.0
P2_PROJECTILE_KABUTO_ACTION phase=Attack action=FireStone tick=8
P2_PROJECTILE_KABUTO_FIRE species=Kabuto homing=0 rig=0 mouth=(175.0,0.0,-180.0)
P2_PROJECTILE_STRIKE kind=Attack damage=250.0 target=1234 attributed=5678 source=0 health_zeroed=1
P2_PROJECTILE_ENGINE_STRIKE target=1234 kind=Attack damage=250.0 applied=1 rejected=0 health=180.0->180.0 stored=0.0->250.0 source=0
P2_PROJECTILE_STONE_CONTACT target=1234 kind=1 health_zeroed=1
P2_PROJECTILE_STONE_DESTROY reason=health traces=4 floors=0 walls=0
"""


# Two-Teki scenario: the bound firer (token 1111) is skipped on the birth tick,
# but a *distinct* victim Teki (token 2222) is struck through the engine receiver.
TWO_TEKI_LOG = """\
Experimental preview window set to 960x540 windowed and centered
P2_PROJECTILES_READY stone=1 egg=0 kabuto=1 rock=0 seed=1
P2_PROJECTILE_KABUTO_FIRE species=Kabuto homing=0 rig=1 mouth=(173.6,0.0,-143.2)
P2_PROJECTILE_SKIP_SELF target=1111
P2_PROJECTILE_ENGINE_STRIKE target=2222 kind=Attack damage=250.0 applied=1 rejected=0 health=180.0->180.0 stored=0.0->250.0 source=0
P2_PROJECTILE_STONE_CONTACT target=2222 kind=1 health_zeroed=1
P2_PROJECTILE_STONE_DESTROY reason=health traces=4 floors=0 walls=0
"""


GROINK_LOG = """\
Experimental preview window set to 960x540 windowed and centered
P2_PROJECTILES_READY stone=1 egg=0 kabuto=1 rock=0 seed=1
P2_PROJECTILE_GROINK_ENGINE_HIT token=3333 kind=Bomb damage=10.0 applied=1 rejected=0 health=30.0->20.0
"""


def _fire_destroy_log(fires, health_hits, aim_none=False, press_hits=0):
    lines = []
    for _ in range(fires):
        lines.append('P2_PROJECTILE_KABUTO_FIRE species=Kabuto homing=1 rig=1 '
                     'mouth=(0.0,0.0,0.0)')
    for _ in range(health_hits):
        lines.append('P2_PROJECTILE_ENGINE_STRIKE target=1234 kind=Attack damage=250.0 '
                     'applied=1 rejected=0 health=180.0->180.0 stored=0.0->250.0 source=0')
    for _ in range(press_hits):
        lines.append('P2_PROJECTILE_ENGINE_STRIKE target=1234 kind=Press damage=10.0 '
                     'applied=1 rejected=0 health=300.0->290.0 stored=0.0->0.0 source=0')
    if aim_none:
        lines.append('P2_PROJECTILE_AIM_NONE fire=99')
    lines.append('P2_PROJECTILE_SKIP_SELF target=9999')
    return '\n'.join(lines) + '\n'


BOMB_HIT_LOG = ('P2_PROJECTILE_BOMB_ENGINE_HIT token=1 kind=Bomb damage=10.0 '
                'applied=1 rejected=0 health=100.0->90.0 dist=15.0\n')
BOMB_NOHIT_LOG = 'P2_PROJECTILE_BOMB_NOHIT dist=999.0\n'


class ProjectileEngineReceiverTests(unittest.TestCase):
    def test_build_config_stone(self):
        text = build_config('stone')
        self.assertTrue(text.startswith(MAGIC))
        self.assertIn('seed 1', text)
        self.assertIn('stone ', text)
        self.assertIn('engine_receiver 1', text)
        self.assertIn('receiver any 20', text)
        self.assertNotIn('kabuto ', text)

    def test_build_config_kabuto(self):
        text = build_config('kabuto')
        self.assertIn('kabuto Kabuto ', text)

    def test_build_config_kabuto_actor(self):
        text = build_config('kabuto_actor', generator=23)
        self.assertIn('kabuto Kabuto ', text)
        self.assertIn('kabuto_rig rig-bank.txt ', text)
        self.assertIn('kabuto_actor 23', text)
        self.assertIn('engine_receiver 1', text)

    def test_build_config_two_teki(self):
        # Primary two-Teki run is NOT injected (no teki_pin); the victim sits at
        # its natural settle in the fire corridor.
        text = build_config('two_teki', generator=23)
        self.assertIn('kabuto Kabuto ', text)
        self.assertIn('kabuto_rig rig-bank.txt ', text)
        self.assertIn('kabuto_actor 23', text)
        self.assertNotIn('teki_pin 1', text)
        self.assertIn(groink_config(), text)
        self.assertIn('engine_receiver 1', text)

    def test_build_config_two_teki_with_pin(self):
        # Opt-in injected scenario: teki_pin is a separately-flagged row.
        text = build_config('two_teki', generator=23, teki_pin=True)
        self.assertIn('teki_pin 1', text)

    def test_build_config_two_teki_has_bomb_row(self):
        text = build_config('two_teki', generator=23)
        self.assertIn('groink ', text)
        self.assertIn('bomb ', text)

    def test_bomb_config_row(self):
        row = bomb_config()
        self.assertTrue(row.startswith('bomb '))
        self.assertEqual(row.count(' '), 4)

    def test_strike_ratio_of_pass(self):
        log = _fire_destroy_log(fires=9, health_hits=7)
        fires, hits, alive_fires = strike_ratio_of(log)
        self.assertEqual((fires, hits, alive_fires), (9, 7, 9))
        result = evaluate(log)
        self.assertEqual(result['strike_ratio'], '7/9')
        self.assertEqual(result['strike_ratio_while_alive'], '7/9')
        self.assertEqual(result['gates']['victim_strike_ratio'], 'PASS')

    def test_strike_ratio_of_fail(self):
        log = _fire_destroy_log(fires=9, health_hits=3)
        fires, hits, alive_fires = strike_ratio_of(log)
        self.assertEqual((fires, hits, alive_fires), (9, 3, 9))
        result = evaluate(log)
        self.assertEqual(result['gates']['victim_strike_ratio'], 'FAIL')

    def test_strike_ratio_untested_when_no_fires(self):
        log = _fire_destroy_log(fires=0, health_hits=0)
        self.assertEqual(strike_ratio_of(log), (0, 0, 0))
        result = evaluate(log)
        self.assertEqual(result['gates']['victim_strike_ratio'], 'UNTESTED')

    def test_strike_ratio_press_is_not_counted_as_hit(self):
        # A Press strike shares the ENGINE_STRIKE format but must NOT count as a
        # health-destroying Attack hit.
        log = _fire_destroy_log(fires=1, health_hits=1, press_hits=1)
        fires, hits, alive_fires = strike_ratio_of(log)
        self.assertEqual((fires, hits, alive_fires), (1, 1, 1))

    def test_strike_ratio_skips_self_target(self):
        log = ('P2_PROJECTILE_KABUTO_FIRE species=Kabuto homing=0 rig=0 mouth=(0.0,0.0,0.0)\n'
               'P2_PROJECTILE_SKIP_SELF target=1234\n'
               'P2_PROJECTILE_ENGINE_STRIKE target=1234 kind=Attack damage=250.0 '
               'applied=1 rejected=0 health=180.0->180.0 stored=0.0->250.0 source=0\n')
        self.assertEqual(strike_ratio_of(log), (1, 0, 1))

    def test_strike_ratio_alive_fires_ends_at_aim_none(self):
        # 9 fires and 7 Attack hits all land before the first AIM_NONE, so the
        # alive-fires count is the full 9 and the gate PASSES.
        log = _fire_destroy_log(fires=9, health_hits=7, aim_none=True)
        self.assertEqual(strike_ratio_of(log), (9, 7, 9))
        result = evaluate(log)
        self.assertEqual(result['gates']['victim_strike_ratio'], 'PASS')

    def test_strike_ratio_alive_fires_truncated_by_aim_none(self):
        # A mid-log AIM_NONE splits the fires: only the 4 preceding it are
        # "alive", dropping alive_fires below the >=9 threshold -> FAIL.
        fire = 'P2_PROJECTILE_KABUTO_FIRE species=Kabuto homing=1 rig=1 mouth=(0.0,0.0,0.0)\n'
        hit = ('P2_PROJECTILE_ENGINE_STRIKE target=1234 kind=Attack damage=250.0 '
               'applied=1 rejected=0 health=180.0->180.0 stored=0.0->250.0 source=0\n')
        log = (fire * 4 + 'P2_PROJECTILE_AIM_NONE fire=99\n' + fire * 5
               + hit * 7 + 'P2_PROJECTILE_SKIP_SELF target=9999\n')
        fires, hits, alive_fires = strike_ratio_of(log)
        self.assertEqual((fires, hits, alive_fires), (9, 7, 4))
        result = evaluate(log)
        self.assertEqual(result['gates']['victim_strike_ratio'], 'FAIL')

    def test_evaluate_bomb_engine_navi_hit_pass(self):
        log = ('P2_PROJECTILE_BOMB_ENGINE_HIT token=1 kind=Bomb damage=10.0 '
               'applied=1 rejected=0 health=100.0->90.0 dist=15.0\n')
        result = evaluate(log)
        self.assertEqual(result['gates']['bomb_engine_navi_hit'], 'PASS')

    def test_evaluate_bomb_engine_navi_hit_fail_if_not_applied(self):
        log = ('P2_PROJECTILE_BOMB_ENGINE_HIT token=1 kind=Bomb damage=10.0 '
               'applied=0 rejected=1 health=100.0->90.0 dist=15.0\n')
        result = evaluate(log)
        self.assertEqual(result['gates']['bomb_engine_navi_hit'], 'FAIL')

    def test_evaluate_bomb_engine_navi_hit_fail_if_no_health_change(self):
        log = ('P2_PROJECTILE_BOMB_ENGINE_HIT token=1 kind=Bomb damage=10.0 '
               'applied=1 rejected=0 health=100.0->100.0 dist=15.0\n')
        result = evaluate(log)
        self.assertEqual(result['gates']['bomb_engine_navi_hit'], 'FAIL')

    def test_bomb_engine_hit_regex_captures_dist(self):
        m = BOMB_ENGINE_HIT_RE.search(BOMB_HIT_LOG)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(3), '1')       # applied
        self.assertEqual(m.group(5), '100.0')   # health before
        self.assertEqual(m.group(6), '90.0')    # health after
        self.assertEqual(m.group(7), '15.0')    # dist

    def test_bomb_nohit_regex_captures_dist(self):
        m = BOMB_NOHIT_RE.search(BOMB_NOHIT_LOG)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), '999.0')

    def test_evaluate_bomb_nohit_leaves_untested(self):
        result = evaluate(BOMB_NOHIT_LOG)
        self.assertEqual(result['gates']['bomb_engine_navi_hit'], 'UNTESTED')

    def test_groink_config_row(self):
        row = groink_config()
        self.assertTrue(row.startswith('groink '))
        self.assertEqual(row.count(' '), 4)

    def test_rig_bank_text_has_attack_clip_and_kuti(self):
        bank = rig_bank_text()
        self.assertTrue(bank.startswith('P2_ATTACHMENTS_1 2 1'))
        self.assertIn('kuti 0', bank)
        self.assertIn('attack 60 2', bank)
        self.assertIn('0 59', bank)

    def test_evaluate_self_hit_skipped(self):
        log = SAMPLE_LOG + ('P2_PROJECTILE_SKIP_SELF target=9999\n')
        result = evaluate(log)
        # target 9999 (the firer) is skipped and is not an Attack strike target.
        self.assertEqual(result['gates']['cannon_self_hit_skipped'], 'PASS')

    def test_evaluate_self_hit_fail_when_still_damaged(self):
        log = SAMPLE_LOG + ('P2_PROJECTILE_SKIP_SELF target=1234\n')
        result = evaluate(log)
        # target 1234 was skipped but IS still an Attack strike target -> FAIL.
        self.assertEqual(result['gates']['cannon_self_hit_skipped'], 'FAIL')

    def test_evaluate_second_teki_strike_passes(self):
        result = evaluate(TWO_TEKI_LOG)
        # The firer (1111) is skipped, and a *different* victim (2222) is struck.
        self.assertEqual(result['gates']['second_teki_engine_strike'], 'PASS')

    def test_evaluate_second_teki_fails_when_victim_marker_stripped(self):
        # Strip the victim ENGINE_STRIKE line: skip-self fires but no second Teki
        # is mutated -> the gate flips to FAIL (over-suppression would be hidden).
        victim_line = ('P2_PROJECTILE_ENGINE_STRIKE target=2222 kind=Attack damage=250.0 '
                       'applied=1 rejected=0 health=180.0->180.0 stored=0.0->250.0 source=0\n')
        stripped = TWO_TEKI_LOG.replace(victim_line, '')
        result = evaluate(stripped)
        self.assertEqual(result['gates']['second_teki_engine_strike'], 'FAIL')

    def test_evaluate_victim_contact_in_flight_passes(self):
        result = evaluate(TWO_TEKI_LOG)
        # No teki_pin row/marker and >=4 traces -> the Stone flew to the victim.
        self.assertEqual(result['gates']['victim_contact_in_flight'], 'PASS')

    def test_evaluate_victim_contact_in_flight_fails_on_injection(self):
        log = TWO_TEKI_LOG + 'P2_PROJECTILE_TEKI_PIN injected=1 anchor=1111\n'
        result = evaluate(log)
        self.assertEqual(result['gates']['victim_contact_in_flight'], 'FAIL')

    def test_evaluate_victim_contact_in_flight_fails_birth_frame(self):
        # traces=2 is the birth-frame contact (teki_pin style), not a trajectory.
        log = TWO_TEKI_LOG.replace('reason=health traces=4', 'reason=health traces=2')
        result = evaluate(log)
        self.assertEqual(result['gates']['victim_contact_in_flight'], 'FAIL')

    def test_evaluate_groink_engine_receiver_navi_hit(self):
        result = evaluate(GROINK_LOG)
        self.assertEqual(result['gates']['groink_engine_receiver_navi_hit'], 'PASS')

    def test_evaluate_groink_engine_no_health_change_is_fail(self):
        # Applied=1 but health did NOT decrease -> the Navi was not really hit.
        no_change = GROINK_LOG.replace('health=30.0->20.0', 'health=30.0->30.0')
        result = evaluate(no_change)
        self.assertEqual(result['gates']['groink_engine_receiver_navi_hit'], 'FAIL')

    def test_evaluate_groink_wind_is_not_bomb(self):
        wind = GROINK_LOG.replace('kind=Bomb damage=10.0 applied=1 rejected=0 health=30.0->20.0',
                                  'kind=Wind damage=0.0 applied=0 rejected=1 health=30.0->30.0')
        result = evaluate(wind)
        self.assertEqual(result['gates']['groink_engine_receiver_navi_hit'], 'FAIL')

    def test_parse_engine_strikes(self):
        strikes = parse_engine_strikes(SAMPLE_LOG)
        self.assertEqual(len(strikes), 1)
        hit = strikes[0]
        self.assertEqual(hit['kind'], 'Attack')
        self.assertEqual(hit['applied'], 1)
        self.assertEqual(hit['stored_before'], 0.0)
        self.assertEqual(hit['stored_after'], 250.0)

    def test_evaluate_teki_attack_mutation_passes(self):
        result = evaluate(SAMPLE_LOG)
        gates = result['gates']
        self.assertEqual(gates['window_960x540_centered'], 'PASS')
        self.assertEqual(gates['config_ready'], 'PASS')
        self.assertEqual(gates['stone_contact'], 'PASS')
        self.assertEqual(gates['cannon_fire_fsm'], 'PASS')
        self.assertEqual(gates['teki_attack_receiver_mutation'], 'PASS')
        self.assertEqual(gates['stone_destroy_teardown'], 'PASS')

    def test_evaluate_teki_mutation_fails_on_immune(self):
        log = SAMPLE_LOG.replace(
            'applied=1 rejected=0 health=180.0->180.0 stored=0.0->250.0',
            'applied=0 rejected=1 health=180.0->180.0 stored=0.0->0.0')
        result = evaluate(log)
        self.assertEqual(result['gates']['teki_attack_receiver_mutation'], 'FAIL')
        self.assertEqual(result['gates']['stone_contact'], 'PASS')

    def test_evaluate_press_mutation(self):
        log = SAMPLE_LOG.replace(
            'kind=Attack damage=250.0 applied=1 rejected=0 health=180.0->180.0 stored=0.0->250.0',
            'kind=Press damage=10.0 applied=1 rejected=0 health=300.0->290.0 stored=0.0->0.0')
        result = evaluate(log)
        self.assertEqual(result['gates']['navipiki_press_receiver_mutation'], 'PASS')
        self.assertEqual(result['gates']['teki_attack_receiver_mutation'], 'FAIL')

    def test_missing_window_is_fail(self):
        result = evaluate(SAMPLE_LOG.replace('960x540 windowed and centered', 'nope'))
        self.assertEqual(result['gates']['window_960x540_centered'], 'FAIL')

    def test_stone_config_contains_disc_parms(self):
        row = stone_config()
        self.assertIn(' 250 ', row)     # moveSpeed fp06
        self.assertIn(' 99999 ', row)   # health fp00
        self.assertTrue(row.count(' ') >= 14)

    def test_kabuto_config_mouth(self):
        row = kabuto_config()
        self.assertIn('Kabuto', row)
        self.assertIn(' 175', row)


if __name__ == '__main__':
    unittest.main()
