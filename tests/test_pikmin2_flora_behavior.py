"""Synthetic tests for experimental/pikmin2_flora_behavior (lane 23, #171).

All inputs are constructed in code; no ISO, disc or native build is required.
"""
import unittest

from experimental import pikmin2_flora_behavior as fb


class TestIdentityAndSpawnability(unittest.TestCase):
    def test_full_roster_size(self):
        self.assertEqual(len(fb.FLORA), 25)
        self.assertEqual(len(fb.PLANT_SPECIES), 17)
        self.assertEqual(len(fb.POM_SPECIES), 6)
        self.assertEqual(fb.FLORA['Pelplant'], 0)
        self.assertEqual(fb.FLORA['RandPom'], 8)
        self.assertEqual(fb.FLORA['Wakame_l'], 52)
        self.assertEqual(fb.FLORA['KareOoinu_l'], 92)

    def test_nonspawnable_base(self):
        self.assertEqual(fb.FLORA['Pom'], 82)
        self.assertEqual(fb.FLORA[fb.POM_BASE], fb.POM_BASE_ID)
        self.assertEqual(fb.NONSPAWNABLE_BASES, {'Pom': 82})
        self.assertEqual(fb.CLASSIFICATION['Pom'], 'nonspawnable_base')
        self.assertFalse(fb.is_spawnable('Pom'))

    def test_spawnable_identities(self):
        self.assertTrue(fb.is_spawnable('Pelplant'))
        self.assertTrue(fb.is_spawnable('RandPom'))
        self.assertTrue(fb.is_spawnable('Tanpopo'))
        self.assertIn('Pom', fb.FLORA)
        self.assertNotIn('Pom', fb.SPAWNABLE_IDS)
        with self.assertRaises(ValueError):
            fb.is_spawnable('NotAFlora')

    def test_classification(self):
        self.assertEqual(fb.CLASSIFICATION['Pelplant'], 'enemy_flora')
        self.assertEqual(fb.CLASSIFICATION['BluePom'], 'enemy_flora')
        self.assertEqual(fb.CLASSIFICATION['Clover'], 'prop_flora')
        self.assertEqual(fb.CLASSIFICATION['Pom'], 'nonspawnable_base')


