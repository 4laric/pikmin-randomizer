"""Synthetic tests for experimental/pikmin2_elemental_behavior (#170, child #349).

All inputs are constructed in code; no ISO or native build is required. The
suite covers every lane-22 ID plus the immunity, theft/drop and Bomb
boundaries and the validation/error paths.
"""
import unittest

from experimental import pikmin2_elemental_behavior as eb


class TestRoster(unittest.TestCase):
    def test_every_id(self):
        self.assertEqual(eb.ENEMY_IDS, {
            'Hiba': 20, 'GasHiba': 21, 'ElecHiba': 22,
            'Tank': 24, 'Wtank': 25,
            'FireOtakara': 59, 'WaterOtakara': 60, 'GasOtakara': 61,
            'ElecOtakara': 62, 'BombOtakara': 93,
        })

    def test_classifications(self):
        for identity in eb.FIXED_HAZARD_IDS + eb.BLOWHOG_IDS + eb.DWEEVIL_IDS:
            self.assertIn(identity, eb.ENEMY_IDS)
        self.assertEqual(eb.classification('Hiba'), 'fixed_hazard')
        self.assertEqual(eb.classification('GasHiba'), 'fixed_hazard')
        self.assertEqual(eb.classification('ElecHiba'), 'fixed_hazard')
        self.assertEqual(eb.classification('Tank'), 'blowhog')
        self.assertEqual(eb.classification('Wtank'), 'blowhog')
        self.assertEqual(eb.classification('FireOtakara'), 'dweevil')
        self.assertEqual(eb.classification('BombOtakara'), 'dweevil')
        with self.assertRaises(ValueError):
            eb.classification('Unknown')

    def test_stimulus_for(self):
        self.assertEqual(eb.stimulus_for('Hiba'), 'InteractFire')
        self.assertEqual(eb.stimulus_for('GasHiba'), 'InteractGas')
        self.assertEqual(eb.stimulus_for('ElecHiba'), 'InteractDenki')
        self.assertEqual(eb.stimulus_for('Tank'), 'InteractFire')
        self.assertEqual(eb.stimulus_for('Wtank'), 'InteractBubble')
        self.assertEqual(eb.stimulus_for('FireOtakara'), 'InteractFire')
        self.assertEqual(eb.stimulus_for('WaterOtakara'), 'InteractBubble')
        self.assertEqual(eb.stimulus_for('GasOtakara'), 'InteractGas')
        self.assertEqual(eb.stimulus_for('ElecOtakara'), 'InteractDenki')
        self.assertIsNone(eb.stimulus_for('BombOtakara'))

    def test_fixed_hazard_classification_table(self):
        self.assertTrue(eb.is_fixed_hazard('Hiba'))
        self.assertTrue(eb.is_fixed_hazard('GasHiba'))
        self.assertTrue(eb.is_fixed_hazard('ElecHiba'))
        self.assertFalse(eb.is_fixed_hazard('Tank'))
        self.assertEqual(eb.FIXED_HAZARD_CLASSIFICATION['Hiba']['element'], 'fire')
        self.assertIsNone(eb.FIXED_HAZARD_CLASSIFICATION['Hiba']['linked_actor'])
        self.assertEqual(eb.FIXED_HAZARD_CLASSIFICATION['GasHiba']['linked_actor'],
                         'bridge_or_gate')
        self.assertEqual(eb.FIXED_HAZARD_CLASSIFICATION['ElecHiba']['linked_actor'],
                         'parent_child_wire_pair')
        for name in eb.FIXED_HAZARD_IDS:
            self.assertEqual(eb.FIXED_HAZARD_CLASSIFICATION[name]['classification'],
                             'fixed_hazard')


