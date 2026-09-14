"""Lane 16 Frog/MaroFrog source combat-model tests (#167/#194/#201)."""
import pytest

from experimental import pikmin2_frog_behavior as frog


def test_retail_parameters_match_the_source_dump():
    assert frog.PARAMS['Frog']['health'] == 800.0
    assert frog.PARAMS['MaroFrog']['health'] == 1100.0
    assert frog.PARAMS['Frog']['attack_damage'] == 10.0
    assert frog.PARAMS['MaroFrog']['attack_damage'] == 20.0
    assert frog.PARAMS['Frog']['jump_fail'] == 0.2
    assert frog.PARAMS['MaroFrog']['jump_fail'] == 0.1
    assert frog.PARAMS['Frog']['attack_range'] == 200.0
    assert frog.PARAMS['MaroFrog']['attack_range'] == 250.0


def test_motion_mapping_and_states_are_the_source_set():
    assert dict(frog.MOTION_CLIPS)['Jump'] == 'type1'
    assert dict(frog.MOTION_CLIPS)['Fall'] == 'type2'
    assert dict(frog.MOTION_CLIPS)['Fail'] == 'damage'
    assert dict(frog.MOTION_CLIPS)['Carry'] == 'type5'
    assert set(frog.FSM_STATES) == {'Dead', 'Wait', 'Turn', 'Jump', 'JumpWait',
                                    'Fall', 'Attack', 'Fail', 'TurnToHome', 'GoHome'}


def test_jump_attack_uses_displacement_over_air_time_plus_jump_speed():
    result = frog.jump_attack('Frog', 150.0, 0.5)
    assert result['air_time'] == 1.0 and result['jump_speed'] == 320.0
    assert result['horizontal_speed'] == 150.0 and result['fails'] is False
    assert frog.jump_attack('Frog', 150.0, 0.05)['fails'] is True
    assert frog.jump_attack('MaroFrog', 100.0, 0.15)['fails'] is False
    assert frog.jump_attack('MaroFrog', 100.0, 0.05)['fails'] is True


def test_jump_inputs_are_validated():
    with pytest.raises(ValueError, match='Unknown frog species'):
        frog.jump_attack('Toady', 1.0, 0.5)
    with pytest.raises(ValueError, match='non-negative'):
        frog.jump_attack('Frog', -1.0, 0.5)
    with pytest.raises(ValueError, match=r'\[0, 1\)'):
        frog.jump_attack('Frog', 1.0, 1.0)


def test_landing_press_is_blocked_only_while_bittered():
    assert frog.landing_press('Frog', bittered=False) is True
    assert frog.landing_press('Frog', bittered=True) is False


def test_landing_press_victims_hits_every_grounded_victim_unless_bittered():
    pressed = frog.landing_press_victims(False, ['piki1', 'piki2'], ['navi0'])
    assert pressed['pressed'] == 3
    assert pressed['pressed_pikmin'] == ['piki1', 'piki2']
    assert pressed['pressed_navi'] == ['navi0']
    assert pressed['bittered'] is False
    blocked = frog.landing_press_victims(True, ['piki1', 'piki2'], ['navi0'])
    assert blocked['pressed'] == 0 and blocked['pressed_pikmin'] == [] and blocked['pressed_navi'] == []
    assert frog.landing_press_victims(False, [], [])['pressed'] == 0
    assert frog.landing_press_victims(False, None, None)['pressed'] == 0


def test_only_marofrog_retargets_living_captains():
    assert frog.retargets_captains('MaroFrog') is True
    assert frog.retargets_captains('Frog') is False


def test_corpse_contract_matches_source_carry_and_reward():
    assert frog.corpse('Frog')['pokos'] == 5
    assert frog.corpse('MaroFrog')['pokos'] == 7
    assert frog.corpse('Frog')['carry'] == (7, 14)
    assert frog.corpse('MaroFrog')['pickup_offset'] == (-0.6, 0.0, -34.0)


def test_carry_route_matches_source_transport_and_accepts_source_ids():
    route = frog.carry_route('Frog')
    assert route['species'] == 'Frog' and route['pokos'] == 5
    assert route['carry'] == (7, 14) and route['onion'] == (8, 8)
    assert route['pickup_radius'] == 22.0 and route['pickup_height'] == 14.0
    assert route['pickup_offset'] == (-27.3, 0.0, 12.3)
    assert frog.carry_route(1)['species'] == 'MaroFrog'
    assert frog.carry_route('MaroFrog')['pokos'] == 7
    with pytest.raises(ValueError, match='Unknown frog species'):
        frog.carry_route('Toady')


def test_validate_ready_accepts_source_health_and_rejects_p1_values():
    good = ('P2_FROG_READY species=Frog generator=201001 health=800.0 max_health=800.0 '
            'behavior=P1_proxy rewards=P1_unchanged\n'
            'P2_FROG_READY species=MaroFrog generator=201002 health=1100.0 max_health=1100.0 '
            'behavior=P1_proxy rewards=P1_unchanged\n')
    assert frog.validate_ready(good)['passed'] is True
    assert frog.validate_ready(good.replace('health=800.0', 'health=100.0'))['passed'] is False
    assert frog.validate_ready('P2_FROG_READY species=Frog generator=201001 health=800.0 '
                               'max_health=800.0 behavior=P1_proxy rewards=P1_unchanged\n')['passed'] is False