class TestPelletPosy(unittest.TestCase):
    def test_growth_uses_disc_seconds(self):
        self.assertEqual(fb.pellet_growth('small', 89.9, growing=True), 'small')
        self.assertEqual(fb.pellet_growth('small', 90.0, growing=True), 'middle')
        self.assertEqual(fb.pellet_growth('middle', 59.9, growing=True), 'middle')
        self.assertEqual(fb.pellet_growth('middle', 60.0, growing=True), 'full')
        self.assertEqual(fb.pellet_growth('full', 999.0, growing=True), 'full')

    def test_growth_header_defaults_differ(self):
        self.assertEqual(fb.PELPLANT_PROPER_HEADER['fp01'], 120.0)
        self.assertEqual(fb.PELPLANT_PROPER_HEADER['fp02'], 120.0)
        self.assertEqual(fb.PELPLANT_PROPER_DISC['fp01'], 90.0)
        self.assertEqual(fb.PELPLANT_PROPER_DISC['fp02'], 60.0)
        self.assertEqual(fb.pellet_growth('small', 119.9, growing=True,
                                          fp01_seconds=fb.PELPLANT_PROPER_HEADER['fp01']),
                         'small')
        self.assertEqual(fb.pellet_growth('small', 120.0, growing=True,
                                          fp01_seconds=fb.PELPLANT_PROPER_HEADER['fp01']),
                         'middle')
        self.assertEqual(fb.pellet_growth('middle', 119.9, growing=True,
                                          fp02_seconds=fb.PELPLANT_PROPER_HEADER['fp02']),
                         'middle')

    def test_growth_only_while_growing(self):
        self.assertEqual(fb.pellet_growth('small', 1000.0, growing=False), 'small')
        self.assertEqual(fb.pellet_growth('middle', 1000.0, growing=False), 'middle')

    def test_growth_validation(self):
        with self.assertRaises(ValueError):
            fb.pellet_growth('huge', 1.0, growing=True)
        with self.assertRaises(ValueError):
            fb.pellet_growth('small', 'soon', growing=True)
        with self.assertRaises(ValueError):
            fb.pellet_growth('small', float('nan'), growing=True)

    def test_vulnerability_only_when_full(self):
        self.assertTrue(fb.pellet_is_vulnerable('full'))
        self.assertFalse(fb.pellet_is_vulnerable('small'))
        self.assertFalse(fb.pellet_is_vulnerable('middle'))
        with self.assertRaises(ValueError):
            fb.pellet_is_vulnerable('dead')

    def test_instant_fell_part_code(self):
        self.assertTrue(fb.pellet_instant_fell('s__0'))
        self.assertTrue(fb.pellet_instant_fell('head0'))
        self.assertFalse(fb.pellet_instant_fell('s__1'))
        self.assertFalse(fb.pellet_instant_fell(''))
        with self.assertRaises(ValueError):
            fb.pellet_instant_fell(None)

    def test_release_on_death(self):
        self.assertTrue(fb.pellet_released_on_death(captured=True, state='dead'))
        self.assertFalse(fb.pellet_released_on_death(captured=False, state='dead'))
        self.assertFalse(fb.pellet_released_on_death(captured=True, state='waitfull'))
        with self.assertRaises(ValueError):
            fb.pellet_released_on_death(captured=True, state='exploded')

    def test_no_attacker_colour_following(self):
        self.assertFalse(fb.PELLET_FOLLOWS_ATTACKER_COLOUR)
        self.assertFalse(fb.PELPLANT_HAS_REGROWTH_TIMER)
        self.assertEqual(fb.PELPLANT_DISC_HEALTH['value'], 50.0)

    def test_generator_colour_is_fixed(self):
        self.assertEqual(fb.pellet_colour(generator_colour='red',
                                          random_setting=False), 'red')
        with self.assertRaises(ValueError):
            fb.pellet_colour(generator_colour=None, random_setting=False)
        with self.assertRaises(ValueError):
            fb.pellet_colour(generator_colour='purple', random_setting=False)

    def test_random_colour_cycles_and_skips_unmet(self):
        all_met = ('blue', 'red', 'yellow')
        self.assertEqual(fb.pellet_colour(random_setting=True, elapsed_seconds=0.0,
                                          met_colours=all_met), 'blue')
        self.assertEqual(fb.pellet_colour(random_setting=True, elapsed_seconds=1.5,
                                          met_colours=all_met), 'red')
        self.assertEqual(fb.pellet_colour(random_setting=True, elapsed_seconds=3.0,
                                          met_colours=all_met), 'yellow')
        self.assertEqual(fb.pellet_colour(random_setting=True, elapsed_seconds=4.5,
                                          met_colours=all_met), 'blue')
        # colours not yet met are skipped
        self.assertEqual(fb.pellet_colour(random_setting=True, elapsed_seconds=0.0,
                                          met_colours=('red', 'yellow')), 'red')
        self.assertEqual(fb.pellet_colour(random_setting=True, elapsed_seconds=1.5,
                                          met_colours=('red', 'yellow')), 'yellow')
        with self.assertRaises(ValueError):
            fb.pellet_colour(random_setting=True, elapsed_seconds=0.0, met_colours=())

    def test_random_colour_validation(self):
        with self.assertRaises(ValueError):
            fb.pellet_colour(random_setting=True, elapsed_seconds=-1.0,
                             met_colours=('blue',))
        with self.assertRaises(ValueError):
            fb.pellet_colour(random_setting=True, elapsed_seconds=1.0,
                             met_colours=('blue',), change_seconds=0.0)

    def test_pellet_sizes(self):
        self.assertEqual(fb.PELPLANT_PELLET_SIZES, (1, 5, 10, 20))
        self.assertFalse(fb.pellet_size_uses_bgrow(1))
        self.assertFalse(fb.pellet_size_uses_bgrow(5))
        self.assertTrue(fb.pellet_size_uses_bgrow(10))
        self.assertTrue(fb.pellet_size_uses_bgrow(20))
        with self.assertRaises(ValueError):
            fb.pellet_size_uses_bgrow(7)