class TestImmunity(unittest.TestCase):
    def test_colour_exclusions(self):
        self.assertTrue(eb.pikmin_immune(stimulus='InteractFire', colour='Red'))
        self.assertFalse(eb.pikmin_immune(stimulus='InteractFire', colour='Blue'))
        self.assertTrue(eb.pikmin_immune(stimulus='InteractBubble', colour='Blue'))
        self.assertFalse(eb.pikmin_immune(stimulus='InteractBubble', colour='Red'))
        self.assertTrue(eb.pikmin_immune(stimulus='InteractGas', colour='White'))
        self.assertFalse(eb.pikmin_immune(stimulus='InteractGas', colour='Red'))
        self.assertTrue(eb.pikmin_immune(stimulus='InteractDenki', colour='Yellow'))
        self.assertFalse(eb.pikmin_immune(stimulus='InteractDenki', colour='Red'))

    def test_bulbmin_immune_to_all(self):
        for stimulus in eb.ELEMENT_IMMUNITY:
            self.assertTrue(eb.pikmin_immune(stimulus=stimulus, colour='Bulbmin'),
                            stimulus)

    def test_gas_extra_gate(self):
        self.assertFalse(eb.pikmin_immune(stimulus='InteractGas', colour='Red'))
        self.assertTrue(eb.pikmin_immune(stimulus='InteractGas', colour='Red',
                                         gas_invincible=True))

    def test_panic_subtypes(self):
        self.assertEqual(eb.panic_for('InteractFire'), 'Fire')
        self.assertEqual(eb.panic_for('InteractBubble'), 'Bubble')
        self.assertEqual(eb.panic_for('InteractGas'), 'Gas')
        self.assertEqual(eb.panic_for('InteractDenki'), 'DenkiDying')

    def test_receiver_accepts(self):
        self.assertEqual(eb.receiver_accepts(stimulus='InteractFire', colour='Blue'),
                         'accept')
        self.assertEqual(eb.receiver_accepts(stimulus='InteractFire', colour='Red'),
                         'reject')
        self.assertEqual(eb.receiver_accepts(stimulus='InteractFire', colour='Blue',
                                              invincible=True), 'reject')
        self.assertEqual(eb.receiver_accepts(stimulus='InteractGas', colour='Red',
                                              gas_invincible=True), 'reject')

    def test_immunity_validation(self):
        with self.assertRaises(ValueError):
            eb.pikmin_immune(stimulus='InteractPoison', colour='Red')
        with self.assertRaises(ValueError):
            eb.pikmin_immune(stimulus='InteractFire', colour='Orange')
        with self.assertRaises(ValueError):
            eb.panic_for('InteractPoison')
        with self.assertRaises(ValueError):
            eb.receiver_accepts(stimulus='InteractFire', colour='Red',
                                invincible='yes')

    def test_immunity_source_anchors(self):
        self.assertEqual(eb.ELEMENT_IMMUNITY['InteractFire']['source'],
                         'src/plugProjectKandoU/interactPiki.cpp:445')
        self.assertEqual(eb.ELEMENT_IMMUNITY['InteractDenki']['source'],
                         'src/plugProjectKandoU/interactPiki.cpp:334')
        self.assertEqual(eb.ELEMENT_IMMUNITY['InteractGas']['extra_gate'],
                         'gasInvicible')


