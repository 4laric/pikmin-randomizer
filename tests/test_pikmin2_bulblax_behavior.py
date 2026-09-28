"""Synthetic tests for experimental/pikmin2_bulblax_behavior (#227).

All inputs are constructed in code; no ISO or native build is required.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from experimental import pikmin2_bulblax_behavior as bb

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT = REPO_ROOT / 'output' / 'bulblax-run1' / 'bulblax.json'


class TestQueenStates(unittest.TestCase):
    def test_state_ids(self):
        self.assertEqual(bb.QUEEN_STATES,
                         {'dead': 0, 'sleep': 1, 'wait': 2, 'damage': 3,
                          'flick': 4, 'rolling': 5, 'born': 6})

    def test_entry_state(self):
        self.assertEqual(bb.queen_entry_state(True), 'wait')
        self.assertEqual(bb.queen_entry_state(False), 'sleep')

    def test_sleep_next(self):
        keep = dict(health=100.0, hit_counter_up=False, larva_due=False,
                    start_flick=False, stuck_pikmin=False)
        self.assertIsNone(bb.queen_sleep_next(**keep))
        self.assertEqual(bb.queen_sleep_next(**dict(keep, larva_due=True)), 'wait')
        self.assertEqual(bb.queen_sleep_next(**dict(keep, larva_due=True, stuck_pikmin=True)),
                         'damage')
        self.assertEqual(bb.queen_sleep_next(**dict(keep, hit_counter_up=True, start_flick=True)),
                         'flick')
        self.assertEqual(bb.queen_sleep_next(**dict(keep, health=0.0, start_flick=True)), 'dead')

    def test_wait_next_override_order(self):
        base = dict(larva_due=False, idle_seconds=0.0, hit_counter_up=False,
                    start_flick=False, health=100.0)
        self.assertIsNone(bb.queen_wait_next(**base))
        self.assertEqual(bb.queen_wait_next(**dict(base, idle_seconds=30.1)), 'sleep')
        # larva due suppresses the idle sleep check entirely
        self.assertEqual(bb.queen_wait_next(**dict(base, idle_seconds=99.0, larva_due=True)),
                         'born')
        # later checks override earlier ones
        self.assertEqual(bb.queen_wait_next(**dict(base, idle_seconds=31.0, hit_counter_up=True)),
                         'damage')
        self.assertEqual(bb.queen_wait_next(**dict(base, hit_counter_up=True, start_flick=True)),
                         'flick')
        self.assertEqual(bb.queen_wait_next(**dict(base, start_flick=True, health=0.0)), 'dead')

    def test_damage_next(self):
        base = dict(larva_due=False, stuck_pikmin=True, start_flick=False, health=100.0)
        self.assertIsNone(bb.queen_damage_next(**base))
        self.assertEqual(bb.queen_damage_next(**dict(base, stuck_pikmin=False)), 'wait')
        self.assertEqual(bb.queen_damage_next(**dict(base, larva_due=True, stuck_pikmin=False)),
                         'wait')
        self.assertEqual(bb.queen_damage_next(**dict(base, stuck_pikmin=False, start_flick=True)),
                         'flick')
        self.assertEqual(bb.queen_damage_next(**dict(base, health=0.0)), 'dead')

    def test_flick_end(self):
        self.assertEqual(bb.queen_flick_end(health=0.0, rolling_left=True), ('dead', None))
        self.assertEqual(bb.queen_flick_end(health=5.0, rolling_left=True), ('rolling', 'left'))
        self.assertEqual(bb.queen_flick_end(health=5.0, rolling_left=False), ('rolling', 'right'))

    def test_roll_direction_alternation(self):
        self.assertTrue(bb.queen_next_roll_is_left(6))   # rolling_r -> left next
        self.assertFalse(bb.queen_next_roll_is_left(5))  # rolling_l -> right next

    def test_roll_pass_reconstructed(self):
        self.assertTrue(getattr(bb.queen_roll_pass, 'reconstructed', False))
        base = dict(dot_along_roll=0.0, rolling_elapsed=0.0, rolling_time=3.5,
                    home_radius=25.0, territory_radius=200.0, health=100.0)
        self.assertEqual(bb.queen_roll_pass(**base), 'continue')
        # territory crash rule: dot > territory - 50
        self.assertEqual(bb.queen_roll_pass(**dict(base, dot_along_roll=151.0)), 'crash')
        self.assertEqual(bb.queen_roll_pass(**dict(base, dot_along_roll=150.0)), 'continue')
        # timed pass end near home
        self.assertEqual(bb.queen_roll_pass(**dict(base, rolling_elapsed=3.6, dot_along_roll=10.0)),
                         'wait')
        self.assertEqual(bb.queen_roll_pass(**dict(base, rolling_elapsed=3.6, dot_along_roll=60.0)),
                         'continue')


class TestQueenParameters(unittest.TestCase):
    def test_larva_hysteresis(self):
        self.assertFalse(bb.queen_larva_room(alive_larvae=50, room_flag=True))
        self.assertTrue(bb.queen_larva_room(alive_larvae=25, room_flag=False))
        self.assertTrue(bb.queen_larva_room(alive_larvae=37, room_flag=True))
        self.assertFalse(bb.queen_larva_room(alive_larvae=37, room_flag=False))
        with self.assertRaises(ValueError):
            bb.queen_larva_room(alive_larvae=-1, room_flag=True)

    def test_birth_due(self):
        self.assertTrue(bb.queen_birth_due(can_create_larva=True, room_flag=True,
                                           birth_timer=2.1, birth_interval=2.0))
        self.assertFalse(bb.queen_birth_due(can_create_larva=True, room_flag=True,
                                            birth_timer=2.0, birth_interval=2.0))
        self.assertFalse(bb.queen_birth_due(can_create_larva=False, room_flag=True,
                                            birth_timer=9.0, birth_interval=2.0))
        self.assertFalse(bb.queen_birth_due(can_create_larva=True, room_flag=False,
                                            birth_timer=9.0, birth_interval=2.0))

    def test_damage_factors(self):
        self.assertEqual(bb.queen_damage_factor(state='sleep', attacker='pikmin_part'), 0.1)
        self.assertEqual(bb.queen_damage_factor(state='flick', attacker='pikmin_part'), 0.2)
        self.assertEqual(bb.queen_damage_factor(state='wait', attacker='pikmin_part'), 1.0)
        self.assertEqual(bb.queen_damage_factor(state='rolling', attacker='pikmin_part',
                                                petrified=True), 0.25)
        self.assertEqual(bb.queen_damage_factor(state='wait', attacker='captain_punch'), 0.0)
        self.assertEqual(bb.queen_damage_factor(state='wait', attacker='earthquake'), 0.0)

    def test_flick_effects(self):
        self.assertEqual(bb.queen_flick_effect('nose'), 'flick')
        self.assertEqual(bb.queen_flick_effect('head'), 'flick')
        self.assertEqual(bb.queen_flick_effect('bod1'), 'flick')
        self.assertEqual(bb.queen_flick_effect('bod5'), 'flick_reversed')
        self.assertEqual(bb.queen_flick_effect('bod3'), 'shake_off')
        self.assertEqual(bb.QUEEN_FLICK['knockback']['disc'], 300.0)
        self.assertEqual(bb.QUEEN_FLICK['damage']['disc'], 1.0)

    def test_variants(self):
        hob = bb.queen_variant('f_01')
        self.assertEqual(hob, {'no_larvae': True, 'easy_first_roll': True, 'health': 3300.0})
        self.assertEqual(bb.QUEEN_PROPER_PARMS['hob_health']['header'], 2500.0)
        hoh = bb.queen_variant('l_02')
        self.assertEqual(hoh['crash_rocks'], 7)
        self.assertEqual(hoh['rock_lifetime_seconds'], 30.0)
        self.assertEqual(bb.queen_variant('f_03', zukan_mode=True), {'no_larvae': True})
        self.assertIsNone(bb.queen_variant('last_1'))

    def test_shake_off_thresholds(self):
        self.assertEqual(bb.QUEEN_SHAKE_OFF_DISC['blows'], (30, 35, 45, 50))
        self.assertEqual(bb.QUEEN_SHAKE_OFF_DISC['sticking'], (5, 10, 15))

    def test_collision_radii(self):
        self.assertEqual(bb.QUEEN_COLLISION['root_radius'], 275.0)
        self.assertEqual(bb.QUEEN_COLLISION['children']['nose'], 10.0)
        self.assertTrue(bb.QUEEN_COLLISION['all_stickable'])


class TestBaby(unittest.TestCase):
    def test_state_ids_and_entry(self):
        self.assertEqual(bb.BABY_STATES,
                         {'dead': 0, 'press': 1, 'born': 2, 'move': 3, 'attack': 4})
        self.assertEqual(bb.baby_entry_state(False), 'born')
        self.assertEqual(bb.baby_entry_state(True), 'move')

    def test_press_crush(self):
        self.assertTrue(bb.baby_press_kills(state_id=3, petrified=False))   # Move
        self.assertTrue(bb.baby_press_kills(state_id=4, petrified=False))   # Attack
        self.assertFalse(bb.baby_press_kills(state_id=2, petrified=False))  # Born
        self.assertFalse(bb.baby_press_kills(state_id=3, petrified=True))

    def test_move_step_reconstructed(self):
        self.assertTrue(getattr(bb.baby_move_step, 'reconstructed', False))
        base = dict(angle_dist=10.0, max_attack_angle=45.0, move_speed=40.0,
                    target_distance=100.0, max_attack_range=30.0, has_target=True)
        self.assertEqual(bb.baby_move_step(**base), (40.0, None))
        # quarter speed while turning
        self.assertEqual(bb.baby_move_step(**dict(base, angle_dist=90.0)), (10.0, None))
        # attack inside range 30 and angle 45
        self.assertEqual(bb.baby_move_step(**dict(base, target_distance=25.0)), (40.0, 'attack'))
        self.assertEqual(bb.baby_move_step(**dict(base, has_target=False)), (0.0, None))

    def test_attack_key2_and_swallow(self):
        self.assertEqual(bb.baby_attack_key2(mouth_occupied=False), 'attackfail')
        self.assertEqual(bb.baby_attack_key2(mouth_occupied=True), 'continue')
        self.assertEqual(bb.BABY_PROPER_PARMS['poison_damage']['disc'], 300.0)

    def test_born_transition(self):
        self.assertIsNone(bb.baby_born_next(landed=False, health=5.0))
        self.assertEqual(bb.baby_born_next(landed=True, health=5.0), 'move')
        self.assertEqual(bb.baby_born_next(landed=True, health=0.0), 'dead')

    def test_facts(self):
        self.assertEqual(bb.BABY_GENERAL_DISC['health']['value'], 5.0)
        self.assertEqual(bb.BABY_GENERAL_DISC['sight_radius']['value'], 800.0)
        self.assertEqual(bb.BABY_GENERAL_DISC['view_angle']['value'], 180.0)
        self.assertEqual(bb.BABY_MOUTH['radius'], 20.0)
        self.assertEqual(bb.BABY_MOUTH['slots'], 1)
        self.assertEqual(bb.BABY_COLLISION['root_radius'], 25.0)
        self.assertEqual(bb.BABY_COLLISION['children']['stickable_child'], 15.0)
        self.assertEqual(set(bb.BABY_DISABLED_EVENTS), {'EB_Cullable', 'EB_LeaveCarcass'})
        self.assertEqual(bb.BABY_PROPER_PARMS['nectar_chance']['disc'], 0.2)


class TestKingChappy(unittest.TestCase):
    def test_state_ids_and_entry(self):
        self.assertEqual(len(bb.KING_STATES), 13)
        self.assertEqual(bb.KING_STATES['hidewait'], 9)
        self.assertEqual(bb.KING_STATES['swallow'], 12)
        self.assertEqual(bb.king_entry_state(), 'hidewait')

    def test_hidewait_wake(self):
        base = dict(nearest_target_distance=59.0, frames_waited=1, scale=1.0,
                    distance_to_spawn=60.0, time_to_appearance=0)
        self.assertTrue(bb.king_hidewait_wake(**base))
        self.assertFalse(bb.king_hidewait_wake(**dict(base, nearest_target_distance=60.0)))
        # disc time_to_appearance is 0; header default 200 keeps it buried
        self.assertFalse(bb.king_hidewait_wake(**dict(base, frames_waited=150,
                                                      time_to_appearance=200)))
        # range scales with the big variant
        self.assertTrue(bb.king_hidewait_wake(**dict(base, nearest_target_distance=89.0,
                                                     scale=1.5)))

    def test_walk_turn_and_give_up(self):
        self.assertEqual(bb.king_walk_turn(goal_angle_off=70.0, required_turning_angle=60.0,
                                           turning_end_angle=40.0), 'turn')
        self.assertEqual(bb.king_walk_turn(goal_angle_off=35.0, required_turning_angle=60.0,
                                           turning_end_angle=40.0), 'finish_turn')
        self.assertEqual(bb.king_walk_turn(goal_angle_off=50.0, required_turning_angle=60.0,
                                           turning_end_angle=40.0), 'walk')
        self.assertTrue(bb.king_walk_give_up(frames_without_target=501,
                                             period_of_incubation=500, out_of_territory=False))
        self.assertTrue(bb.king_walk_give_up(frames_without_target=0,
                                             period_of_incubation=500, out_of_territory=True))
        self.assertFalse(bb.king_walk_give_up(frames_without_target=500,
                                              period_of_incubation=500, out_of_territory=False))

    def test_check_flick(self):
        # under half HP, roll below 0.5 -> WarCry
        self.assertEqual(bb.king_check_flick(health=600.0, max_health=1300.0, roll=0.4), 'warcry')
        self.assertEqual(bb.king_check_flick(health=600.0, max_health=1300.0, roll=0.5), 'flick')
        # at/over half HP always Flick
        self.assertEqual(bb.king_check_flick(health=1300.0, max_health=1300.0, roll=0.1), 'flick')

    def test_damage_tiers(self):
        self.assertEqual(bb.king_damage_tier(petrified=True, has_part=False, stuck_to_part=False,
                                             attacker_dy=0.0, sqr_distance_xz=0.0), 0.1)
        self.assertEqual(bb.king_damage_tier(petrified=False, has_part=True, stuck_to_part=True,
                                             attacker_dy=0.0, sqr_distance_xz=0.0), 1.0)
        self.assertEqual(bb.king_damage_tier(petrified=False, has_part=False, stuck_to_part=False,
                                             attacker_dy=0.0, sqr_distance_xz=100.0), 0.2)
        self.assertEqual(bb.king_damage_tier(petrified=False, has_part=False, stuck_to_part=False,
                                             attacker_dy=0.0, sqr_distance_xz=1601.0), 0.0)
        self.assertEqual(bb.king_damage_tier(petrified=False, has_part=False, stuck_to_part=False,
                                             attacker_dy=6.0, sqr_distance_xz=0.0), 0.0)

    def test_bombs(self):
        self.assertEqual(bb.king_bomb_damage(bombs_eaten=3), 600.0)
        self.assertEqual(bb.king_bomb_damage(bombs_eaten=0), 0.0)
        self.assertTrue(bb.king_eatable_bomb('BOMB_Wait'))
        self.assertFalse(bb.king_eatable_bomb('BOMB_CountDown'))
        self.assertEqual(bb.KING_BOMB['stun_frames']['disc'], 180)
        self.assertEqual(bb.KING_BOMB['stun_frames']['header'], 10)
        self.assertEqual(bb.KING_BOMB['external_blast_factor']['value'], 0.25)

    def test_big_variant(self):
        self.assertTrue(bb.king_is_big(cave_id='f_03'))
        self.assertTrue(bb.king_is_big(cave_id='last_1', force_big=True))
        self.assertFalse(bb.king_is_big(cave_id='last_1'))
        self.assertEqual(bb.KING_BIG_VARIANT['scale']['disc'], 1.5)
        self.assertEqual(bb.KING_BIG_VARIANT['health']['disc'], 1800.0)
        self.assertEqual(bb.KING_BIG_VARIANT['speed']['disc'], 45.0)
        self.assertEqual(bb.KING_BIG_VARIANT['floor_offset'], 60.0)

    def test_attack_and_flick_reconstructed(self):
        self.assertTrue(getattr(bb.king_attack_step, 'reconstructed', False))
        self.assertTrue(getattr(bb.king_flick_step, 'reconstructed', False))
        actions = bb.king_attack_step(key=bb.KEYEVENT_6, mouth_slots_free=True,
                                      bombs_in_range=True, pikmin_in_range=True)
        self.assertEqual(actions, frozenset({'eat_bomb', 'eat_pikmin'}))
        actions = bb.king_attack_step(key=bb.KEYEVENT_6, mouth_slots_free=False,
                                      bombs_in_range=True, pikmin_in_range=False)
        self.assertEqual(actions, frozenset())
        flick = bb.king_flick_step(pikmin_in_trample_range=3, captains_in_trample_range=0)
        self.assertTrue(flick['flick_captains'])
        flick = bb.king_flick_step(pikmin_in_trample_range=0, captains_in_trample_range=1)
        self.assertFalse(flick['flick_captains'])

    def test_warcry_and_mouth(self):
        self.assertEqual(bb.KING_WARCRY['astonish_range']['disc'], 300.0)
        self.assertEqual(bb.KING_WARCRY['astonish_angle_deg']['disc'], 180.0)
        self.assertEqual(bb.KING_WARCRY['cross_emperor']['wake_state'], 'appear')
        self.assertEqual(bb.KING_WARCRY['cross_emperor']['roar_state'], 'warcry')
        self.assertEqual(bb.KING_MOUTH['slots'], 9)
        self.assertEqual(bb.KING_MOUTH['slot_joints'][0], 'kamu1')
        self.assertEqual(bb.KING_MOUTH['slot_joints'][-1], 'kamu9')
        self.assertEqual(bb.KING_MOUTH['slot_radius'], 25.0)
        self.assertTrue(bb.KING_MOUTH['slot_radius_scaled'])
        self.assertEqual(bb.KING_MOUTH['tongue_joint'], 'bero6')
        self.assertEqual(bb.KING_MOUTH['tongue_radius'], 5.0)
        self.assertEqual(bb.KING_ATTACK['swallow_poison_damage']['value'], 300.0)
        self.assertEqual(bb.KING_ATTACK['captain_damage']['disc'], 5.0)

    def test_stone_state_and_collision(self):
        self.assertEqual(bb.KING_STONE_STATE_PARTS['mark_stickable'], ('back', 'ketu'))
        self.assertEqual(bb.KING_COLLISION['root_radius'], 80.0)
        self.assertEqual(bb.KING_COLLISION['children']['ketu'], 40.0)
        self.assertEqual(set(bb.KING_COLLISION['stickable']), {'head', 'hana', 'kuti'})


class TestSharedFacts(unittest.TestCase):
    def test_boss_flags_and_rewards(self):
        self.assertTrue(bb.IS_ENEMY_BOSS['Queen'])
        self.assertTrue(bb.IS_ENEMY_BOSS['KingChappy'])
        self.assertFalse(bb.IS_ENEMY_BOSS['Baby'])
        self.assertEqual(bb.QUEEN_CHILD_BUDGET['count'], 50)
        self.assertEqual(bb.QUEEN_ROCK_RESERVE['count'], 10)
        self.assertEqual(bb.CARCASS['Queen']['pokos'], 15)
        self.assertEqual((bb.CARCASS['Queen']['carry_min'], bb.CARCASS['Queen']['carry_max']),
                         (20, 30))
        self.assertIsNone(bb.CARCASS['Baby'])
        self.assertEqual(bb.NECTAR_ON_PETRIFIED_KILL['Queen']['rolls'], 5)
        self.assertEqual(bb.NECTAR_ON_PETRIFIED_KILL['Queen']['yellow_chance'], 0.85)
        self.assertEqual(bb.NECTAR_ON_PETRIFIED_KILL['Baby']['rolls'], 1)
        self.assertEqual(bb.NECTAR_ON_PETRIFIED_KILL['Baby']['yellow_chance'], 0.99)

    def test_rosters(self):
        self.assertEqual(len(bb.ROSTERS), 8)
        by_cave = {(r['cave'], r['floor']): r for r in bb.ROSTERS}
        self.assertEqual(by_cave[('tutorial_3', 8)]['treasure'], 'Repugnant Appendage')
        self.assertEqual(by_cave[('forest_1', 5)]['entries'], ('Queen_radar_a',))
        self.assertEqual(by_cave[('forest_3', 7)]['treasure'], 'Forged Courage')
        self.assertEqual(len(by_cave[('last_1', 4)]['entries']), 2)
        self.assertEqual(len(by_cave[('last_2', 10)]['entries']), 2)
        self.assertEqual(by_cave[('ch_MUKI_king', 4)]['treasure'], 'The Key')
        self.assertEqual(len(by_cave[('ch_MUKI_king', 5)]['entries']), 3)
        self.assertTrue(bb.NO_SURFACE_OR_BATTLE_PLACEMENTS)

    def test_animation_streams(self):
        # type 0/1 bracket loops; types 2-6 gameplay events
        for clips in (bb.QUEEN_CLIPS, bb.BABY_CLIPS, bb.KING_CLIPS):
            for name, clip in clips.items():
                for frame, event in clip['loops']:
                    self.assertIn(event, (0, 1), name)
                    self.assertIn([frame, event], clip['events'], name)
                for frame, event in clip['events']:
                    self.assertGreaterEqual(frame, 0, name)
                    self.assertIn(event, range(0, 7), name)
        self.assertEqual(bb.ANIM_BLEND_FRAMES, 30)
        self.assertIn('queen_roll_pass', bb.RECONSTRUCTED)
        self.assertIn('baby_move_step', bb.RECONSTRUCTED)
        self.assertIn('king_attack_step', bb.RECONSTRUCTED)
        self.assertIn('king_flick_step', bb.RECONSTRUCTED)


class TestExtractionReportCheck(unittest.TestCase):
    def test_check_matches_report(self):
        if not REPORT.is_file():
            self.skipTest('extraction report not present')
        self.assertEqual(bb.check(REPORT), [])

    def test_check_detects_mismatch(self):
        if not REPORT.is_file():
            self.skipTest('extraction report not present')
        report = json.loads(REPORT.read_text())
        report['species']['Queen']['clips'][0]['events'] = [[0, 9]]
        tmp = REPO_ROOT / 'output' / '_bulblax_check_fixture.json'
        try:
            tmp.write_text(json.dumps(report))
            self.assertTrue(any('Queen' in p for p in bb.check(tmp)))
        finally:
            tmp.unlink(missing_ok=True)

    def test_cli_exit_codes(self):
        if not REPORT.is_file():
            self.skipTest('extraction report not present')
        ok = subprocess.run([sys.executable, '-m', 'experimental.pikmin2_bulblax_behavior',
                             '--check', str(REPORT)], cwd=REPO_ROOT,
                            capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)


if __name__ == '__main__':
    unittest.main()