class TestCandypopBud(unittest.TestCase):
    def test_budgets_all_six(self):
        for species in ('BluePom', 'RedPom', 'YellowPom', 'BlackPom', 'WhitePom'):
            self.assertEqual(fb.candypop_budget(species), 5)
        self.assertEqual(fb.candypop_budget('RandPom'), 1)
        with self.assertRaises(ValueError):
            fb.candypop_budget('Pelplant')

    def test_colours_all_six(self):
        self.assertEqual(fb.candypop_own_colour('BluePom'), 'blue')
        self.assertEqual(fb.candypop_own_colour('RedPom'), 'red')
        self.assertEqual(fb.candypop_own_colour('YellowPom'), 'yellow')
        self.assertEqual(fb.candypop_own_colour('BlackPom'), 'purple')
        self.assertEqual(fb.candypop_own_colour('WhitePom'), 'white')
        self.assertIsNone(fb.candypop_own_colour('RandPom'))

    def test_accept_colour_bud_paths(self):
        self.assertTrue(fb.candypop_accept(species='BluePom', slot_pressed=True,
                                           armed=True, used_slots=4))
        self.assertFalse(fb.candypop_accept(species='BluePom', slot_pressed=True,
                                            armed=True, used_slots=5))
        self.assertFalse(fb.candypop_accept(species='BluePom', slot_pressed=False,
                                            armed=True, used_slots=0))
        self.assertFalse(fb.candypop_accept(species='BluePom', slot_pressed=True,
                                            armed=False, used_slots=0))

    def test_accept_queen_path(self):
        self.assertTrue(fb.candypop_accept(species='RandPom', slot_pressed=True,
                                           armed=True, used_slots=0))
        self.assertFalse(fb.candypop_accept(species='RandPom', slot_pressed=True,
                                            armed=True, used_slots=1))

    def test_accept_validation(self):
        with self.assertRaises(ValueError):
            fb.candypop_accept(species='BluePom', slot_pressed=True, armed=True,
                               used_slots=-1)
        with self.assertRaises(ValueError):
            fb.candypop_accept(species='Clover', slot_pressed=True, armed=True,
                               used_slots=0)

    def test_refund_every_colour_bud(self):
        for species, colour in (('BluePom', 'blue'), ('RedPom', 'red'),
                                ('YellowPom', 'yellow'), ('BlackPom', 'purple'),
                                ('WhitePom', 'white')):
            self.assertTrue(fb.candypop_refund(species=species, thrown_colour=colour))
        self.assertFalse(fb.candypop_refund(species='BluePom', thrown_colour='red'))
        self.assertFalse(fb.candypop_refund(species='WhitePom', thrown_colour='purple'))

    def test_queen_has_no_refund(self):
        for colour in ('blue', 'red', 'yellow'):
            self.assertFalse(fb.candypop_refund(species='RandPom', thrown_colour=colour))

    def test_refund_validation(self):
        with self.assertRaises(ValueError):
            fb.candypop_refund(species='BluePom', thrown_colour='green')
        with self.assertRaises(ValueError):
            fb.candypop_refund(species='Pelplant', thrown_colour='blue')

    def test_close_stays_open_then_shoots(self):
        self.assertIsNone(fb.candypop_close(seconds_since_last_swallow=0.5,
                                            remain_open_seconds=1.0,
                                            budget_spent=False, pikmin_inside=1))
        self.assertEqual(fb.candypop_close(seconds_since_last_swallow=1.0,
                                           remain_open_seconds=1.0,
                                           budget_spent=False, pikmin_inside=1), 'shot')
        self.assertEqual(fb.candypop_close(seconds_since_last_swallow=1.0,
                                           remain_open_seconds=1.0,
                                           budget_spent=False, pikmin_inside=0), 'reopen')

    def test_close_when_budget_spent(self):
        self.assertEqual(fb.candypop_close(seconds_since_last_swallow=0.0,
                                           remain_open_seconds=1.0,
                                           budget_spent=True, pikmin_inside=2), 'shot')
        self.assertEqual(fb.candypop_close(seconds_since_last_swallow=0.0,
                                           remain_open_seconds=1.0,
                                           budget_spent=True, pikmin_inside=0), 'reopen')

    def test_close_header_remain_time(self):
        self.assertEqual(fb.POM_PROPER_HEADER['fp01'], 30.0)
        self.assertEqual(fb.POM_PROPER_DISC['fp01'], 1.0)
        self.assertIsNone(fb.candypop_close(seconds_since_last_swallow=29.0,
                                            remain_open_seconds=30.0,
                                            budget_spent=False, pikmin_inside=1))

    def test_close_validation(self):
        with self.assertRaises(ValueError):
            fb.candypop_close(seconds_since_last_swallow='now', remain_open_seconds=1.0,
                              budget_spent=False, pikmin_inside=0)

    def test_shot_count_paths(self):
        self.assertEqual(fb.candypop_shot_count(species='BluePom', swallowed=3), 3)
        self.assertEqual(fb.candypop_shot_count(species='WhitePom', swallowed=2), 2)
        self.assertEqual(fb.candypop_shot_count(species='RandPom', swallowed=3), 27)
        self.assertEqual(fb.candypop_shot_count(species='RandPom', swallowed=0), 0)
        with self.assertRaises(ValueError):
            fb.candypop_shot_count(species='RandPom', swallowed=-1)
        with self.assertRaises(ValueError):
            fb.candypop_shot_count(species='Pom', swallowed=1)

    def test_queen_colour_is_deterministic(self):
        all_met = ('blue', 'red', 'yellow')
        self.assertEqual(fb.candypop_queen_colour(elapsed_seconds=0.0,
                                                 met_colours=all_met), 'blue')
        self.assertEqual(fb.candypop_queen_colour(elapsed_seconds=2.6,
                                                 met_colours=all_met), 'red')
        self.assertEqual(fb.candypop_queen_colour(elapsed_seconds=5.2,
                                                 met_colours=all_met), 'yellow')
        self.assertEqual(fb.candypop_queen_colour(elapsed_seconds=7.8,
                                                 met_colours=all_met), 'blue')
        # skip unmet colours
        self.assertEqual(fb.candypop_queen_colour(elapsed_seconds=0.0,
                                                 met_colours=('yellow',)), 'yellow')
        with self.assertRaises(ValueError):
            fb.candypop_queen_colour(elapsed_seconds=0.0, met_colours=())
        with self.assertRaises(ValueError):
            fb.candypop_queen_colour(elapsed_seconds=-1.0, met_colours=all_met)
        self.assertEqual(fb.POM_PROPER_DISC['fp02'], 2.6)
        self.assertEqual(fb.POM_PROPER_HEADER['fp02'], 1.25)

    def test_launch_and_sprout_facts(self):
        self.assertEqual(fb.POM_SPROUT_LAUNCH, (110.0, 750.0, 110.0))
        self.assertEqual(fb.POM_SPROUT_MATURITY, 'leaf')
        self.assertTrue(fb.POM_BULBMIN_NOT_COUNTED_AS_LOSS)
        self.assertEqual(fb.POM_SLOT['radius'], 30.0)
        self.assertTrue(fb.POM_SLOT['accepts_any_colour'])
        self.assertEqual(fb.POM_UNREAD_KEYS, ('ip02', 'ip12', 'fp03'))
        self.assertEqual(fb.POM_PROPER_DISC['ip13'], 9)
        self.assertEqual(fb.POM_PROPER_HEADER['ip13'], 5)

    def test_invulnerability_facts(self):
        self.assertTrue(fb.POM_EXCLUDED_FROM_DROP_JITTER)
        self.assertTrue(fb.POM_INVULNERABLE_AFTER_LANDING)
        self.assertTrue(fb.POM_BITTER_IMMUNE)
        self.assertFalse(fb.POM_HAS_SHADOW)
        self.assertFalse(fb.POM_HAS_CORPSE)
        self.assertEqual(fb.POM_CUTSCENE_TRIGGER_RADIUS, 350.0)