class TestFixedHazards(unittest.TestCase):
    def test_states(self):
        self.assertEqual(eb.HAZARD_STATES['Hiba'], {'dead': 0, 'wait': 1, 'attack': 2})
        self.assertEqual(eb.HAZARD_STATES['GasHiba'], {'dead': 0, 'wait': 1, 'attack': 2})
        self.assertEqual(eb.HAZARD_STATES['ElecHiba'],
                         {'dead': 0, 'wait': 1, 'sign': 2, 'attack': 3})

    def test_header_vs_disc_timing(self):
        # The audit calls out the geyser timing differences; header defaults
        # and retail disc values must stay distinct.
        self.assertEqual(eb.HAZARD_TIMING_HEADER['Hiba']['wait'], 2.5)
        self.assertEqual(eb.HAZARD_TIMING_DISC['Hiba']['wait'], 3.0)
        self.assertEqual(eb.HAZARD_TIMING_DISC['GasHiba']['wait'], 0.0)
        self.assertEqual(eb.HAZARD_TIMING_DISC['GasHiba']['attack_start'], 0.6)
        self.assertEqual(eb.HAZARD_TIMING_DISC['ElecHiba']['wait'], 1.5)
        self.assertEqual(eb.HAZARD_TIMING_DISC['ElecHiba']['warning'], 1.5)
        self.assertEqual(eb.HAZARD_TIMING_DISC['Hiba']['stop'], 30.0)

    def test_hiba_activate(self):
        self.assertEqual(eb.hiba_activate(health=10.0, wait_elapsed=2.0), 'wait')
        self.assertEqual(eb.hiba_activate(health=10.0, wait_elapsed=3.0), 'attack')
        self.assertEqual(eb.hiba_activate(health=0.0, wait_elapsed=9.0), 'dead')
        # explicit header wait keeps it waiting at the disc threshold
        self.assertEqual(eb.hiba_activate(health=10.0, wait_elapsed=2.6,
                                          wait_time=2.5), 'attack')

    def test_gashiba_activate_zero_wait(self):
        self.assertEqual(eb.gashiba_activate(health=10.0, wait_elapsed=0.0), 'attack')
        self.assertEqual(eb.gashiba_activate(health=0.0, wait_elapsed=0.0), 'dead')

    def test_hazard_activate_validation(self):
        with self.assertRaises(ValueError):
            eb.hazard_activate(hazard='Tank', health=1.0, wait_elapsed=1.0)
        with self.assertRaises(ValueError):
            eb.hazard_activate(hazard='Nope', health=1.0, wait_elapsed=1.0)
        with self.assertRaises(ValueError):
            eb.hiba_activate(health=float('nan'), wait_elapsed=1.0)

    def test_hiba_emit(self):
        self.assertTrue(eb.hiba_emit(state='attack', health=10.0, active_elapsed=0.0))
        self.assertTrue(eb.hiba_emit(state='attack', health=10.0, active_elapsed=2.4))
        self.assertFalse(eb.hiba_emit(state='attack', health=10.0, active_elapsed=2.5))
        self.assertFalse(eb.hiba_emit(state='wait', health=10.0, active_elapsed=0.0))
        self.assertFalse(eb.hiba_emit(state='attack', health=0.0, active_elapsed=0.0))
        with self.assertRaises(ValueError):
            eb.hiba_emit(state='sign', health=1.0, active_elapsed=0.0)

    def test_gashiba_emit(self):
        # before attack start no emission
        self.assertFalse(eb.gashiba_emit(state='attack', attack_elapsed=0.5,
                                         active_elapsed=0.5))
        # after attack start it emits
        self.assertTrue(eb.gashiba_emit(state='attack', attack_elapsed=0.6,
                                        active_elapsed=0.6))
        # positive wait time makes the active-time condition finish it
        self.assertFalse(eb.gashiba_emit(state='attack', attack_elapsed=1.0,
                                         active_elapsed=3.0, wait_time=1.0))
        # retail disc wait time is 0.0, so time alone never finishes it
        self.assertTrue(eb.gashiba_emit(state='attack', attack_elapsed=1.0,
                                        active_elapsed=99.0))
        self.assertFalse(eb.gashiba_emit(state='wait', attack_elapsed=1.0,
                                         active_elapsed=99.0))

    def test_gashiba_linked_owner_reconstructed(self):
        self.assertTrue(getattr(eb.gashiba_linked_owner, 'reconstructed', False))
        self.assertEqual(eb.gashiba_linked_owner(bridge_linked=True, gate_linked=False),
                         'bridge')
        self.assertEqual(eb.gashiba_linked_owner(bridge_linked=False, gate_linked=True),
                         'gate')
        self.assertEqual(eb.gashiba_linked_owner(bridge_linked=True, gate_linked=True),
                         'bridge+gate')
        self.assertIsNone(eb.gashiba_linked_owner(bridge_linked=False, gate_linked=False))

    def test_elechiba_nodes(self):
        self.assertEqual(eb.elechiba_node_positions(center=100.0, separation=40.0),
                         (80.0, 120.0))
        with self.assertRaises(ValueError):
            eb.elechiba_node_positions(center=0.0, separation=-1.0)

    def test_elechiba_team_head_damage(self):
        self.assertEqual(eb.elechiba_team_head_damage(is_parent=True, invulnerable=False),
                         'route_to_head')
        self.assertEqual(eb.elechiba_team_head_damage(is_parent=False, invulnerable=False),
                         'route_to_head')
        self.assertEqual(eb.elechiba_team_head_damage(is_parent=True, invulnerable=True),
                         'reject')

    def test_elechiba_advance_chain(self):
        common = dict(health=10.0, wait_time=1.5, warning_time=1.5, active_time=2.5)
        self.assertEqual(eb.elechiba_advance(state='wait', elapsed=1.0, **common),
                         ('wait', False))
        self.assertEqual(eb.elechiba_advance(state='wait', elapsed=1.5, **common),
                         ('sign', False))
        self.assertEqual(eb.elechiba_advance(state='sign', elapsed=1.0, **common),
                         ('sign', False))
        self.assertEqual(eb.elechiba_advance(state='sign', elapsed=1.5, **common),
                         ('attack', True))
        self.assertEqual(eb.elechiba_advance(state='attack', elapsed=1.0, **common),
                         ('attack', True))
        self.assertEqual(eb.elechiba_advance(state='attack', elapsed=2.5, **common),
                         ('wait', False))
        self.assertEqual(eb.elechiba_advance(state='attack', elapsed=0.1,
                                             counter_done=True, **common),
                         ('wait', False))
        self.assertEqual(eb.elechiba_advance(state='attack', elapsed=0.0,
                                             **dict(common, health=0.0)),
                         ('dead', False))
        with self.assertRaises(ValueError):
            eb.elechiba_advance(state='flick', elapsed=0.0, **common)

    def test_elechiba_versus_reconstructed(self):
        self.assertTrue(getattr(eb.elechiba_versus_stimulus, 'reconstructed', False))
        self.assertEqual(eb.elechiba_versus_stimulus(attribute='neutral'),
                         'InteractDenki')
        self.assertEqual(eb.elechiba_versus_stimulus(attribute='red'), 'InteractFire')
        self.assertEqual(eb.elechiba_versus_stimulus(attribute='blue'),
                         'InteractBubble')
        with self.assertRaises(ValueError):
            eb.elechiba_versus_stimulus(attribute='green')


class TestBlowhogs(unittest.TestCase):
    def test_entry_and_stimulus(self):
        self.assertEqual(eb.blowhog_entry_state(), 'wait')
        self.assertEqual(eb.BLOWHOG_STIMULUS['Tank'], 'InteractFire')
        self.assertEqual(eb.BLOWHOG_STIMULUS['Wtank'], 'InteractBubble')
        self.assertEqual(eb.BLOWHOG_STATES['attack'], 5)
        self.assertEqual(eb.BLOWHOG_ATTACK_START_KEY, 2)
        self.assertEqual(eb.BLOWHOG_ATTACK_END_KEY, 7)
        self.assertEqual(eb.BLOWHOG_BLOW_TRACE_RADIUS, 2.5)
        self.assertTrue(eb.TANK_KILL_FINISHES_EFFECT)

    def test_attack_geometry(self):
        base = dict(lateral_distance=10.0, vertical_distance=10.0,
                    forward_distance=50.0, attack_radius=25.0, range_distance=100.0)
        self.assertEqual(eb.blowhog_attack(species='Tank', **base), 'InteractFire')
        self.assertEqual(eb.blowhog_attack(species='Wtank', **base), 'InteractBubble')
        self.assertIsNone(eb.blowhog_attack(species='Tank',
                                            **dict(base, lateral_distance=26.0)))
        self.assertIsNone(eb.blowhog_attack(species='Tank',
                                            **dict(base, vertical_distance=-26.0)))
        self.assertIsNone(eb.blowhog_attack(species='Tank',
                                            **dict(base, forward_distance=101.0)))
        self.assertIsNone(eb.blowhog_attack(species='Tank',
                                            **dict(base, forward_distance=-1.0)))
        self.assertIsNone(eb.blowhog_attack(species='Tank',
                                            **dict(base, wall_blocked=True)))

    def test_attack_validation(self):
        base = dict(lateral_distance=0.0, vertical_distance=0.0,
                    forward_distance=0.0, attack_radius=1.0, range_distance=1.0)
        with self.assertRaises(ValueError):
            eb.blowhog_attack(species='Hiba', **base)
        with self.assertRaises(ValueError):
            eb.blowhog_attack(species='Tank', **dict(base, attack_radius=-1.0))
        with self.assertRaises(ValueError):
            eb.blowhog_attack(species='Tank', **dict(base, forward_distance=float('inf')))

    def test_range_reconstructed(self):
        self.assertTrue(getattr(eb.blowhog_range, 'reconstructed', False))
        self.assertEqual(eb.blowhog_range(base_range=20.0, attack_timer=2.0,
                                          grow_rate=5.0), 30.0)
        self.assertEqual(eb.blowhog_range(base_range=20.0, attack_timer=2.0,
                                          grow_rate=5.0, trace_hit=True), 20.0)
        self.assertEqual(eb.blowhog_range(base_range=20.0, attack_timer=-3.0,
                                          grow_rate=5.0), 20.0)