class TestCandypopSpawnGating(unittest.TestCase):
    def test_violet_ivory_early_floor_cap(self):
        self.assertFalse(fb.candypop_spawn_allowed(
            species='BlackPom', floor=1, cave='Emergence Cave',
            met_colours=('purple',), player_count=20))
        self.assertTrue(fb.candypop_spawn_allowed(
            species='BlackPom', floor=1, cave='Emergence Cave',
            met_colours=('purple',), player_count=19))
        self.assertFalse(fb.candypop_spawn_allowed(
            species='WhitePom', floor=2, cave='White Flower Garden',
            met_colours=('white',), player_count=20))
        # cap only applies on the early floors/caves
        self.assertTrue(fb.candypop_spawn_allowed(
            species='BlackPom', floor=3, cave='Some Cave',
            met_colours=('purple',), player_count=20))

    def test_ivory_needs_whites_except_wfg(self):
        self.assertFalse(fb.candypop_spawn_allowed(
            species='WhitePom', floor=3, cave='Some Cave',
            met_colours=(), player_count=0))
        self.assertTrue(fb.candypop_spawn_allowed(
            species='WhitePom', floor=3, cave='Some Cave',
            met_colours=('white',), player_count=0))
        self.assertTrue(fb.candypop_spawn_allowed(
            species='WhitePom', floor=3, cave='White Flower Garden',
            met_colours=(), player_count=0))

    def test_lapis_and_golden_need_met_colour(self):
        self.assertFalse(fb.candypop_spawn_allowed(
            species='BluePom', floor=3, cave='Some Cave',
            met_colours=(), player_count=0))
        self.assertTrue(fb.candypop_spawn_allowed(
            species='BluePom', floor=3, cave='Some Cave',
            met_colours=('blue',), player_count=0))
        self.assertFalse(fb.candypop_spawn_allowed(
            species='YellowPom', floor=3, cave='Some Cave',
            met_colours=(), player_count=0))
        self.assertTrue(fb.candypop_spawn_allowed(
            species='YellowPom', floor=3, cave='Some Cave',
            met_colours=('yellow',), player_count=0))
        # no met-colour gate is asserted for the Crimson bud
        self.assertTrue(fb.candypop_spawn_allowed(
            species='RedPom', floor=3, cave='Some Cave',
            met_colours=(), player_count=0))

    def test_gating_validation(self):
        with self.assertRaises(ValueError):
            fb.candypop_spawn_allowed(species='BluePom', floor=0, cave='X',
                                      met_colours=(), player_count=0)
        with self.assertRaises(ValueError):
            fb.candypop_spawn_allowed(species='BluePom', floor=1, cave='X',
                                      met_colours=(), player_count=-1)
        with self.assertRaises(ValueError):
            fb.candypop_spawn_allowed(species='Clover', floor=1, cave='X',
                                      met_colours=(), player_count=0)


class TestPlants(unittest.TestCase):
    def test_plant_lod_roles(self):
        self.assertEqual(fb.plant_lod('Clover', 'territory'), 'lifted_sphere')
        self.assertEqual(fb.plant_lod('Tanpopo', 'private_radius'), 'cylinder')
        self.assertEqual(fb.plant_lod('Wakame_l', 'home_radius'), 'cylinder')
        self.assertEqual(fb.plant_lod('Clover', 'fp01'), 'floor_offset')
        self.assertIsNone(fb.plant_lod('Tanpopo', 'fp01'))
        self.assertIsNone(fb.plant_lod('Clover', 'mystery'))

    def test_plant_lod_validation(self):
        with self.assertRaises(ValueError):
            fb.plant_lod('Pelplant', 'territory')
        with self.assertRaises(ValueError):
            fb.plant_lod('NotAFlora', 'territory')

    def test_floor_offset_reconstructed(self):
        self.assertIn('plant_floor_offset', fb.RECONSTRUCTED)
        self.assertTrue(getattr(fb.plant_floor_offset, 'reconstructed', False))
        clover = fb.plant_floor_offset('Clover')
        self.assertEqual(clover['audit_disc'], 25.0)
        self.assertEqual(clover['general_fp01_disc'], 40.0)
        self.assertEqual(clover['inert_extra_fp01_disc'], 25.0)
        self.assertIsNone(fb.plant_floor_offset('Tanpopo'))

    def test_sway_on_touch(self):
        self.assertTrue(fb.plant_sways(mover='captain', speed=2.0, past_volume=True))
        self.assertTrue(fb.plant_sways(mover='pikmin', speed=-3.0, past_volume=True))
        self.assertFalse(fb.plant_sways(mover='captain', speed=1.0, past_volume=True))
        self.assertFalse(fb.plant_sways(mover='captain', speed=5.0, past_volume=False))
        self.assertTrue(fb.plant_sways(mover='purple_quake', speed=0.0, past_volume=False))
        self.assertFalse(fb.plant_sways(mover='enemy', speed=99.0, past_volume=True))
        with self.assertRaises(ValueError):
            fb.plant_sways(mover='treasure', speed=1.0, past_volume=True)

    def test_touch_sound_only_captains(self):
        self.assertEqual(fb.plant_touch_sound('captain'), fb.PLANT_CAPTAIN_TOUCH_SOUND)
        self.assertIsNone(fb.plant_touch_sound('pikmin'))
        self.assertIsNone(fb.plant_touch_sound('enemy'))
        with self.assertRaises(ValueError):
            fb.plant_touch_sound('ship')

    def test_spectralid_declared_species(self):
        self.assertEqual(set(fb.SPECTRALID_DECLARED),
                         {'Tanpopo', 'Ooinu_l', 'Magaret'})
        for species in fb.SPECTRALID_DECLARED:
            self.assertTrue(fb.spectralid_reserved(species))
        self.assertFalse(fb.spectralid_reserved('Ooinu_s'))
        self.assertFalse(fb.spectralid_reserved('Clover'))

    def test_spectralid_spawn_sentinel(self):
        self.assertEqual(fb.SPECTRALID_PER_TOUCH, 5)
        self.assertEqual(fb.spectralid_spawn(species='Tanpopo', has_sentinel=True,
                                             first_touch=True), 5)
        self.assertEqual(fb.spectralid_spawn(species='Tanpopo', has_sentinel=True,
                                             first_touch=False), 0)
        self.assertEqual(fb.spectralid_spawn(species='Tanpopo', has_sentinel=False,
                                             first_touch=True), 0)
        # a non-declaring species can spawn but has no reserved slot
        self.assertEqual(fb.spectralid_spawn(species='Clover', has_sentinel=True,
                                             first_touch=True), 5)
        self.assertFalse(fb.spectralid_reserved('Clover'))
        with self.assertRaises(ValueError):
            fb.spectralid_spawn(species='Pelplant', has_sentinel=True, first_touch=True)

    def test_piklopedia_entries(self):
        self.assertEqual(len(fb.PIKLOPEDIA_ENTRIES), 11)
        self.assertEqual(sorted(fb.PIKLOPEDIA_ENTRIES.values()), list(range(59, 70)))
        self.assertEqual(fb.piklopedia_number('HikariKinoko'), 59)
        self.assertEqual(fb.piklopedia_number('Wakame_l'), 69)
        self.assertIsNone(fb.piklopedia_number('Ooinu_s'))
        self.assertIsNone(fb.piklopedia_number('Pom'))

    def test_has_no_info_folding(self):
        self.assertEqual(set(fb.HAS_NO_INFO),
                         {'Ooinu_s', 'Wakame_s', 'DaiodoGreen', 'Chiyogami',
                          'KareOoinu_s', 'KareOoinu_l'})
        self.assertEqual(fb.folded_into('Ooinu_s'), 'Ooinu_l')
        self.assertEqual(fb.folded_into('Wakame_s'), 'Wakame_l')
        self.assertEqual(fb.folded_into('DaiodoGreen'), 'DaiodoRed')
        self.assertEqual(fb.folded_into('KareOoinu_s'), 'Ooinu_l')
        self.assertEqual(fb.folded_into('KareOoinu_l'), 'Ooinu_l')
        self.assertIsNone(fb.folded_into('Chiyogami'))
        self.assertIsNone(fb.folded_into('Clover'))

    def test_plant_shared_facts(self):
        self.assertEqual(fb.PLANT_BASE, 'Plants')
        self.assertEqual(fb.PLANT_DISC_HEALTH['value'], 1100.0)
        self.assertFalse(fb.PLANT_DISC_HEALTH['read'])
        self.assertEqual(fb.PLANT_ANIM_COUNT, 1)
        self.assertFalse(fb.PLANT_HAS_FSM)
        self.assertTrue(fb.PLANT_INVULNERABLE)
        self.assertEqual(fb.PLANT_CAVE_ROSTER_CAP, 100)
        self.assertEqual(fb.PLANT_SURFACE_SOURCE, 'plantsgen.txt')
        self.assertEqual(fb.SPECTRALID_CHILD, 'ShijimiChou')


class TestReconstructedMarkers(unittest.TestCase):
    def test_markers_present(self):
        self.assertIn('plant_floor_offset', fb.RECONSTRUCTED)
        self.assertIn('brown_figwort_offset_assignment', fb.RECONSTRUCTED)
        self.assertTrue(getattr(fb.plant_floor_offset, 'reconstructed', False))

    def test_source_anchors_recorded(self):
        self.assertEqual(fb.PELPLANT_STATES_SOURCE,
                         'include/Game/Entities/Pelplant.h:37-50')
        self.assertEqual(fb.POM_STATES_SOURCE,
                         'include/Game/Entities/Pom.h:153-161')
        self.assertIn('Pom.cpp', fb.POM_SLOT['source'])
        self.assertEqual(fb.PELPLANT_PROPER_DISC['source'].split()[0],
                         'enemy/parm/enemyParms.szs')


if __name__ == '__main__':
    unittest.main()