class TestDweevils(unittest.TestCase):
    def test_states_and_stimulus(self):
        self.assertEqual(len(eb.DWEEVIL_STATES), 14)
        self.assertEqual(eb.DWEEVIL_STATES['take'], 5)
        self.assertEqual(eb.DWEEVIL_STATES['item_drop'], 10)
        self.assertEqual(eb.DWEEVIL_STATES['bomb_turn'], 13)
        self.assertEqual(eb.BOMB_CARRY_STATES, ('bomb_wait', 'bomb_move', 'bomb_turn'))
        self.assertEqual(eb.dweevil_stimulus('FireOtakara'), 'InteractFire')
        self.assertEqual(eb.dweevil_stimulus('WaterOtakara'), 'InteractBubble')
        self.assertEqual(eb.dweevil_stimulus('GasOtakara'), 'InteractGas')
        self.assertEqual(eb.dweevil_stimulus('ElecOtakara'), 'InteractDenki')
        self.assertIsNone(eb.dweevil_stimulus('BombOtakara'))
        with self.assertRaises(ValueError):
            eb.dweevil_stimulus('Tank')

    def test_theft_decision(self):
        eligible = dict(alive=True, pickable=True, captured=False,
                        within_territory=True)
        self.assertTrue(eb.dweevil_theft_decision(**eligible))
        self.assertFalse(eb.dweevil_theft_decision(**dict(eligible, alive=False)))
        self.assertFalse(eb.dweevil_theft_decision(**dict(eligible, pickable=False)))
        self.assertFalse(eb.dweevil_theft_decision(**dict(eligible, captured=True)))
        self.assertFalse(eb.dweevil_theft_decision(**dict(eligible, within_territory=False)))
        self.assertFalse(eb.dweevil_theft_decision(**dict(eligible, carrying=True)))

    def test_capture_health(self):
        self.assertEqual(eb.dweevil_capture_health(otakara_life=80.0), 80.0)
        with self.assertRaises(ValueError):
            eb.dweevil_capture_health(otakara_life=0.0)
        with self.assertRaises(ValueError):
            eb.dweevil_capture_health(otakara_life=-5.0)

    def test_damage_route(self):
        self.assertEqual(eb.dweevil_damage_route(carrying=True), 'treasure')
        self.assertEqual(eb.dweevil_damage_route(carrying=False), 'dweevil')

    def test_drop_exactly_once(self):
        for reason in ('death', 'stone', 'earthquake', 'interruption'):
            self.assertEqual(eb.dweevil_drop(carrying=True, reason=reason),
                             (True, False))
        # a second drop for the same capture must not refund twice
        self.assertEqual(eb.dweevil_drop(carrying=True, reason='death',
                                         already_dropped=True), (False, False))
        # nothing to drop
        self.assertEqual(eb.dweevil_drop(carrying=False, reason='death'),
                         (False, False))
        with self.assertRaises(ValueError):
            eb.dweevil_drop(carrying=True, reason='nibble')
        with self.assertRaises(ValueError):
            eb.dweevil_drop(carrying='yes', reason='death')

    def test_bomb_payload(self):
        base = dict(payload_present=True, bittered=False, earthquake=False)
        self.assertEqual(eb.bomb_otakara_payload(**base), 'chase_payload')
        self.assertEqual(eb.bomb_otakara_payload(**dict(base, chase_elapsed=1.5)),
                         'force_bomb')
        self.assertEqual(eb.bomb_otakara_payload(**dict(base, chase_elapsed=1.4)),
                         'chase_payload')
        self.assertEqual(eb.bomb_otakara_payload(**dict(base, bittered=True)),
                         'damage_payload')
        self.assertEqual(eb.bomb_otakara_payload(**dict(base, earthquake=True)),
                         'force_bomb')
        self.assertEqual(eb.bomb_otakara_payload(**dict(base, payload_present=False)),
                         'kill_carrier')

    def test_bomb_boundary(self):
        self.assertTrue(getattr(eb.bomb_otakara_payload, 'reconstructed', False))
        self.assertTrue(eb.BOMB_OTAKARA_CONSUMES_SHARED_BLAST)
        self.assertEqual(eb.BOMB_FORCE_DELAY_SECONDS, 1.5)
        with self.assertRaises(ValueError):
            eb.bomb_otakara_payload(payload_present=1, bittered=False,
                                    earthquake=False)
        with self.assertRaises(ValueError):
            eb.bomb_otakara_payload(payload_present=True, bittered=False,
                                    earthquake=False, chase_elapsed=float('nan'))


class TestMarkers(unittest.TestCase):
    def test_reconstructed_membership(self):
        self.assertIn('gashiba_linked_owner', eb.RECONSTRUCTED)
        self.assertIn('elechiba_versus_stimulus', eb.RECONSTRUCTED)
        self.assertIn('blowhog_range', eb.RECONSTRUCTED)
        self.assertIn('bomb_otakara_payload', eb.RECONSTRUCTED)

    def test_unknowns_documented(self):
        self.assertTrue(eb.UNKNOWNS)
        self.assertTrue(any('reload' in item for item in eb.UNKNOWNS))
        self.assertTrue(any('Bomb explosion' in item for item in eb.UNKNOWNS))


if __name__ == '__main__':
    unittest.main()
